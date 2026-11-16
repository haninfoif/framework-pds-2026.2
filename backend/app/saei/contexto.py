# V1 no SAEI: o que ancora o documento é a matrícula (aluno, professor,
# disciplina, tutor e preferências). No texto livre a âncora é o próprio
# solicitante, sem vínculo — e é a política que decide o que isso permite.

from __future__ import annotations

from app.core.exceptions import RecursoNaoEncontradoError
from app.framework import (
    Contexto,
    ContextoRef,
    DocumentoIlegivelError,
    DocumentoNormalizado,
    EntradaInvalidaError,
    Normalizador,
)
from app.models import TipoDocumento
from app.saei.refs import referencia_de_documento

TIPO_CONTEXTO_MATRICULA = "MATRICULA"
TIPO_CONTEXTO_LIVRE = "LIVRE"


class ContextoSAEI:
    def __init__(self, matricula_repo, documento_repo, normalizador: Normalizador) -> None:
        self._matricula_repo = matricula_repo
        self._documento_repo = documento_repo
        self._normalizador = normalizador

    def resolver(self, ref: ContextoRef) -> Contexto:
        if ref.tipo == TIPO_CONTEXTO_MATRICULA:
            return self._resolver_matricula(ref)
        if ref.tipo == TIPO_CONTEXTO_LIVRE:
            return self._resolver_livre(ref)
        raise EntradaInvalidaError(
            f"Tipo de contexto '{ref.tipo}' não é resolvido por esta instância."
        )

    def carregar_documentos_de_contexto(
        self, contexto: Contexto
    ) -> list[DocumentoNormalizado]:
        """
        Laudos da matrícula compõem o registro do sujeito.

        Chamado depois do portão: nenhuma leitura de conteúdo acontece antes da
        autorização. Laudo ilegível é ignorado, como já era o comportamento da
        aplicação — análise não pode travar por um anexo corrompido.
        """
        matricula_id = contexto.registro.get("matricula_id")
        if not matricula_id:
            return []

        documentos = self._documento_repo.listar_por_matricula(int(matricula_id))
        laudos: list[DocumentoNormalizado] = []
        for documento in documentos:
            if documento.tipo != TipoDocumento.LAUDO_MEDICO:
                continue
            try:
                laudos.append(
                    self._normalizador.normalizar(referencia_de_documento(documento))
                )
            except (DocumentoIlegivelError, ValueError):
                continue
        return laudos

    def _resolver_matricula(self, ref: ContextoRef) -> Contexto:
        try:
            matricula_id = int(ref.identificador)
        except (TypeError, ValueError) as exc:
            raise EntradaInvalidaError(
                f"Identificador de matrícula inválido: {ref.identificador!r}."
            ) from exc

        matricula = self._matricula_repo.buscar_por_id(matricula_id)
        if not matricula:
            raise RecursoNaoEncontradoError(
                f"Matrícula com ID '{matricula_id}' não encontrada."
            )

        aluno = matricula.aluno
        registro = {
            "vinculo": True,
            "matricula_id": matricula.id,
            "aluno_id": matricula.aluno_id,
            "professor_id": matricula.professor_id,
            "tutor_id": getattr(aluno, "tutor_id", None),
            "disciplina": getattr(matricula.disciplina, "nome", "") or "",
            "preferencias_do_aluno": (matricula.preferencias_do_aluno or "").strip(),
        }
        return Contexto(
            ref=ref,
            rotulo=f"Matrícula {matricula.id}",
            registro=registro,
        )

    def _resolver_livre(self, ref: ContextoRef) -> Contexto:
        registro = {**dict(ref.metadados or {}), "vinculo": False}
        solicitante = ref.solicitante
        return Contexto(
            ref=ref,
            rotulo=f"Solicitante {getattr(solicitante, 'id', 'sem-id')}",
            registro=registro,
        )
