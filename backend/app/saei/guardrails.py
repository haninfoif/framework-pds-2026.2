# V5 no SAEI: as proibições que não são adivinháveis.
#
# Cada regra entra no prompt como instrução explícita. Quem pode ser verificado
# vira `verificacao` e é executado pelo núcleo sobre a saída já validada — a
# regra deixa de depender da boa vontade do modelo.

from __future__ import annotations

from app.framework import PapelAcesso, Regra, TipoAnalise
from app.saei.analises import (
    ANALISE_ACESSIBILIDADE,
    ANALISE_ADAPTACAO,
    ANALISE_RESUMO,
    ANALISE_TUTORIA,
)

REGRAS_POR_ANALISE: dict[str, tuple[Regra, ...]] = {
    ANALISE_RESUMO.chave: (
        Regra(
            "RESUMO_SEM_INFERENCIA",
            "Não deduza diagnóstico, prognóstico ou recomendação que não esteja "
            "escrito no documento.",
        ),
        Regra(
            "RESUMO_SEM_INVENCAO",
            "Não invente prazos, números de processo, artigos de lei, nomes ou datas.",
        ),
    ),
    ANALISE_TUTORIA.chave: (
        Regra(
            "TUTOR_NAO_ENTREGA_RESPOSTA",
            "Não entregue a resposta pronta da atividade: decomponha o raciocínio "
            "em etapas que o estudante consiga seguir sozinho.",
        ),
        Regra(
            "TUTOR_SEM_ROTULO",
            "Não rotule o estudante pelo diagnóstico nem cite o laudo de forma "
            "estigmatizante.",
        ),
    ),
    ANALISE_ADAPTACAO.chave: (
        Regra(
            "ADAPTACAO_PRESERVA_CURRICULO",
            "Preserve os objetos de conhecimento e a BNCC: altere o formato de "
            "entrega e de avaliação, nunca o currículo.",
        ),
        Regra(
            "ADAPTACAO_SO_DO_TEXTO",
            "Não crie aulas, exercícios ou dinâmicas que não estejam expressamente "
            "no material original.",
        ),
    ),
    ANALISE_ACESSIBILIDADE.chave: (
        Regra(
            "DUA_SO_DO_TEXTO",
            "Avalie apenas o texto fornecido; não suponha deficiências ou laudos.",
        ),
    ),
}

_REGRA_GERAL = Regra(
    "GERAL_SO_DO_DOCUMENTO",
    "Todo item deve ser sustentado por um trecho literal do documento analisado.",
)


class GuardrailsSAEI:
    def regras(self, analise: TipoAnalise, papel: PapelAcesso) -> list[Regra]:
        return list(REGRAS_POR_ANALISE.get(analise.chave, (_REGRA_GERAL,)))
