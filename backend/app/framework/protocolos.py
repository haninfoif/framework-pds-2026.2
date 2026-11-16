# Protocolos dos slots e dos pontos flexíveis.
#
# Nenhuma instância importa o núcleo para existir; o núcleo importa apenas estas
# interfaces. É por isso que trocar país, instituição ou provedor de IA não deve
# exigir edição em `framework/`.

from __future__ import annotations

from typing import Any, Protocol, Sequence

from pydantic import BaseModel

from .contrato import (
    Acao,
    Contexto,
    ContextoRef,
    DocumentoNormalizado,
    DocumentoRef,
    EventoExecucao,
    PacoteAnalise,
    PapelAcesso,
    Regra,
    ResultadoNucleo,
    TipoAnalise,
)
from .estrategias import Prompt
from .evidencia import Evidencia


# --- Pontos variáveis (hot spots obrigatórios) -------------------------------


class ContextoProvider(Protocol):
    """V1 — resolve o que ancora o documento e o registro do sujeito/contraparte."""

    def resolver(self, ref: ContextoRef) -> Contexto: ...

    def carregar_documentos_de_contexto(
        self, contexto: Contexto
    ) -> list[DocumentoNormalizado]:
        """
        Documentos adicionais que compõem o registro do sujeito (laudos, anexos
        do caso). Chamado só DEPOIS do portão, para que nenhuma leitura de
        conteúdo aconteça antes da autorização.
        """
        ...


class Politica(Protocol):
    """V3 — relações de poder do domínio, aplicadas antes de qualquer leitura."""

    def autorizar(self, solicitante: Any, contexto: Contexto, acao: Acao) -> bool: ...


class Guardrails(Protocol):
    """V5 — proibições do par (análise, destinatário)."""

    def regras(self, analise: TipoAnalise, papel: PapelAcesso) -> list[Regra]: ...


class Projecao(Protocol):
    """V4 — schema de saída de uma audiência."""

    papel: PapelAcesso
    analises: tuple[str, ...]

    def projetar(self, entrada: ResultadoNucleo) -> BaseModel: ...


# --- Pontos flexíveis (com default no repositório) ---------------------------


class ExtratorConteudo(Protocol):
    """F1 — extrator por formato (PDF, OCR, DOCX, HTML, texto colado)."""

    def suporta(self, ref: DocumentoRef) -> bool: ...

    def extrair(self, ref: DocumentoRef) -> Sequence[tuple[int, str]]: ...


class ProvedorIA(Protocol):
    """F2 — provedor de IA. O núcleo só conhece `gerar(prompt) -> texto`."""

    nome: str

    def gerar(self, prompt: Prompt) -> str: ...


class ProvedorDiretrizes(Protocol):
    """F4 — base de diretrizes do domínio, resolvida por contexto."""

    def obter(self, contexto: Contexto) -> Any: ...


class ResolvedorEvidenciaProtocol(Protocol):
    """F6 — transforma termos em fontes reais."""

    def resolver(
        self,
        termos: Sequence[str],
        contexto: Contexto,
        pacote: PacoteAnalise,
    ) -> list[Evidencia]: ...


class RegistradorExecucao(Protocol):
    """F9 — destino do registro de execução."""

    def registrar(self, evento: EventoExecucao) -> None: ...
