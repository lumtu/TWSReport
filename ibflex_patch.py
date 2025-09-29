from dataclasses import fields, make_dataclass
from typing import Type

def create_extended_order_class(base_cls: Type, extra_fields: dict):
    base_fields = [(f.name, f.type, f) for f in fields(base_cls)]
    new_fields = [(name, typ, None) for name, typ in extra_fields.items()]
    
    NewCls = make_dataclass(
        cls_name=base_cls.__name__,
        fields=base_fields + new_fields,
        bases=(base_cls,),
        namespace={},
        frozen=True,  # ⬅️ Muss True sein, weil Originalklasse frozen ist
    )
    return NewCls
