from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from prometheus_client import start_http_server, Counter, Histogram
from src.utils.logger import setup_logger
import requests
import urllib.parse
import time
import os

logger = setup_logger("API")

# Inicialização do Monitoramento (Métricas Prometheus)
API_REQUESTS_TOTAL = Counter('api_requests_total', 'Total de requisições recebidas', ['method', 'endpoint', 'status'])
API_REQUEST_LATENCY = Histogram('api_request_duration_seconds', 'Latência das requisições', ['endpoint'])

# Inicializa o servidor de monitoramento na porta isolada 9101
start_http_server(9101)
logger.info("Servidor de Monitoramento do Prometheus iniciado na porta 9101")

app = FastAPI(title="Genshin Wish Importer API")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/?serverSelectionTimeoutMS=5000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class WishRequest(BaseModel):
    url: str

@app.get("/health")
def health_check():
    API_REQUESTS_TOTAL.labels(method='GET', endpoint='/health', status='200').inc()
    return {"status": "healthy", "message": "API rodando perfeitamente!"}

@app.get("/history")
def get_banner_history():
    start_time = time.time()
    try:
        client = MongoClient(MONGO_URI)
        db = client['genshin_data']
        collection = db['banner_history']
        
        cursor = collection.find({}, {"_id": 0})
        banners_list = list(cursor)
        
        if not banners_list:
            API_REQUESTS_TOTAL.labels(method='GET', endpoint='/history', status='404').inc()
            raise HTTPException(status_code=404, detail="Nenhum dado encontrado no banco.")
            
        API_REQUESTS_TOTAL.labels(method='GET', endpoint='/history', status='200').inc()
        API_REQUEST_LATENCY.labels(endpoint='/history').observe(time.time() - start_time)
        return {"banners": banners_list}
        
    except Exception as e:
        logger.error(f"Erro ao buscar histórico de banners: {str(e)}")
        API_REQUESTS_TOTAL.labels(method='GET', endpoint='/history', status='500').inc()
        raise HTTPException(status_code=500, detail=f"Erro interno no banco de dados.")

@app.post("/import")
def import_wishes(wish_request: WishRequest):
    start_time = time.time()
    user_url = wish_request.url
    parsed_url = urllib.parse.urlparse(user_url)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    
    if 'authkey' not in query_params:
        API_REQUESTS_TOTAL.labels(method='POST', endpoint='/import', status='400').inc()
        raise HTTPException(status_code=400, detail="Authkey não encontrada na URL.")

    base_api_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
    gacha_types = ['100', '200', '301', '302']
    all_wishes = []

    try:
        for gacha_type in gacha_types:
            end_id = '0'
            has_more = True
            
            while has_more:
                params = {k: v[0] for k, v in query_params.items()} 
                params['gacha_type'] = gacha_type
                params['size'] = '20'
                params['end_id'] = end_id
                
                response = requests.get(base_api_url, params=params)
                data = response.json()
                
                if data.get('retcode') != 0:
                    API_REQUESTS_TOTAL.labels(method='POST', endpoint='/import', status='400').inc()
                    raise HTTPException(status_code=400, detail=f"Erro HoYoverse: {data.get('message')}")
                    
                wish_list = data['data']['list']
                if not wish_list:
                    has_more = False
                else:
                    all_wishes.extend(wish_list)
                    end_id = wish_list[-1]['id']
                    time.sleep(0.5) 
                    
        API_REQUESTS_TOTAL.labels(method='POST', endpoint='/import', status='200').inc()
        API_REQUEST_LATENCY.labels(endpoint='/import').observe(time.time() - start_time)
        logger.info(f"Importação concluída com sucesso. Total de {len(all_wishes)} wishes lidas.")
        return {"status": "success", "total_wishes": len(all_wishes), "data": all_wishes}

    except requests.RequestException as e:
        logger.error(f"Erro de comunicação com a HoYoverse: {str(e)}")
        API_REQUESTS_TOTAL.labels(method='POST', endpoint='/import', status='502').inc()
        raise HTTPException(status_code=502, detail="Falha ao comunicar com os servidores da HoYoverse.")