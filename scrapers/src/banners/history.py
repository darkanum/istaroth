import hashlib
import re
import requests
from bs4 import BeautifulSoup
from src.utils.logger import setup_logger

logger = setup_logger("Banners-Engine")
URL = "https://genshin-impact.fandom.com/api.php?action=parse&page=Wish/History&format=json"

def normalize_name(name):
    name = re.sub(r'\(.*?\)', '', name)
    return re.sub(r'[^a-zA-Z0-9]', '', name).lower()

def parse_html_table(table):
    rows = table.find_all('tr')
    grid = []
    for r_idx, row in enumerate(rows):
        cells = row.find_all(['td', 'th'])
        col_idx = 0
        for cell in cells:
            while len(grid) <= r_idx: grid.append([])
            while len(grid[r_idx]) <= col_idx: grid[r_idx].append(None)
            if grid[r_idx][col_idx] is not None:
                col_idx += 1
                continue
            rowspan = int(cell.get('rowspan', 1))
            colspan = int(cell.get('colspan', 1))
            for i in range(rowspan):
                for j in range(colspan):
                    while len(grid) <= r_idx + i: grid.append([])
                    while len(grid[r_idx + i]) <= col_idx + j: grid[r_idx + i].append(None)
                    grid[r_idx + i][col_idx + j] = cell
            col_idx += colspan
    return grid

def process_banners_timeline(db):
    logger.info("Mapeando histórico cronológico de banners...")
    
    # Monta Fonte da Verdade em memória
    norm_db = {}
    for char in db['characters'].find():
        norm_db[normalize_name(char["name"])] = {"name": char["name"], "rarity": int(char.get("rarity", 4)), "type": "character"}
    for wpn in db['weapons'].find():
        norm_db[normalize_name(wpn["name"])] = {"name": wpn["name"], "rarity": int(wpn.get("rarity", 4)), "type": "weapon"}

    headers = {'User-Agent': 'GenshinWishHistoryBot/1.0'}
    response = requests.get(URL, headers=headers, timeout=20)
    if response.status_code != 200: return None, None

    html_content = response.json()['parse']['text']['*']
    content_hash = hashlib.md5(html_content.encode('utf-8')).hexdigest()
    soup = BeautifulSoup(html_content, 'html.parser')
    
    periods_dict = {}
    tables = soup.find_all('table', class_=lambda c: c and ('wikitable' in c or 'article-table' in c))
    
    for table in tables:
        prev_h = table.find_previous(['h2', 'h3'])
        current_version = prev_h.find(class_='mw-headline').text.strip() if prev_h and prev_h.find(class_='mw-headline') else "Unknown"
        if "Version" not in current_version and "Luna" not in current_version: continue
        
        grid = parse_html_table(table)
        if not grid: continue
        
        wish_col, dur_col, feat_cols = -1, -1, []
        for idx, cell in enumerate(grid[0]):
            if cell:
                txt = cell.get_text(strip=True).lower()
                if 'wish' in txt: wish_col = idx
                elif 'duration' in txt: dur_col = idx
                else: feat_cols.append(idx) 
                
        if wish_col == -1 or not feat_cols: continue
        
        for row in grid[1:]:
            if len(row) <= wish_col: continue
            wish_cell = row[wish_col]
            dur_cell = row[dur_col] if dur_col != -1 and len(row) > dur_col else None
            if not wish_cell: continue
            
            a_tag = wish_cell.find('a')
            banner_name = a_tag.get_text(strip=True) if a_tag and a_tag.get_text(strip=True) else wish_cell.get_text(strip=True)
            banner_name = re.sub(r'\d{4}-\d{2}-\d{2}.*', '', banner_name).strip()
            if not banner_name: continue
            
            img_url = ""
            img = wish_cell.find('img')
            if img:
                img_url = img.get('data-src') or img.get('src') or ""
                img_url = img_url.split('/revision/')[0]
                
            period = re.sub(r'\s+', ' ', dur_cell.get_text(separator=" ").strip()) if dur_cell else "Unknown"
            
            items = {"5_star_characters": [], "4_star_characters": [], "5_star_weapons": [], "4_star_weapons": []}
            for f_col in feat_cols:
                if len(row) > f_col and row[f_col]:
                    for a in row[f_col].find_all('a'):
                        title = a.get('title') or (a.find('img').get('title') if a.find('img') else None) or a.get_text(strip=True)
                        if not title: continue
                        norm_title = normalize_name(title)
                        if norm_title in norm_db:
                            info = norm_db[norm_title]
                            list_key = f"{info['rarity']}_star_{info['type']}s"
                            if info['name'] not in items[list_key]: items[list_key].append(info['name'])

            has_chars = bool(items["5_star_characters"] or items["4_star_characters"])
            has_wpns = bool(items["5_star_weapons"] or items["4_star_weapons"])
            if has_chars and has_wpns: b_type = "chronicled"
            elif has_wpns: b_type = "weapon"
            else: b_type = "character"
            
            dict_key = f"{current_version}::{period}"
            if dict_key not in periods_dict:
                periods_dict[dict_key] = {"version_name": current_version, "banner_period": period, "active_banner": []}
                
            periods_dict[dict_key]["active_banner"].append({
                "name": banner_name, "image_url": img_url, "type": b_type, "items": items
            })
            
    return list(periods_dict.values()), content_hash