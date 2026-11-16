# Estratégias de resumo (V2). Os prompts vêm dos antigos `resumo_strategies.py`;
# o que mudou é que agora cada item exige âncora estruturada e o texto do
# documento chega com marcador de página.

from __future__ import annotations

from app.saei.esquemas import ResumoInterno, ResumoLaudoInterno
from app.saei.estrategias.base import EstrategiaSAEI

CONTRATO_RESUMO = """{
  "titulo_documento": "Um título curto para o documento",
  "resumo_geral": {"texto": "O resumo principal", "ancora": {"documento": "título do documento", "pagina": 1, "trecho": "cópia literal"}},
  "pontos_chave": [
    {"texto": "Ponto 1", "ancora": {"documento": "título do documento", "pagina": 1, "trecho": "cópia literal"}},
    {"texto": "Ponto 2", "ancora": {"documento": "título do documento", "pagina": 2, "trecho": "cópia literal"}}
  ],
  "proximos_passos_ou_recomendacoes": {"texto": "O que deve ser feito a partir daqui", "ancora": {"documento": "título do documento", "pagina": 2, "trecho": "cópia literal"}},
  "termos_busca": ["Tópico Principal 1 Khan Academy", "Tópico Principal 2 Brasil Escola"]
}
Devolva no mínimo um item em "pontos_chave". Se não houver tópicos acadêmicos, devolva [] em "termos_busca"."""


class ResumoLaudoMedico(EstrategiaSAEI):
    nome = "resumo-laudo-medico"
    schema_interno = ResumoLaudoInterno
    permite_evidencia_externa = False
    instrucao_focal = (
        "Analise o laudo médico abaixo. O seu objetivo é APENAS RESUMIR os fatos médicos "
        "e o diagnóstico apresentados. É ESTRITAMENTE PROIBIDO criar, deduzir ou sugerir "
        "recomendações próprias. No campo 'proximos_passos_ou_recomendacoes', insira APENAS "
        "o que o médico recomendou expressamente no texto. Se o médico não escreveu nenhuma "
        "recomendação, escreva: 'Nenhuma recomendação médica explícita no laudo.' "
        "No campo 'termos_busca', devolva SEMPRE uma lista vazia []."
    )
    contrato_de_resposta = CONTRATO_RESUMO


class ResumoPlanoDeAula(EstrategiaSAEI):
    nome = "resumo-plano-de-aula"
    schema_interno = ResumoInterno
    permite_evidencia_externa = True
    instrucao_focal = (
        "Analise o plano de aula abaixo. Foque em resumir os objetivos principais, a "
        "metodologia de ensino e como o aluno será avaliado. No campo 'termos_busca', "
        "extraia de 2 a 3 termos de pesquisa focados nos temas centrais da aula."
    )
    contrato_de_resposta = CONTRATO_RESUMO


class ResumoAtividade(EstrategiaSAEI):
    nome = "resumo-atividade"
    schema_interno = ResumoInterno
    permite_evidencia_externa = True
    instrucao_focal = (
        "Analise a atividade escolar abaixo. Faça um breve resumo dos conteúdos e conceitos "
        "principais abordados. No campo 'termos_busca', extraia OBRIGATORIAMENTE de 2 a 3 "
        "termos de busca curtos e diretos sobre os assuntos centrais "
        "(exemplo: ['Equação de 2 grau Khan Academy', 'Fotossintese Brasil Escola'])."
    )
    contrato_de_resposta = CONTRATO_RESUMO


class ResumoPadrao(EstrategiaSAEI):
    nome = "resumo-padrao"
    schema_interno = ResumoInterno
    permite_evidencia_externa = True
    instrucao_focal = (
        "Faça um resumo analítico e objetivo do documento abaixo. No campo 'termos_busca', "
        "extraia de 1 a 3 termos principais caso seja um documento educativo."
    )
    contrato_de_resposta = CONTRATO_RESUMO
