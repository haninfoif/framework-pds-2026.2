# Escudo e tradutor de erros da API. Sem ele, qualquer erro lançado em um service viraria uma falha genérica interna 500 (Internal Server Error). Ele escuta cada exceção e a converte no código HTTP semântico correspondente.

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    MatriculaObrigatoriaError, MatriculaJaCadastradaError,
    EmailJaEmUsoError, MultiplasContasError,
    CredenciaisInvalidasError, UsuarioNaoEncontradoError,
    PermissaoNegadaError, VinculoJaExistenteError,
    RecursoNaoEncontradoError, CodigoDisciplinaJaExisteError,
    TurmaNaoEncontradaError, DisciplinaNaoEncontradaError
)
from app.framework import (
    AcessoNegadoError,
    AncoragemInvalidaError,
    DocumentoIlegivelError,
    EntradaInvalidaError,
    FalhaProvedorError,
    GuardrailVioladoError,
    InstanciacaoIncompletaError,
    SaidaForaDeContratoError,
)

# Função que acopla todos os interceptadores de erro dentro da aplicação FastAPI.
def registrar_handlers_de_excecao(app: FastAPI):
    
    # Agrupa exceções que resultam em erro 400 (Bad Request)
    @app.exception_handler(MatriculaObrigatoriaError)
    @app.exception_handler(MatriculaJaCadastradaError)
    @app.exception_handler(EmailJaEmUsoError)
    @app.exception_handler(MultiplasContasError)
    @app.exception_handler(VinculoJaExistenteError)
    @app.exception_handler(CodigoDisciplinaJaExisteError)
    async def bad_request_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    # Agrupa exceções que resultam em erro 401 (Unauthorized)
    # Obs: PermissaoNegadaError é registrada apenas no grupo 403 abaixo — antes ela estava
    # declarada nos dois grupos e o registro posterior silenciosamente sobrescrevia o primeiro.
    @app.exception_handler(CredenciaisInvalidasError)
    async def unauthorized_handler(request: Request, exc: CredenciaisInvalidasError):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": str(exc)},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Erro 404 (Not Found)
    @app.exception_handler(UsuarioNaoEncontradoError)
    @app.exception_handler(RecursoNaoEncontradoError)
    @app.exception_handler(TurmaNaoEncontradaError)
    @app.exception_handler(DisciplinaNaoEncontradaError)
    async def not_found_handler(request: Request, exc: UsuarioNaoEncontradoError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    # Erro 403 (Forbidden)
    @app.exception_handler(PermissaoNegadaError)
    async def forbidden_handler(request: Request, exc: Exception):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": str(exc)},
                headers={"WWW-Authenticate": "Bearer"},
            )

    # --- Núcleo de análise ---------------------------------------------------

    # Entrada inválida do núcleo: documento sem texto, texto vazio, referência
    # de contexto inválida. É erro do pedido, não do servidor.
    @app.exception_handler(EntradaInvalidaError)
    @app.exception_handler(DocumentoIlegivelError)
    async def entrada_invalida_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    # O portão do PF2 recusou: mesmo significado de PermissaoNegadaError.
    @app.exception_handler(AcessoNegadoError)
    async def acesso_negado_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc)},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # O núcleo executou, mas o modelo devolveu saída fora do contrato, âncora
    # inexistente, guardrail violado ou o provedor falhou. É falha de fronteira
    # (IA), então 502: a aplicação está no ar, a resposta não é entregável.
    @app.exception_handler(AncoragemInvalidaError)
    @app.exception_handler(SaidaForaDeContratoError)
    @app.exception_handler(GuardrailVioladoError)
    @app.exception_handler(FalhaProvedorError)
    async def resposta_ia_invalida_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": str(exc)},
        )

    # Instanciação incompleta é erro de configuração do servidor, não do usuário.
    @app.exception_handler(InstanciacaoIncompletaError)
    async def instanciacao_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc)},
        )
