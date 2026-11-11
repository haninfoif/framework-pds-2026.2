# Identidade de audiência do SAEI. O núcleo só conhece os nomes; a tradução de
# UserRole para PapelAcesso é decisão de domínio e vive aqui.

from __future__ import annotations

from app.framework import AcessoNegadoError, PapelAcesso
from app.models import UserRole

PAPEL_ALUNO = PapelAcesso("ALUNO")
PAPEL_PROFESSOR = PapelAcesso("PROFESSOR")
PAPEL_COORDENADOR = PapelAcesso("COORDENADOR")

_PAPEL_POR_ROLE = {
    UserRole.ALUNO: PAPEL_ALUNO,
    UserRole.PROFESSOR: PAPEL_PROFESSOR,
    UserRole.COORDENADOR: PAPEL_COORDENADOR,
}


def papel_do_usuario(usuario) -> PapelAcesso:
    """Converte o usuário logado na audiência que ele pode receber."""
    papel = _PAPEL_POR_ROLE.get(getattr(usuario, "role", None))
    if papel is None:
        raise AcessoNegadoError(
            "Usuário sem papel reconhecido não pode receber resultado de análise."
        )
    return papel
