# Smart Nery's Home

Sistema de automação residencial (TCC) com interface web para controle de dispositivos IoT via comandos de texto e voz, interpretados por IA.

## Visão geral

```text
Usuário
  -> Frontend React/Vite
    -> Backend FastAPI
      -> Postgres (usuários, sessão de auth)
      -> Redis (sessão de login)
      -> Tuya Cloud (dispositivos IoT reais)
      -> n8n (interpretação de linguagem natural via Gemini)
```

O **backend é a fachada única** entre o frontend e o restante do sistema: login, cadastro e verificação de sessão são resolvidos direto no Postgres/Redis; o n8n é usado apenas para interpretar a linguagem natural do usuário (via Gemini) e devolver um comando estruturado, que o backend então executa nos dispositivos Tuya.

## Estrutura do repositório

```text
backend/                 API FastAPI
  src/
    api.py               entrypoint (rotas HTTP)
    core/                config e integrações compartilhadas (Tuya, prompt da IA, Redis)
    iot/                 execução de comandos IoT (dispositivos e cenas)
    voice/               transcrição de áudio
    scripts/             utilitários manuais de diagnóstico (não usados pela API)
    db/                  models e sessão SQLAlchemy
    services/            regras de autenticação e sessão
  alembic/                migrations do banco

frontend/zenith-house/   aplicação React + Vite + TypeScript

N8N-WORKFLOW/             workflow exportado do n8n (interpretação de comandos)

baseknowledge/refactor/   documentação de arquitetura e decisões de refactor
```

## Stack

- **Frontend**: React 18, TypeScript, Vite, React Router, TanStack Query, Tailwind
- **Backend**: FastAPI, SQLAlchemy + Alembic, Redis, httpx
- **Banco**: PostgreSQL
- **IoT**: Tuya OpenAPI (`tuya-connector-python`)
- **IA/NLU**: n8n + Gemini (fora do backend, acessado via webhook)
- **Voz**: `SpeechRecognition` (Google, sem credenciais) + `ffmpeg`

## Pré-requisitos

- Node.js 18+ e npm
- Python 3.11+ (testado com 3.13/3.14)
- `ffmpeg` disponível no `PATH` (necessário para transcrição de voz)
- Acesso a uma instância Postgres e Redis
- Projeto na [Tuya IoT Platform](https://iot.tuya.com) com IoT Core e Smart Home Basic Service assinados
- Instância n8n com o workflow de `N8N-WORKFLOW/AGENTE CASA.json` importado

## Setup do backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# preencha .env com suas credenciais reais (Postgres, Redis, Tuya, n8n)
```

Aplique as migrations do banco:

```bash
python -m alembic upgrade head
```

Suba o servidor:

```bash
python init_iot.py
# ou
uvicorn src.api:app --reload
```

A API sobe em `http://localhost:8000` por padrão (`PORT` no `.env`). Documentação interativa em `/docs`.

### Variáveis de ambiente

Veja [`backend/.env.example`](backend/.env.example) para a lista completa. Blocos principais:

- **Database**: `DATABASE_URL` (formato `postgresql+psycopg2://...`) ou `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASSWORD` como fallback
- **Redis**: `REDIS_HOST`/`REDIS_PORT`/`REDIS_PASSWORD`/`REDIS_DB`/`REDIS_SESSION_TTL` — usado para sessão de login, próprio do backend (distinto de qualquer Redis usado pelo n8n)
- **n8n**: `WEBHOOK_BASE_URL`, `WEBHOOK_MESSAGE_CHAT_RESPONSE`, `N8N_STATUS_CHECK`
- **Segurança backend → n8n**: `N8N_INTERNAL_SECRET_HEADER`/`N8N_INTERNAL_SECRET` — validado como "Header Auth" no node Webhook do n8n, para impedir chamadas diretas de terceiros à automação
- **Tuya**: `TUYA_ACCESS_ID`/`TUYA_ACCESS_SECRET`/`TUYA_ENDPOINT`/`TUYA_UID`/`TUYA_HOME_ID` + IDs de dispositivos e cenas específicos

## Setup do frontend

```bash
cd frontend/zenith-house
npm install
cp .env.example .env
npm run dev
```

Sobe em `http://localhost:8080` (ou porta seguinte livre). O frontend fala **apenas com o backend** — não há chamada direta a n8n ou banco.

Scripts disponíveis: `npm run dev`, `npm run build`, `npm run lint`, `npm run preview`.

## Endpoints principais do backend

| Rota | Descrição |
|---|---|
| `GET /ping` | healthcheck |
| `POST /register_user` | cadastro de usuário (Postgres, senha com bcrypt) |
| `POST /login_user` | autenticação (Postgres) + criação de sessão (Redis) |
| `GET /auth_check_user` | validação de sessão via cookie/header |
| `POST /message_input` | encaminha comando de texto para o n8n e executa ações IoT localmente |
| `POST /voice_transcribe` | recebe áudio gravado, transcreve e devolve o texto |
| `GET /status_check` | proxy autenticado para o webhook de status do n8n (diagnóstico) |

## Fluxos principais

- **Login**: frontend → `POST /login_user` → Postgres valida credenciais → sessão criada no Redis → cookie `session_id`
- **Chat de texto**: frontend → `POST /message_input` → backend valida sessão no Redis → encaminha ao n8n (com o system prompt do agente) → n8n interpreta via Gemini → backend executa comandos IoT retornados
- **Voz**: frontend grava áudio (`MediaRecorder`) → `POST /voice_transcribe` → texto transcrito é enviado pelo mesmo pipeline do chat de texto
- **IoT**: lâmpada e sensor de portão são controlados por DP direto; portão e ar-condicionado são acionados via cenas Tap-to-Run da Tuya

## Documentação adicional

Decisões de arquitetura, inventário de variáveis de ambiente e planos de refactor estão documentados em [`baseknowledge/refactor/`](baseknowledge/refactor/) — leia antes de propor mudanças estruturais. Regras específicas para agentes de IA trabalhando neste repositório estão em [`CLAUDE.md`](CLAUDE.md).
