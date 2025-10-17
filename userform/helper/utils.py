from datetime import date, datetime
from decimal import Decimal

def session_safe(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, (date, datetime)):
            out[k] = v.strftime('%Y-%m-%d')
        elif isinstance(v, Decimal):
            out[k] = str(v)
        else:
            out[k] = v
    return out

def mask_phone(phone: str|None) -> str|None:
    if not phone:
        return None
    
    p =''.join(ch for ch in phone if ch.isdigit())
    if len(p) >= 4:
        return f"{phone[:-4]}****"
    
    return phone