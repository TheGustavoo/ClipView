# ClipView

Plataforma SaaS para transformar vídeos longos em clipes curtos com apoio de IA.

> **Status:** fundação em desenvolvimento. O painel inicial já possui páginas de cadastro e login integradas à API por rotas proxy do Next.js, com sessão em cookie HttpOnly. Upload persistente, processamento com IA, renderização, cobrança e publicação ainda não estão implementados em produção.

## Visão do produto

- Cadastro, autenticação e gestão de usuários
- Projetos e fontes de vídeo autorizadas
- Transcrição e análise audiovisual
- Detecção de momentos relevantes e reações
- Sugestão e revisão de cortes
- Renderização com FFmpeg
- Créditos, planos e pagamentos
- Exportação e publicação em redes sociais

## Arquitetura planejada

- **Frontend:** Next.js, React, TypeScript e Tailwind CSS
- **API:** Python + FastAPI
- **Persistência:** SQLAlchemy com SQLite local ou PostgreSQL configurado por `DATABASE_URL`
- **Fila:** Redis + Celery (planejado)
- **Mídia:** FFmpeg e armazenamento compatível com S3 (planejado)
- **Execução:** Docker Compose (planejado)

## Rodar localmente

Requisitos: Node.js 20 ou superior, npm e Python 3.12 ou superior.

### 1. Inicie a API

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

A API ficará em `http://localhost:8000`. Ela cria as tabelas iniciais automaticamente no startup para facilitar o desenvolvimento local.

### 2. Inicie o frontend em outro terminal

```bash
cd apps/web
cp .env.example .env.local  # Windows: copie o arquivo manualmente
npm install
npm run dev
```

Abra `http://localhost:3000`. O `API_URL` do `.env.local` deve apontar para a API (`http://localhost:8000` por padrão). O frontend disponibiliza `/register` e `/login`; as rotas proxy guardam o token em cookie `HttpOnly`, `SameSite=Lax` e `Secure` em produção.

O painel exige uma sessão válida. O seletor de arquivo ainda apenas mostra o nome localmente e não envia o vídeo para um servidor.

## Endpoints iniciais da API

- `GET /health` — estado da API.
- `POST /auth/register` — cadastro; recebe `name`, `email` e `password` (mínimo 10 caracteres).
- `POST /auth/login` — login; recebe `email` e `password`.
- `GET /auth/me` — perfil autenticado; exige `Authorization: Bearer <access_token>`.

Para executar os testes automatizados, na pasta `apps/api`, rode `pytest`.

## Segurança e direitos de conteúdo

As senhas são armazenadas com hash Argon2 e nunca retornadas pela API. Tokens de acesso são JWT. O frontend mantém o token em cookie `HttpOnly`, inacessível ao JavaScript do navegador. O segredo padrão existe apenas para desenvolvimento local; defina `SECRET_KEY` forte e privado em qualquer ambiente compartilhado.

Para produção, substitua a criação automática de tabelas por migrações versionadas (Alembic), use PostgreSQL, configure HTTPS, limites de tentativas de login, monitoramento e política de recuperação de conta. Configure origens CORS específicas e revise a proteção CSRF das rotas autenticadas antes de expor o serviço.

A plataforma deverá processar apenas arquivos enviados pelo usuário ou fontes para as quais ele tenha autorização. Integrações com plataformas externas devem respeitar seus termos, APIs e controles de acesso. URLs fornecidas pelo usuário exigem validação contra SSRF, incluindo DNS, IPs privados, redirecionamentos e destinos finais.

Segredos e credenciais nunca devem ser versionados. Use `.env.example` como referência e mantenha `.env` local.

## Roadmap inicial

1. Estrutura de monorepo, configuração e documentação
2. API, banco de dados, autenticação e projetos
3. Upload seguro e armazenamento de mídia
4. Pipeline assíncrono de transcrição e análise audiovisual
5. Detecção de momentos e editor de cortes
6. Renderização, exportação e histórico
7. Créditos, pagamentos e publicação social
8. Testes, observabilidade, hardening e deploy

## Licença

A definir antes de qualquer distribuição pública.
