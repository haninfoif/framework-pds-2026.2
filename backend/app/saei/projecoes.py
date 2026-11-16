# V4 no SAEI: uma projeção por audiência.
#
# As projeções devolvem exatamente os schemas que o front-end já consome, então a
# API continua idêntica. A diferença é estrutural: o aluno não recebe a projeção
# do professor nem tem como pedi-la (a política recusa), e a âncora estruturada
# volta a ser texto só no último passo — depois de verificada.

from __future__ import annotations

from pydantic import BaseModel

from app.framework import (
    BaseProjecao,
    PapelAcesso,
    RegistroProjecoes,
    ResultadoNucleo,
    SaidaForaDeContratoError,
)
from app.saei.analises import (
    ANALISE_ACESSIBILIDADE,
    ANALISE_ADAPTACAO,
    ANALISE_RESUMO,
    ANALISE_TUTORIA,
)
from app.saei.esquemas import (
    AcessibilidadeInterna,
    AdaptacaoInterna,
    ResumoInterno,
    TutorInterno,
)
from app.saei.papeis import PAPEL_ALUNO, PAPEL_COORDENADOR, PAPEL_PROFESSOR
from app.schemas.documento_schemas import ResumoIAResponse
from app.schemas.ia_schemas import (
    IAAdaptacaoInternal,
    IAAcessibilidadeInternal,
    TutorAlunoResponse,
)


def _exigir(dados: BaseModel, tipo: type, projecao: BaseProjecao):
    if not isinstance(dados, tipo):
        raise SaidaForaDeContratoError(
            f"A projeção '{type(projecao).__name__}' recebeu um resultado que não é "
            f"'{tipo.__name__}'."
        )
    return dados


class _ProjecaoResumo(BaseProjecao):
    """Resumo para as três audiências. O recorte é o schema, não um `if` na tela."""

    analises = (ANALISE_RESUMO.chave,)

    def projetar(self, entrada: ResultadoNucleo) -> ResumoIAResponse:
        dados = _exigir(entrada.dados, ResumoInterno, self)
        return ResumoIAResponse(
            titulo_documento=dados.titulo_documento,
            resumo_geral=dados.resumo_geral.texto,
            pontos_chave=[item.texto for item in dados.pontos_chave],
            proximos_passos_ou_recomendacoes=dados.proximos_passos_ou_recomendacoes.texto,
            links_estudo=[evidencia.url for evidencia in entrada.evidencias],
            aviso_ia=entrada.limite_uso,
        )


class ProjecaoResumoAluno(_ProjecaoResumo):
    papel: PapelAcesso = PAPEL_ALUNO


class ProjecaoResumoProfessor(_ProjecaoResumo):
    papel: PapelAcesso = PAPEL_PROFESSOR


class ProjecaoResumoCoordenador(_ProjecaoResumo):
    papel: PapelAcesso = PAPEL_COORDENADOR


class ProjecaoTutoriaAluno(BaseProjecao):
    """
    Visão do aluno. Não existe campo clínico aqui — nem por omissão na tela, mas
    por construção do schema.
    """

    papel: PapelAcesso = PAPEL_ALUNO
    analises = (ANALISE_TUTORIA.chave,)

    def projetar(self, entrada: ResultadoNucleo) -> TutorAlunoResponse:
        dados = _exigir(entrada.dados, TutorInterno, self)
        return TutorAlunoResponse(
            explicacao_pedagogica=dados.explicacao_pedagogica.texto,
            passo_a_passo_resolucao=[item.texto for item in dados.passo_a_passo_resolucao],
            links_recomendados=[evidencia.para_dict() for evidencia in entrada.evidencias],
        )


class _ProjecaoAdaptacao(BaseProjecao):
    analises = (ANALISE_ADAPTACAO.chave,)

    def projetar(self, entrada: ResultadoNucleo) -> IAAdaptacaoInternal:
        dados = _exigir(entrada.dados, AdaptacaoInterna, self)
        return IAAdaptacaoInternal(
            mudancas_sugeridas=[
                f"Na seção '{mudanca.secao}': {mudanca.acao}"
                for mudanca in dados.mudancas_sugeridas
            ],
            justificativa_inclusiva=dados.justificativa_inclusiva.texto,
            dicas_de_abordagem=[item.texto for item in dados.dicas_de_abordagem],
        )


class ProjecaoAdaptacaoProfessor(_ProjecaoAdaptacao):
    papel: PapelAcesso = PAPEL_PROFESSOR


class ProjecaoAdaptacaoCoordenador(_ProjecaoAdaptacao):
    papel: PapelAcesso = PAPEL_COORDENADOR


class _ProjecaoAcessibilidade(BaseProjecao):
    analises = (ANALISE_ACESSIBILIDADE.chave,)

    def projetar(self, entrada: ResultadoNucleo) -> IAAcessibilidadeInternal:
        dados = _exigir(entrada.dados, AcessibilidadeInterna, self)
        return IAAcessibilidadeInternal(
            score_acessibilidade=dados.score_acessibilidade,
            pontos_positivos=[item.texto for item in dados.pontos_positivos],
            pontos_de_melhoria=[item.texto for item in dados.pontos_de_melhoria],
            sugestao_imediata=dados.sugestao_imediata.texto,
        )


class ProjecaoAcessibilidadeProfessor(_ProjecaoAcessibilidade):
    papel: PapelAcesso = PAPEL_PROFESSOR


class ProjecaoAcessibilidadeCoordenador(_ProjecaoAcessibilidade):
    papel: PapelAcesso = PAPEL_COORDENADOR


def registro_de_projecoes() -> RegistroProjecoes:
    registro = RegistroProjecoes()
    registro.registrar(ProjecaoResumoAluno())
    registro.registrar(ProjecaoResumoProfessor())
    registro.registrar(ProjecaoResumoCoordenador())
    registro.registrar(ProjecaoTutoriaAluno())
    registro.registrar(ProjecaoAdaptacaoProfessor())
    registro.registrar(ProjecaoAdaptacaoCoordenador())
    registro.registrar(ProjecaoAcessibilidadeProfessor())
    registro.registrar(ProjecaoAcessibilidadeCoordenador())
    return registro
