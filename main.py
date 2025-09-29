import os
import json
import ibflex.Types as types
import csv

from dataclasses import field
from collections import defaultdict
from decimal import Decimal
from datetime import datetime, timedelta
from ibflex import client, parser
from ibflex.Types import Order as OriginalOrder
from ibflex_patch import create_extended_order_class

# Neue Klasse erzeugen
Order = create_extended_order_class(OriginalOrder, {
    'tradePrice': Decimal,
    'ibCommission': Decimal,
    'closePrice': Decimal,
    'fifoPnlRealized': Decimal,
    'capitalGainsPnl': Decimal,
    'fxPnl': Decimal,
    'transactionID': str,
})

# Override der Klasse im Parser, sodass er unsere verwendet
types.Order = Order

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
summe = defaultdict(lambda: defaultdict(lambda: {"gewinne": Decimal("0"), "verluste": Decimal("0") }))

for stmt in report.FlexStatements:
    # Baue ein Mapping: Währungspaar → Kurs für diesen Statement-Tag
    conversion = {}
    for cr in stmt.ConversionRates:
        # cr.fromCurrency, cr.toCurrency, cr.rate sind Felder
        conversion[(cr.fromCurrency, cr.toCurrency)] = cr.rate


    option_premien = defaultdict(list)

    for trade in stmt.Trades:
        if trade.assetCategory.value == "OPT" and trade.transactionType.value == "ExchTrade":
            if trade.openCloseIndicator == "O" and trade.buySell == "SELL":
                key = (trade.symbol, getattr(trade, "strike", None), getattr(trade, "expirationDate", None))
                option_premien[key].append({
                    "tradeDate": trade.tradeDate,
                    "symbol": trade.symbol,
                    "prämie": trade.proceeds,  # proceeds ist negativ bei SELL → Gewinn
                    "währung": trade.currency,
                    "exchange_rate": conversion.get((trade.currency, "EUR"), Decimal("1")),
                })

    for trade in stmt.Trades:
        if trade.assetCategory.value == "STK" and trade.transactionType.value == "BookTrade":
            key = (trade.symbol, None, None)  # Vereinfachung, ggf. mit mehr Detail

            # Versuche passende Option zu finden
            mögliche_optionen = option_premien.get(key, [])

            if mögliche_optionen:
                opt = mögliche_optionen.pop(0)  # Erste passende nehmen
                prämie = -opt["prämie"]  # Proceeds ist negativ bei SELL
                prämie_eur = prämie * opt["exchange_rate"]
            else:
                prämie = Decimal("0")
                prämie_eur = Decimal("0")

            # Jetzt echten Gewinn der Aktie berechnen
            pnl_aktie = None
            if hasattr(trade, "fifoPnlRealized") and trade.fifoPnlRealized is not None:
                pnl_aktie = trade.fifoPnlRealized
            else:
                pnl_aktie = trade.realizedPnl or Decimal("0")

            # pnl_aktie = trade.realizedPnl or Decimal("0")
            kurs = conversion.get((trade.currency, "EUR"), Decimal("1"))
            pnl_aktie_eur = pnl_aktie * kurs

            # → Jetzt trennen
            ergebnisse.append({
                "tradeDate": trade.tradeDate,
                "symbol": trade.symbol,
                "typ": "STOCK_ASSIGNMENT",
                "pnl_aktie_eur": pnl_aktie_eur,
                "prämie_eur": prämie_eur,
                "gesamt": pnl_aktie_eur + prämie_eur,
            })


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

        '''
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
        '''

        # trade.tradeDate ist ein datetime.date
        jahr = trade.tradeDate.year  # z. B. 2025
        
        
        # realisierte PNL
        realisiert = pnl_eur or Decimal("0")
        
        # trade.assetCategory ist z. B. AssetClass.STOCK, AssetClass.OPT etc.
        kategorie = trade.assetCategory.name.upper()  # z. B. "STOCK", "OPT"

        # Prüfe auf angediente Aktien (PUT) oder ausgebuchte (CALL)
        if trade.assetCategory.value == "STK" and trade.transactionType.value.upper() == "BOOKTRADE":
            kategorie = "STOCK_ASSIGNED"  # oder z. B. "ASSIGNMENT"

        # Alternativ auch OPT erkennen, wenn du Optionsdaten einliest
        elif trade.assetCategory.value == "OPT" and trade.transactionType.value.upper() == "BOOKTRADE":
            kategorie = "OPTION_ASSIGNED"

        if realisiert >= 0:
            summe[jahr][kategorie]["gewinne"] += realisiert
        else:
            summe[jahr][kategorie]["verluste"] += -realisiert  # Verlust positiv zählen



# Ausgabe

'''
for r in ergebnisse:
    print(
        f"{r['tradeDate']}: {r['symbol']} ({r['assetCategory']}) — "
        f"{r['pnl_original']} {r['currency']} @ {r['exchange_rate']} = {r['pnl_eur']} EUR"
    )
'''

# Ausgabe der Ergebnisse mit Trennung von Prämie und Aktiengewinn
print("\nDetailausgabe je Trade:")
for r in ergebnisse:
    if r.get("typ") == "STOCK_ASSIGNMENT":
        print(
            f"{r['tradeDate']}: {r['symbol']} "
            f"\n  Aktiengewinn:   {r['pnl_aktie_eur']:.2f} EUR"
            f"\n  Optionsprämie:  {r['prämie_eur']:.2f} EUR"
            f"\n  Gesamtgewinn:   {r['gesamt']:.2f} EUR"
            "\n" + "-" * 40
        )
    else:
        # Fallback: normale Anzeige (z. B. Optionsverkauf etc.)
        print(
            f"{r['tradeDate']}: {r['symbol']} ({r.get('assetCategory', 'UNBEKANNT')}) — "
            f"{r.get('pnl_original', '???')} {r.get('currency', '')} "
            f"@ {r.get('exchange_rate', '???')} = {r.get('pnl_eur', '???')} EUR"
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
# with open("trades_eur.csv", "w", newline="") as f:
#     writer = csv.writer(f)
#     writer.writerow([
#         "tradeDate", "symbol", "assetCategory",
#         "pnl_original", "currency", "exchange_rate", "pnl_eur"
#     ])
#     for r in ergebnisse:
#         writer.writerow([
#             r["tradeDate"], r["symbol"], r["assetCategory"],
#             str(r["pnl_original"]), r["currency"], str(r["exchange_rate"]), str(r["pnl_eur"])
#         ])



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