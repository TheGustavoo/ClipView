# ClipView

Plataforma SaaS para transformar vídeos longos em clipes curtos com apoio de IA.

> **Status:** fundação inicial em desenvolvimento. Os módulos de ingestão, análise multimodal, seleção automática, renderização, cobrança e publicação ainda não estão implementados em produção.

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
- **Persistência:** PostgreSQL
- **Fila:** Redis + Celery
- **Mídia:** FFmpeg e armazenamento compatível com S3
- **Execução:** Docker Compose

## Segurança e direitos de conteúdo

A plataforma deverá processar apenas arquivos enviados pelo usuário ou fontes para as quais ele tenha autorização. Integrações com plataformas externas devem respeitar seus termos, APIs e controles de acesso. URLs fornecidas pelo usuário exigem validação contra SSRF, incluindo DNS, IPs privados, redirecionamentos e destinos finais.

Segredos e credenciais nunca devem ser versionados. Use `.env.example` como referência e mantenha `.env` local.

## Desenvolvimento

A configuração executável será documentada à medida que os serviços forem adicionados e testados. Não considere este repositório pronto para produção.

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
