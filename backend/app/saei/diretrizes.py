# F4 no SAEI: a base de diretrizes institucionais de Educação Especial e DUA.
#
# O JSON e o cache continuam exatamente onde estavam (`core/utils` e `data/`).
# O que muda é que agora existe uma fonte declarada, que o núcleo exige e que a
# estratégia é obrigada a consumir.

from __future__ import annotations

from app.core.utils.diretrizes_loader import obter_diretrizes_inclusao
from app.framework import Contexto, DiretrizesEstaticas, InstanciacaoIncompletaError

ROTULO_DIRETRIZES_SAEI = "Diretrizes institucionais de Educação Especial e DUA (SAEI)"


class DiretrizesInclusaoSAEI:
    def obter(self, contexto: Contexto) -> DiretrizesEstaticas:
        itens = obter_diretrizes_inclusao()
        if not itens:
            raise InstanciacaoIncompletaError(
                "A base de diretrizes institucionais está vazia ou ilegível "
                "(backend/app/data/diretrizes_inclusao.json). O núcleo não executa "
                "adaptação sem base de diretrizes."
            )
        return DiretrizesEstaticas(rotulo=ROTULO_DIRETRIZES_SAEI, itens=dict(itens))
