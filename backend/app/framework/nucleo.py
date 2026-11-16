# PF1 — orquestrador da análise multi-fonte.
#
# Este é o único lugar em que o ciclo existe. A aplicação chama `executar` uma
# vez e fornece os cinco slots; o núcleo decide a ordem, aplica o portão antes de
# ler conteúdo, valida a saída, confere as âncoras, resolve evidência, projeta
# por audiência, anexa o limite de uso e registra a execução.
#
# A ordem abaixo é fixa e não reordenável pela instância.

from __future__ import annotations

import time
from typing import Any, Sequence

from pydantic import BaseModel, ValidationError

from .contrato import (
    Acao,
    Contexto,
    ContextoRef,
    DocumentoNormalizado,
    DocumentoRef,
    EventoExecucao,
    PacoteAnalise,
    PapelAcesso,
    ResultadoAnalise,
    ResultadoNucleo,
    SchemaInterno,
    TipoAnalise,
)
from .erros import (
    EntradaInvalidaError,
    FalhaProvedorError,
    GuardrailVioladoError,
    InstanciacaoIncompletaError,
    SaidaForaDeContratoError,
)
from .estrategias import BaseEstrategia, Prompt, RegistroEstrategias
from .evidencia import Evidencia, ResolvedorNulo, SaneadorVozExterna
from .normalizacao import Normalizador, VerificadorAncoras, truncar_documento
from .portao import Portao
from .projecao import RegistroProjecoes
from .protocolos import (
    ContextoProvider,
    Guardrails,
    ProvedorIA,
)
from .registro import ConfiguracaoNucleo, RegistradorLog


class NucleoAnalise:
    """
    O núcleo de análise documental ancorada e com audiência.

    A instância fornece tudo o que é do domínio; o núcleo fornece o ciclo. Se um
    slot obrigatório estiver ausente, a construção falha agora — não no meio de
    uma requisição de usuário.
    """

    def __init__(
        self,
        *,
        nome: str,
        contexto: ContextoProvider,
        politica: Any,
        estrategias: RegistroEstrategias,
        guardrails: Guardrails,
        provedor: ProvedorIA,
        projecoes: RegistroProjecoes,
        diretrizes: Any,
        normalizador: Normalizador,
        resolvedor_evidencia: Any | None = None,
        registrador: Any | None = None,
        config: ConfiguracaoNucleo | None = None,
        verificador_ancoras: VerificadorAncoras | None = None,
        saneador_voz_externa: SaneadorVozExterna | None = None,
    ) -> None:
        self._nome = nome
        self._contexto = self._exigir(contexto, "ContextoProvider (V1)")
        self._politica_dependencia = self._exigir(politica, "Politica (V3)")
        self._estrategias = self._exigir(estrategias, "RegistroEstrategias (V2)")
        self._guardrails = self._exigir(guardrails, "Guardrails (V5)")
        self._provedor = self._exigir(provedor, "ProvedorIA (F2)")
        self._projecoes = self._exigir(projecoes, "RegistroProjecoes (V4)")
        self._diretrizes = self._exigir(diretrizes, "base de diretrizes (F4)")
        self._normalizador = self._exigir(normalizador, "Normalizador (PF3)")
        self._resolvedor = resolvedor_evidencia or ResolvedorNulo()
        self._registrador = registrador or RegistradorLog()
        self._config = config or ConfiguracaoNucleo()

        if not hasattr(self._provedor, "gerar"):
            raise InstanciacaoIncompletaError(
                "O provedor de IA não implementa gerar(prompt) -> str."
            )
        if not (
            hasattr(self._diretrizes, "obter")
            or hasattr(self._diretrizes, "para_prompt")
            or callable(self._diretrizes)
        ):
            raise InstanciacaoIncompletaError(
                "A base de diretrizes precisa ser um provedor com obter(contexto), "
                "uma base com para_prompt() ou um chamável."
            )

        # Verificação de instanciação: estratégia que ignora a base de diretrizes
        # ou o documento-alvo derruba o núcleo aqui.
        self._estrategias.validar()
        self._projecoes.validar(self._estrategias.analises())

        self._verificador = verificador_ancoras or VerificadorAncoras(
            self._config.cobertura_ancora
        )
        self._saneador = saneador_voz_externa or SaneadorVozExterna()
        self._portao = Portao(self._politica_dependencia, self._projecoes)

    # --- contrato público -----------------------------------------------------

    def executar(
        self,
        contexto: ContextoRef,
        documentos: Sequence[DocumentoRef],
        analise: TipoAnalise,
        destinatario: PapelAcesso,
    ) -> ResultadoAnalise:
        """
        Executa o ciclo uma vez. É a única porta de entrada da análise.
        """
        if not isinstance(contexto, ContextoRef):
            raise EntradaInvalidaError("executar exige um ContextoRef (V1).")
        if not isinstance(analise, TipoAnalise):
            raise EntradaInvalidaError("executar exige um TipoAnalise (V2).")
        if not isinstance(destinatario, PapelAcesso):
            raise EntradaInvalidaError("executar exige um PapelAcesso (PF2).")
        refs = list(documentos)
        if not refs:
            raise EntradaInvalidaError(
                "Nenhuma análise é feita sobre uma fonte só: envie ao menos um documento."
            )

        inicio = time.perf_counter()
        estrategia: BaseEstrategia | None = None
        quantidade_ancoras = 0
        evidencias: list[Evidencia] = []

        try:
            # 1. resolve o contexto (V1)
            ctx = self._contexto.resolver(contexto)

            # 2. autoriza (PF2) — antes de qualquer leitura de conteúdo
            self._portao.exigir(ctx, Acao("analisar", analise.chave))
            self._portao.exigir(ctx, Acao("projetar", destinatario.nome))

            # 3. normaliza os N documentos (PF3)
            limites = self._config.limites_de(analise.chave)
            entradas = [
                self._normalizador.normalizar(ref, limites.limite_caracteres_fonte)
                for ref in refs
            ]
            alvo = entradas[0]

            # 4. monta o pacote de três fontes
            documentos_de_contexto: list[DocumentoNormalizado] = []
            if limites.incluir_documentos_de_contexto:
                documentos_de_contexto = self._documentos_de_contexto(
                    ctx, entrada_ids=refs
                )
                if limites.limite_caracteres_contexto:
                    documentos_de_contexto = [
                        truncar_documento(doc, limites.limite_caracteres_contexto)
                        for doc in documentos_de_contexto
                    ]

            pacote = PacoteAnalise(
                contexto=ctx,
                alvo=alvo,
                documentos_entrada=entradas,
                documentos_de_contexto=documentos_de_contexto,
                diretrizes=self._obter_diretrizes(ctx),
                guardrails=list(self._guardrails.regras(analise, destinatario)),
                parametros=dict(analise.parametros),
            )

            # 5. seleciona a estratégia do par (tipo de documento, análise)
            estrategia = self._estrategias.selecionar(analise.chave, alvo.tipo_documento)

            # 6. chama o provedor de IA (F2)
            prompt = self._aplicar_limite_de_saida(estrategia.construir(pacote), limites)
            bruto = self._gerar(prompt, estrategia)

            # 7. valida contra o schema (V4)
            dados = self._validar(estrategia, bruto)

            # 8. verifica as âncoras (PF3)
            if self._config.exigir_ancoras:
                quantidade_ancoras = self._verificador.verificar(
                    dados,
                    pacote.documentos,
                    estrategia.identificador,
                    pacote.alvo.rotulo,
                )
            else:  # pragma: no cover - configuração explícita de auditoria
                quantidade_ancoras = len(dados.ancoras(pacote.alvo.rotulo))

            # 9. evidência externa resolvida (F6/PF4) + guardrails verificáveis
            self._saneador.verificar(dados, pacote)
            self._executar_guardrails(pacote, dados)
            evidencias = self._resolver_evidencia(estrategia, dados, pacote)

            # 10. projeta por destinatário (PF2)
            limite_de_uso = self._config.limite_de_uso(analise.chave)
            entrada_projecao = ResultadoNucleo(
                analise=analise,
                papel=destinatario,
                contexto=ctx,
                dados=dados,
                evidencias=evidencias,
                limite_uso=limite_de_uso,
                documentos=pacote.documentos,
            )
            dados_projetados = self._portao.projetar(
                analise.chave, destinatario, entrada_projecao
            )

            # 11 e 12. limite de uso anexado e execução registrada (F9)
            evento = self._evento(
                analise=analise,
                papel=destinatario,
                ctx=ctx,
                refs=refs,
                estrategia=estrategia,
                inicio=inicio,
                ancoras=quantidade_ancoras,
                evidencias=evidencias,
                sucesso=True,
                limite_de_uso=limite_de_uso,
            )
            self._registrar(evento)

            return ResultadoAnalise(
                analise=analise,
                papel=destinatario,
                dados=dados_projetados,
                limite_uso=limite_de_uso,
                execucao=evento,
            )

        except Exception as exc:  # noqa: BLE001 - registra e devolve o erro original
            evento = self._evento(
                analise=analise,
                papel=destinatario,
                ctx=locals().get("ctx"),
                refs=refs,
                estrategia=estrategia,
                inicio=inicio,
                ancoras=quantidade_ancoras,
                evidencias=evidencias,
                sucesso=False,
                limite_de_uso=self._config.aviso_padrao,
                erro=f"{type(exc).__name__}: {exc}",
            )
            self._registrar(evento)
            raise

    # --- etapas internas ------------------------------------------------------

    def _documentos_de_contexto(
        self,
        contexto: Contexto,
        entrada_ids: Sequence[DocumentoRef],
    ) -> list[DocumentoNormalizado]:
        documentos = list(self._contexto.carregar_documentos_de_contexto(contexto))
        ids_de_entrada = {str(ref.identificador) for ref in entrada_ids}
        # O documento-alvo não se repete como documento de contexto.
        return [
            doc for doc in documentos if str(doc.identificador) not in ids_de_entrada
        ]

    def _obter_diretrizes(self, contexto: Contexto) -> Any:
        fonte = self._diretrizes
        if hasattr(fonte, "obter"):
            diretrizes = fonte.obter(contexto)
        elif hasattr(fonte, "para_prompt"):
            diretrizes = fonte
        else:
            diretrizes = fonte(contexto)
        if not hasattr(diretrizes, "para_prompt"):
            raise InstanciacaoIncompletaError(
                "A base de diretrizes devolvida não implementa para_prompt()."
            )
        return diretrizes

    def _aplicar_limite_de_saida(
        self, prompt: Prompt, limites: Any
    ) -> Prompt:
        if prompt.max_tokens is None and limites.max_tokens is not None:
            return Prompt(
                texto=prompt.texto, formato=prompt.formato, max_tokens=limites.max_tokens
            )
        return prompt

    def _gerar(self, prompt: Prompt, estrategia: BaseEstrategia) -> str:
        try:
            bruto = self._provedor.gerar(prompt)
        except Exception as exc:  # noqa: BLE001 - provedor é fronteira externa
            if isinstance(exc, (FalhaProvedorError, InstanciacaoIncompletaError)):
                raise
            raise FalhaProvedorError(
                f"Falha na comunicação com o provedor de IA: {exc}"
            ) from exc
        if not isinstance(bruto, str) or not bruto.strip():
            raise FalhaProvedorError(
                f"O provedor '{getattr(self._provedor, 'nome', 'desconhecido')}' "
                f"devolveu resposta vazia para a estratégia '{estrategia.identificador}'."
            )
        return bruto

    def _validar(self, estrategia: BaseEstrategia, bruto: str) -> SchemaInterno:
        schema = estrategia.schema_interno
        if schema is None:  # pragma: no cover - barrado na instanciação
            raise InstanciacaoIncompletaError(
                f"A estratégia '{estrategia.identificador}' não declara schema interno."
            )
        try:
            return schema.model_validate_json(bruto)
        except ValidationError as exc:
            raise SaidaForaDeContratoError(
                "A saída do modelo não respeita o schema interno da análise "
                f"'{estrategia.identificador}': {exc.errors()[0].get('msg', exc)} "
                f"no campo '{'.'.join(str(p) for p in exc.errors()[0].get('loc', ()))}'."
            ) from exc
        except ValueError as exc:
            raise SaidaForaDeContratoError(
                "A saída do modelo não é um JSON válido para a análise "
                f"'{estrategia.identificador}': {exc}"
            ) from exc

    def _executar_guardrails(self, pacote: PacoteAnalise, dados: SchemaInterno) -> None:
        for regra in pacote.guardrails:
            if regra.verificacao is None:
                continue
            try:
                regra.verificacao(dados)
            except GuardrailVioladoError:
                raise
            except Exception as exc:  # noqa: BLE001 - normaliza o erro da regra
                raise GuardrailVioladoError(
                    f"Guardrail '{regra.identificador}' recusou a saída: {exc}"
                ) from exc

    def _resolver_evidencia(
        self,
        estrategia: BaseEstrategia,
        dados: SchemaInterno,
        pacote: PacoteAnalise,
    ) -> list[Evidencia]:
        if not self._config.resolver_evidencia:
            return []
        if not estrategia.permite_evidencia_externa:
            return []
        termos = [t.strip() for t in dados.termos_de_busca() if isinstance(t, str) and t.strip()]
        if not termos:
            return []

        brutas = self._resolvedor.resolver(termos, pacote.contexto, pacote)
        evidencias: list[Evidencia] = []
        for item in brutas or []:
            if isinstance(item, Evidencia) and item.url.lower().startswith(("http://", "https://")):
                evidencias.append(item)
        return evidencias

    def _evento(
        self,
        *,
        analise: TipoAnalise,
        papel: PapelAcesso,
        ctx: Contexto | None,
        refs: Sequence[DocumentoRef],
        estrategia: BaseEstrategia | None,
        inicio: float,
        ancoras: int,
        evidencias: Sequence[Evidencia],
        sucesso: bool,
        limite_de_uso: str,
        erro: str | None = None,
    ) -> EventoExecucao:
        return EventoExecucao(
            analise=analise.chave,
            papel=papel.nome,
            contexto=ctx.rotulo if ctx is not None else str(refs[0].identificador),
            documentos=tuple(str(ref.identificador) for ref in refs),
            estrategia=estrategia.identificador if estrategia is not None else "-",
            provedor=str(getattr(self._provedor, "nome", type(self._provedor).__name__)),
            duracao_ms=int((time.perf_counter() - inicio) * 1000),
            ancoras=ancoras,
            evidencias=len(evidencias),
            sucesso=sucesso,
            limite_uso=limite_de_uso,
            erro=erro,
        )

    def _registrar(self, evento: EventoExecucao) -> None:
        try:
            self._registrador.registrar(evento)
        except Exception:  # noqa: BLE001 - auditoria não pode derrubar a entrega
            pass

    @staticmethod
    def _exigir(valor: Any, rotulo: str) -> Any:
        if valor is None:
            raise InstanciacaoIncompletaError(
                f"Slot obrigatório ausente: {rotulo}. O núcleo não inicia incompleto."
            )
        return valor
