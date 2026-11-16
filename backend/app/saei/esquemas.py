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
    """Afirmação + prova de origem. Item sem âncora não passa na validação."""

    texto: str = Field(min_length=1)
    ancora: TrechoCitado


class MudancaAncorada(BaseModel):
    """Mudança de adaptação: seção do original, ação e a âncora que a sustenta."""

    secao: str = Field(min_length=1)
    acao: str = Field(min_length=1)
    ancora: TrechoCitado


def _ancoras(itens: list, documento_padrao: str) -> list[Ancora]:
    return [item.ancora.para_ancora(documento_padrao) for item in itens]


# --- RESUMO ------------------------------------------------------------------


class ResumoInterno(SchemaInterno):
    titulo_documento: str
    resumo_geral: ItemAncorado
    pontos_chave: list[ItemAncorado] = Field(min_length=1)
    proximos_passos_ou_recomendacoes: ItemAncorado
    termos_busca: list[str] = Field(default_factory=list)

    def ancoras(self, documento_padrao: str = "") -> list[Ancora]:
        return _ancoras(
            [self.resumo_geral, *self.pontos_chave, self.proximos_passos_ou_recomendacoes],
            documento_padrao,
        )

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
    mudancas_sugeridas: list[MudancaAncorada] = Field(min_length=1)
    justificativa_inclusiva: ItemAncorado
    dicas_de_abordagem: list[ItemAncorado] = Field(min_length=1)

    def ancoras(self, documento_padrao: str = "") -> list[Ancora]:
        return [
            *[mudanca.ancora.para_ancora(documento_padrao) for mudanca in self.mudancas_sugeridas],
            self.justificativa_inclusiva.ancora.para_ancora(documento_padrao),
            *_ancoras(self.dicas_de_abordagem, documento_padrao),
        ]


# --- TUTORIA -----------------------------------------------------------------


class TutorInterno(SchemaInterno):
    explicacao_pedagogica: ItemAncorado
    passo_a_passo_resolucao: list[ItemAncorado] = Field(min_length=1)
    termos_busca_duckduckgo: list[str] = Field(default_factory=list)

    def ancoras(self, documento_padrao: str = "") -> list[Ancora]:
        return _ancoras(
            [self.explicacao_pedagogica, *self.passo_a_passo_resolucao],
            documento_padrao,
        )

    def termos_de_busca(self) -> list[str]:
        return list(self.termos_busca_duckduckgo)


# --- ACESSIBILIDADE ----------------------------------------------------------


class AcessibilidadeInterna(SchemaInterno):
    score_acessibilidade: int = Field(ge=0, le=100)
    pontos_positivos: list[ItemAncorado] = Field(min_length=1)
    pontos_de_melhoria: list[ItemAncorado] = Field(min_length=1)
    sugestao_imediata: ItemAncorado

    def ancoras(self, documento_padrao: str = "") -> list[Ancora]:
        return _ancoras(
            [
                *self.pontos_positivos,
                *self.pontos_de_melhoria,
                self.sugestao_imediata,
            ],
            documento_padrao,
        )
