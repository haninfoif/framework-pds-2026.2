# PF3 — normalização e ancoragem verificável.
#
# Duas metades do mesmo ponto fixo:
#   1. Normalizador: todo documento vira texto canônico com página e trecho,
#      independentemente do formato de origem (F1).
#   2. VerificadorAncoras: cada item do resultado afirma de onde veio e o núcleo
#      CONFERe o trecho contra esse texto canônico. Item sem âncora válida é
#      reprovado — a promessa "não invente" deixa de ser instrução de prompt.

from __future__ import annotations

import re
import unicodedata
from typing import Sequence

from .contrato import Ancora, DocumentoNormalizado, DocumentoRef, SchemaInterno, TrechoDocumento
from .erros import AncoragemInvalidaError, DocumentoIlegivelError
from .protocolos import ExtratorConteudo

_ESPACOS = re.compile(r"\s+")
_CONTROLE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def normalizar_texto(texto: str) -> str:
    """
    Normalização canônica de comparação: sem acento, minúsculo, sem pontuação.

    É usada só pelo verificador (nunca no texto enviado ao modelo), porque a
    comparação precisa tolerar a diferença entre o que a IA copiou e o original
    sem tolerar invenção.
    """
    decomposto = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(ch for ch in decomposto if not unicodedata.combining(ch))
    minusculo = sem_acento.lower()
    apenas_texto = re.sub(r"[^a-z0-9\s]+", " ", minusculo)
    return _ESPACOS.sub(" ", apenas_texto).strip()


class Normalizador:
    """
    Converte DocumentoRef em DocumentoNormalizado usando o extrator que declara
    suportar o formato. A ordem dos extratores é a prioridade da instância.
    """

    def __init__(self, extratores: Sequence[ExtratorConteudo]) -> None:
        self._extratores = list(extratores)

    def normalizar(
        self,
        ref: DocumentoRef,
        limite_caracteres: int | None = None,
    ) -> DocumentoNormalizado:
        if ref.conteudo is not None:
            paginas: list[tuple[int, str]] = [(1, ref.conteudo)]
        else:
            paginas = self._extrair(ref)

        rotulo = ref.rotulo or f"Documento {ref.identificador}"
        trechos: list[TrechoDocumento] = []
        restante = limite_caracteres

        for numero, texto in paginas:
            limpo = _limpar(texto)
            if not limpo:
                continue
            if restante is not None:
                if restante <= 0:
                    break
                limpo = limpo[:restante]
                restante -= len(limpo)
            trechos.append(TrechoDocumento(rotulo, max(1, int(numero)), limpo))

        documento = DocumentoNormalizado(
            identificador=ref.identificador,
            rotulo=rotulo,
            tipo_documento=ref.tipo_documento,
            trechos=trechos,
        )
        if documento.vazio:
            raise DocumentoIlegivelError(
                f"O documento '{rotulo}' não tem texto legível para análise."
            )
        return documento

    def _extrair(self, ref: DocumentoRef) -> list[tuple[int, str]]:
        if not ref.origem:
            raise DocumentoIlegivelError(
                f"O documento '{ref.rotulo or ref.identificador}' não informa origem "
                "nem conteúdo."
            )
        for extrator in self._extratores:
            if extrator.suporta(ref):
                return list(extrator.extrair(ref))
        raise DocumentoIlegivelError(
            f"Nenhum extrator configurado suporta o documento "
            f"'{ref.rotulo or ref.identificador}'."
        )


def truncar_documento(
    documento: DocumentoNormalizado, limite_caracteres: int
) -> DocumentoNormalizado:
    """Aplica o limite de contexto (F7) a um documento já normalizado."""
    trechos: list[TrechoDocumento] = []
    restante = limite_caracteres
    for trecho in documento.trechos:
        if restante <= 0:
            break
        trechos.append(
            TrechoDocumento(
                documento=trecho.documento,
                pagina=trecho.pagina,
                texto=trecho.texto[:restante],
            )
        )
        restante -= len(trecho.texto)
    return DocumentoNormalizado(
        identificador=documento.identificador,
        rotulo=documento.rotulo,
        tipo_documento=documento.tipo_documento,
        trechos=trechos,
    )


def _limpar(texto: str) -> str:
    texto = _CONTROLE.sub(" ", texto or "").replace("\r\n", "\n").replace("\r", "\n")
    linhas = [linha.strip() for linha in texto.split("\n")]
    return "\n".join(linha for linha in linhas if linha).strip()


class VerificadorAncoras:
    """
    Confere cada âncora contra o texto canônico por página.

    Aceita duas formas de conferência, ambas contra o original:
      - o trecho normalizado aparece literalmente na página; ou
      - o trecho cobre pelo menos `cobertura_minima` dos tokens da página
        (tolera uma palavra copiada com erro, não tolera frase inventada).
    """

    def __init__(self, cobertura_minima: float = 0.85) -> None:
        if not 0 < cobertura_minima <= 1:
            raise ValueError("cobertura_minima deve estar entre 0 e 1.")
        self._cobertura_minima = cobertura_minima

    def verificar(
        self,
        dados: SchemaInterno,
        documentos: Sequence[DocumentoNormalizado],
        estrategia: str = "",
        documento_padrao: str = "",
    ) -> int:
        ancoras = dados.ancoras(documento_padrao)
        if not ancoras:
            raise AncoragemInvalidaError(
                "O resultado não trouxe nenhuma âncora verificável"
                + (f" (estratégia '{estrategia}')" if estrategia else "")
                + ". Todo item precisa citar documento, página e trecho do original."
            )

        for ancora in ancoras:
            documento = _localizar(documentos, ancora.documento)
            if documento is None:
                raise AncoragemInvalidaError(
                    f"Âncora aponta para o documento '{ancora.documento}', que não faz "
                    "parte do pacote analisado."
                )

            texto_pagina = documento.pagina_para_texto.get(int(ancora.pagina))
            if texto_pagina is None:
                raise AncoragemInvalidaError(
                    f"Âncora cita a página {ancora.pagina} de '{documento.rotulo}', "
                    f"mas o documento tem {len(documento.trechos)} página(s)."
                )

            if not self._conferir(ancora.trecho, texto_pagina):
                raise AncoragemInvalidaError(
                    f"O trecho citado não existe no texto de '{documento.rotulo}' "
                    f"(p. {ancora.pagina}): \"{_resumir(ancora.trecho)}\". "
                    "Análise sem âncora verificável é recusada."
                )

        return len(ancoras)

    def _conferir(self, trecho: str, texto_pagina: str) -> bool:
        alvo = normalizar_texto(trecho)
        if not alvo:
            return False
        pagina = normalizar_texto(texto_pagina)
        if alvo in pagina:
            return True

        tokens_do_trecho = [token for token in alvo.split(" ") if len(token) > 2]
        if not tokens_do_trecho:
            return False
        tokens_da_pagina = set(pagina.split(" "))
        cobertura = sum(1 for token in tokens_do_trecho if token in tokens_da_pagina) / len(
            tokens_do_trecho
        )
        return cobertura >= self._cobertura_minima


def _localizar(
    documentos: Sequence[DocumentoNormalizado], referencia: str
) -> DocumentoNormalizado | None:
    alvo = normalizar_texto(referencia)
    if not alvo:
        return None
    for documento in documentos:
        if str(documento.identificador).lower() == referencia.strip().lower():
            return documento
        rotulo = normalizar_texto(documento.rotulo)
        # O modelo repete o título que leu no cabeçalho; pequenas diferenças de
        # sufixo/acentuação não podem invalidar a âncora, mas um documento
        # diferente do pacote não pode ser aceito.
        if rotulo == alvo or (rotulo and (rotulo in alvo or alvo in rotulo)):
            return documento
    return None


def _resumir(texto: str, limite: int = 120) -> str:
    texto = _ESPACOS.sub(" ", texto or "").strip()
    return texto if len(texto) <= limite else f"{texto[:limite]}..."
