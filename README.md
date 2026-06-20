# Genshin Wish Parser & Data Pipeline

![Python](https://img.shields.io/badge/Python-3.10-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![MongoDB](https://img.shields.io/badge/MongoDB-4EA94B?style=for-the-badge&logo=mongodb)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker)
![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=prometheus)

O **Genshin Wish Parser** é um ecossistema backend completo projetado para extrair, normalizar e servir dados estruturados do universo de Genshin Impact. Mais do que um simples agregador, o projeto é um pipeline de dados (ETL) construído sob os princípios de **Clean Architecture** e **Separation of Concerns**.

O sistema contorna as inconsistências de formatação e os bloqueios de segurança (Cloudflare) da Wiki oficial da Fandom utilizando a MediaWiki API e algoritmos avançados de *DOM Traversal* para achatar matrizes HTML complexas (como materiais de ascensão com *rowspans* dinâmicos). Ele constrói uma "Fonte da Verdade" em um banco NoSQL e a utiliza para tipar e classificar o histórico cronológico de banners do jogo de forma 100% autônoma.

## ✨ Principais Funcionalidades

* **Extrator de Catálogo Resiliente:** Um cronjob assíncrono que mapeia profundamente personagens e armas, extraindo status base, multiplicadores de talentos, biografia e materiais, blindado contra duplicação de dados.
* **Motor de Classificação de Banners:** Cruza o histórico de *Wishes* com a base de dados do catálogo em memória para inferir, sem intervenção humana, o tipo do banner (`Character`, `Weapon` ou `Chronicled`).
* **HoYoverse Proxy:** Uma API RESTful que permite importar o log de tiros (wishes) pessoal do usuário diretamente dos servidores oficiais do jogo utilizando a `authkey`.
* **Observabilidade:** Métricas nativas em tempo real expostas para o Prometheus, monitorando o total de execuções do scraper, latência da API e o volume de entidades armazenadas no catálogo.
* **Infraestrutura Modular:** Totalmente conteinerizado com Docker, separando as responsabilidades de extração e roteamento de API em microserviços isolados.