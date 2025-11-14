from datetime import date, datetime
from decimal import Decimal
import re
from django.conf import settings
import time
from xml.sax.saxutils import escape
from reportlab.platypus import Paragraph

OTP_TTL = getattr(settings, 'OTP_TTL', 60)

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

def format_vn_phone(phone):
    if isinstance(phone, str) and phone.startswith('84') and len(phone) == 11:
        local = '0' + phone[2:]
        return f"{local[:4]} {local[4:7]} {local[7:]}"
    return phone

def format_vn_currency(amount, currency='VND'):
    if isinstance(amount, (int, float, Decimal)):
        formatted =f'{int(amount):,}'.replace(',', '.')
        return f'{formatted} {currency}'
    return str(amount)

def otp_seconds_left(session) -> int:
    sent = session.get("otp_sent_at")
    if not sent: return 0
    try:
        left = OTP_TTL - (int(time.time()) - int(sent))
        return left if left > 0 else 0
    except Exception:
        raise 0
    
def make_checkbox_paragraph(text: str, checked: bool, base_style):
    """
    Tạo Paragraph có symbol ☑/☐ (DejaVuSans) + chữ (TimesNewRoman).
    """
    sym = '☑' if checked else '☐'
    safe_text = escape(text or "")
    html = (
        f"<font name='DejaVuSans'>{sym}</font> "
        f"<font name='TimesNewRoman'>{safe_text}</font>"
    )
    return Paragraph(html, base_style)