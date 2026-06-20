# Documentação Interna: Pipeline do Scraper

O Scraper foi projetado como um pipeline linear para evitar ambiguidades de dados. A execução (`main_scraper.py`) ocorre sempre na seguinte ordem: **Weapons -> Characters -> Banners**.

## 1. Módulo de Catálogo (A "Fonte da Verdade")

### `catalog/weapons.py`
Varre a API da Wiki buscando os 5 tipos de armas.
* **Lógica:** Extrai Base ATK, Status Secundário e a Habilidade Passiva das tabelas.
* **Mecanismo Anti-Falha:** Define a raridade cruzando o texto bruto (ex: `4-star`) e analisando a cor de fundo (`bg-4star`) das células da tabela.

#### Esquema de Dados (Weapon Data Model)
Os documentos gerados na coleção `weapons` seguem a seguinte estrutura:

```json
{
  "name": "Amos' Bow",
  "overview": "A 5-star Bow.",
  "secondary_title": "",
  "data-image-key": "https://...",
  "base_attack": 46,
  "2nd_stat": "ATK 10.8%",
  "quality": "5-star",
  "weapon_type": "Bow",
  "passive_ability": "Increases Normal Attack and Charged Attack DMG by 12%.",
  "rarity": 5,
  "type": "weapon"
}
```

### `catalog/characters.py`
Módulo mais complexo do sistema. Realiza web scraping profundo (*Deep Mapeamento*) nos perfis individuais.
* **Anti-Duplicação de Materiais:** Utiliza `id(cell)` do BeautifulSoup armazenados em um `set()` para lidar com células HTML que possuem `rowspan` (onde um material mescla várias linhas da tabela). Isso garante que o multiplicador de quantidade extraído não seja salvo múltiplas vezes.
* **Mapeamento de DOM Dinâmico:** Encontra talentos e constelações buscando a tag principal (`<h2>`) e iterando via `find_next_sibling()` para agrupar as habilidades e tabelas filhas dinamicamente, sem depender de classes CSS propensas a quebra.

#### Esquema de Dados (Character Data Model)
Os documentos gerados na coleção `characters` extraem todas as nuances de jogabilidade e lore:

```json
{
  "name": "Aino",
  "overview": "Aino is a playable Hydro character in Genshin Impact...",
  "secondary_title": "Spokesperson of the Nod-Krai",
  "images": {
    "card": "https://...",
    "wish": "https://...",
    "in_game": "https://..."
  },
  "data-image-key": "https://...",
  "quality": "4-star",
  "weapon_type": "Claymore",
  "element": "Hydro",
  "model_type": "Short Female",
  "team_bonus": "Nod-Krai",
  "character_roles": [],
  "bio": {
    "birthday": "September 10",
    "constellation": "Cygnus",
    "region": "Nod-Krai",
    "affiliations": ["Nod-Krai Parliament"],
    "specialty": "Aino's Special Dish",
    "namecard": "Aino: Swansong"
  },
  "release_date": "September 10, 2025",
  "additional_titles": [],
  "ascension_materials": {
    "ascension_stages": [
      {
        "stage": 1,
        "materials": [
          { "name": "Varunada Lazurite Sliver", "quantity": 1 },
          { "name": "Portable Bearing", "quantity": 3 }
        ]
      }
    ]
  },
  "talents": {
    "normal_attack": {
      "name": "Strike of the Depths",
      "description": "Performs up to 4 consecutive strikes...",
      "levels": [
        { "level": 1, "damage": "1-Hit DMG: 74.3% | 2-Hit DMG: 68.5%" }
      ]
    },
    "elemental_skill": {
      "name": "Tidal Wave",
      "description": "Summons a wave...",
      "levels": []
    },
    "elemental_burst": {
      "name": "Ocean's Fury",
      "description": "Unleashes the full power of the ocean...",
      "levels": []
    },
    "talent_upgrade_materials": {
      "normal_attack": [
        {
          "level": 2,
          "materials": [
            { "name": "Teachings of Equity", "quantity": 3 }
          ]
        }
      ],
      "elemental_skill": [],
      "elemental_burst": []
    }
  },
  "contelation": [
    {
      "name": "First Ripple",
      "description": "Increases Elemental Skill DMG by 20%.",
      "level": 1
    }
  ],
  "rarity": 4,
  "type": "character"
}
```

## 2. Módulo de Banners (Classificação)

### `banners/history.py`
Acessa o histórico geral e constrói a linha do tempo.
* **Cruzamento de Dados:** Ao encontrar uma string como "Absolution", ele verifica no Catálogo em memória. Se a entidade existir e possuir `{ "type": "weapon", "rarity": 5 }`, ela é alocada no Array `5_star_weapons`.
* **Motor de Tipagem Cega:** O Scraper ignora o título do banner dado pelos editores da Wiki. Ele deduz o tipo baseado na **carga extraída**:
  * Possui *apenas* personagens? `type = character`
  * Possui *apenas* armas? `type = weapon`
  * Possui *ambos* (personagens e armas mapeadas)? `type = chronicled`
* **Persistência:** Salva cada período ("Version X :: Dates") como um documento individual no MongoDB (`banner_history`) para contornar limites de tamanho de BSON e otimizar buscas do Backend.