# Provedor de IA do SAEI (F2).
#
# Depois da extração do framework, este arquivo é só o canal de inferência: ele
# recebe um Prompt pronto e devolve texto. Prompt, schema, âncora e projeção não
# moram mais aqui — é justamente isso que permite trocar de provedor sem tocar
# em nenhum arquivo do núcleo.

import os

from groq import Groq

from app.framework import Prompt

MODELO_PADRAO = "qwen/qwen3.8-27b"


class GroqClient:
    nome: str

    def __init__(self, modelo: str | None = None):
        # GROQ_API_KEY é a primária e GROQ_API_KEY_B é a reserva ("plano B"): se a primária falhar
        # na hora da requisição, o _enviar_prompt tenta a reserva antes de devolver erro ao chamador.
        # As chaves são pegas lá do ambiente do docker, estão localizadas em docker-compose.yml
        chaves = [k for k in (os.getenv("GROQ_API_KEY"), os.getenv("GROQ_API_KEY_B")) if k]
        # dict.fromkeys preserva a ordem e evita tentar duas vezes a mesma chave duplicada
        self._api_keys = list(dict.fromkeys(chaves))
        self._clients = {}
        # F2: o modelo deixou de estar fixo no método; pode ser trocado por ambiente.
        self._modelo = modelo or os.getenv("GROQ_MODEL") or MODELO_PADRAO
        self.nome = f"groq/{self._modelo}"

    def _get_client(self, api_key: str) -> Groq:
        """Inicializa e devolve o cliente Groq de uma chave sob demanda (Lazy Loading, um por chave)."""
        # Cria a conexão com a SDK da Groq apenas na primeira utilização e reutiliza nas chamadas seguintes.
        client = self._clients.get(api_key)
        if not client:
            client = Groq(api_key=api_key)
            self._clients[api_key] = client
        return client

    def gerar(self, prompt: Prompt) -> str:
        """Contrato do núcleo: recebe o prompt da estratégia e devolve o texto do modelo."""
        return self._enviar_prompt(
            prompt.texto,
            response_format=prompt.formato,
            max_tokens=prompt.max_tokens,
        )

    def _enviar_prompt(
        self,
        prompt: str,
        response_format: str = "json_object",
        max_tokens: int | None = None
    ) -> str:
        """
        max_tokens é opcional, visto que o termômetro de acessibilidade limita a saída
        e as outras análises não.
        """
        # Sem nenhuma chave configurada não há o que tentar: avisa na hora (como antes).
        if not self._api_keys:
            raise RuntimeError("GROQ_API_KEY não configurada no ambiente.")

        # Parâmetros base da inferência: saída estrita no formato especificado (JSON)
        parametros = {
            "response_format": {"type": response_format},
        }

        # Limite de tokens aplicado apenas quando solicitado explicitamente pelo caso de uso
        if max_tokens is not None:
            parametros["max_tokens"] = max_tokens

        # Tenta cada chave em ordem (primária e depois a reserva). Só devolve erro
        # quando TODAS as chaves configuradas falharem.
        ultimo_erro = None
        for api_key in self._api_keys:
            try:
                # Obtém a conexão ativa com a Groq para esta chave
                client = self._get_client(api_key)

                # Dispara a requisição de inferência
                chat_completion = client.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    # Modelo de alto desempenho para seguir contratos e estruturas de dados rígidas
                    model=self._modelo,
                    **parametros
                )

                # Retorna apenas o corpo textual gerado pelo modelo
                return chat_completion.choices[0].message.content

            except Exception as e:
                # Captura falhas de conexão, limites de cota, chave inválida ou indisponibilidade da API:
                # anota o erro e passa para a próxima chave (plano B) antes de desistir.
                ultimo_erro = e
                continue

        # Todas as chaves falharam: encapsula o último erro para as rotas
        raise RuntimeError(f"Falha na comunicação com a API da IA: {str(ultimo_erro)}")
