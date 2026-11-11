# PF4 — evidência resolvida.
#
# O modelo emite TERMOS. O núcleo resolve FONTES. Nenhuma URL, link ou fonte
# externa chega ao destinatário sem ter passado por um resolvedor (F6).
#
# O padrão do núcleo é o resolvedor nulo: sem instância configurada, o resultado
# simplesmente não carrega evidência externa. Isso torna "desligar a busca"
# (auditoria, sigilo) uma configuração, não uma alteração de código.

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Sequence

from pydantic import BaseModel

from .contrato import Contexto, PacoteAnalise
from .erros import SaidaForaDeContratoError

# Formatos de URL que o modelo não pode emitir por conta própria.
_PADRAO_URL = re.compile(r"(https?://|www\.)\S+", re.IGNORECASE)


@dataclass(frozen=True)
class Evidencia:
    """
    Fonte externa real, devolvida por um resolvedor.

    `titulo` e `url` existem porque é o que as projeções precisam; `termo` fica
    guardado para auditoria (qual termo do modelo gerou esta fonte).
    """

    titulo: str
    url: str
    termo: str = ""

    def para_dict(self) -> dict[str, str]:
        return {"titulo": self.titulo, "url": self.url}


class ResolvedorNulo:
    """
    F6 desligado: devolve nenhuma evidência.

    Existe para que `resolver_evidencia=False` seja explícito e testável, em vez
    de um `if` espalhado pelo núcleo.
    """

    def resolver(
        self,
        termos: Sequence[str],
        contexto: Contexto,
        pacote: PacoteAnalise,
    ) -> list[Evidencia]:
        return []


def _caminhos_de_texto(dados: BaseModel, prefixo: str = "") -> list[tuple[str, str]]:
    """Percorre a saída interna e devolve (caminho, texto) de todos os campos string."""
    encontrados: list[tuple[str, str]] = []

    def visitar(valor: Any, caminho: str) -> None:
        if isinstance(valor, str):
            encontrados.append((caminho, valor))
        elif isinstance(valor, BaseModel):
            for nome, campo in valor.__class__.model_fields.items():
                visitar(getattr(valor, nome, None), f"{caminho}.{nome}" if caminho else nome)
        elif isinstance(valor, (list, tuple)):
            for indice, item in enumerate(valor):
                visitar(item, f"{caminho}[{indice}]")
        elif isinstance(valor, dict):
            for chave, item in valor.items():
                visitar(item, f"{caminho}.{chave}" if caminho else str(chave))

    visitar(dados, prefixo)
    return encontrados


class SaneadorVozExterna:
    """
    Verificação do PF4 sobre a saída interna.

    O modelo não pode emitir URL própria. A única exceção é citação literal: se
    a mesma URL aparece no texto de origem, ela não foi inventada, foi copiada —
    e isso também é rastreável.
    """

    def __init__(self, padrao: re.Pattern[str] = _PADRAO_URL) -> None:
        self._padrao = padrao

    def verificar(self, dados: BaseModel, pacote: PacoteAnalise) -> None:
        texto_de_origem = "\n".join(doc.texto_completo for doc in pacote.documentos)
        for caminho, texto in _caminhos_de_texto(dados):
            for encontrada in self._padrao.findall(texto):
                if encontrada in texto_de_origem:
                    continue
                raise SaidaForaDeContratoError(
                    "A saída do modelo trouxe uma fonte externa que não passou pelo "
                    f"resolvedor de evidências (campo '{caminho}'). "
                    "O modelo deve emitir apenas termos de busca."
                )
