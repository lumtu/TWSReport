# fifo_vergleich.py
import ibflex.Types as types

from decimal import Decimal
from collections import defaultdict


def erzeuge_key(symbol, expiry=None, put_call=None, strike=None):
    if expiry is None or put_call is None or strike is None:
        return symbol  # 🔁 symbol ist bereits der vollständige key

    # Normalfall: symbol ist z. B. "XSP", dann baue vollständigen key
    pc = "C" if put_call.value == "CALL" else "P"
    strike_int = int(strike * 1000)
    return f"{symbol}{expiry:%y%m%d}{pc}{strike_int:08d}"



def vergleiche_mit_ibkr_summary(report, eigene_ergebnisse):
    ibkr_summe = defaultdict(lambda: Decimal("0"))

    for stmt in report.FlexStatements:
        
        entries = stmt.FIFOPerformanceSummaryInBase

        for entry in entries:
            key = erzeuge_key(
                entry.symbol,
                entry.expiry,
                entry.putCall,
                entry.strike
            )

            if entry.assetCategory != None and entry.assetCategory.value == "OPT":
                key = entry.symbol

            realisiert = entry.totalRealizedPnl
            if realisiert is not None and realisiert != 0:
                ibkr_summe[key] += realisiert

            # Werte noch nicht im query enthalten
            # total = (
            #     (entry.realizedSTProfit or Decimal("0"))
            #     - (entry.realizedSTLoss or Decimal("0"))
            #     + (entry.realizedLTProfit or Decimal("0"))
            #     - (entry.realizedLTLoss or Decimal("0"))
            # )
            #
            #if total != realisiert:
            #    print("Werte stimmen nicht überein : ", total, "!=", realisiert )


    eigene_symbol_summe = defaultdict(lambda: Decimal("0"))
    for eintrag in eigene_ergebnisse:
        symbol = eintrag["symbol"]
        expiry = eintrag.get("expiry")
        put_call = eintrag.get("putCall")
        strike = eintrag.get("strike")
        key = eintrag["key"]

        typ = eintrag.get("typ")

        if typ == "STOCK_ASSIGNMENT":
            eigene_symbol_summe[key] += eintrag["gesamt"]
        elif typ == "OPTION_TRADE":
            eigene_symbol_summe[key] += eintrag["pnl_eur"]
        # Weitere Typen können ergänzt werden

    print("\n📊 Vergleich: Eigene Summe vs. IBKR FIFO Summary (Basiswährung EUR)")
    print("=" * 70)
    print(f"{'Symbol':<55} | {'Eigene Summe':>15} | {'IBKR FIFO':>15} | {'Differenz':>10}")
    print("-" * 70)

    # alle_symbole = set(eigene_symbol_summe) | set(ibkr_summe)
    alle_keys = set(filter(None, eigene_symbol_summe)) | set(filter(None, ibkr_summe))
    abweichung_warnung = False
    
    # for symbol in sorted(s for s in alle_symbole if symbol is not None):
    for key in sorted(alle_keys):
        eigene = eigene_symbol_summe.get(key, Decimal("0"))
        ibkr = ibkr_summe.get(key, Decimal("0"))
        diff = eigene - ibkr

        if abs(diff) > Decimal("1.00"):
            abweichung_warnung = True
        else:
            continue    


        print(f"{key:<55} | {eigene:>15.2f} | {ibkr:>15.2f} | {diff:>+10.2f}")

    if abweichung_warnung:
        print("\n⚠️  Warnung: Abweichungen > 1 EUR festgestellt.")
    else:
        print("\n✅  Abgleich mit IBKR FIFO Summary erfolgreich (±1 EUR).")
