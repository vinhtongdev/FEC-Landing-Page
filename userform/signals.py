# ITV_FEC_ICustomer/userform/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import CustomerInfo
from django.urls import reverse
from management.utils import send_push_to_managers

@receiver(post_save, sender=CustomerInfo)
def customer_created_notify(sender, instance, created, **kwargs):
    if not created:
        return
    
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    # PDF hiện có không?
    f = getattr(instance, "signature_document", None)
    has_pdf = bool(f and getattr(f, "name", None))

    payload = {
        "kind": "customer_created",
        "id": instance.id,
        "full_name": instance.full_name or "",
        "gender_display": instance.get_gender_display(),
        "phone_number": instance.phone_number or "",
        "id_card": instance.id_card or "",
        "permanent_address_display": instance.get_permanent_address_display(),
        "income": int(instance.income or 0),
        "loan_amount": int(instance.loan_amount or 0),
        "created_at": instance.created_at.strftime("%H:%M %d/%m/%Y") if instance.created_at else "",
        "has_pdf": has_pdf,
        "pdf_download_url": reverse("management:download_file", args=[instance.id]) if has_pdf else None,
        "detail_url": reverse("management:customer_detail", args=[instance.id]),
    }

    async_to_sync(channel_layer.group_send)(
        "dashboard_customers",
        {"type": "add_message", "data": payload}
    )
    
    # 🔔 WEB PUSH CHO MANAGER
    try:
        detail_url = reverse("management:customer_detail", args=[instance.id])
    except Exception as e:
        # fallback nếu chưa có view chi tiết
        detail_url = reverse("management:dashboard")
    
    full_name = getattr(instance, "full_name", "") or ""
    phone = getattr(instance, "phone_number", "") or ""

    push_payload = {
        "title": "Khách hàng mới đăng ký",
        "body": f"{full_name} - {phone}",
        "url": detail_url,
    }
    send_push_to_managers(push_payload)
