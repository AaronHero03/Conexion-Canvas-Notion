import requests
from ics import Calendar
from datetime import datetime, timedelta, timezone

# ⚙️ CONFIGURA AQUÍ TUS DATOS
NOTION_TOKEN = "tu_notion_token_aquí"
DATABASE_ID_RAW = "tu_database_id_aquí"  # Sin guiones ni llaves
ICS_PATH = "ruta/a/tu/archivo.ics"  # Ruta al archivo ICS local o URL

# 🔧 Convertir a UUID
def format_uuid(uuid_str):
    return f"{uuid_str[0:8]}-{uuid_str[8:12]}-{uuid_str[12:16]}-{uuid_str[16:20]}-{uuid_str[20:32]}"

DATABASE_ID = format_uuid(DATABASE_ID_RAW)

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# 📥 Leer eventos del .ics
def leer_eventos_ics(ruta_ics):
    response = requests.get(ruta_ics)
    response.raise_for_status()
    c = Calendar(response.text)

    eventos = []
    for e in c.events:
        eventos.append({
            "summary": e.name,
            "dtstart": e.begin.datetime,
            "dtend": e.end.datetime,
            "description": e.description or ""
        })
    return eventos

# 🔎 Verificar si ya existe un evento
def evento_ya_existe(summary, dtend_iso):
    query_url = "https://api.notion.com/v1/databases/{}/query".format(DATABASE_ID)
    filtro = {
        "filter": {
            "and": [
                {
                    "property": "Nombre",
                    "rich_text": {
                        "contains": summary
                    }
                },
                {
                    "property": "Fecha límite",
                    "date": {
                        "equals": dtend_iso
                    }
                }
            ]
        }
    }

    response = requests.post(query_url, headers=HEADERS, json=filtro)
    if response.status_code == 200:
        resultados = response.json().get("results", [])
        return len(resultados) > 0
    else:
        print(f"⚠️ Error consultando base de datos: {response.text}")
        return False

# 📤 Crear evento si no existe
def crear_evento_notion(event):
    resumen = f"🟠 {event['summary']}"
    fecha_limite = event['dtend'].isoformat()

    if evento_ya_existe(event['summary'], fecha_limite):
        print(f"🔁 Evento ya existe: {event['summary']}")
        return

    data = {
        "parent": { "database_id": DATABASE_ID },
        "properties": {
            "Nombre": {
                "title": [
                    {
                        "text": {
                            "content": resumen
                        }
                    }
                ]
            },
            "Fecha de creación": {
                "date": {
                    "start": event['dtstart'].isoformat()
                }
            },
            "Fecha límite": {
                "date": {
                    "start": fecha_limite
                }
            },
            "Responsable": {
                "people": [
                    {
                        "id": "1ecd872b-594c-8128-8e5c-00027b673c19"
                    }
                ]
            }
        },
        "children": []
    }

    MAX_LENGTH = 2000
    if event['description']:
        descripcion = event['description']
        for i in range(0, len(descripcion), MAX_LENGTH):
            fragmento = descripcion[i:i + MAX_LENGTH]
            data["children"].append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": fragmento
                            }
                        }
                    ]
                }
            })

    response = requests.post("https://api.notion.com/v1/pages", headers=HEADERS, json=data)

    if response.status_code == 200:
        print(f"✅ Evento creado: {event['summary']}")
    else:
        print(f"❌ Error creando evento '{event['summary']}': {response.text}")

# 🧠 Filtrar eventos recientes
def filtrar_eventos_recientes(eventos, dias=2):
    fecha_limite = datetime.now(timezone.utc) - timedelta(days=dias)
    return [ev for ev in eventos if ev['dtend'] >= fecha_limite]

# 🧾 Proceso completo
def importar_eventos_recientes():
    print("📥 Leyendo eventos del archivo ICS...")
    eventos = leer_eventos_ics(ICS_PATH)
    eventos_recientes = filtrar_eventos_recientes(eventos)

    print(f"🗓️ Se encontraron {len(eventos_recientes)} eventos recientes.")
    for ev in eventos_recientes:
        crear_evento_notion(ev)

# ▶️ Ejecutar
if __name__ == "__main__":
    importar_eventos_recientes()
