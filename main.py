import os
import json
from datetime import datetime, timedelta
from ibflex import client
from flex_parser import parse_flex_statement
from analyse import analysiere_trades
from console_output import ausgabe_auf_konsole
from fifo_vergleich import vergleiche_mit_ibkr_summary


CONFIG_PATH = "./config/config.json"
DATA_FILE = "data.xml"

def is_file_older_than(file_path, delta_days=1):
    if not os.path.exists(file_path):
        return True
    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
    return datetime.now() - file_mtime > timedelta(days=delta_days)

# Config laden
with open(CONFIG_PATH, 'r') as f:
    config = json.load(f)

token = config['token']
query_id = config['query_id']

# Daten holen oder laden
if is_file_older_than(DATA_FILE, delta_days=1):
    print("⏬ Lade neue FlexQuery-Daten von IBKR...")
    try:
        response = client.download(token, query_id)
        with open(DATA_FILE, 'wb') as fw:
            fw.write(response)
    except Exception as e:
        print(f"❌ Fehler beim Abrufen: {e}")
        exit(1)
else:
    print("📄 Verwende vorhandene lokale FlexQuery-Datei.")
    with open(DATA_FILE, 'rb') as fr:
        response = fr.read()

# FlexQuery parsen & analysieren
statement = parse_flex_statement(response)
ergebnisse, summe = analysiere_trades(statement)

# Ergebnisse auf Konsole ausgeben
ausgabe_auf_konsole(ergebnisse, summe)


# Optionaler Abgleich mit IBKR FIFO Summary
vergleiche_mit_ibkr_summary(statement, ergebnisse)

