# ClipView

Plataforma SaaS para transformar vídeos longos em clipes curtos com apoio de IA.

> **Status:** fundação em desenvolvimento. O painel possui cadastro/login integrados e upload de arquivos de vídeo para armazenamento local no servidor, com projetos associados ao usuário. Pipeline de IA, edição de cortes, renderização, cobrança e publicação ainda não estão implementados.

## Visão do produto

- Cadastro, autenticação e gestão de usuários
- Projetos e fontes de vídeo autorizadas
- Transcrição e análise audiovisual
- Detecção de momentos relevantes e reações
- Sugestão e revisão de cortes
- Renderização com FFmpeg
- Créditos, planos e pagamentos
- Exportação e publicação em redes sociais

## Arquitetura

- **Frontend:** Next.js, React, TypeScript e Tailwind CSS
- **API:** Python + FastAPI
- **Persistência:** SQLAlchemy com SQLite local ou PostgreSQL configurado por `DATABASE_URL`
- **Armazenamento atual:** diretório local privado configurado por `UPLOAD_DIR`
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
cp .env.example .env       # Windows: copie o arquivo manualmente
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

A API ficará em `http://localhost:8000`. Ela cria as tabelas iniciais automaticamente no startup para facilitar o desenvolvimento local. Os arquivos são gravados em `apps/api/var/uploads` por padrão; esse diretório não deve ser exposto publicamente.

### 2. Inicie o frontend em outro terminal

```bash
cd apps/web
cp .env.example .env.local  # Windows: copie o arquivo manualmente
npm install
npm run dev
```

Abra `http://localhost:3000`. O `API_URL` do `.env.local` deve apontar para a API (`http://localhost:8000` por padrão). O frontend disponibiliza `/register` e `/login`; as rotas proxy guardam o token em cookie `HttpOnly`, `SameSite=Lax` e `Secure` em produção.

Crie uma conta, entre e use a área “Comece um novo projeto” para enviar um vídeo. Formatos aceitos: MP4, MOV, WebM e MKV. Limite padrão: 500 MB por arquivo.

## Endpoints iniciais da API

- `GET /health` — estado da API.
- `POST /auth/register` — cadastro; recebe `name`, `email` e `password` (mínimo 10 caracteres).
- `POST /auth/login` — login; recebe `email` e `password`.
- `GET /auth/me` — perfil autenticado; exige `Authorization: Bearer <access_token>`.
- `GET /projects` — lista somente os projetos do usuário autenticado.
- `POST /projects/upload` — recebe multipart `file`, valida extensão, assinatura básica do contêiner e tamanho, grava o arquivo e cria um projeto para o usuário autenticado.

Para executar os testes automatizados, na pasta `apps/api`, rode `pytest`.

## Segurança, limitações e direitos de conteúdo

As senhas são armazenadas com hash Argon2 e nunca retornadas pela API. Tokens de acesso são JWT. O frontend mantém o token em cookie `HttpOnly`, inacessível ao JavaScript do navegador.

O upload atual usa armazenamento local no servidor, não armazenamento de objetos redundante. A validação da assinatura identifica alguns contêineres comuns, mas não substitui análise completa de mídia com FFmpeg/ffprobe nem varredura antimalware. Configure também limites de corpo no proxy/reverse proxy e quotas por usuário antes de aceitar uploads públicos. Para produção, use armazenamento privado de objetos, URLs assinadas, isolamento de workers, migrações Alembic, PostgreSQL, HTTPS, rate limiting e monitoramento.

O segredo padrão existe apenas para desenvolvimento local; defina `SECRET_KEY` forte e privado em qualquer ambiente compartilhado. Configure origens CORS específicas e revise a proteção CSRF das rotas autenticadas antes de expor o serviço.

A plataforma deverá processar apenas arquivos enviados pelo usuário ou fontes para as quais ele tenha autorização. Integrações com plataformas externas devem respeitar seus termos, APIs e controles de acesso. URLs fornecidas pelo usuário exigem validação contra SSRF, incluindo DNS, IPs privados, redirecionamentos e destinos finais.

Segredos e credenciais nunca devem ser versionados. Use os arquivos `.env.example` como referência e mantenha `.env` local.

## Roadmap

1. Estrutura de monorepo, configuração e documentação
2. API, banco de dados, autenticação e projetos
3. Upload autenticado e armazenamento local inicial
4. Armazenamento privado escalável e pipeline assíncrono
5. Transcrição, análise audiovisual e detecção de momentos
6. Editor de cortes e renderização
7. Créditos, pagamentos e publicação social
8. Testes, observabilidade, hardening e deploy

## Licença

A definir antes de qualquer distribuição pública.
