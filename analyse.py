# analyse.py
from collections import defaultdict
from decimal import Decimal
from fifo_vergleich import erzeuge_key

def analysiere_trades(report):
    ergebnisse = []
    summe = defaultdict(lambda: defaultdict(lambda: {"gewinne": Decimal("0"), "verluste": Decimal("0")}))
    
    for stmt in report.FlexStatements:
        conversion = {
            (cr.fromCurrency, cr.toCurrency): cr.rate
            for cr in stmt.ConversionRates
        }

        option_premien = defaultdict(list)
        for trade in stmt.Trades:
            if trade.assetCategory.value == "OPT" and trade.transactionType.value == "ExchTrade":
                if trade.openCloseIndicator == "O" and trade.buySell == "SELL":
                    key = (trade.symbol, getattr(trade, "strike", None), getattr(trade, "expirationDate", None))
                    option_premien[key].append({
                        "tradeDate": trade.tradeDate,
                        "symbol": trade.symbol,
                        "prämie": trade.proceeds,
                        "währung": trade.currency,
                        "exchange_rate": trade.fxRateToBase, # conversion.get((trade.currency, "EUR"), Decimal("1")),
                    })

        for trade in stmt.Trades:
            if trade.assetCategory.value == "STK" and trade.transactionType.value == "BookTrade":
                key = (trade.symbol, None, None)
                mögliche_optionen = option_premien.get(key, [])
                if mögliche_optionen:
                    opt = mögliche_optionen.pop(0)
                    prämie = -opt["prämie"]
                    prämie_eur = prämie * opt["exchange_rate"]
                else:
                    prämie = Decimal("0")
                    prämie_eur = Decimal("0")

                pnl_aktie = trade.fifoPnlRealized or Decimal("0")
                kurs = trade.fxRateToBase # conversion.get((trade.currency, "EUR"), Decimal("1"))
                pnl_aktie_eur = pnl_aktie * kurs
                
                key = trade.symbol
                
                ergebnisse.append({
                    "key": key,
                    "tradeDate": trade.tradeDate,
                    "symbol": trade.symbol,
                    "typ": "STOCK_ASSIGNMENT",
                    "pnl_aktie_eur": pnl_aktie_eur,
                    "prämie_eur": prämie_eur,
                    "gesamt": pnl_aktie_eur + prämie_eur,
                })

            if trade.assetCategory.value == "OPT" and trade.transactionType.value == "ExchTrade":
                expiry = getattr(trade, "expirationDate", None)
                put_call = getattr(trade, "putCall", None)
                strike = getattr(trade, "strike", None)

                pnl = trade.fifoPnlRealized or Decimal("0")
                kurs = trade.fxRateToBase # conversion.get((trade.currency, "EUR"), Decimal("1"))
                pnl_eur = pnl * kurs

                key = erzeuge_key(trade.symbol, expiry, put_call, strike)

                ergebnisse.append({
                    "key": key,
                    "tradeDate": trade.tradeDate,
                    "symbol": trade.symbol,
                    "expiry": expiry,
                    "putCall": put_call,
                    "strike": strike,
                    "typ": "OPTION_TRADE",
                    "pnl_eur": pnl_eur,
                })

        for trade in stmt.Trades:
            währung = trade.currency
            pnl = trade.fifoPnlRealized or Decimal("0")
            kurs = trade.fxRateToBase # conversion.get((währung, "EUR"), None)
            pnl_eur = pnl * Decimal(str(kurs)) if kurs else None
            jahr = trade.tradeDate.year
            realisiert = pnl_eur or Decimal("0")
            kategorie = trade.assetCategory.name.upper()

            if trade.assetCategory.value == "STK" and trade.transactionType.value.upper() == "BOOKTRADE":
                kategorie = "STOCK_ASSIGNED"
            elif trade.assetCategory.value == "OPT" and trade.transactionType.value.upper() == "BOOKTRADE":
                kategorie = "OPTION_ASSIGNED"

            if realisiert >= 0:
                summe[jahr][kategorie]["gewinne"] += realisiert
            else:
                summe[jahr][kategorie]["verluste"] += -realisiert

    return ergebnisse, summe
