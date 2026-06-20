# Documentação de Endpoints (API)

A API roda por padrão em `http://localhost:8005`. O Swagger nativo da aplicação pode ser acessado na rota `/docs`.

---

### 1. Health Check
Verifica a disponibilidade do serviço.
* **URL:** `/health`
* **Método:** `GET`
* **Resposta de Sucesso:**
```json
  {
    "status": "healthy",
    "message": "API rodando perfeitamente!"
  }
  ```

---

### 2. Histórico de Banners
Retorna o histórico cronológico de todos os banners, classificados e equipados com seus itens.
* **URL:** `/history`
* **Método:** `GET`
* **Resposta de Sucesso (200 OK):**
```json
  {
    "banners": [
      {
        "version_name": "Version 4.7",
        "banner_period": "June 5, 2024 — June 25, 2024",
        "active_banner": [
          {
            "name": "Illuminating Lightning",
            "image_url": "https://...",
            "type": "character",
            "items": {
              "5_star_characters": ["Clorinde"],
              "4_star_characters": ["Sethos", "Bennett", "Thoma"],
              "5_star_weapons": [],
              "4_star_weapons": []
            }
          }
        ]
      }
    ]
  }
  ```

---

### 3. Importação de Wishes (HoYoverse Proxy)
Importa o histórico do gacha de um usuário utilizando uma URL com AuthKey fornecida pelo jogo.
* **URL:** `/import`
* **Método:** `POST`
* **Body:**
```json
  {
    "url": "[https://hk4e-api-os.hoyoverse.com/event/gacha_info/api/getGachaLog?authkey=EXEMPLO](https://hk4e-api-os.hoyoverse.com/event/gacha_info/api/getGachaLog?authkey=EXEMPLO)..."
  }
  ```
* **Resposta de Sucesso (200 OK):**
```json
  {
    "status": "success",
    "total_wishes": 145,
    "data": [
      {
        "uid": "123456789",
        "gacha_type": "301",
        "item_id": "",
        "count": "1",
        "time": "2024-06-10 14:30:00",
        "name": "Clorinde",
        "item_type": "Character",
        "rank_type": "5"
      }
    ]
  }
  ```