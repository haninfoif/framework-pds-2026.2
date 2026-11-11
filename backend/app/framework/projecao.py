# V4 — schemas de saída por audiência.
#
# A projeção é o segundo braço do PF2. O que o destinatário não pode ver não é
# escondido na tela: simplesmente não existe no schema dele. Registrar projeções
# é registrar quais recortes de resultado o sistema sabe produzir.

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from pydantic import BaseModel

from .contrato import PapelAcesso, ResultadoNucleo
from .erros import InstanciacaoIncompletaError, ProjecaoAusenteError


class BaseProjecao(ABC):
    """
    Contrato de uma projeção (V4).

    `analises` restringe a quais análises a projeção se aplica; `("*",)` cobre
    todas. Assim a projeção do aluno para tutoria não pode ser reutilizada por
    engano numa análise de professor.
    """

    papel: PapelAcesso
    analises: tuple[str, ...] = ("*",)

    @abstractmethod
    def projetar(self, entrada: ResultadoNucleo) -> BaseModel:
        """Devolve o schema público da audiência, já no formato do contrato externo."""


class RegistroProjecoes:
    """Catálogo (análise, papel) -> projeção, com fallback por análise."""

    def __init__(self) -> None:
        self._projecoes: dict[tuple[str, str], BaseProjecao] = {}

    def registrar(self, projecao: BaseProjecao) -> "RegistroProjecoes":
        if not isinstance(getattr(projecao, "papel", None), PapelAcesso):
            raise InstanciacaoIncompletaError(
                f"A projeção '{type(projecao).__name__}' não declara um PapelAcesso."
            )
        analises: Sequence[str] = getattr(projecao, "analises", ("*",)) or ("*",)
        for analise in analises:
            self._projecoes[(str(analise), projecao.papel.nome)] = projecao
        return self

    def selecionar(self, analise: str, papel: PapelAcesso) -> BaseProjecao:
        for chave in ((analise, papel.nome), ("*", papel.nome)):
            projecao = self._projecoes.get(chave)
            if projecao is not None:
                return projecao
        raise ProjecaoAusenteError(
            f"Não existe schema de projeção para a análise '{analise}' "
            f"com o destinatário '{papel.nome}'."
        )

    def papeis(self, analise: str) -> set[str]:
        return {
            papel
            for (chave, papel) in self._projecoes
            if chave in (analise, "*")
        }

    def validar(self, analises_declaradas: set[str]) -> None:
        if not self._projecoes:
            raise InstanciacaoIncompletaError("Nenhuma projeção registrada (V4).")
        for analise in analises_declaradas:
            if not self.papeis(analise):
                raise InstanciacaoIncompletaError(
                    f"A análise '{analise}' não tem nenhum schema de projeção por "
                    "audiência. Sem projeção, não há resultado entregável."
                )
