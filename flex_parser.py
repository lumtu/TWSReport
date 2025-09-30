from ibflex import parser
import ibflex.Types as types
from decimal import Decimal
from ibflex.Types import Order as OriginalOrder
from ibflex_patch import create_extended_order_class

# Eigene Order-Klasse mit zusätzlichen Feldern
Order = create_extended_order_class(OriginalOrder, {
    'tradePrice': Decimal,
    'ibCommission': Decimal,
    'closePrice': Decimal,
    'fifoPnlRealized': Decimal,
    'capitalGainsPnl': Decimal,
    'fxPnl': Decimal,
    'transactionID': str,
})

# ibflex Patch anwenden
types.Order = Order

def parse_flex_statement(xml_bytes):
    return parser.parse(xml_bytes)
