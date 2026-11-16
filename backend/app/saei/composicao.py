# Composição: onde o SAEI instancia o framework.
#
# Este arquivo é a prova de que a instanciação é feita de classes e módulos que
# complementam o núcleo — contexto, política, guardrails, estratégias, projeções,
# diretrizes, resolvedor e provedor — sem editar nada em `framework/`.
#
# A montagem é por requisição porque o contexto e os repositórios compartilham a
# sessão do banco daquela requisição. O que é stateless (estratégias, projeções,
# guardrails, diretrizes) é criado de forma barata a cada chamada.

from __future__ import annotations

from sqlalchemy.orm import Session

from app.framework import (
    ConfiguracaoNucleo,
    LimitesAnalise,
    Normalizador,
    NucleoAnalise,
    RegistradorLog,
)
from app.repositories.documento_repository import DocumentoRepository
from app.repositories.matricula_repository import MatriculaRepository
from app.saei.analises import (
    ANALISE_ACESSIBILIDADE,
    ANALISE_ADAPTACAO,
    ANALISE_RESUMO,
    ANALISE_TUTORIA,
)
from app.saei.contexto import ContextoSAEI
from app.saei.diretrizes import DiretrizesInclusaoSAEI
from app.saei.estrategias import registro_de_estrategias
from app.saei.evidencia import ResolvedorDuckDuckGo
from app.saei.extratores import ExtratorPDF
from app.saei.guardrails import GuardrailsSAEI
from app.saei.politica import PoliticaSAEI
from app.saei.projecoes import registro_de_projecoes
from app.services.ia.ia_client import GroqClient

# F8: o texto do resumo continua exatamente o que o front-end já exibe; as demais
# análises usam o aviso padrão do núcleo.
AVISO_RESUMO = (
    "Aviso: Este resumo foi gerado por Inteligência Artificial e pode não ser 100% "
    "preciso. Consulte o documento original."
)


def configuracao_saei() -> ConfiguracaoNucleo:
    # F7: o laudo de contexto era truncado em 1000 caracteres em cada método;
    # agora o limite é declarado uma vez, por análise.
    return ConfiguracaoNucleo(
        aviso_por_analise={ANALISE_RESUMO.chave: AVISO_RESUMO},
        limites={
            # Resumo e termômetro DUA nunca leram laudos: a análise é do material.
            ANALISE_RESUMO.chave: LimitesAnalise(incluir_documentos_de_contexto=False),
            ANALISE_ACESSIBILIDADE.chave: LimitesAnalise(
                max_tokens=500, incluir_documentos_de_contexto=False
            ),
            # Tutoria e adaptação usavam os laudos da matrícula como contexto clínico.
            ANALISE_TUTORIA.chave: LimitesAnalise(limite_caracteres_contexto=1000),
            ANALISE_ADAPTACAO.chave: LimitesAnalise(limite_caracteres_contexto=1000),
        },
    )


def montar_nucleo(db: Session) -> NucleoAnalise:
    normalizador = Normalizador([ExtratorPDF()])
    return NucleoAnalise(
        nome="nucleo-analise-saei",
        contexto=ContextoSAEI(
            matricula_repo=MatriculaRepository(db),
            documento_repo=DocumentoRepository(db),
            normalizador=normalizador,
        ),
        politica=PoliticaSAEI(),
        estrategias=registro_de_estrategias(),
        guardrails=GuardrailsSAEI(),
        provedor=GroqClient(),
        projecoes=registro_de_projecoes(),
        diretrizes=DiretrizesInclusaoSAEI(),
        normalizador=normalizador,
        resolvedor_evidencia=ResolvedorDuckDuckGo(),
        registrador=RegistradorLog(),
        config=configuracao_saei(),
    )
