def ausgabe_auf_konsole(ergebnisse, summe):
    print("\n" + "=" * 60)
    print("🟢 Alle realisierten Trades mit G/V (Detailansicht)")
    print("=" * 60)
    for r in ergebnisse:
        if r.get("typ") == "STOCK_ASSIGNMENT":
            print(
                f"{r['tradeDate']}: {r['symbol']} (Zwangsausübung Stillhalter)"
                f"\n  Aktiengewinn:   {r['pnl_aktie_eur']:.2f} EUR"
                f"\n  Optionsprämie:  {r['prämie_eur']:.2f} EUR"
                f"\n  Gesamtgewinn:   {r['gesamt']:.2f} EUR"
                "\n" + "-" * 40
            )

    print("\n" + "=" * 60)
    print("🔵 Übersicht für Anlage KAP-AUS (Gewinne/Verluste pro Jahr)")
    print("=" * 60)

    relevante_kategorien = {
        "STK": "Aktienverkäufe",
        "OPT": "Optionen (Stillhalter/Long)",
        "STOCK_ASSIGNED": "Aktien durch Ausübung",
        "OPTION_ASSIGNED": "Option ausgeübt",
    }

    for jahr in sorted(summe.keys()):
        print(f"\n📅 Jahr: {jahr}")
        for kat, werte in summe[jahr].items():
            beschreibung = relevante_kategorien.get(kat, kat)
            gew = werte["gewinne"]
            verl = werte["verluste"]
            netto = gew - verl
            print(
                f"  {beschreibung:<25}: "
                f"Gewinne = {gew:>8.2f} EUR | Verluste = {verl:>8.2f} EUR | Netto = {netto:>8.2f} EUR"
            )
        print("-" * 60)
