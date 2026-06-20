# Genshin Wish Parser - Scraper Service

Este módulo é o motor de dados do projeto. Ele atua como um worker assíncrono que varre a Wiki Oficial da Fandom (via API MediaWiki) para manter o banco de dados sempre atualizado com as versões mais recentes do jogo.

## Responsabilidades
- Catalogar dados profundos de todas as armas e personagens.
- Lidar com matrizes complexas de HTML (mesclagens, rowspans) para extrair materiais de ascensão e multiplicadores de talentos.
- Cruzar dados de texto bruto da Wiki com o catálogo para classificar banners de forma inteligente (`Character`, `Weapon` ou `Chronicled`).

## Estrutura do Módulo
- `/config`: Configurações de banco de dados.
- `/utils`: Ferramentas compartilhadas (Loggers estruturados).
- `/catalog`: Pipelines de extração profunda (A "Fonte da Verdade").
- `/banners`: Motor de classificação temporal.

## Execução
Iniciado pelo orquestrador raiz: `docker-compose up -d scraper`.
Ele executa uma carga inicial imediata ao ser ligado e aguarda o agendamento diário.

## Variáveis de Ambiente
* `MONGO_URI`: String de conexão com o MongoDB.
* `RUN_TIME`: Horário (formato `HH:MM` UTC-5) para disparo do cronjob (Padrão: `00:05`).