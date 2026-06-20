import re
import time
import requests
from bs4 import BeautifulSoup
from src.utils.logger import setup_logger

logger = setup_logger("Catalog-Characters")
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
        logger.error(f"Erro ao buscar página {page_name}: {e}")
    return None

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

def extract_materials_from_cell(cell):
    materials = []
    cards = cell.find_all(['div', 'span'], class_=lambda c: c and 'card_container' in c)
    if cards:
        for card in cards:
            a_tag = card.find('a')
            if not a_tag: continue
            name = a_tag.get('title') or a_tag.get_text(strip=True)
            qty_tag = card.find('span', class_=lambda c: c and 'card_text' in c)
            qty_text = clean_text(qty_tag.text) if qty_tag else "1"
            qty_match = re.search(r'[\d,]+', qty_text)
            qty = int(qty_match.group().replace(',', '')) if qty_match else 1
            if name: materials.append({"name": name, "quantity": qty})
    else:
        for a in cell.find_all('a'):
            name = a.get('title') or a.get_text(strip=True)
            if name and "Mora" not in name: 
                materials.append({"name": name, "quantity": 1})
    return materials

def parse_talent_scaling(table):
    grid = parse_html_table(table)
    if not grid or len(grid) < 2: return []
    headers = grid[0]
    levels = []
    level_indices = {}
    seen_headers = set()
    
    for idx, cell in enumerate(headers):
        if cell and id(cell) not in seen_headers:
            seen_headers.add(id(cell))
            match = re.search(r'Level\s*(\d+)', clean_text(cell.text), re.IGNORECASE)
            if match: level_indices[idx] = int(match.group(1))

    level_data = {lvl: [] for lvl in level_indices.values()}
    for row in grid[1:]:
        if not row[0]: continue
        attr_name = clean_text(row[0].text)
        seen_cells = set()
        for idx, lvl in level_indices.items():
            if idx < len(row) and row[idx]:
                cell = row[idx]
                if id(cell) not in seen_cells:
                    seen_cells.add(id(cell))
                    val = clean_text(cell.text)
                    level_data[lvl].append(f"{attr_name}: {val}")
                
    for lvl, damages in level_data.items():
        levels.append({"level": lvl, "damage": " | ".join(damages)})
    return levels

def scrape_characters_pipeline(db):
    logger.info("Iniciando pipeline de extração de personagens...")
    chars_coll = db['characters']
    chars_coll.delete_many({})
    
    soup = get_soup_api("Character/List")
    if not soup: return 0

    tables = soup.find_all('table', class_='article-table')
    if not tables: return 0

    char_links = []
    for row in tables[0].find_all('tr')[1:]:
        cols = row.find_all(['td', 'th'])
        if len(cols) < 2: continue
        a_tag = cols[1].find('a')
        if not a_tag: continue
        name = a_tag.get_text(strip=True)
        href = a_tag.get('href')
        if not href or "Traveler" in name: continue
        
        page_name = href.split('/wiki/')[-1]
        img_tag = cols[0].find('img')
        
        char_links.append({"name": name, "page_name": page_name, "thumbnail": extract_image(img_tag)})

    logger.info(f"Encontrados {len(char_links)} personagens. Baixando perfis...")

    total_characters = 0
    for idx, char in enumerate(char_links):
        soup = get_soup_api(char['page_name'])
        if not soup: continue
        
        infobox = soup.find('aside', class_='portable-infobox')
        def get_info(ds):
            if not infobox: return ""
            item = infobox.find(attrs={"data-source": ds})
            if item:
                val_div = item.find('div', class_='pi-data-value')
                if val_div: return clean_text(val_div.get_text(separator=' '))
            return ""

        rarity = "4-star"
        r_div = infobox.find(attrs={"data-source": "quality"}) if infobox else None
        if r_div and ("5_star" in str(r_div).lower() or "5 star" in str(r_div).lower()): rarity = "5-star"

        overview = ""
        content_div = soup.find('div', class_='mw-parser-output')
        if content_div:
            for p in content_div.find_all('p', recursive=False):
                if p.text.strip() and not p.find('aside'):
                    overview = clean_text(p.text)
                    break

        images_dict = {"card": char['thumbnail'], "wish": "", "in_game": ""}
        if content_div:
            for img in content_div.find_all('img'):
                alt = img.get('alt', '').lower()
                if 'wish' in alt or 'gacha' in alt: images_dict['wish'] = extract_image(img)
                if 'in-game' in alt or 'model' in alt: images_dict['in_game'] = extract_image(img)

        affiliations = [a.strip() for a in get_info("affiliation").split(',')] if get_info("affiliation") else []
        titles = [t.strip() for t in get_info("title").split(',')] if get_info("title") else []

        # Matrizes de Ascensão
        ascension_data = {"ascension_stages": []}
        asc_head = soup.find(id=re.compile(r'Ascensions?'))
        if asc_head:
            asc_table = asc_head.find_next('table', class_='wikitable')
            if asc_table:
                grid = parse_html_table(asc_table)
                for row in grid[1:]:
                    if len(row) < 3 or not row[0]: continue
                    stage_match = re.search(r'\d+', clean_text(row[0].text))
                    if stage_match:
                        stage_num = int(stage_match.group())
                        materials = []
                        seen_cells = set()
                        for cell in row[1:]:
                            if cell is None or id(cell) in seen_cells: continue
                            seen_cells.add(id(cell))
                            materials.extend(extract_materials_from_cell(cell))
                        if not any(s['stage'] == stage_num for s in ascension_data["ascension_stages"]):
                            ascension_data["ascension_stages"].append({"stage": stage_num, "materials": materials})

        # Talentos
        talents_data = {
            "normal_attack": {"name": "", "description": "", "levels": []},
            "elemental_skill": {"name": "", "description": "", "levels": []},
            "elemental_burst": {"name": "", "description": "", "levels": []},
            "talent_upgrade_materials": {"normal_attack": [], "elemental_skill": [], "elemental_burst": []}
        }
        
        talents_head = soup.find(id=re.compile(r'Talents?|Skills?'))
        if talents_head:
            h2 = talents_head.find_parent('h2')
            if h2:
                curr = h2.find_next_sibling()
                skill_idx = 0
                keys = ["normal_attack", "elemental_skill", "elemental_burst"]
                while curr and curr.name != 'h2' and skill_idx < 3:
                    if curr.name == 'h3':
                        current_key = keys[skill_idx]
                        talents_data[current_key]["name"] = clean_text(curr.text)
                        desc_texts = []
                        sib = curr.find_next_sibling()
                        while sib and sib.name not in ['h3', 'h2', 'table']:
                            if sib.name in ['p', 'div']: desc_texts.append(clean_text(sib.text))
                            sib = sib.find_next_sibling()
                        talents_data[current_key]["description"] = "\n".join(desc_texts).strip()
                        if sib and sib.name == 'table' and 'wikitable' in sib.get('class', []):
                            talents_data[current_key]["levels"] = parse_talent_scaling(sib)
                        skill_idx += 1
                    curr = curr.find_next_sibling()

        # Upgrade de Talentos
        upg_head = soup.find(id=re.compile(r'Talent_Leveling|Talent_Upgrading'))
        if upg_head:
            upg_table = upg_head.find_next('table', class_='wikitable')
            if upg_table:
                grid = parse_html_table(upg_table)
                general_materials = []
                for row in grid[1:]:
                    if not row or not row[0]: continue
                    lvl_match = re.search(r'\d+', clean_text(row[0].text))
                    if lvl_match:
                        lvl = int(lvl_match.group())
                        mats = []
                        seen_cells = set()
                        for cell in row[1:]:
                            if cell is None or id(cell) in seen_cells: continue
                            seen_cells.add(id(cell))
                            mats.extend(extract_materials_from_cell(cell))
                        general_materials.append({"level": lvl, "materials": mats})
                talents_data["talent_upgrade_materials"] = {
                    "normal_attack": general_materials, "elemental_skill": general_materials, "elemental_burst": general_materials
                }

        # Constelações
        constellations_data = []
        const_head = soup.find(id=re.compile(r'Constellations?'))
        if const_head:
            h2 = const_head.find_parent('h2')
            if h2:
                curr = h2.find_next_sibling()
                c_idx = 1
                while curr and curr.name != 'h2' and c_idx <= 6:
                    if curr.name == 'h3':
                        c_name = clean_text(curr.text)
                        desc_texts = []
                        sib = curr.find_next_sibling()
                        while sib and sib.name not in ['h3', 'h2', 'table']:
                            if sib.name in ['p', 'div']: desc_texts.append(clean_text(sib.text))
                            sib = sib.find_next_sibling()
                        constellations_data.append({"name": c_name, "description": "\n".join(desc_texts).strip(), "level": c_idx})
                        c_idx += 1
                    curr = curr.find_next_sibling()

        char_data = {
            "name": char['name'], "overview": overview, "secondary_title": titles[0] if titles else "",
            "images": images_dict, "data-image-key": char['thumbnail'], "quality": rarity,
            "weapon_type": get_info("weapon"), "element": get_info("element"), "model_type": get_info("model"),
            "team_bonus": get_info("region"), "character_roles": [],
            "bio": {
                "birthday": get_info("birthday"), "constellation": get_info("constellation"),
                "region": get_info("region"), "affiliations": affiliations, "specialty": get_info("dish"), "namecard": get_info("namecard")
            },
            "release_date": get_info("releaseDate"), "additional_titles": titles[1:] if len(titles) > 1 else [],
            "ascension_materials": ascension_data, "talents": talents_data, "contelation": constellations_data,
            "rarity": int(rarity[0]) if rarity[0].isdigit() else 4, "type": "character"
        }
        chars_coll.insert_one(char_data)
        total_characters += 1
        time.sleep(0.1)
        
    logger.info(f"Catálogo de personagens atualizado com sucesso! Total: {total_characters}")
    return total_characters