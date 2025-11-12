from datetime import datetime, date
from decimal import Decimal, InvalidOperation

def is_manager(user):
    return user.is_authenticated and user.is_active and (user.is_superuser or user.groups.filter(name="manage").exists())

def _parse_date(v):
    if v in (None, "",):
        return None
    
    if isinstance(v, date):
        return v
    
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(v), fmt).date()
        except ValueError:
            continue
    raise ValueError("Ngày tháng không hợp lệ")

def _to_int_or_none(v):
    if v in (None, "",):
        return None
    try:
        return int(v)
    except ValueError:
        return None

def _to_decimal_or_none(v):
    if v in (None, "",):
        return None
    try:
        s = str(v).replace(",", "")
        return Decimal(s)
    except (InvalidOperation, ValueError):
        raise ValueError("Giá trị tiền không hợp lệ")