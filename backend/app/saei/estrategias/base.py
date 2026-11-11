# Base das estratégias do SAEI (V2).
#
# O que todas compartilham é exatamente o que o núcleo exige: o prompt tem que
# conter o documento-alvo, a base de diretrizes, o registro do sujeito e as
# regras do par (análise, destinatário). O contrato de âncoras é único, para que
# o verificador do PF3 valha para toda análise sem caso especial.

from __future__ import annotations

import json

from app.framework import PacoteAnalise, Prompt
from app.framework.estrategias import BaseEstrategia

BLOCO_ANCORAGEM = """--- ANCORAGEM OBRIGATÓRIA (verificada automaticamente pelo sistema) ---
Todo campo ancorado é um objeto com "texto" (a afirmação) e "ancora".
A âncora tem sempre esta forma:
  {"documento": "<título exato do documento citado>", "pagina": <inteiro do marcador [p. N]>, "trecho": "<cópia LITERAL do original>"}
Regras:
1. O "trecho" é conferido contra o documento original: copie sem parafrasear, sem traduzir e sem corrigir.
2. Item cuja âncora não exista no texto invalida a resposta inteira.
3. Não escreva URLs, links, artigos de lei nem números de processo. Se precisar de material externo, use apenas a lista de termos de busca."""


class EstrategiaSAEI(BaseEstrategia):
    """Monta o prompt comum e deixa só a instrução focal e o contrato para a filha."""

    papel_no_prompt = "especialista em pedagogia inclusiva e Desenho Universal de Aprendizagem"
    instrucao_focal = ""
    contrato_de_resposta = ""

    def construir(self, pacote: PacoteAnalise) -> Prompt:
        return Prompt(texto=self._montar(pacote), formato="json_object")

    def _montar(self, pacote: PacoteAnalise) -> str:
        rotulo_diretrizes = getattr(pacote.diretrizes, "rotulo", "diretrizes do domínio")
        partes = [
            f"Você é {self.papel_no_prompt}.",
            "--- REGRAS DO DOMÍNIO (não negociáveis) ---\n" + self._regras(pacote),
            f"--- BASE DE DIRETRIZES INSTITUCIONAIS: {rotulo_diretrizes} ---\n"
            + pacote.diretrizes.para_prompt(),
            "--- REGISTRO DO SUJEITO / CONTRAPARTE ---\n" + self._registro(pacote),
            "--- DOCUMENTOS DE CONTEXTO DO SUJEITO ---\n" + self._documentos_de_contexto(pacote),
            "--- DOCUMENTO PRINCIPAL (origem das âncoras) ---\n"
            + pacote.alvo.texto_ancoravel(),
            "--- INSTRUÇÃO FOCAL ---\n" + self.instrucao_focal,
            BLOCO_ANCORAGEM,
            "--- CONTRATO DE RESPOSTA (JSON puro, sem markdown) ---\n"
            + self.contrato_de_resposta,
        ]
        return "\n\n".join(partes)

    def _regras(self, pacote: PacoteAnalise) -> str:
        if not pacote.guardrails:
            return "Nenhuma regra adicional para este par (análise, destinatário)."
        return "\n".join(f"- {regra.enunciado}" for regra in pacote.guardrails)

    def _registro(self, pacote: PacoteAnalise) -> str:
        registro = {
            chave: valor
            for chave, valor in pacote.contexto.registro.items()
            if valor not in (None, "", [], {})
        }
        if not registro:
            registro = {"sujeito": "não informado"}
        return json.dumps(registro, ensure_ascii=False, default=str)

    def _documentos_de_contexto(self, pacote: PacoteAnalise) -> str:
        if not pacote.documentos_de_contexto:
            return "Nenhum documento de contexto anexado."
        return "\n\n".join(
            f"[{documento.rotulo}]\n{documento.texto_completo}"
            for documento in pacote.documentos_de_contexto
        )
