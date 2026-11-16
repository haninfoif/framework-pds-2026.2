# PF2 — portão de acesso e projeção por audiência.
#
# Duas garantias acopladas no mesmo ponto fixo:
#   1. Portão: nenhuma leitura de conteúdo e nenhuma chamada de IA acontece sem
#      autorização prévia. O núcleo não tem caminho alternativo.
#   2. Projeção: a saída é validada contra o schema da audiência. O que o
#      destinatário não pode ver não é escondido — não existe como campo.

from __future__ import annotations

from pydantic import BaseModel

from .contrato import Acao, Contexto, PapelAcesso, ResultadoNucleo
from .erros import AcessoNegadoError
from .projecao import RegistroProjecoes
from .protocolos import Politica


class Portao:
    def __init__(self, politica: Politica, projecoes: RegistroProjecoes) -> None:
        self._politica = politica
        self._projecoes = projecoes

    def exigir(self, contexto: Contexto, acao: Acao) -> None:
        permitido = self._politica.autorizar(contexto.solicitante, contexto, acao)
        if permitido is not True:
            raise AcessoNegadoError(
                f"A política de acesso recusou a ação '{acao}' no contexto "
                f"'{contexto.rotulo}'."
            )

    def projetar(
        self,
        analise: str,
        papel: PapelAcesso,
        entrada: ResultadoNucleo,
    ) -> BaseModel:
        projecao = self._projecoes.selecionar(analise, papel)
        dados = projecao.projetar(entrada)
        if not isinstance(dados, BaseModel):
            raise AcessoNegadoError(
                f"A projeção '{type(projecao).__name__}' não devolveu um schema "
                "Pydantic; o resultado não pode ser entregue sem contrato."
            )
        return dados
