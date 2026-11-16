# Estratégia do Termômetro de Acessibilidade DUA (V2). Também era prompt
# embutido no client; agora é estratégia registrada, com âncora obrigatória.

from __future__ import annotations

from app.saei.esquemas import AcessibilidadeInterna
from app.saei.estrategias.base import EstrategiaSAEI


class AvaliacaoAcessibilidadeDUA(EstrategiaSAEI):
    nome = "avaliacao-acessibilidade-dua"
    schema_interno = AcessibilidadeInterna
    permite_evidencia_externa = False
    papel_no_prompt = (
        "especialista em Desenho Universal para a Aprendizagem (DUA) e acessibilidade "
        "pedagógica"
    )
    instrucao_focal = (
        "Avalie o nível de acessibilidade geral do material didático (sem depender de laudos "
        "específicos).\n"
        "1. 'score_acessibilidade': número inteiro de 0 a 100, considerando clareza, organização "
        "visual e objetividade do texto.\n"
        "2. 'pontos_positivos': de 2 a 4 pontos fortes. Se não houver, registre explicitamente "
        "'Nenhum ponto positivo de acessibilidade relevante identificado'.\n"
        "3. 'pontos_de_melhoria': de 1 a 3 pontos a aprimorar. Se o texto já for acessível, "
        "registre 'Texto já apresenta excelente estrutura DUA'.\n"
        "4. 'sugestao_imediata': uma dica prática e acionável para o professor aplicar já.\n"
        "O score DEVE ser um inteiro puro (85, nunca '85%' ou '85/100')."
    )
    contrato_de_resposta = """{
  "score_acessibilidade": 85,
  "pontos_positivos": [
    {"texto": "Linguagem direta e objetiva", "ancora": {"documento": "título do material", "pagina": 1, "trecho": "cópia literal"}}
  ],
  "pontos_de_melhoria": [
    {"texto": "Uso de termos técnicos sem explicação prévia", "ancora": {"documento": "título do material", "pagina": 1, "trecho": "cópia literal"}}
  ],
  "sugestao_imediata": {"texto": "Adicione um pequeno glossário no início", "ancora": {"documento": "título do material", "pagina": 1, "trecho": "cópia literal"}}
}
As listas não podem vir vazias."""
