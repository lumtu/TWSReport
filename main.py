import json
from ibflex import client
from ibflex import parser

# Pfad zur Konfigurationsdatei
CONFIG_PATH = "./config/config.json"

# Config laden
with open(CONFIG_PATH, 'r') as f:
    config = json.load(f)

# Token und Query ID extrahieren
token = config['token']
query_id = config['query_id']

# FlexQuery-Daten abrufen
# response = client.get_response(token=token, query_id=query_id)
response = client.download(token, query_id)
# Ausgabe der ersten 215 Zeichen
print(response[:1024])
with open('data.xml', 'wb') as fw:
    fw.write(response)


report = parser.parse(response)

