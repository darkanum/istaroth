# Genshin Wish Parser - System Design Document (SDD)

## 1. Visão Geral
O Genshin Wish Parser é um ecossistema projetado para extrair, normalizar, armazenar e expor dados relacionados ao jogo Genshin Impact. Seu objetivo principal é fornecer um histórico consolidado de banners (Wishes) cruzado com dados precisos de personagens e armas, além de atuar como proxy para importação do histórico pessoal de tiros (wishes) dos usuários direto dos servidores da HoYoverse.

## 2. Arquitetura do Sistema
O projeto adota uma arquitetura orientada a serviços (Microserviços em Monorepo) baseada nos princípios de *Clean Architecture* e *Separation of Concerns*. 

Os componentes são isolados e se comunicam apenas através do banco de dados:
* **Módulo de Extração (Scraper):** Um worker autônomo (Cron) que interage com a MediaWiki API da Fandom.
* **Módulo de API:** Um servidor web RESTful (FastAPI) que serve os dados para o frontend.
* **Camada de Dados:** MongoDB para persistência de documentos complexos (NoSQL).
* **Camada de Observabilidade:** Prometheus para captura de métricas expostas pelas portas `9100` e `9101`.

## 3. Fluxo de Dados (Data Flow)
1. O **Módulo de Extração** acorda no horário agendado (`RUN_TIME`).
2. Ele executa a rotina de Catálogo (`weapons` e `characters`), gerando a "Fonte da Verdade" no banco de dados.
3. Em seguida, executa o motor de Banners (`history`), cruzando os links do histórico com a "Fonte da Verdade" para classificar e tipar os banners retroativamente.
4. O cliente (Frontend) faz uma requisição HTTP para a **API**.
5. A API lê a coleção `banner_history` já consolidada e devolve em milissegundos.

## 4. Stack Tecnológico
* **Backend:** Python 3.10
* **Framework Web:** FastAPI, Uvicorn
* **Scraping:** BeautifulSoup4, Requests
* **Banco de Dados:** MongoDB 6.0
* **Orquestração:** Docker & Docker Compose
* **Monitoramento:** Prometheus Client