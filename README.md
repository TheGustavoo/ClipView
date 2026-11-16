# ClipView

Plataforma SaaS para transformar vídeos longos em clipes curtos com apoio de IA.

> **Status:** fundação em desenvolvimento. O painel possui cadastro/login integrados e upload de arquivos de vídeo para armazenamento local no servidor, com projetos associados ao usuário. A fila assíncrona, inspeção técnica com FFprobe e transcrição inicial de áudio com Whisper foram adicionadas ao código. A primeira seleção automática de cortes baseada em sinais da transcrição está implementada. O painel já possui player autenticado do vídeo original e prévia dos intervalos selecionados. Análise visual de reações, detecção de cenas, renderização final, cobrança e publicação ainda não estão implementados.

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
- **Fila:** Redis + Celery (primeira integração implementada)
- **Worker de mídia:** FFmpeg/FFprobe, faster-whisper e pontuação explicável de trechos em serviço Docker separado
- **Mídia:** FFmpeg e armazenamento compatível com S3 (planejado)
- **Execução:** Docker Compose com migração de banco antes de iniciar API e worker

## Preparar o ambiente para testar

A forma mais simples de testar o processamento de vídeos é executar API, banco de dados, Redis e worker pelo Docker Compose, e abrir o frontend localmente. Assim, o Redis e o worker também ficam ativos quando você enviar um vídeo.

### 1. Inicie os serviços de backend

Requisitos: Docker Desktop (ou Docker Engine) com Docker Compose.

Na raiz do repositório, execute:

```bash
docker compose up --build -d
```

Isso inicia PostgreSQL, Redis, API e worker Celery com FFmpeg/FFprobe e faster-whisper. A API ficará em `http://localhost:8000`. Confira se está respondendo:

```bash
curl http://localhost:8000/health
docker compose ps
```

Na primeira execução, o worker baixa o modelo Whisper configurado (padrão: `small`), o que pode levar algum tempo e baixar centenas de MB. O cache fica preservado em volume Docker. Para acompanhar o processamento e eventuais erros:

```bash
docker compose logs -f api worker
```

### 2. Inicie o frontend

Abra outro terminal, na raiz do repositório, e execute:

```bash
cd apps/web
cp .env.example .env.local  # Windows: copie o arquivo manualmente
npm install
npm run dev
```

Abra `http://localhost:3000`, crie uma conta em `/register` e entre. Na área “Comece um novo projeto”, envie um vídeo MP4, MOV, WebM ou MKV de até 500 MB. Aguarde o worker concluir a transcrição; na primeira execução, o download do modelo pode demorar. Depois, confira as sugestões, ajuste os tempos e use “Pré-visualizar corte”.

### 3. Parar os serviços

No terminal da raiz do projeto:

```bash
docker compose down
```

Esse comando mantém os volumes, incluindo banco de dados, vídeos enviados e cache do modelo. **Não use `docker compose down -v` se quiser preservar esses dados.** As credenciais padrão do Compose são apenas para desenvolvimento local; não exponha essa configuração publicamente.

### 4. Executar os testes automatizados da API (opcional)

Com Python 3.12 ou superior, em outro terminal:

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements-dev.txt
pytest -q
```

Os testes automatizados usam banco SQLite temporário. Eles não substituem o teste manual de upload, transcrição e reprodução descrito acima.

## Endpoints iniciais da API

- `GET /health` — estado da API.
- `POST /auth/register` — cadastro; recebe `name`, `email` e `password` (mínimo 10 caracteres).
- `POST /auth/login` — login; recebe `email` e `password`.
- `GET /auth/me` — perfil autenticado; exige `Authorization: Bearer <access_token>`.
- `GET /projects` — lista somente os projetos do usuário autenticado.
- `GET /projects/{project_id}/video` — reproduz o vídeo do próprio usuário com suporte a requisições HTTP Range, necessário para avançar e retroceder no player.
- `POST /projects/upload` — recebe multipart `file`, valida extensão, assinatura básica do contêiner e tamanho, grava o arquivo e cria um projeto e uma tarefa de processamento na fila.
- `GET /jobs/{job_id}` — consulta o status da tarefa do próprio usuário e retorna metadados técnicos, idioma detectado, transcrição com marcações de tempo e sugestões de cortes pontuadas quando disponíveis. `PATCH /jobs/{job_id}/clips/{clip_index}` atualiza os tempos de início e fim de uma sugestão do próprio usuário.


## Segurança, limitações e direitos de conteúdo

As senhas são armazenadas com hash Argon2 e nunca retornadas pela API. Tokens de acesso são JWT. O frontend mantém o token em cookie `HttpOnly`, inacessível ao JavaScript do navegador.

O upload atual usa armazenamento local no servidor, não armazenamento de objetos redundante. A validação da assinatura identifica alguns contêineres comuns, mas não substitui varredura antimalware. O worker executa FFprobe para extrair duração, formato, codecs e dimensões, extrai a faixa de áudio com FFmpeg e usa faster-whisper para produzir texto com marcações de tempo. A primeira sugestão de cortes usa heurísticas transparentes sobre perguntas, termos de impacto, ênfase, duração e continuidade da fala. O painel permite reproduzir o vídeo original, ajustar e salvar os tempos de início e fim e pré-visualizar cada trecho no player. A geração e exportação de um novo arquivo de vídeo recortado ainda não estão disponíveis. A pontuação é indicativa, não uma previsão de viralização. A transcrição pode consumir bastante CPU e memória; ainda não há análise visual de reações, detecção de cenas nem geração/exportação dos clipes. Configure também limites de corpo no proxy/reverse proxy e quotas por usuário antes de aceitar uploads públicos. Para produção, use armazenamento privado de objetos, URLs assinadas, isolamento de workers, migrações Alembic, PostgreSQL, HTTPS, rate limiting e monitoramento.

O segredo padrão existe apenas para desenvolvimento local; defina `SECRET_KEY` forte e privado em qualquer ambiente compartilhado. Configure origens CORS específicas e revise a proteção CSRF das rotas autenticadas antes de expor o serviço.

A plataforma deverá processar apenas arquivos enviados pelo usuário ou fontes para as quais ele tenha autorização. Integrações com plataformas externas devem respeitar seus termos, APIs e controles de acesso. URLs fornecidas pelo usuário exigem validação contra SSRF, incluindo DNS, IPs privados, redirecionamentos e destinos finais.

Segredos e credenciais nunca devem ser versionados. Use os arquivos `.env.example` como referência e mantenha `.env` local.

## Roadmap

1. Estrutura de monorepo, configuração e documentação
2. API, banco de dados, autenticação e projetos
3. Upload autenticado e armazenamento local inicial
4. Pipeline assíncrono com Redis, Celery, FFprobe e transcrição Whisper
5. Análise audiovisual, reações e detecção de cenas para melhorar as sugestões
6. Editor de cortes e renderização
7. Créditos, pagamentos e publicação social
8. Testes, observabilidade, hardening e deploy

## Licença

A definir antes de qualquer distribuição pública.
