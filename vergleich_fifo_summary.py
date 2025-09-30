from flex_parser import parse_flex_statement
from analyse import analysiere_trades
from decimal import Decimal
from collections import defaultdict

# Pfad zur lokalen XML-Datei (kannst du natürlich parametrieren)
DATA_FILE = "data.xml"

# -------------------------
# 🟡 Lade und parse FlexQuery-XML
# -------------------------
with open(DATA_FILE, "rb") as f:
    xml = f.read()

report = parse_flex_statement(xml)

# -------------------------
# 🟡 Eigene Berechnung auf Basis Trades
# -------------------------
eigene_ergebnisse, eigene_summe = analysiere_trades(report)

# -------------------------
# 🟢 IBKR FIFO Summary (in Basiswährung)
# -------------------------
ibkr_summe = defaultdict(lambda: Decimal("0"))

for stmt in report.FlexStatements:
    for entry in stmt.FIFOPerformanceSummariesInBase:
        symbol = entry.symbol
        realisiert = entry.realizedPnL
        if realisiert is not None:
            ibkr_summe[symbol] += realisiert

# -------------------------
# 🔍 Vergleich pro Symbol
# -------------------------
eigene_symbol_summe = defaultdict(lambda: Decimal("0"))
for eintrag in eigene_ergebnisse:
    symbol = eintrag["symbol"]
    eintrag_typ = eintrag.get("typ")

    if eintrag_typ == "STOCK_ASSIGNMENT":
        eigene_symbol_summe[symbol] += eintrag["gesamt"]
    # Wenn du andere Typen auswertest, hier ergänzen

print("\n📊 Vergleich: Eigene Berechnung vs. IBKR FIFO Summary (in EUR)")
print("=" * 65)
print(f"{'Symbol':<10} | {'Eigene Summe':>15} | {'IBKR Summary':>15} | {'Differenz':>10}")
print("-" * 65)

alle_symbole = set(eigene_symbol_summe.keys()).union(ibkr_summe.keys())

abweichung_warnung = False

for symbol in sorted(alle_symbole):
    eigene = eigene_symbol_summe.get(symbol, Decimal("0"))
    ibkr = ibkr_summe.get(symbol, Decimal("0"))
    diff = eigene - ibkr

    if abs(diff) > Decimal("1.00"):
        abweichung_warnung = True

    print(f"{symbol:<10} | {eigene:>15.2f} | {ibkr:>15.2f} | {diff:>+10.2f}")

if abweichung_warnung:
    print("\n⚠️ Hinweis: Eine oder mehrere Abweichungen sind > 1 EUR.")
else:
    print("\n✅ Alle Summen sind im erwarteten Toleranzbereich.")
