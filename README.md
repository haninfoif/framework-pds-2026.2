# SAEI — Sistema de Apoio à Educação Inclusiva

Plataforma com FastAPI + PostgreSQL (backend) e React + Vite (frontend), orquestrada com Docker Compose. As funcionalidades de IA (resumo de documentos, tutor de estudos, adaptação de materiais e Termômetro de Acessibilidade DUA) usam a API da **Groq**.

## Pré-requisitos

- Docker e Docker Compose instalados.

## Configurando as chaves da API da Groq

As chaves ficam no arquivo `.env` na raiz do projeto (ele é ignorado pelo Git, então não vai parar no repositório).

1. Copie o modelo e abra o arquivo para editar:

   ```bash
   cp .env.example .env
   ```

2. **Gere as chaves** em [console.groq.com/keys](https://console.groq.com/keys):
   - Crie uma conta ou faça login em [console.groq.com](https://console.groq.com/);
   - No menu **API Keys**, clique em **Create API Key**;
   - Dê um nome à chave (ex.: `saei-primaria`) e copie o valor (começa com `gsk_`). **A Groq mostra a chave só uma vez** — salve na hora.

3. Preencha o `.env` com duas chaves (pode criar duas chaves distintas no console):

   ```bash
   GROQ_API_KEY=gsk_sua_chave_primaria
   GROQ_API_KEY_B=gsk_sua_chave_reserva
   ```

   - `GROQ_API_KEY` é a **chave primária**, usada em todas as chamadas.
   - `GROQ_API_KEY_B` é a **chave reserva ("plano B")**: se a primária falhar na hora da requisição (chave inválida, cota estourada, instabilidade), o backend tenta a reserva automaticamente. O usuário só vê erro se **as duas** falharem. Se a primária estiver saudável, a reserva não é tocada.

## Executando o sistema

Na raiz do projeto:

```bash
docker compose up -d --build
```

Depois acesse:

| Serviço  | URL                          |
| -------- | ---------------------------- |
| Frontend | http://localhost:5173        |
| API      | http://localhost:8000        |
| Swagger  | http://localhost:8000/docs   |

Para parar: `docker compose down`. Mudanças no `.env` exigem recriar o container do backend: `docker compose up -d` (sem `--build`, basta recriar).

## Núcleo de análise (framework)

As quatro análises de IA (resumo, tutor, adaptação e termômetro DUA) rodam sobre um núcleo extraído do SAEI: `backend/app/framework/` guarda o contrato e o ciclo, e `backend/app/saei/` é a instância do domínio. Rotas, payloads e respostas continuam os mesmos. Contrato, pontos fixos, slots e o passo a passo de instanciação estão em [`backend/app/framework/README.md`](backend/app/framework/README.md).

## Testes

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```
