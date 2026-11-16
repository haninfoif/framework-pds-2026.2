# Superfície pública do núcleo de análise documental assistida.
#
# A instância importa daqui. O que não estiver exportado é detalhe interno e não
# deve ser usado por aplicações que apenas consomem o framework.

from .contrato import (
    Acao,
    Ancora,
    Contexto,
    ContextoRef,
    DocumentoNormalizado,
    DocumentoRef,
    EventoExecucao,
    PacoteAnalise,
    PapelAcesso,
    Regra,
    ResultadoAnalise,
    ResultadoNucleo,
    SchemaInterno,
    TipoAnalise,
    TrechoDocumento,
)
from .diretrizes import DiretrizesEstaticas
from .erros import (
    AcessoNegadoError,
    AncoragemInvalidaError,
    DocumentoIlegivelError,
    EntradaInvalidaError,
    ErroNucleo,
    EstrategiaAusenteError,
    FalhaProvedorError,
    GuardrailVioladoError,
    InstanciacaoIncompletaError,
    ProjecaoAusenteError,
    SaidaForaDeContratoError,
)
from .estrategias import (
    BaseEstrategia,
    Prompt,
    RegistroEstrategias,
    verificar_consumo_do_pacote,
)
from .evidencia import Evidencia, ResolvedorNulo, SaneadorVozExterna
from .normalizacao import Normalizador, VerificadorAncoras, normalizar_texto
from .nucleo import NucleoAnalise
from .portao import Portao
from .projecao import BaseProjecao, RegistroProjecoes
from .registro import (
    AVISO_PADRAO,
    ConfiguracaoNucleo,
    LimitesAnalise,
    RegistradorLog,
    RegistradorMemoria,
)

__all__ = [
    "AVISO_PADRAO",
    "Acao",
    "AcessoNegadoError",
    "Ancora",
    "AncoragemInvalidaError",
    "BaseEstrategia",
    "BaseProjecao",
    "ConfiguracaoNucleo",
    "Contexto",
    "ContextoRef",
    "DiretrizesEstaticas",
    "DocumentoIlegivelError",
    "DocumentoNormalizado",
    "DocumentoRef",
    "EntradaInvalidaError",
    "ErroNucleo",
    "EstrategiaAusenteError",
    "Evidencia",
    "EventoExecucao",
    "FalhaProvedorError",
    "GuardrailVioladoError",
    "InstanciacaoIncompletaError",
    "LimitesAnalise",
    "Normalizador",
    "NucleoAnalise",
    "PacoteAnalise",
    "PapelAcesso",
    "Portao",
    "ProjecaoAusenteError",
    "Prompt",
    "RegistradorLog",
    "RegistradorMemoria",
    "RegistroEstrategias",
    "RegistroProjecoes",
    "Regra",
    "ResolvedorNulo",
    "ResultadoAnalise",
    "ResultadoNucleo",
    "SaidaForaDeContratoError",
    "SaneadorVozExterna",
    "SchemaInterno",
    "TipoAnalise",
    "TrechoDocumento",
    "VerificadorAncoras",
    "normalizar_texto",
    "verificar_consumo_do_pacote",
]
