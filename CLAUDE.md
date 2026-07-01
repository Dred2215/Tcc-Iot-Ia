# CLAUDE.md

## Visao do repositorio

Este repositorio contem um sistema de automacao residencial com quatro blocos principais:

- `frontend/zenith-house`: aplicacao React/Vite usada por usuarios finais
- `backend/src`: API FastAPI que faz proxy para n8n e executa comandos IoT locais
- `N8N-WORKFLOW`: workflow exportado do n8n com login, auth, cadastro e interpretacao de comandos
- `baseknowledge/refactor`: documentacao de arquitetura, limpeza e reestruturacao

## Regras para agentes

- Leia primeiro `baseknowledge/refactor/SYSTEM_ARCHITECTURE.md` e `baseknowledge/refactor/ENV_RESTRUCTURING_AND_REPO_CLEANUP_PLAN.md` antes de propor mudancas grandes.
- Nao introduza secrets, tokens, URLs privadas ou credenciais reais em arquivos versionados.
- Nunca commite `.env`, `backend/secret/*.json`, `__pycache__`, `*.pyc`, `node_modules` ou `dist`.
- Trate o backend como a fachada preferencial entre frontend e n8n. Novas integracoes nao devem aumentar chamadas diretas do frontend para webhooks sem necessidade.
- Preserve os contratos atuais de login, auth check, `message_input` e websockets, a menos que o refactor inclua migracao documentada.
- Quando alterar configuracao, mantenha `.env.example` atualizado.

## Convencoes de codigo

- Prefira mudancas pequenas e localizadas.
- Evite hardcodes de dominio, porta ou rota quando a informacao puder vir da env.
- Ao tocar o backend, mantenha separadas as responsabilidades de proxy HTTP, execucao IoT e validacao de configuracao.
- Ao tocar o frontend, centralize acesso a ambiente e endpoints em modulos de configuracao.
- Ao tocar o workflow do n8n, documente impacto em backend e frontend.

## Fluxos criticos

- Login: frontend -> backend `/login_user` -> n8n `login_user_webhook`
- Auth check: frontend -> backend `/auth_check_user` -> n8n `auth_check`
- Chat: frontend -> backend `/message_input` -> n8n `message_input` -> Tuya via backend
- Voz: frontend Web Speech -> backend websocket -> n8n -> Tuya via backend
- Cadastro: frontend -> webhook `register-user` no estado atual

## Riscos conhecidos

- `frontend/zenith-house/.env` foi versionado e deve ser tratado como incidente de configuracao
- ha artefatos Python gerados versionados no Git
- o backend ainda procura env em `backend/src/.env`
- existem fallbacks hardcoded para dominios antigos
- a porta/configuracao de websocket de voz diverge entre `.env` e `Dockerfile`

## Validacao minima apos mudancas

- backend compila/importa sem erro
- frontend builda ou ao menos passa em lint
- envs necessarias estao documentadas
- fluxos `ping`, `login`, `auth_check`, `message_input` e `ws-voice` continuam coerentes

## Preferencias de refactor

- Priorize seguranca operacional antes de mudancas cosmeticas.
- Priorize remocao de acoplamento e padronizacao de configuracao antes de adicionar features.
- Se houver duvida entre manter compatibilidade e limpar arquitetura, documente a migracao no mesmo PR ou task.
