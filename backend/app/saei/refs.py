# Tradução entre o modelo ORM de documento e a referência opaca do núcleo.

from app.framework import DocumentoRef


def referencia_de_documento(documento) -> DocumentoRef:
    return DocumentoRef(
        identificador=documento.id,
        tipo_documento=documento.tipo.value,
        rotulo=documento.titulo,
        origem=documento.caminho_arquivo,
    )
