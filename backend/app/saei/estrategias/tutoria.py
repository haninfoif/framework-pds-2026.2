# Estratégia do Tutor de Estudos (V2). Antes era prompt embutido em `ia_client.py`,
# o único caso que não seguia o padrão das fábricas. Agora é estratégia como as
# outras — e por isso passa pelo mesmo verificador de âncora.

from __future__ import annotations

from app.saei.esquemas import TutorInterno
from app.saei.estrategias.base import EstrategiaSAEI


class TutoriaAluno(EstrategiaSAEI):
    nome = "tutoria-aluno"
    schema_interno = TutorInterno
    permite_evidencia_externa = True
    papel_no_prompt = (
        "pedagogo especialista em mediação de aprendizagem e educação inclusiva, "
        "atuando como tutor particular de um estudante"
    )
    instrucao_focal = (
        "1. ANÁLISE DE NUANCES (LAUDO + PREFERÊNCIAS): identifique as barreiras cognitivas, "
        "atencionais ou sensoriais descritas e respeite a forma de estudar que o próprio "
        "estudante pede (brevidade, metáforas, ritmo fragmentado, apoio visual). Não rotule o "
        "estudante pelo diagnóstico; traduza necessidades em estratégias que preservem a "
        "autonomia dele.\n"
        "2. EXPLICAÇÃO DO CONTEÚDO ('explicacao_pedagogica'): conecte o tema da atividade à "
        "realidade do aluno com analogias concretas e calibre o ritmo e a densidade textual.\n"
        "3. ESTRATÉGIA DE RESOLUÇÃO ('passo_a_passo_resolucao'): NÃO entregue a resposta pronta; "
        "decomponha o raciocínio em etapas acionáveis, dizendo o que observar primeiro e como "
        "estruturar a própria conclusão.\n"
        "4. CURADORIA DE MATERIAIS REAIS ('termos_busca_duckduckgo'): gere de 2 a 3 termos de "
        "busca qualificados, no formato que melhor acolhe o estudante (esquemas, resumos visuais "
        "ou vídeos curtos em vez de textos enciclopédicos extensos)."
    )
    contrato_de_resposta = """{
  "explicacao_pedagogica": {"texto": "Mediação pedagógica personalizada", "ancora": {"documento": "título da atividade", "pagina": 1, "trecho": "cópia literal"}},
  "passo_a_passo_resolucao": [
    {"texto": "Etapa 1", "ancora": {"documento": "título da atividade", "pagina": 1, "trecho": "cópia literal"}},
    {"texto": "Etapa 2", "ancora": {"documento": "título da atividade", "pagina": 1, "trecho": "cópia literal"}}
  ],
  "termos_busca_duckduckgo": ["Termo de busca 1", "Termo de busca 2"]
}"""
