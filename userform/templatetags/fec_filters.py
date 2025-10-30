from django import template

from userform.helper.utils import format_vn_currency, format_vn_phone, mask_phone

register = template.Library()

@register.filter(name='money_vn')
def money_vn(value, currency='VND'):
    try:
        return format_vn_currency(value, currency)
    except Exception:
        return value
    
@register.filter(name='phone_vn')
def phone_vn(value):
    try:
        return format_vn_phone(value)
    except Exception:
        return value