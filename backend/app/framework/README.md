# Núcleo de análise documental assistida

Framework extraído do SAEI. Domínio: análise de documentos em que o resultado é
condicionado por um registro de sujeito e por uma base de diretrizes, entregue a
públicos diferentes e rastreável ao texto original.

Não é wrapper de LLM, gerenciador de arquivos nem CRUD com botão de IA: o núcleo
segura apenas o ciclo, o portão com projeção, a ancoragem verificável e a
ausência de voz própria da IA.

## O contrato

```python
executar(
    contexto: ContextoRef,            # V1 — o que ancora o documento
    documentos: list[DocumentoRef],   # 1..N
    analise: TipoAnalise,             # V2 — tipo + objetivo
    destinatario: PapelAcesso         # PF2 — para quem é o resultado
) -> ResultadoAnalise                 # V4, já validado e projetado
```

A aplicação chama uma vez. Nas lacunas, o núcleo chama o código da aplicação.

## Pontos fixos: o que cada um verifica

| Ponto | Responsabilidade | Verificação |
|---|---|---|
| **PF1** `nucleo.py` | executa o ciclo na ordem fixa (contexto → portão → normalização → pacote → estratégia → IA → schema → âncoras → evidência → projeção → aviso → registro) | cada estratégia é executada contra um pacote de prova no boot; se o prompt não contiver o documento-alvo e a base de diretrizes, o núcleo não inicia |
| **PF2** `portao.py` | autoriza antes de ler conteúdo e projeta por audiência | política é consultada antes da normalização; a saída é o schema da audiência (sem schema, sem entrega) |
| **PF3** `normalizacao.py` | texto canônico por página + âncora estruturada | cada trecho é conferido contra a página; item sem âncora válida reprova a análise inteira |
| **PF4** `evidencia.py` | termos no modelo, fontes no núcleo; limite de uso sempre presente | URL que não veio de um resolvedor (e não é citação do original) é recusada; aviso vazio é erro de instanciação |

## Slots obrigatórios (sem default)

```python
ContextoProvider.resolver(ref) -> Contexto
ContextoProvider.carregar_documentos_de_contexto(contexto) -> list[DocumentoNormalizado]
Estrategia.construir(pacote) -> Prompt
Politica.autorizar(solicitante, contexto, acao) -> bool
Projecao(papel).projetar(entrada) -> BaseModel
Guardrails.regras(analise, papel) -> list[Regra]
```

Também são exigidos na construção: `ProvedorIA.gerar(prompt) -> str`, uma base de
diretrizes (`obter(contexto)` ou `para_prompt()`), um `Normalizador` e um
`RegistroEstrategias`/`RegistroProjecoes` consistentes.

## Pontos flexíveis e defaults no repositório

| Ponto | Default no SAEI |
|---|---|
| F1 extrator | `saei/extratores.py` (PDF por página, via `PDFExtractor`) |
| F2 provedor | `services/ia/ia_client.py` (Groq primária + reserva, modelo por `GROQ_MODEL`) |
| F3 estratégias | `saei/estrategias/` com fallback por análise |
| F4 diretrizes | `saei/diretrizes.py` sobre `diretrizes_inclusao.json` |
| F5 armazenamento | `core/utils/arquivo_storage.py` (inalterado, fora do núcleo) |
| F6 evidência | `saei/evidencia.py` (DuckDuckGo); `resolver_evidencia=False` desliga |
| F7 limites | `saei/composicao.py` (`LimitesAnalise` por análise) |
| F8 limite de uso | `ConfiguracaoNucleo.aviso_padrao` + `aviso_por_analise` |
| F9 registro | `RegistradorLog` (log da aplicação) |

## Como instanciar

1. Subclasse/seu objeto para cada slot, sem importar nada além de `app.framework`.
2. `RegistroEstrategias` com um fallback `"*"` por análise.
3. `RegistroProjecoes` com o schema de cada par (análise, papel).
4. `NucleoAnalise(...)` — se faltar slot, estratégia que ignore o pacote ou
   análise sem projeção, a construção falha na hora.

Exemplo completo: `backend/app/saei/composicao.py`. A instância SAEI inclui ainda
camada de controle (`api/routers/ia.py`) e de dados (`repositories/`), que
continuam sendo responsabilidade da aplicação, não do framework.

## Testes

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```
