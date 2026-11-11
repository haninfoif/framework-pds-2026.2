# Orquestra o ciclo de vida dos documentos: valida a matrícula, delega as regras
# de permissão à DocumentoPolicy, delega o disco ao ArquivoStorage e entrega as
# análises de IA ao núcleo — que é quem executa o ciclo (PF1).
#
# O serviço não monta prompt, não extrai texto e não checa papel de IA: ele só
# traduz o documento persistido em referências do contrato e devolve a projeção.

from pathlib import Path

from fastapi import UploadFile

from app.core.exceptions import PermissaoNegadaError, RecursoNaoEncontradoError
from app.core.utils.arquivo_storage import ArquivoStorage
from app.framework import ContextoRef, NucleoAnalise, ResultadoAnalise
from app.models import Documento, TipoDocumento, Usuario
from app.repositories.documento_repository import DocumentoRepository
from app.repositories.matricula_repository import MatriculaRepository
from app.saei.analises import (
    ANALISE_ACESSIBILIDADE,
    ANALISE_ADAPTACAO,
    ANALISE_RESUMO,
    ANALISE_TUTORIA,
)
from app.saei.contexto import TIPO_CONTEXTO_MATRICULA
from app.saei.papeis import papel_do_usuario
from app.saei.refs import referencia_de_documento
from app.schemas.documento_schemas import (
    DocumentoResponse,
    MatriculaDocumentosResponse,
    ResumoIAResponse,
)
from app.schemas.ia_schemas import (
    IAAdaptacaoInternal,
    IAAcessibilidadeInternal,
    TutorAlunoResponse,
)
from app.services.documento_permissions import DocumentoPolicy


class DocumentoService:
    def __init__(
        self,
        documento_repo: DocumentoRepository,
        matricula_repo: MatriculaRepository,
        policy: DocumentoPolicy,
        storage: ArquivoStorage,
        nucleo: NucleoAnalise,
    ):
        self.documento_repo = documento_repo
        self.matricula_repo = matricula_repo
        self.policy = policy
        self.storage = storage
        self.nucleo = nucleo

    # --- 1. UPLOAD DE DOCUMENTO ---
    def salvar_documento(
        self,
        matricula_id: int,
        titulo: str,
        tipo: TipoDocumento,
        arquivo: UploadFile,
        usuario_logado: Usuario
    ) -> Documento:
        # Busca a matrícula no banco
        matricula = self.matricula_repo.buscar_por_id(matricula_id)
        if not matricula:
            raise RecursoNaoEncontradoError(f"Matrícula com ID '{matricula_id}' não encontrada.")

        # Regra de Apenas o Aluno da matrícula pode enviar pro Professor / apenas o Professor pro Aluno
        self.policy.exigir_envio_permitido(usuario_logado, matricula)

        # Grava o arquivo físico no disco com nome único
        caminho_destino = self.storage.salvar_upload(arquivo)

        # Cria a entidade Documento e registra no banco
        novo_documento = Documento(
            titulo=titulo.strip(),
            tipo=tipo,
            caminho_arquivo=caminho_destino,
            matricula_id=matricula.id,
            remetente_id=usuario_logado.id
        )

        return self.documento_repo.salvar(novo_documento)

    # --- 2. LISTAGEM EM DUAS LISTAS POR MATRÍCULA ---
    def listar_documentos_matricula(
        self,
        matricula_id: int,
        usuario_logado: Usuario
    ) -> MatriculaDocumentosResponse:
        matricula = self.matricula_repo.buscar_por_id(matricula_id)
        if not matricula:
            raise RecursoNaoEncontradoError(f"Matrícula com ID '{matricula_id}' não encontrada.")

        # Regra de Acesso: Aluno da matrícula, Professor da matrícula e Coordenadores
        if not self.policy.pode_visualizar_matricula(usuario_logado, matricula):
            raise PermissaoNegadaError("Você não tem permissão para visualizar os documentos desta matrícula.")

        documentos = self.documento_repo.listar_por_matricula(matricula_id)

        # Separa exatamente nas duas listas
        enviados_aluno = []
        enviados_professor = []

        for doc in documentos:
            doc_schema = DocumentoResponse.model_validate(doc)
            if doc.remetente_id == matricula.aluno_id:
                enviados_aluno.append(doc_schema)
            elif doc.remetente_id == matricula.professor_id:
                enviados_professor.append(doc_schema)

        return MatriculaDocumentosResponse(
            matricula_id=matricula.id,
            enviados_pelo_aluno=enviados_aluno,
            enviados_pelo_professor=enviados_professor
        )

    # --- 3. DOWNLOAD DE DOCUMENTO ---
    def obter_documento_para_download(
        self,
        documento_id: int,
        usuario_logado: Usuario
    ) -> tuple[str, str]:
        """
        Valida a segurança e retorna (caminho_fisico, nome_sugerido_para_download).
        """
        documento = self.documento_repo.buscar_por_id(documento_id)
        if not documento:
            raise RecursoNaoEncontradoError(f"Documento com ID '{documento_id}' não encontrado.")

        matricula = documento.matricula
        if not matricula:
            raise RecursoNaoEncontradoError("Matrícula associada a este documento não foi localizada.")

        # Confere se o usuário logado tem permissão para baixar este documento
        if not self.policy.pode_baixar(usuario_logado, matricula):
            raise PermissaoNegadaError("Você não tem permissão para baixar este documento.")

        if not Path(documento.caminho_arquivo).exists():
            raise RecursoNaoEncontradoError("Arquivo físico não foi encontrado no servidor.")

        # Monta um nome amigável para o arquivo baixado
        extensao = Path(documento.caminho_arquivo).suffix
        nome_download = f"{documento.titulo}{extensao}"

        return documento.caminho_arquivo, nome_download

    # --- 4. DELETAR DOCUMENTOS ---
    def deletar_documento(self, documento_id: int, usuario_logado: Usuario):
        documento = self.documento_repo.buscar_por_id(documento_id)
        if not documento:
            raise RecursoNaoEncontradoError(f"Documento com ID '{documento_id}' não encontrado.")

        # Só quem enviou o documento ou o Coordenador pode apagá-lo
        if not self.policy.pode_excluir(usuario_logado, documento):
            raise PermissaoNegadaError("Você não tem permissão para excluir este documento.")

        # Remove o arquivo físico (se existir) e o registro do banco
        self.storage.remover(documento.caminho_arquivo)
        self.documento_repo.deletar(documento)

    # --- 5. RESUMO COM IA ---
    def gerar_resumo(self, documento_id: int, usuario_logado: Usuario) -> ResumoIAResponse:
        documento = self._buscar_documento(documento_id)
        return self._analisar(documento, ANALISE_RESUMO, usuario_logado).dados

    # --- 6. TUTOR DE ESTUDOS PERSONALIZADO (VISÃO DO ALUNO) ---
    def gerar_tutoria_documento(
        self, documento_id: int, usuario_logado: Usuario
    ) -> TutorAlunoResponse:
        documento = self._buscar_documento(documento_id)
        return self._analisar(documento, ANALISE_TUTORIA, usuario_logado).dados

    # --- 7. ADAPTAÇÃO INTELIGENTE DE MATERIAIS (VISÃO DO PROFESSOR E COORDENADOR) ---
    def gerar_adaptacao_documento(
        self, documento_id: int, usuario_logado: Usuario
    ) -> IAAdaptacaoInternal:
        documento = self._buscar_documento(documento_id)
        return self._analisar(documento, ANALISE_ADAPTACAO, usuario_logado).dados

    # --- 8. TERMÔMETRO DE ACESSIBILIDADE DUA (PROFESSOR E COORDENADOR) ---
    def gerar_avaliacao_acessibilidade_documento(
        self, documento_id: int, current_user: Usuario
    ) -> IAAcessibilidadeInternal:
        documento = self._buscar_documento(documento_id)
        return self._analisar(documento, ANALISE_ACESSIBILIDADE, current_user).dados

    # --- apoio ---
    def _buscar_documento(self, documento_id: int) -> Documento:
        documento = self.documento_repo.buscar_por_id(documento_id)
        if not documento:
            raise RecursoNaoEncontradoError("Documento não encontrado.")
        return documento

    def _analisar(
        self, documento: Documento, analise, usuario_logado: Usuario
    ) -> ResultadoAnalise:
        """
        Entrega ao núcleo o contrato inteiro: contexto que ancora, documentos de
        entrada, análise e destinatário. Permissão, prompt, IA, âncora e projeção
        são do núcleo.
        """
        return self.nucleo.executar(
            contexto=ContextoRef(
                tipo=TIPO_CONTEXTO_MATRICULA,
                identificador=documento.matricula_id,
                solicitante=usuario_logado,
            ),
            documentos=[referencia_de_documento(documento)],
            analise=analise,
            destinatario=papel_do_usuario(usuario_logado),
        )
