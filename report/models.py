from django.db import models

# Create your models here.
class ReportStub(models.Model):
    """
    Model rỗng chỉ để treo permission tuỳ biến 'report.view_reports'.
    """
    class Meta:
        managed = False # Không tạo bảng
        default_permissions = () # không tạo add/change/delete/view mặc định
        permissions = (
            ('view_reports', 'Xem báo cáo'),
        )