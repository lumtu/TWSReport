from collections import defaultdict
import csv
from decimal import Decimal
import os
import json
from datetime import datetime, timedelta
from ibflex import client, parser

# Pfad zur Konfigurationsdatei
CONFIG_PATH = "./config/config.json"
DATA_FILE = "data.xml"

# Config laden
with open(CONFIG_PATH, 'r') as f:
    config = json.load(f)

# Token und Query ID extrahieren
token = config['token']
query_id = config['query_id']


def is_file_older_than(file_path, delta_days=1):
    """Prüft, ob die Datei älter als delta_days ist."""
    if not os.path.exists(file_path):
        return True
    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
    return datetime.now() - file_mtime > timedelta(days=delta_days)


# Prüfe, ob wir neue Daten laden müssen
if is_file_older_than(DATA_FILE, delta_days=1):
    print("Lade neue FlexQuery-Daten...")
    try:
        response = client.download(token, query_id)
        with open(DATA_FILE, 'wb') as fw:
            fw.write(response)
    except Exception as e:
        print(f"Fehler beim Abrufen der FlexQuery-Daten: {e}")
        exit(1)
else:
    print("Verwende vorhandene lokale Datei.")
    with open(DATA_FILE, 'rb') as fr:
        response = fr.read()


# Zeigt alle enthaltenen Sektionen des Reports
report = parser.parse(response)
#


# Ergebnisse mit Umrechnung
ergebnisse = []  # Liste von Diktaten je Trade
# Ergebnisse: dict: Jahr -> Kategorie -> {"gewinne": Decimal, "verluste": Decimal}
summe = defaultdict(lambda: defaultdict(lambda: {"gewinne": Decimal("0"), "verluste": Decimal("0") }))

for stmt in report.FlexStatements:
    # Baue ein Mapping: Währungspaar → Kurs für diesen Statement-Tag
    conversion = {}
    for cr in stmt.ConversionRates:
        # cr.fromCurrency, cr.toCurrency, cr.rate sind Felder
        conversion[(cr.fromCurrency, cr.toCurrency)] = cr.rate

    for trade in stmt.Trades:
        # Originalwährung und PnL
        währung = trade.currency  # z. B. "USD"
        # Bevorzugter PnL-Wert
        pnl = None
        if hasattr(trade, "fifoPnlRealized") and trade.fifoPnlRealized is not None:
            pnl = trade.fifoPnlRealized
        else:
            pnl = trade.realizedPnl or Decimal("0")

        # Finde passenden Wechselkurs
        # Annahme: fromCurrency = trade.currency, toCurrency = "EUR"
        key = (währung, "EUR")
        kurs = conversion.get(key, None)
        if kurs is None:
            # Fallback oder Warnung
            print(f"Kein Wechselkurs für {währung} → EUR am {stmt.reportDate}")
            pnl_eur = None
        else:
            pnl_eur = pnl * Decimal(str(kurs))

        # Sammle Daten
        ergebnisse.append({
            "tradeDate": trade.tradeDate,
            "symbol": trade.symbol,
            "assetCategory": trade.assetCategory.name,
            "pnl_original": pnl,
            "currency": währung,
            "exchange_rate": kurs,
            "pnl_eur": pnl_eur
        })

        # trade.tradeDate ist ein datetime.date
        jahr = trade.tradeDate.year  # z. B. 2025
        
        # trade.assetCategory ist z. B. AssetClass.STOCK, AssetClass.OPT etc.
        kategorie = trade.assetCategory.name  # z. B. "STOCK", "OPT"
        
        # realisierte PNL
        realisiert = pnl_eur or Decimal("0")
        
        if realisiert >= 0:
            summe[jahr][kategorie]["gewinne"] += realisiert
        else:
            summe[jahr][kategorie]["verluste"] += -realisiert  # Verlust positiv zählen



# Ausgabe
for r in ergebnisse:
    print(
        f"{r['tradeDate']}: {r['symbol']} ({r['assetCategory']}) — "
        f"{r['pnl_original']} {r['currency']} @ {r['exchange_rate']} = {r['pnl_eur']} EUR"
    )


# Ausgabe (Konsole)
print("Steuerlicher Gewinn-/Verlust-Report gemäß ibflex:")
for jahr in sorted(summe.keys()):
    print(f"Jahr: {jahr}")
    for kat, werte in summe[jahr].items():
        gew = werte["gewinne"]
        verl = werte["verluste"]
        netto = gew - verl
        print(f"  {kat}: Gewinne = {gew} | Verluste = {verl} | Netto = {netto}")
    print("-" * 40)




# Optional: CSV
with open("trades_eur.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "tradeDate", "symbol", "assetCategory",
        "pnl_original", "currency", "exchange_rate", "pnl_eur"
    ])
    for r in ergebnisse:
        writer.writerow([
            r["tradeDate"], r["symbol"], r["assetCategory"],
            str(r["pnl_original"]), r["currency"], str(r["exchange_rate"]), str(r["pnl_eur"])
        ])



"""""
# Gewinn/Verlust-Auswertung
# Ergebnisse: dict: Jahr -> Kategorie -> {"gewinne": Decimal, "verluste": Decimal}
ergebnisse = defaultdict(lambda: defaultdict(lambda: {"gewinne": Decimal("0"), "verluste": Decimal("0") }))

for stmt in report.FlexStatements:
    for trade in stmt.Trades:
        # trade.tradeDate ist ein datetime.date
        jahr = trade.tradeDate.year  # z. B. 2025
        
        # trade.assetCategory ist z. B. AssetClass.STOCK, AssetClass.OPT etc.
        kategorie = trade.assetCategory.name  # z. B. "STOCK", "OPT"
        
        # realisierte PNL
        realisiert = trade.fifoPnlRealized or Decimal("0")
        
        if realisiert >= 0:
            ergebnisse[jahr][kategorie]["gewinne"] += realisiert
        else:
            ergebnisse[jahr][kategorie]["verluste"] += -realisiert  # Verlust positiv zählen



# Ausgabe (Konsole)
print("Steuerlicher Gewinn-/Verlust-Report gemäß ibflex:")
for jahr in sorted(ergebnisse.keys()):
    print(f"Jahr: {jahr}")
    for kat, werte in ergebnisse[jahr].items():
        gew = werte["gewinne"]
        verl = werte["verluste"]
        netto = gew - verl
        print(f"  {kat}: Gewinne = {gew} | Verluste = {verl} | Netto = {netto}")
    print("-" * 40)



# Wahlweise: CSV-Export
with open("steuerbericht_ibflex.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Jahr", "Kategorie", "Gewinne", "Verluste", "Netto"])
    for jahr in sorted(ergebnisse.keys()):
        for kat, werte in ergebnisse[jahr].items():
            gw = werte["gewinne"]
            vl = werte["verluste"]
            nt = gw - vl
            writer.writerow([jahr, kat, str(gw), str(vl), str(nt)])

"""