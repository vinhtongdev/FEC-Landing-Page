from datetime import datetime, date
from decimal import Decimal, InvalidOperation
import json
from django.conf import settings
from pywebpush import webpush, WebPushException
from .models import PushSubscription

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
    
def send_push_to_managers(payload: dict):
    """
    payload: dict sẽ gửi xuống service worker. VD:
    {"title": "...", "body": "...", "url": "/dashboard/..."}
    """
    subs = (
        PushSubscription.objects
        .filter(is_active=True, user__groups__name="manage")
        .select_related("user")
    )
    
    # TTL (Time To Live) cho notification, tính bằng giây.
    # Ví dụ: 1 ngày = 86400 giây.
    ttl = 86400 
    
    if not subs.exists():
        print("[PUSH] No active subscriptions for managers")
        return

    print(f"[PUSH] Sending to {subs.count()} subscriptions")
    for sub in subs:
        subscription_info = {
            "endpoint": sub.endpoint,
            "keys": {
                "p256dh": sub.p256dh,
                "auth": sub.auth,
            },
        }
        try:
            # Lấy origin từ endpoint để tạo 'aud' claim
            # VD: "https://fcm.googleapis.com/fcm/send/..." -> "https://fcm.googleapis.com"
            aud = '/'.join(sub.endpoint.split('/')[:3])
            
            vapid_claims = settings.WEBPUSH_VAPID_CLAIMS.copy()
            vapid_claims['aud'] = aud
            
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(payload),
                vapid_private_key=settings.WEBPUSH_VAPID_PRIVATE_KEY,
                vapid_claims=vapid_claims,
                ttl=ttl
            )
            print(f"[PUSH] Sent to {sub.user} / {sub.endpoint[:50]}...")
        except WebPushException as ex:
            # Log lỗi chi tiết hơn
            print("[PUSH] WebPush error:", repr(ex))
            if ex.response is not None:
                print("[PUSH] response status:", ex.response.status_code)
                print("[PUSH] response body:", ex.response.content)
            # nếu 410/404 → subscription hết hạn, disable
            if ex.response and ex.response.status_code in (404, 410):
                sub.is_active = False
                sub.save(update_fields=["is_active"])
            else:
                # log nhưng đừng crash app
                print("WebPush error:", repr(ex))