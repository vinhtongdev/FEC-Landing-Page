from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from django.db.models import Q, UniqueConstraint

from userform.helper.utils import normalize_id, normalize_phone

class CustomerInfo(models.Model):
    class Meta:
        db_table = 'Customer'
        # ❗ Chỉ cho phép 1 hồ sơ OPEN cho mỗi (phone_number, id_card)
        constraints = [
            UniqueConstraint(
                fields=['phone_number', 'id_card'],
                condition=Q(status='OPEN'),
                name='uniq_open_application_per_phone_and_id'
            )
        ]
    
    PROVINCES = [
        ("ha_noi", "Hà Nội"),
        ("tp_ho_chi_minh", "Thành phố Hồ Chí Minh"),
        ("hai_phong", "Hải Phòng"),
        ("da_nang", "Đà Nẵng"),
        ("can_tho", "Cần Thơ"),
        ("hue", "Huế"),

        # 28 tỉnh
        ("cao_bang", "Cao Bằng"),
        ("dien_bien", "Điện Biên"),
        ("ha_tinh", "Hà Tĩnh"),
        ("lai_chau", "Lai Châu"),
        ("lang_son", "Lạng Sơn"),
        ("nghe_an", "Nghệ An"),
        ("quang_ninh", "Quảng Ninh"),
        ("thanh_hoa", "Thanh Hóa"),
        ("son_la", "Sơn La"),

        ("tuyen_quang", "Tuyên Quang"),
        ("lao_cai", "Lào Cai"),
        ("thai_nguyen", "Thái Nguyên"),
        ("phu_tho", "Phú Thọ"),
        ("bac_ninh", "Bắc Ninh"),
        ("hung_yen", "Hưng Yên"),
        ("ninh_binh", "Ninh Bình"),
        ("quang_tri", "Quảng Trị"),
        ("quang_ngai", "Quảng Ngãi"),
        ("gia_lai", "Gia Lai"),
        ("khanh_hoa", "Khánh Hòa"),
        ("lam_dong", "Lâm Đồng"),
        ("dak_lak", "Đắk Lắk"),
        ("dong_nai", "Đồng Nai"),
        ("tay_ninh", "Tây Ninh"),
        ("vinh_long", "Vĩnh Long"),
        ("dong_thap", "Đồng Tháp"),
        ("ca_mau", "Cà Mau"),
        ("an_giang", "An Giang"),
    ]

    WORK_STATUS = [
        ('nhan_vien_van_phong', 'Nhân viên văn phòng'),
        ('cong_nhan', 'Công nhân'),
        ('tu_do', 'Tự do'),
        ('sinh_vien', 'Sinh viên'),
        ('khac', 'Khác'),
        # Thêm tùy theo nhu cầu
    ]
    
    DOC_TYPES = [
        ('hoa_don_dien_nuoc', 'Hóa đơn điện nước'),
        ('sao_ke_ngan_hang', 'Sao kê ngân hàng'),
        ('hop_dong_lao_dong', 'Hợp đồng lao động'),
        ('khac', 'Khác'),
        # Thêm tùy theo ảnh
    ]
    
    GENDER_CHOICES = [
        ('nam', 'Nam'),
        ('nu', 'Nữ'),
    ]
    
    STATUS_CHOICES = [
        ('OPEN', 'Đang mở / chờ xử lý'),
        ('CLOSED', 'Đã đóng'),
    ]
    
    permanent_address = models.CharField(max_length=100, choices=PROVINCES, verbose_name='Nơi đăng ký thường trú')  # Dropdown địa chỉ
    full_name = models.CharField(max_length=100, verbose_name='Họ tên đầy đủ trên CCCD')
    gender = models.CharField(max_length=3, choices=GENDER_CHOICES, verbose_name='Giới tính')
    
    phone_number = models.CharField(max_length=15, verbose_name='Số điện thoại', null=False, blank=False)
    birth_date = models.DateField(verbose_name='Ngày tháng năm sinh') 
    id_card = models.CharField(max_length=20, verbose_name='CCCD/CMND/Căn cước')
    
    work_status = models.CharField(max_length=50, choices=WORK_STATUS, verbose_name='Trạng thái công việc')  # Dropdown
    doc_provided = models.CharField(max_length=50, choices=DOC_TYPES, verbose_name='Chứng từ cung cấp')  # Dropdown
    loan_amount = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='Số tiền đăng ký')  # 10-100 triệu
    income = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='Thu nhập')
    monthly_payment = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='Tổng tiền trả góp hàng tháng', blank=True)
    
    agree_call = models.BooleanField(default=False, verbose_name='Tôi đồng ý nhận cuộc gọi từ CNEXT JSC')
    agree_policy = models.BooleanField(default=False, verbose_name='Tôi đã đọc và đồng ý với Chính sách bảo vệ dữ liệu')
    agree_vpb = models.BooleanField(default=False, verbose_name='Tôi đồng ý với VPB SMBC FC thu thập dữ liệu')
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='OPEN', verbose_name='Trạng thái')
    
    signature = models.ImageField(upload_to='signatures/', verbose_name='Chữ ký điện tử', null=True, blank=True)
    signature_document = models.FileField(upload_to='signed_docs/', verbose_name='Văn bản xác nhận đã ký', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.full_name} - {self.phone_number}'
    
    def clean(self):
        self.phone_number = normalize_phone(self.phone_number)
        self.id_card = normalize_id(self.id_card)
        super().clean()
        
    def save(self, *args, **kwargs):
        self.phone_number = normalize_phone(self.phone_number)
        self.id_card = normalize_id(self.id_card)
        return super().save(*args, **kwargs)
    
    

