# V2 — catálogo tipo x análise e a prova de que a estratégia consome o pacote.
#
# O ponto fixo PF1 só pode afirmar "a estratégia consumiu o pacote" se isso for
# testável. Aqui a prova acontece na inicialização: cada estratégia é executada
# contra um pacote de prova com dois sentinelas (texto do documento e diretriz).
# Estratégia que ignora qualquer um dos dois derruba o núcleo no boot — é erro de
# instanciação, não escolha de runtime.

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Mapping, Sequence

from .contrato import (
    Contexto,
    ContextoRef,
    DocumentoNormalizado,
    PacoteAnalise,
    SchemaInterno,
    TrechoDocumento,
    TipoAnalise,
)
from .diretrizes import DiretrizesEstaticas
from .erros import EstrategiaAusenteError, InstanciacaoIncompletaError

SENTINELA_DOCUMENTO = "SENTINELA-DO-DOCUMENTO-ALVO-7f3a"
SENTINELA_DIRETRIZ = "SENTINELA-DA-BASE-DE-DIRETRIZES-9c1b"


@dataclass(frozen=True)
class Prompt:
    """O que o núcleo envia ao provedor de IA (F2): instrução pronta e limites."""

    texto: str
    formato: str = "json_object"
    max_tokens: int | None = None


class BaseEstrategia(ABC):
    """
    Contrato de uma estratégia (V2).

    `schema_interno` é obrigatório porque o núcleo valida a resposta antes de
    qualquer projeção; `permite_evidencia_externa` é a única forma de autorizar
    o resolvedor (F6) a trabalhar para esta análise.
    """

    nome: str = ""
    schema_interno: type[SchemaInterno] | None = None
    permite_evidencia_externa: bool = False

    def __init_subclass__(cls, **kwargs):  # pragma: no cover - validação estrutural
        super().__init_subclass__(**kwargs)

    @property
    def identificador(self) -> str:
        return self.nome or self.__class__.__name__

    @abstractmethod
    def construir(self, pacote: PacoteAnalise) -> Prompt:
        """Monta o prompt a partir do pacote de três fontes."""


def pacote_de_prova() -> PacoteAnalise:
    """Pacote mínimo com sentinelas, usado só na validação de instanciação."""
    alvo = DocumentoNormalizado(
        identificador="documento-de-prova",
        rotulo="Documento de prova",
        tipo_documento="PROVA",
        trechos=[TrechoDocumento("Documento de prova", 1, SENTINELA_DOCUMENTO)],
    )
    contexto = Contexto(
        ref=ContextoRef(tipo="PROVA", identificador="contexto-de-prova"),
        rotulo="Contexto de prova",
        registro={"sujeito": "registro de prova"},
    )
    return PacoteAnalise(
        contexto=contexto,
        alvo=alvo,
        documentos_entrada=[alvo],
        documentos_de_contexto=[],
        diretrizes=DiretrizesEstaticas(
            rotulo="base de prova",
            itens={SENTINELA_DIRETRIZ: "diretriz mínima de prova"},
        ),
        guardrails=[],
        parametros={},
    )


def verificar_consumo_do_pacote(estrategia: BaseEstrategia) -> None:
    """
    Executa a estratégia contra o pacote de prova e exige os dois sentinelas.

    É a verificação que transforma "a estratégia deveria usar as diretrizes" em
    garantia: sem o sentinela da diretriz no prompt, a instanciação é recusada.
    """
    pacote = pacote_de_prova()
    try:
        prompt = estrategia.construir(pacote)
    except Exception as exc:  # noqa: BLE001 - o objetivo é transformar em erro de instanciação
        raise InstanciacaoIncompletaError(
            f"A estratégia '{estrategia.identificador}' falhou ao construir o prompt "
            f"do pacote de prova: {type(exc).__name__}: {exc}"
        ) from exc

    if not isinstance(prompt, Prompt) or not prompt.texto.strip():
        raise InstanciacaoIncompletaError(
            f"A estratégia '{estrategia.identificador}' não devolveu um Prompt com texto."
        )

    faltando = [
        rotulo
        for rotulo, sentinela in (
            ("documento-alvo", SENTINELA_DOCUMENTO),
            ("base de diretrizes", SENTINELA_DIRETRIZ),
        )
        if sentinela not in prompt.texto
    ]
    if faltando:
        raise InstanciacaoIncompletaError(
            f"A estratégia '{estrategia.identificador}' ignora {', '.join(faltando)}. "
            "O núcleo não aceita estratégia que não consome o pacote de três fontes."
        )

    if estrategia.schema_interno is None or not (
        isinstance(estrategia.schema_interno, type)
        and issubclass(estrategia.schema_interno, SchemaInterno)
    ):
        raise InstanciacaoIncompletaError(
            f"A estratégia '{estrategia.identificador}' não declara um schema_interno "
            "derivado de SchemaInterno (V4)."
        )


class RegistroEstrategias:
    """
    Catálogo analise -> estratégia, com fallback por análise.

    Registrar sem tocar no núcleo é o objetivo: a instância cria o registro,
    registra o padrão e as especializações, e o núcleo apenas seleciona.
    """

    def __init__(self) -> None:
        self._estrategias: dict[tuple[str, str], BaseEstrategia] = {}

    def registrar(
        self,
        analise: TipoAnalise | str,
        estrategia: BaseEstrategia,
        tipos_documento: Sequence[str] = ("*",),
    ) -> "RegistroEstrategias":
        chave = analise.chave if isinstance(analise, TipoAnalise) else str(analise)
        if not tipos_documento:
            tipos_documento = ("*",)
        for tipo in tipos_documento:
            self._estrategias[(chave, str(tipo))] = estrategia
        return self

    def selecionar(self, analise: TipoAnalise | str, tipo_documento: str) -> BaseEstrategia:
        chave = analise.chave if isinstance(analise, TipoAnalise) else str(analise)
        tipos = [str(tipo_documento), "*"]
        for tipo in tipos:
            estrategia = self._estrategias.get((chave, tipo))
            if estrategia is not None:
                return estrategia
        raise EstrategiaAusenteError(
            f"Nenhuma estratégia registrada para a análise '{chave}' "
            f"com o tipo de documento '{tipo_documento}'."
        )

    def analises(self) -> set[str]:
        return {chave for chave, _ in self._estrategias}

    def por_analise(self) -> Mapping[str, list[BaseEstrategia]]:
        agrupado: dict[str, list[BaseEstrategia]] = {}
        for (chave, _), estrategia in self._estrategias.items():
            lista = agrupado.setdefault(chave, [])
            if estrategia not in lista:
                lista.append(estrategia)
        return agrupado

    def validar(self) -> None:
        if not self._estrategias:
            raise InstanciacaoIncompletaError("Nenhuma estratégia registrada (V2).")
        for chave, estrategias in self.por_analise().items():
            if not any(tipo == "*" for analise, tipo in self._estrategias if analise == chave):
                raise InstanciacaoIncompletaError(
                    f"A análise '{chave}' não declara estratégia padrão para tipos "
                    "de documento não mapeados."
                )
            for estrategia in estrategias:
                verificar_consumo_do_pacote(estrategia)
