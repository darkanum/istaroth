import os
import time
import schedule
from datetime import datetime
from prometheus_client import start_http_server, Gauge, Counter
from src.config.db import connect_db
from src.catalog.weapons import scrape_weapons
from src.catalog.characters import scrape_characters_pipeline
from src.banners.history import process_banners_timeline
from src.utils.logger import setup_logger

logger = setup_logger("Scraper-Core")

# Inicialização das Métricas do Prometheus para Monitoramento do Sistema
SCRAPER_RUNS_TOTAL = Counter('scraper_execution_total', 'Contador de execuções do pipeline')
CATALOG_CHARACTERS_GAUGE = Gauge('catalog_characters_total', 'Total de personagens armazenados no catálogo')
CATALOG_WEAPONS_GAUGE = Gauge('catalog_weapons_total', 'Total de armas armazenadas no catálogo')
TIMELINE_BANNERS_GAUGE = Gauge('timeline_banners_total', 'Total de períodos de banners mapeados')

# Expõe as métricas na porta isolada 9100
start_http_server(9100)
logger.info("Servidor de métricas do Prometheus do Scraper online na porta 9100")

RUN_TIME = os.getenv("RUN_TIME", "00:05")

def main_job():
    logger.info("=== INICIANDO EXECUÇÃO DO PIPELINE DE EXTRAÇÃO ===")
    SCRAPER_RUNS_TOTAL.inc()
    try:
        db = connect_db()
        
        # Fase 1: Atualizar Catálogo Central (Fontes da Verdade)
        weapons_count = scrape_weapons(db)
        CATALOG_WEAPONS_GAUGE.set(weapons_count)
        
        characters_count = scrape_characters_pipeline(db)
        CATALOG_CHARACTERS_GAUGE.set(characters_count)
        
        # Fase 2: Processar as Linhas do Tempo de Banners baseando-se no novo catálogo
        docs, current_hash = process_banners_timeline(db)
        
        if not docs:
            logger.warning("Nenhum dado retornado do processador de banners.")
            return

        meta = db['scraping_metadata']
        last_run = meta.find_one({"_id": "latest_run_v12"})
        
        if last_run and last_run.get('hash') == current_hash and db['banner_history'].count_documents({}) > 0:
            logger.info("A Wiki Fandom não sofreu alterações desde o último parse. Banco preservado.")
        else:
            logger.info(f"Nova versão detectada na Wiki. Gravando {len(docs)} novos documentos de período...")
            db['banner_history'].delete_many({})
            db['banner_history'].insert_many(docs)
            meta.update_one({"_id": "latest_run_v12"}, {"$set": {"hash": current_hash, "updated_at": datetime.now()}}, upsert=True)
            logger.info("Banco de dados sincronizado com sucesso!")
            
        TIMELINE_BANNERS_GAUGE.set(db['banner_history'].count_documents({}))
        
    except Exception as e:
        logger.critical(f"Falha fatal durante a rotina do pipeline: {str(e)}", exc_info=True)

if __name__ == "__main__":
    logger.info(f"Agendador do Scraper ativado. Rodando diariamente às {RUN_TIME}")
    main_job() # Dispara a primeira carga imediatamente
    
    schedule.every().day.at(RUN_TIME).do(main_job)
    while True:
        schedule.run_pending()
        time.sleep(60)