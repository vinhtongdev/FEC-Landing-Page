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
    
    # payload
    payload = {
        "id": instance.id,
        "name": getattr(instance, "full_name", "") or "",
        "phone": getattr(instance, "phone_number", "") or "",
        "gender": getattr(instance, "get_gender_display", lambda: "")(),
        "income": str(getattr(instance, "income", "")),
        "loan": str(getattr(instance, "loan_amount", "")),
        "created_at": getattr(instance, "created_at", "") and instance.created_at.strftime("%H:%M %d/%m/%Y"),
        "has_pdf": bool(getattr(instance, "signature_document", None)),
    }
    
    async_to_sync(channel_layer.group_send)("dashboard_customers", payload)