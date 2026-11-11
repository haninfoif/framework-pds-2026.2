# Erros do núcleo. Cada classe existe porque o chamador precisa reagir de forma
# diferente: entrada inválida, falta de instanciação, saída fora do contrato,
# âncora inexistente, acesso negado ou falha do provedor de IA.
#
# Alguns erros herdam de ValueError de propósito: os tratadores de rota que já
# existiam no SAEI convertem ValueError em HTTP 400, então o comportamento
# observável da API não muda quando a falha é da entrada.


class ErroNucleo(Exception):
    """Erro base de tudo o que o núcleo recusa executar."""


class InstanciacaoIncompletaError(ErroNucleo, RuntimeError):
    """Algum slot obrigatório ou alguma garantia de instanciação está ausente."""


class EntradaInvalidaError(ErroNucleo, ValueError):
    """O pedido de análise não forma um pacote mínimo (sem documento, por exemplo)."""


class DocumentoIlegivelError(ErroNucleo, ValueError):
    """O documento existe, mas não há texto canônico que possa ser ancorado."""


class AcessoNegadoError(ErroNucleo):
    """A política de acesso recusou o solicitante ou o destinatário pedido."""


class EstrategiaAusenteError(InstanciacaoIncompletaError):
    """Não há estratégia registrada para o par (análise, tipo de documento)."""


class ProjecaoAusenteError(InstanciacaoIncompletaError):
    """Não há schema de projeção registrado para o par (análise, destinatário)."""


class SaidaForaDeContratoError(ErroNucleo, RuntimeError):
    """A saída do modelo não passou no schema interno ou trouxe conteúdo proibido."""


class AncoragemInvalidaError(ErroNucleo, RuntimeError):
    """Algum item do resultado citou um trecho que não existe no texto normalizado."""


class GuardrailVioladoError(ErroNucleo, RuntimeError):
    """Uma regra de domínio verificável foi desrespeitada pela saída do modelo."""


class FalhaProvedorError(ErroNucleo, RuntimeError):
    """O provedor de IA não devolveu resposta utilizável."""
