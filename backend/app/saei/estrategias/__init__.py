# Registro do catálogo de estratégias do SAEI (V2).
#
# Instanciar o framework é, em boa parte, isto: declarar quais análises existem,
# qual tipo de documento cada uma entende e qual é o fallback. O núcleo não muda.

from __future__ import annotations

from app.framework import RegistroEstrategias
from app.models import TipoDocumento
from app.saei.analises import (
    ANALISE_ACESSIBILIDADE,
    ANALISE_ADAPTACAO,
    ANALISE_RESUMO,
    ANALISE_TUTORIA,
)
from app.saei.estrategias.acessibilidade import AvaliacaoAcessibilidadeDUA
from app.saei.estrategias.adaptacao import AdaptacaoAtividade, AdaptacaoPlanoDeAula
from app.saei.estrategias.resumo import (
    ResumoAtividade,
    ResumoLaudoMedico,
    ResumoPadrao,
    ResumoPlanoDeAula,
)
from app.saei.estrategias.tutoria import TutoriaAluno


def registro_de_estrategias() -> RegistroEstrategias:
    registro = RegistroEstrategias()

    registro.registrar(
        ANALISE_RESUMO,
        ResumoLaudoMedico(),
        tipos_documento=(TipoDocumento.LAUDO_MEDICO.value,),
    )
    registro.registrar(
        ANALISE_RESUMO,
        ResumoPlanoDeAula(),
        tipos_documento=(TipoDocumento.PLANO_DE_AULA.value,),
    )
    registro.registrar(
        ANALISE_RESUMO,
        ResumoAtividade(),
        tipos_documento=(TipoDocumento.ATIVIDADE.value,),
    )
    # Fallback de resumo: OUTROS e qualquer tipo novo.
    registro.registrar(ANALISE_RESUMO, ResumoPadrao())

    registro.registrar(
        ANALISE_ADAPTACAO,
        AdaptacaoAtividade(),
        tipos_documento=(TipoDocumento.ATIVIDADE.value,),
    )
    # Materiais diversos caem no foco de plano de aula, como antes.
    registro.registrar(ANALISE_ADAPTACAO, AdaptacaoPlanoDeAula())

    # Tutoria e acessibilidade não dependem do tipo do documento.
    registro.registrar(ANALISE_TUTORIA, TutoriaAluno())
    registro.registrar(ANALISE_ACESSIBILIDADE, AvaliacaoAcessibilidadeDUA())

    return registro
