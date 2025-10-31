# ITV_FEC_ICustomer/userform/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import CustomerInfo

@receiver(post_save, sender=CustomerInfo)
def customer_created_notify(sender, instance, created, **kwargs):
    if not created:
        return
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    payload = {
        "kind": "customer_created",  # ✅ NHÃN SỰ KIỆN
        "id": instance.id,
        "name": getattr(instance, "full_name", "") or "",
        "phone": getattr(instance, "phone_number", "") or "",
        "gender": getattr(instance, "get_gender_display", lambda: "")(),
        "income": str(getattr(instance, "income", "")),
        "loan": str(getattr(instance, "loan_amount", "")),
        "created_at": instance.created_at.strftime("%H:%M %d/%m/%Y") if getattr(instance, "created_at", None) else "",
    }

    async_to_sync(channel_layer.group_send)(
        "dashboard_customers",
        {"type": "add_message", "data": payload}
    )
