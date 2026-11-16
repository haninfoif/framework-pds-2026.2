# Estratégias de adaptação de material (V2), visão do professor/coordenador.
# Processamento 100% textual: nenhuma busca externa.

from __future__ import annotations

from app.saei.esquemas import AdaptacaoInterna
from app.saei.estrategias.base import EstrategiaSAEI

_CONTRATO_ADAPTACAO = """{
  "mudancas_sugeridas": [
    {"secao": "Nome da seção do texto original", "acao": "Ação concreta e específica", "ancora": {"documento": "título do material", "pagina": 1, "trecho": "cópia literal"}}
  ],
  "justificativa_inclusiva": {"texto": "Um parágrafo único e direto", "ancora": {"documento": "título do material", "pagina": 1, "trecho": "cópia literal"}},
  "dicas_de_abordagem": [
    {"texto": "Dica prática de mediação", "ancora": {"documento": "título do material", "pagina": 2, "trecho": "cópia literal"}}
  ]
}
Forneça de 3 a 5 ações em "mudancas_sugeridas", todas ligadas a tópicos que existam no texto."""

_REGRAS_DE_OURO = (
    "REGRAS DE OURO:\n"
    "1. ESTRITAMENTE BASEADO NO TEXTO: é proibido inventar aulas, temas, exercícios ou "
    "dinâmicas que não estejam expressamente no documento original.\n"
    "2. ANCORAGEM: toda mudança deve citar a parte exata do texto que está sendo alterada.\n"
    "3. ADAPTAÇÃO DE ESCALA: se o texto for um plano macro (ementa anual, plano de curso), "
    "adapte as regras gerais de avaliação e metodologia apresentadas. Se for um plano micro "
    "(uma única aula), adapte o ritmo e a dinâmica de sala.\n"
)


class AdaptacaoPlanoDeAula(EstrategiaSAEI):
    nome = "adaptacao-plano-de-aula"
    schema_interno = AdaptacaoInterna
    permite_evidencia_externa = False
    instrucao_focal = _REGRAS_DE_OURO + (
        "Foque em adaptar a METODOLOGIA, os RECURSOS e a AVALIAÇÃO presentes no texto. "
        "Traduza as estratégias de ensino originais para formatos inclusivos. Se o documento "
        "citar avaliações somativas ou contínuas, sugira fracionamento ou formatos alternativos "
        "de entrega. Se citar ferramentas práticas (laboratórios, softwares, projetos em grupo), "
        "indique como mediar a participação do estudante específico nelas. Não altere a ementa "
        "nem os objetos de conhecimento (a BNCC deve ser mantida); altere apenas o formato de "
        "entrega e cobrança."
    )
    contrato_de_resposta = _CONTRATO_ADAPTACAO


class AdaptacaoAtividade(EstrategiaSAEI):
    nome = "adaptacao-atividade"
    schema_interno = AdaptacaoInterna
    permite_evidencia_externa = False
    instrucao_focal = _REGRAS_DE_OURO + (
        "Foque na ESTRUTURA DO EXERCÍCIO. Sugira mudanças concretas na formatação do enunciado, "
        "quebra de comandos longos em etapas curtas, substituição de vocabulário abstrato por "
        "concreto e adaptação dos critérios de avaliação da tarefa. Indique exatamente qual "
        "questão ou parágrafo precisa de intervenção."
    )
    contrato_de_resposta = _CONTRATO_ADAPTACAO
