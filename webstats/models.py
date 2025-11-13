from django.db import models

class PageView(models.Model):
    path = models.CharField(max_length=300)
    session_key = models.CharField(max_length=100, blank=True, null=True)
    ip = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["path"]),
        ]

    def __str__(self):
        return f"{self.path} @ {self.created_at:%Y-%m-%d %H:%M}"
