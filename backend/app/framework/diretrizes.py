# F4 — base de diretrizes do domínio.
#
# O núcleo não sabe se são diretrizes de inclusão, de compliance ou de redação
# jurídica. Ele só exige que exista uma fonte declarada, não vazia, e que a
# estratégia a consuma (verificado na inicialização, em estrategias.py).

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class DiretrizesEstaticas:
    """
    Base de diretrizes em memória, indexada por chave.

    É o formato que o SAEI já usa (`diretrizes_inclusao.json`): um dicionário
    chave -> texto. Instâncias que carregam de banco, S3 ou de uma API apenas
    constroem este objeto (ou outro com a mesma interface `para_prompt`).
    """

    rotulo: str
    itens: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.rotulo or not self.rotulo.strip():
            raise ValueError("DiretrizesEstaticas exige um rótulo.")
        if not self.itens:
            raise ValueError(
                f"A base de diretrizes '{self.rotulo}' está vazia: "
                "o núcleo não executa análise sem base de diretrizes."
            )

    def chaves(self) -> list[str]:
        return list(self.itens.keys())

    def para_prompt(self) -> str:
        return "\n".join(f"- {chave}: {texto}" for chave, texto in self.itens.items())
