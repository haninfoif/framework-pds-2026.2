# Catálogo de análises do SAEI (V2). A chave é o que a rota pede ao núcleo; os
# parâmetros são livres e a estratégia decide se usa.

from app.framework import TipoAnalise

ANALISE_RESUMO = TipoAnalise("RESUMO")
ANALISE_TUTORIA = TipoAnalise("TUTORIA_ALUNO")
ANALISE_ADAPTACAO = TipoAnalise("ADAPTACAO_MATERIAL")
ANALISE_ACESSIBILIDADE = TipoAnalise("AVALIACAO_ACESSIBILIDADE")
