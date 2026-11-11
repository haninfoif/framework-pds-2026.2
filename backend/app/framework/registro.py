# F8 e F9 — limite de uso e registro de execução, ambos com default no núcleo.
#
# O texto do aviso é estrutural (PF4): o núcleo recusa-se a devolver resultado com
# aviso vazio. Quem muda o texto por domínio (ressalva OAB, aviso LGPD) altera a
# configuração, não o ciclo.

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .contrato import EventoExecucao
from .erros import InstanciacaoIncompletaError

logger = logging.getLogger("nucleo.analise")

AVISO_PADRAO = (
    "Aviso: Este conteúdo foi gerado por Inteligência Artificial e pode não ser "
    "100% preciso. Consulte o documento original."
)


@dataclass(frozen=True)
class LimitesAnalise:
    """F7 — limites de contexto e saída por análise."""

    max_tokens: int | None = None
    limite_caracteres_fonte: int | None = None
    limite_caracteres_contexto: int | None = None
    # Nem toda análise deve receber os documentos do registro do sujeito no
    # prompt. Resumo de um material, por exemplo, não deve passar a mencionar o
    # laudo só porque o laudo existe na matrícula.
    incluir_documentos_de_contexto: bool = True


@dataclass
class ConfiguracaoNucleo:
    """
    Configuração do ciclo. Todos os campos têm default seguro, exceto o aviso,
    que nunca pode ser vazio.
    """

    aviso_padrao: str = AVISO_PADRAO
    aviso_por_analise: dict[str, str] = field(default_factory=dict)
    limites: dict[str, LimitesAnalise] = field(default_factory=dict)
    exigir_ancoras: bool = True
    resolver_evidencia: bool = True
    cobertura_ancora: float = 0.85

    def __post_init__(self) -> None:
        if not (self.aviso_padrao or "").strip():
            raise InstanciacaoIncompletaError(
                "O limite de uso padrão está vazio: todo resultado precisa declarar "
                "o que a IA não faz."
            )

    def limite_de_uso(self, analise: str) -> str:
        texto = self.aviso_por_analise.get(analise) or self.aviso_padrao
        if not (texto or "").strip():
            raise InstanciacaoIncompletaError(
                f"O limite de uso da análise '{analise}' está vazio."
            )
        return texto

    def limites_de(self, analise: str) -> LimitesAnalise:
        return self.limites.get(analise) or LimitesAnalise()


class RegistradorLog:
    """F9 default: log da aplicação, sem persistência."""

    def registrar(self, evento: EventoExecucao) -> None:
        nivel = logging.INFO if evento.sucesso else logging.ERROR
        logger.log(
            nivel,
            "nucleo analise=%s papel=%s contexto=%s estrategia=%s provedor=%s "
            "duracao=%dms ancoras=%d evidencias=%d sucesso=%s erro=%s",
            evento.analise,
            evento.papel,
            evento.contexto,
            evento.estrategia,
            evento.provedor,
            evento.duracao_ms,
            evento.ancoras,
            evento.evidencias,
            evento.sucesso,
            evento.erro or "-",
        )


class RegistradorMemoria:
    """F9 alternativo: guarda os eventos em memória. Útil em teste e auditoria leve."""

    def __init__(self) -> None:
        self.eventos: list[EventoExecucao] = []

    def registrar(self, evento: EventoExecucao) -> None:
        self.eventos.append(evento)
