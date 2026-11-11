# F6 no SAEI: DuckDuckGo. O provedor devolve termos; este resolvedor devolve
# fontes reais. Nada aqui é usado pelas projeções para montar URL: elas apenas
# expõem as evidências que o núcleo já resolveu.

from __future__ import annotations

from typing import Sequence

from app.core.utils.search_helper import buscar_links_detalhados_por_termos
from app.framework import Contexto, Evidencia, PacoteAnalise


class ResolvedorDuckDuckGo:
    nome = "duckduckgo"

    def resolver(
        self,
        termos: Sequence[str],
        contexto: Contexto,
        pacote: PacoteAnalise,
    ) -> list[Evidencia]:
        resumo_laudo = _resumo_do_registro(pacote)
        preferencias = str(
            (pacote.contexto.registro.get("preferencias_do_aluno") or "")
        ).strip()

        brutos = buscar_links_detalhados_por_termos(
            termos=list(termos),
            resumo_laudo=resumo_laudo,
            preferencias_aluno=preferencias,
        )
        return [
            Evidencia(
                titulo=str(item.get("titulo") or item.get("url") or ""),
                url=str(item.get("url") or ""),
            )
            for item in brutos
            if str(item.get("url") or "").strip()
        ]


def _resumo_do_registro(pacote: PacoteAnalise) -> str:
    """Resumo clínico disponível: laudos do contexto ou o texto colado na tela."""
    if pacote.documentos_de_contexto:
        return "\n".join(
            f"[{documento.rotulo}]: {documento.texto_completo}"
            for documento in pacote.documentos_de_contexto
        )
    return str(pacote.contexto.registro.get("resumo_laudo") or "")
