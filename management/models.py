from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField # nếu dùng Postgres
from django.db.models import JSONField  
from django.conf import settings
from userform.models import CustomerInfo

User = get_user_model()

class EditApproval(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("used", "Used"),
        ("expired", "Expired"),
        ("rejected", "Rejected"),
    )

    customer = models.ForeignKey(CustomerInfo, on_delete=models.CASCADE, related_name="edit_approvals")
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="requested_edits")
    approver = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_edits")
    code = models.CharField(max_length=6)
    payload = JSONField()  # dữ liệu thay đổi: {"full_name": "…", "income": 10000000, ...}
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    
    def is_expired(self):
        return timezone.now() >= self.expires_at
    

class PushSubscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
    )
    endpoint = models.TextField()
    
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "endpoint")

    def __str__(self):
        return f"{self.user} - {self.endpoint[:40]}..."