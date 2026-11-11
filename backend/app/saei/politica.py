# V3 no SAEI: quem pode pedir cada análise e qual audiência cada um pode receber.
#
# Esta é a única implementação da regra. Antes ela estava duplicada em
# `documento_service.py` e em `api/routers/ia.py`; agora o núcleo pergunta e a
# resposta vem daqui, antes de qualquer leitura de conteúdo.

from __future__ import annotations

from typing import Any

from app.framework import Acao, AcessoNegadoError, Contexto
from app.saei.analises import (
    ANALISE_ACESSIBILIDADE,
    ANALISE_ADAPTACAO,
    ANALISE_RESUMO,
    ANALISE_TUTORIA,
)
from app.saei.papeis import (
    PAPEL_ALUNO,
    PAPEL_COORDENADOR,
    PAPEL_PROFESSOR,
    papel_do_usuario,
)
from app.services.documento_permissions import DocumentoPolicy

ANALISES_POR_PAPEL: dict[str, set[str]] = {
    ANALISE_RESUMO.chave: {PAPEL_ALUNO.nome, PAPEL_PROFESSOR.nome, PAPEL_COORDENADOR.nome},
    ANALISE_TUTORIA.chave: {PAPEL_ALUNO.nome},
    ANALISE_ADAPTACAO.chave: {PAPEL_PROFESSOR.nome, PAPEL_COORDENADOR.nome},
    ANALISE_ACESSIBILIDADE.chave: {PAPEL_PROFESSOR.nome, PAPEL_COORDENADOR.nome},
}


class PoliticaSAEI:
    def autorizar(self, solicitante: Any, contexto: Contexto, acao: Acao) -> bool:
        try:
            papel = papel_do_usuario(solicitante)
        except AcessoNegadoError:
            return False

        if acao.nome == "analisar":
            papeis = ANALISES_POR_PAPEL.get(acao.parametro or "")
            if not papeis or papel.nome not in papeis:
                return False
            return self._vinculo_permitido(solicitante, contexto)

        if acao.nome == "projetar":
            # Cada usuário só recebe a projeção do próprio papel: aluno não
            # pede a visão do professor, e vice-versa.
            if papel.nome != acao.parametro:
                return False
            return self._vinculo_permitido(solicitante, contexto)

        return False

    def _vinculo_permitido(self, usuario: Any, contexto: Contexto) -> bool:
        registro = contexto.registro
        if not registro.get("vinculo", True):
            # Contexto sem vínculo (texto colado): a checagem de papel acima já
            # decidiu; não existe matrícula para conferir.
            return True
        return DocumentoPolicy.pode_acessar_contexto(
            usuario,
            aluno_id=registro.get("aluno_id"),
            professor_id=registro.get("professor_id"),
            tutor_id=registro.get("tutor_id"),
        )
