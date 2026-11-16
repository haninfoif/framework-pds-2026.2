# Schemas internos do SAEI (V4).
#
# É aqui que a âncora deixa de ser texto dentro de uma string e vira campo
# estruturado: cada item ancorado carrega documento, página e trecho literal. O
# núcleo percorre `ancoras()` sem conhecer pedagogia; a projeção depois devolve
# exatamente o formato que o front-end já consome.

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.framework import Ancora, SchemaInterno


class TrechoCitado(BaseModel):
    """Âncora como o modelo a devolve: título (opcional), página e trecho."""

    documento: str | None = None
    pagina: int = Field(ge=1, description="Número do marcador [p. N] do original")
    trecho: str = Field(
        min_length=3, description="Cópia literal de um trecho da página"
    )

    def para_ancora(self, documento_padrao: str = "") -> Ancora:
        return Ancora(
            documento=(self.documento or documento_padrao or "documento"),
            pagina=int(self.pagina),
            trecho=self.trecho,
        )


class ItemAncorado(BaseModel):
    """Citação direta: afirmação + prova de origem. Sem âncora não passa."""

    texto: str = Field(min_length=1)
    ancora: TrechoCitado


class ItemDerivado(BaseModel):
    """
    Síntese, recomendação ou orientação — não é cópia do documento.

    Não carrega âncora de propósito: conferir citação é conferir o que veio do
    original, não o que o modelo concluiu a partir dele. Por isso não entra em
    `ancoras()` e o verificador do PF3 não tem o que reprovar aqui.
    """

    texto: str = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def _aceitar_texto_simples(cls, valor):
        """O modelo pode devolver só a string; normalizamos para {"texto": ...}."""
        if isinstance(valor, str):
            return {"texto": valor}
        return valor


class MudancaAncorada(BaseModel):
    """Mudança de adaptação: seção do original, ação e a âncora que a sustenta."""

    secao: str = Field(min_length=1)
    acao: str = Field(min_length=1)
    ancora: TrechoCitado


def _ancoras(itens: list, documento_padrao: str) -> list[Ancora]:
    return [item.ancora.para_ancora(documento_padrao) for item in itens]


# --- RESUMO ------------------------------------------------------------------


class ResumoInterno(SchemaInterno):
    """
    Resumo: só `pontos_chave` é citação direta e por isso carrega âncora.

    `resumo_geral` sintetiza e `proximos_passos_ou_recomendacoes` orienta;
    nenhum dos dois tem origem literal no documento. No laudo, por exemplo, a
    frase "Nenhuma recomendação médica explícita no laudo" é uma declaração de
    ausência — exigir âncora dela reprovaria a análise por construção.
    """

    titulo_documento: str
    resumo_geral: ItemDerivado
    pontos_chave: list[ItemAncorado] = Field(min_length=1)
    proximos_passos_ou_recomendacoes: ItemDerivado
    termos_busca: list[str] = Field(default_factory=list)

    def ancoras(self, documento_padrao: str = "") -> list[Ancora]:
        return _ancoras(self.pontos_chave, documento_padrao)

    def termos_de_busca(self) -> list[str]:
        return list(self.termos_busca)


class ResumoLaudoInterno(ResumoInterno):
    """
    Resumo de laudo médico.

    O laudo não gera busca externa: qualquer termo devolvido é descartado pelo
    schema, não pelo prompt. É a versão verificável da regra que antes existia só
    como instrução ("retorne SEMPRE uma lista vazia").
    """

    @model_validator(mode="after")
    def _sem_busca_externa(self) -> "ResumoLaudoInterno":
        if self.termos_busca:
            self.termos_busca = []
        return self


# --- ADAPTAÇÃO ---------------------------------------------------------------


class AdaptacaoInterna(SchemaInterno):
    # A mudança cita a seção do original: é citação. A justificativa argumenta e
    # as dicas orientam — campos derivados, sem âncora.
    mudancas_sugeridas: list[MudancaAncorada] = Field(min_length=1)
    justificativa_inclusiva: ItemDerivado
    dicas_de_abordagem: list[ItemDerivado] = Field(min_length=1)

    def ancoras(self, documento_padrao: str = "") -> list[Ancora]:
        return [
            mudanca.ancora.para_ancora(documento_padrao)
            for mudanca in self.mudancas_sugeridas
        ]


# --- TUTORIA -----------------------------------------------------------------


class TutorInterno(SchemaInterno):
    """
    Tutoria: explicação e etapas são mediação, não cópia do enunciado.

    Nenhum campo é citação direta, então `ancoras()` fica vazio e o PF3 não
    confere nada aqui — o verificador só atua onde o schema declara citação.
    """

    explicacao_pedagogica: ItemDerivado
    passo_a_passo_resolucao: list[ItemDerivado] = Field(min_length=1)
    termos_busca_duckduckgo: list[str] = Field(default_factory=list)

    def termos_de_busca(self) -> list[str]:
        return list(self.termos_busca_duckduckgo)


# --- ACESSIBILIDADE ----------------------------------------------------------


class AcessibilidadeInterna(SchemaInterno):
    score_acessibilidade: int = Field(ge=0, le=100)
    # Pontos positivos e de melhoria apontam para o material (citação); a
    # sugestão imediata é orientação prática do professor, sem origem literal.
    pontos_positivos: list[ItemAncorado] = Field(min_length=1)
    pontos_de_melhoria: list[ItemAncorado] = Field(min_length=1)
    sugestao_imediata: ItemDerivado

    def ancoras(self, documento_padrao: str = "") -> list[Ancora]:
        return _ancoras(
            [*self.pontos_positivos, *self.pontos_de_melhoria],
            documento_padrao,
        )
