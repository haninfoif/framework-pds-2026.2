# Utilitário de extração de texto em arquivos PDF.
# Responsabilidade única: abrir o arquivo físico salvo em disco, varrer suas páginas
# e consolidar todo o conteúdo textual legível para consumo dos serviços de IA.

import PyPDF2

class PDFExtractor:
    @staticmethod
    def extrair_paginas(caminho_arquivo: str) -> list[tuple[int, str]]:
        """
        Lê o PDF e devolve [(número_da_página, texto)] preservando a página.

        A página é o que torna a âncora verificável: sem ela não haveria como
        conferir o trecho citado contra o original.
        """
        paginas: list[tuple[int, str]] = []
        try:
            # Abre o arquivo em modo binário de leitura (rb) para manipulação pelo PyPDF2
            with open(caminho_arquivo, 'rb') as arquivo:
                leitor = PyPDF2.PdfReader(arquivo)

                for indice, pagina in enumerate(leitor.pages, start=1):
                    texto = pagina.extract_text() or ""
                    if texto.strip():
                        paginas.append((indice, texto))

            return paginas

        except Exception as e:
            # Se o arquivo estiver corrompido ou o caminho for inválido, lança erro legível
            raise ValueError(f"Falha ao ler o arquivo PDF: {str(e)}")

    @staticmethod
    def extrair_texto(caminho_arquivo: str) -> str:
        """Lê o arquivo PDF do disco e devolve o texto bruto concatenado."""
        return "\n".join(texto for _, texto in PDFExtractor.extrair_paginas(caminho_arquivo)).strip()