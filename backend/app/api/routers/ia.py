# Rotas de IA.
#
# Nenhuma regra de acesso mora aqui: quem decide é a política do núcleo (V3), e
# quem projeta o resultado é o schema da audiência (V4). A rota só traduz HTTP em
# contrato e devolve a projeção — exatamente no formato que o front já consome.

from fastapi import APIRouter, Depends, status

from app.api.dependencies import (
    get_analise_service,
    get_current_user,
    get_documento_service,
)
from app.models import TipoDocumento, Usuario
from app.saei.analises import (
    ANALISE_ACESSIBILIDADE,
    ANALISE_ADAPTACAO,
    ANALISE_TUTORIA,
)
from app.schemas.ia_schemas import (
    AdaptarMaterialRequest,
    AvaliarAcessibilidadeRequest,
    IAAdaptacaoInternal,
    IAAcessibilidadeInternal,
    TutorAlunoRequest,
    TutorAlunoResponse,
)
from app.services.analise_service import AnaliseService
from app.services.documento_service import DocumentoService

router = APIRouter(prefix="/ia", tags=["Inteligência Artificial"])


# Endpoint que recebe o payload JSON direto
@router.post(
    "/tutor-aluno",
    response_model=TutorAlunoResponse,
    status_code=status.HTTP_200_OK,
    summary="Tutor de Estudos Personalizado (Exclusivo para Alunos)"
)
def tutor_estudos_personalizado(
    dados: TutorAlunoRequest,
    service: AnaliseService = Depends(get_analise_service),
    current_user: Usuario = Depends(get_current_user)
):
    resultado = service.analisar_texto(
        texto=dados.texto_atividade,
        tipo_documento=TipoDocumento.OUTROS.value,
        analise=ANALISE_TUTORIA,
        usuario=current_user,
        registro={
            "resumo_laudo": dados.resumo_laudo or "Nenhum laudo informado.",
            "preferencias_do_aluno": dados.preferencias_aluno
            or "Nenhuma preferência específica informada.",
        },
    )
    return resultado.dados


# Endpoint integrado para o botão "Estudar com o Tutor" num PDF de Atividade do Aluno
@router.post(
    "/tutor-aluno/documento/{documento_id}",
    response_model=TutorAlunoResponse,
    status_code=status.HTTP_200_OK,
    summary="Tutor de Estudos Personalizado a partir de um documento PDF"
)
def tutor_estudos_por_documento(
    documento_id: int,
    service: DocumentoService = Depends(get_documento_service),
    current_user: Usuario = Depends(get_current_user)
):
    return service.gerar_tutoria_documento(documento_id, current_user)


# Adaptação Inteligente de Materiais a partir do texto enviado pelo cliente
# (Visão do Professor e do Coordenador — guia metodológico de inclusão em sala)
@router.post(
    "/adaptar-material",
    response_model=IAAdaptacaoInternal,
    status_code=status.HTTP_200_OK,
    summary="Adaptação Inteligente de Planos de Aula e Atividades"
)
def adaptar_material(
    dados: AdaptarMaterialRequest,
    service: AnaliseService = Depends(get_analise_service),
    current_user: Usuario = Depends(get_current_user)
):
    resultado = service.analisar_texto(
        texto=dados.texto_material,
        tipo_documento=dados.tipo_documento.value,
        analise=ANALISE_ADAPTACAO,
        usuario=current_user,
        registro={"resumo_laudo": dados.resumo_laudo or "Nenhum laudo informado."},
    )
    return resultado.dados


# Endpoint integrado para o botão "Adaptar Material" num PDF de Plano de Aula/Atividade
# (extrai o texto do arquivo, puxa os laudos da matrícula e delega à mesma lógica acima)
@router.post(
    "/adaptar-material/documento/{documento_id}",
    response_model=IAAdaptacaoInternal,
    status_code=status.HTTP_200_OK,
    summary="Adaptação Inteligente de Material a partir de um documento PDF"
)
def adaptar_material_documento(
    documento_id: int,
    service: DocumentoService = Depends(get_documento_service),
    current_user: Usuario = Depends(get_current_user)
):
    return service.gerar_adaptacao_documento(documento_id, current_user)


# Termômetro de Acessibilidade DUA (Foco no Professor e Coordenador)
@router.post(
    "/avaliar-acessibilidade",
    response_model=IAAcessibilidadeInternal,
    status_code=status.HTTP_200_OK,
    summary="Termômetro de Acessibilidade (DUA) de Materiais Didáticos"
)
def avaliar_acessibilidade(
    dados: AvaliarAcessibilidadeRequest,
    service: AnaliseService = Depends(get_analise_service),
    current_user: Usuario = Depends(get_current_user)
):
    resultado = service.analisar_texto(
        texto=dados.texto_material,
        tipo_documento=TipoDocumento.OUTROS.value,
        analise=ANALISE_ACESSIBILIDADE,
        usuario=current_user,
    )
    return resultado.dados


# Endpoint integrado para o botão "Termômetro DUA" num PDF de Atividade/Plano de Aula
@router.post(
    "/avaliar-acessibilidade/documento/{documento_id}",
    response_model=IAAcessibilidadeInternal,
    status_code=status.HTTP_200_OK,
    summary="Termômetro de Acessibilidade (DUA) a partir de um documento PDF"
)
def avaliar_acessibilidade_documento(
    documento_id: int,
    service: DocumentoService = Depends(get_documento_service),
    current_user: Usuario = Depends(get_current_user)
):
    return service.gerar_avaliacao_acessibilidade_documento(documento_id, current_user)
