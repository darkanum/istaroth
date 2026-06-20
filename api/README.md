# Genshin Wish Parser - API Service

Este módulo contém a API RESTful responsável por servir os dados consolidados de Genshin Impact para aplicações cliente (Frontend). É construída em **FastAPI**, focando em alta performance e documentação nativa.

## Responsabilidades
- Servir o histórico completo de banners (`/history`).
- Atuar como proxy para o servidor da HoYoverse para importação de tiros de usuários (`/import`).
- Expor métricas de uso e latência para o Prometheus.

## Pré-requisitos
- Docker e Docker Compose.
- MongoDB em execução (gerenciado pelo orquestrador raiz).

## Execução e Setup
O serviço foi projetado para rodar via Docker Compose na raiz do projeto.
Caso deseje rodar localmente para desenvolvimento:
1. `pip install -r requirements.txt`
2. Configure a variável de ambiente: `MONGO_URI=mongodb://localhost:27017/`
3. Inicie o servidor: `uvicorn src.main:app --reload --port 8000`

## Variáveis de Ambiente
* `MONGO_URI`: String de conexão com o MongoDB. (Padrão: `mongodb://genshin_mongodb:27017/?serverSelectionTimeoutMS=5000`)

## Monitoramento
A API expõe métricas nativas do Prometheus na porta `9101`.