# F1 no SAEI: extrator PDF por página.
#
# O extrator antigo concatenava as páginas e perdia a referência de página — sem
# ela, âncora verificável não existe. O método antigo continua disponível para
# quem só quer o texto corrido.

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from app.core.utils.pdf_extractor import PDFExtractor
from app.framework import DocumentoRef


class ExtratorPDF:
    formatos = (".pdf",)

    def suporta(self, ref: DocumentoRef) -> bool:
        return bool(ref.origem) and Path(ref.origem).suffix.lower() in self.formatos

    def extrair(self, ref: DocumentoRef) -> Sequence[tuple[int, str]]:
        if not ref.origem:
            return []
        return PDFExtractor.extrair_paginas(ref.origem)
