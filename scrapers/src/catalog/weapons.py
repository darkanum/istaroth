import re
import requests
from bs4 import BeautifulSoup
from src.utils.logger import setup_logger

logger = setup_logger("Catalog-Weapons")
API_URL = "https://genshin-impact.fandom.com/api.php"

def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()

def extract_image(tag):
    if not tag: return ""
    url = tag.get('data-src') or tag.get('src') or ""
    return url.split('/revision/')[0] if url else ""

def get_soup_api(page_name):
    params = {"action": "parse", "page": page_name, "format": "json"}
    headers = {'User-Agent': 'GenshinDatabaseBot/3.0'}
    try:
        response = requests.get(API_URL, params=params, headers=headers, timeout=20)
        if response.status_code == 200:
            data = response.json()
            if 'parse' in data and 'text' in data['parse']:
                return BeautifulSoup(data['parse']['text']['*'], 'html.parser')
    except Exception as e:
        logger.error(f"Falha na API ao buscar {page_name}: {e}")
    return None

def scrape_weapons(db):
    logger.info("Iniciando extração do catálogo de armas...")
    weapons_coll = db['weapons']
    weapons_coll.delete_many({})
    
    weapon_types = ["Bow", "Catalyst", "Claymore", "Polearm", "Sword"]
    total_count = 0
    
    for w_type in weapon_types:
        soup = get_soup_api(w_type)
        if not soup: continue
        
        count = 0
        tables = soup.find_all('table', class_=lambda c: c and ('article-table' in c or 'wikitable' in c))
        for table in tables:
            rows = table.find_all('tr')[1:] 
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) < 4: continue
                
                a_tag = cols[1].find('a')
                if not a_tag: continue
                name = a_tag.get_text(strip=True)
                
                img_cell = cols[0]
                rarity = "4-star"
                r_html = str(row).lower()
                if "5_star" in r_html or "5 star" in r_html or "bg-5star" in r_html: rarity = "5-star"
                elif "4_star" in r_html or "4 star" in r_html or "bg-4star" in r_html: rarity = "4-star"
                elif "3_star" in r_html or "3 star" in r_html or "bg-3star" in r_html: rarity = "3-star"

                texts = [clean_text(c.text) for c in cols]
                base_attack = texts[2] if len(texts) > 2 else "0"
                second_stat = texts[3] if len(texts) > 3 else ""
                passive = texts[4] if len(texts) > 4 else ""

                weapon_data = {
                    "name": name,
                    "overview": f"A {rarity} {w_type}.",
                    "secondary_title": "",
                    "data-image-key": extract_image(img_cell.find('img')),
                    "base_attack": int(re.sub(r'\D', '', base_attack)) if re.search(r'\d', base_attack) else 0,
                    "2nd_stat": second_stat,
                    "quality": rarity,
                    "weapon_type": w_type,
                    "passive_ability": passive,
                    "rarity": int(rarity[0]) if rarity[0].isdigit() else 4,
                    "type": "weapon"
                }
                weapons_coll.update_one({"name": name}, {"$set": weapon_data}, upsert=True)
                count += 1
                total_count += 1
        logger.info(f"Categoria {w_type}s finalizada: {count} itens inseridos.")
    return total_count