from datetime import date, datetime
from decimal import Decimal
import re

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

def normalize_phone(v: str) -> str:
    if not v: return v
    digits = re.sub(r'\D', '', v)
    if digits.startswith('0'): digits = '84' + digits[1:]
    if digits.startswith('84'): return digits
    return '84' + digits


def normalize_id(v: str) -> str:
    return re.sub(r'\D', '', v or '')