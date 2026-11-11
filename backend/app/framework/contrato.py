# O contrato do núcleo.
#
# Este módulo é o único vocabulário que o núcleo e as instâncias compartilham.
# Nada aqui conhece FastAPI, SQLAlchemy, Groq ou o domínio do SAEI: o núcleo
# recebe referências opacas e devolve resultados já projetados.
#
# A assinatura pública que tudo isto sustenta está em nucleo.py:
#
#   executar(contexto, documentos, analise, destinatario) -> ResultadoAnalise

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field

# Identificador é opaco para o núcleo: pode ser um inteiro do banco, um UUID do
# storage ou uma chave composta. Quem resolve é o ContextoProvider (V1).
Identificador = str | int


@dataclass(frozen=True)
class PapelAcesso:
    """Audiência do resultado. O núcleo só compara nomes; quem os define é o domínio."""

    nome: str

    def __post_init__(self) -> None:
        if not self.nome or not self.nome.strip():
            raise ValueError("PapelAcesso exige um nome não vazio.")

    def __str__(self) -> str:  # pragma: no cover - conveniência de log
        return self.nome


@dataclass(frozen=True)
class Acao:
    """
    Ação submetida à política (V3).

    O núcleo usa duas famílias fixas:
      - Acao("analisar", <chave da análise>)
      - Acao("projetar", <nome do papel>)
    Uma instância pode acrescentar ações próprias sem tocar no núcleo.
    """

    nome: str
    parametro: str | None = None

    def __str__(self) -> str:  # pragma: no cover - conveniência de log
        return f"{self.nome}:{self.parametro}" if self.parametro else self.nome


@dataclass(frozen=True)
class TipoAnalise:
    """
    O que se quer produzir (V2). `parametros` é livre: profundidade, idioma,
    quantidade de itens — o núcleo apenas repassa para a estratégia.
    """

    chave: str
    parametros: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.chave or not self.chave.strip():
            raise ValueError("TipoAnalise exige uma chave não vazia.")


@dataclass(frozen=True)
class ContextoRef:
    """
    O que ancora o documento (V1).

    `solicitante` é o ator que pediu a análise, mantido opaco de propósito: o
    núcleo precisa entregá-lo à política antes de ler qualquer conteúdo, mas não
    deve saber se é um usuário do banco, um funcionário de escritório ou um
    cliente. Quem interpreta é a política (V3).
    """

    tipo: str
    identificador: Identificador
    solicitante: Any = field(default=None, repr=False)
    metadados: Mapping[str, Any] = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class DocumentoRef:
    """
    Referência a um documento de entrada.

    `origem` aponta para o conteúdo externo (caminho de arquivo, chave de bucket,
    URL assinada) e é resolvida pelo extrator (F1). `conteudo` já traz o texto
    quando ele nasceu na própria requisição (texto colado na tela).
    """

    identificador: Identificador
    tipo_documento: str
    rotulo: str = ""
    origem: str | None = None
    conteudo: str | None = None


@dataclass(frozen=True)
class Ancora:
    """Prova de origem de um item: documento, página e trecho literal."""

    documento: str
    pagina: int
    trecho: str


@dataclass(frozen=True)
class TrechoDocumento:
    """Um bloco canônico de texto, sempre associado a uma página."""

    documento: str
    pagina: int
    texto: str


@dataclass
class DocumentoNormalizado:
    """
    Documento convertido em texto canônico por página.

    É o produto do PF3: sem ele não existe verificação de âncora possível, porque
    não haveria contra o que conferir o trecho citado.
    """

    identificador: Identificador
    rotulo: str
    tipo_documento: str
    trechos: list[TrechoDocumento] = field(default_factory=list)

    @property
    def pagina_para_texto(self) -> dict[int, str]:
        return {trecho.pagina: trecho.texto for trecho in self.trechos}

    @property
    def texto_completo(self) -> str:
        return "\n".join(trecho.texto for trecho in self.trechos)

    @property
    def vazio(self) -> bool:
        return not self.texto_completo.strip()

    def texto_ancoravel(self) -> str:
        """
        Serialização enviada ao modelo: cabeçalho com o rótulo e marcadores de
        página que ele deve repetir no campo `ancora.pagina`.
        """
        linhas = [f"=== DOCUMENTO: {self.rotulo} (id {self.identificador}) ==="]
        for trecho in self.trechos:
            linhas.append(f"[p. {trecho.pagina}] {trecho.texto}")
        return "\n".join(linhas)


@dataclass
class Contexto:
    """
    Contexto resolvido (V1).

    `registro` é o registro do sujeito/contraparte em forma de dicionário plano:
    o núcleo não interpreta as chaves, apenas as entrega à estratégia e à
    política. É o que permite o mesmo núcleo servir matrícula, caso jurídico ou
    candidatura.
    """

    ref: ContextoRef
    rotulo: str
    registro: dict[str, Any] = field(default_factory=dict)
    metadados: dict[str, Any] = field(default_factory=dict)

    @property
    def solicitante(self) -> Any:
        return self.ref.solicitante


@dataclass(frozen=True)
class Regra:
    """
    Guardrail (V5).

    `enunciado` entra no prompt como proibição explícita. `verificacao`, quando
    existe, é executada sobre a saída interna já validada: guardrail que não
    pode ser checado continua sendo regra, mas deixa de ser só decoração de
    prompt quando ganha verificador.
    """

    identificador: str
    enunciado: str
    verificacao: Callable[[BaseModel], None] | None = field(
        default=None, compare=False, repr=False
    )


class SchemaInterno(BaseModel):
    """
    Base dos schemas internos (V4).

    O núcleo não conhece os campos de cada instância: ele só pergunta onde estão
    as âncoras e quais termos de busca foram pedidos. Isso é o que permite o
    verificador do PF3 e o resolvedor do PF4 funcionarem sem schedule de domínio.
    """

    model_config = ConfigDict(extra="ignore")

    def ancoras(self, documento_padrao: str = "") -> list[Ancora]:
        """
        Toda âncora contida no resultado. Instâncias sobrescrevem.

        `documento_padrao` é o rótulo do documento-alvo, usado quando o modelo
        omitiu o campo `documento` na âncora (o caso mais comum) — assim a âncora
        continua verificável sem exigir do modelo um identificador que ele não vê.
        """
        return []

    def termos_de_busca(self) -> list[str]:
        """Termos externos a resolver (F6). Instâncias sobrescrevem."""
        return []


@dataclass
class PacoteAnalise:
    """
    O pacote de três fontes que a estratégia é obrigada a consumir:

      1. documento-alvo (`alvo` e `documentos_entrada`)
      2. registro do sujeito/contraparte (`contexto.registro` e `documentos_de_contexto`)
      3. base de diretrizes do domínio (`diretrizes`)

    Mais os guardrails do par (análise, destinatário), que também são instrução.
    """

    contexto: Contexto
    alvo: DocumentoNormalizado
    documentos_entrada: list[DocumentoNormalizado]
    documentos_de_contexto: list[DocumentoNormalizado]
    diretrizes: Any  # Fonte de diretrizes (F4); Protocol em protocolos.py
    guardrails: list[Regra] = field(default_factory=list)
    parametros: Mapping[str, Any] = field(default_factory=dict)

    @property
    def documentos(self) -> list[DocumentoNormalizado]:
        return [*self.documentos_entrada, *self.documentos_de_contexto]

    def documento(self, referencia: str) -> DocumentoNormalizado | None:
        """Localiza um documento pelo rótulo ou pelo identificador, para ancoragem."""
        alvo = referencia.strip().lower()
        for documento in self.documentos:
            if str(documento.identificador).lower() == alvo:
                return documento
            if documento.rotulo.strip().lower() == alvo:
                return documento
        return None


@dataclass
class ResultadoNucleo:
    """
    Tudo o que a projeção (V4) recebe. A projeção nunca vê o prompt nem a
    resposta crua do modelo; ela vê o schema interno já validado, as evidências
    já resolvidas e o limite de uso já preenchido pelo núcleo.
    """

    analise: TipoAnalise
    papel: PapelAcesso
    contexto: Contexto
    dados: SchemaInterno
    evidencias: list[Any]
    limite_uso: str
    documentos: list[DocumentoNormalizado]


@dataclass(frozen=True)
class EventoExecucao:
    """Registro de uma execução do ciclo (F9)."""

    analise: str
    papel: str
    contexto: str
    documentos: tuple[str, ...]
    estrategia: str
    provedor: str
    duracao_ms: int
    ancoras: int
    evidencias: int
    sucesso: bool
    limite_uso: str
    erro: str | None = None


@dataclass
class ResultadoAnalise:
    """O que sai do núcleo: já validado, já ancorado e já recortado por audiência."""

    analise: TipoAnalise
    papel: PapelAcesso
    dados: BaseModel
    limite_uso: str
    execucao: EventoExecucao | None = None
