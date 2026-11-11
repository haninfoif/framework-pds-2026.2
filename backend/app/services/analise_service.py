# Análise de texto colado na tela (sem documento persistido).
#
# Continua sendo análise de verdade: o texto entra como documento-alvo com uma
# página, a base de diretrizes e o registro do solicitante entram no pacote, e o
# resultado passa pelo mesmo portão, verificador de âncora e projeção.

from __future__ import annotations

from app.framework import (
    ContextoRef,
    DocumentoRef,
    EntradaInvalidaError,
    NucleoAnalise,
    ResultadoAnalise,
    TipoAnalise,
)
from app.saei.contexto import TIPO_CONTEXTO_LIVRE
from app.saei.papeis import papel_do_usuario


class AnaliseService:
    def __init__(self, nucleo: NucleoAnalise) -> None:
        self.nucleo = nucleo

    def analisar_texto(
        self,
        *,
        texto: str,
        tipo_documento: str,
        analise: TipoAnalise,
        usuario,
        registro: dict | None = None,
    ) -> ResultadoAnalise:
        texto = (texto or "").strip()
        if not texto:
            raise EntradaInvalidaError("O texto enviado para análise está vazio.")

        identificador_usuario = getattr(usuario, "id", "anon")
        return self.nucleo.executar(
            contexto=ContextoRef(
                tipo=TIPO_CONTEXTO_LIVRE,
                identificador=f"usuario:{identificador_usuario}",
                solicitante=usuario,
                metadados=registro or {},
            ),
            documentos=[
                DocumentoRef(
                    identificador=f"texto:{identificador_usuario}",
                    tipo_documento=tipo_documento,
                    rotulo="Texto enviado para análise",
                    conteudo=texto,
                )
            ],
            analise=analise,
            destinatario=papel_do_usuario(usuario),
        )
