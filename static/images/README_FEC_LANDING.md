# FEC Landing Page – Project Profile (Django 4.2)

## 1) Mục tiêu & phạm vi
- Thu thập lead cho FE Credit (form đăng ký, xác thực OTP).
- **OTP qua South SMS API**, **resend cooldown 45s (AJAX + progress modal)**.
- Giao diện **responsive** với **Bootstrap 5**, hỗ trợ mobile.
- Database: **PostgreSQL**.
- Bổ sung:
  - Trang **Chính sách bảo vệ dữ liệu** (privacy_policy) – link ngay trên form.
  - **Ký điện tử** (SignaturePad) trên “Văn bản xác nhận”, lưu chữ ký (PNG base64).
  - **Invalid-access** page thân thiện.
  - **Sign-done** page + **Django messages**.
  - **Dashboard** (`management`) để xem danh sách, lọc, phân trang, **export CSV**.
- Định dạng ngày **dd/mm/yyyy**, 3 ô tiền có **stepper ±1.000.000**, placeholder/validate rõ ràng.

---

## 2) Cấu trúc apps
```
project_root/
├─ accounts/         # (tuỳ chọn) A: Custom User / B: ManagerAccount
├─ management/       # dashboard (list, detail, export)
│  ├─ templates/management/
│  │  ├─ dashboard_list.html
│  │  └─ customer_detail.html
├─ userform/         # form, OTP, privacy, ký điện tử
│  ├─ forms/
│  │  └─ forms.py
│  ├─ helper/
│  │  └─ utils.py
│  ├─ models.py
│  ├─ templates/userform/
│  │  ├─ form.html
│  │  ├─ otp.html
│  │  ├─ privacy_policy.html
│  │  ├─ sign.html
│  │  ├─ sign_done.html
│  │  └─ invalid_access.html
│  ├─ urls.py
│  └─ views/views.py
├─ static/
│  ├─ css/
│  │  ├─ app.css
│  │  ├─ otp.css
│  │  ├─ privacy.css
│  │  └─ sign.css
│  └─ js/
│     ├─ form.js
│     └─ otp.js
├─ templates/        # (nếu có dùng templates chung)
└─ README_FEC_LANDING.md
```

---

## 3) Model chính
```python
# userform/models.py
class CustomerInfo(models.Model):
    class Meta:
        db_table = 'Customer'

    PROVINCES = [...]                  # danh sách chọn tỉnh/thành
    WORK_STATUS = [...]
    DOC_TYPES = [...]
    GENDER_CHOICES = [('nam','Nam'),('nu','Nữ')]

    permanent_address = models.CharField(max_length=100, choices=PROVINCES)
    full_name        = models.CharField(max_length=100)
    gender           = models.CharField(max_length=3, choices=GENDER_CHOICES)
    phone_number     = models.CharField(max_length=15)
    birth_date       = models.DateField()                 # dd/mm/yyyy (render/parse ở Form)
    id_card          = models.CharField(max_length=20)    # 12 digits validate
    work_status      = models.CharField(max_length=50, choices=WORK_STATUS)
    doc_provided     = models.CharField(max_length=50, choices=DOC_TYPES)
    loan_amount      = models.DecimalField(max_digits=12, decimal_places=0)
    income           = models.DecimalField(max_digits=12, decimal_places=0)
    monthly_payment  = models.DecimalField(max_digits=12, decimal_places=0, blank=True)
    agree_call       = models.BooleanField(default=False)
    agree_policy     = models.BooleanField(default=False)
    agree_vpb        = models.BooleanField(default=False)
    created_at       = models.DateTimeField(auto_now_add=True)
```
> **Chống trùng đăng ký**
> - Check `(phone_number, id_card)` theo **cửa sổ thời gian** (ví dụ 30–90 ngày) trước khi lưu; nếu tồn tại → hỏi người dùng có cập nhật hồ sơ cũ không.  
> - Nếu **cấm trùng tuyệt đối** → đặt UniqueConstraint `(phone_number, id_card)`.

---

## 4) Form & Validation (tóm tắt)
- `CustomerInfoForm`:
  - `birth_date` `input_formats=['%d/%m/%Y']`, widget type `text`, placeholder `dd/mm/yyyy`.
  - `gender` `TypedChoiceField` + `RadioSelect` (label có `for` → click chọn).
  - `permanent_address`, `work_status`, `doc_provided`: `PlaceholderSelect` (option đầu rỗng, chữ mờ).
  - `loan_amount/income/monthly_payment`: NumberInput + **JS stepper ±1.000.000**; không < 0; placeholder khi mới vào; nếu trống mà bấm “–” → cảnh báo; khi về 0 tiếp tục “–” thì không cảnh báo.
  - Rule:
    - `loan_amount`: 10–100 triệu
    - `income`: 3–100 triệu
    - `monthly_payment` ≤ 50% `income`
    - `id_card`: 12 số
    - Bắt buộc 3 checkbox (một message tổng hoặc riêng từng field).
- `OTPForm`: `otp` 6 ký tự.

---

## 5) OTP Flow (South SMS API)
- Sinh OTP: `generate_otp()` → chuỗi 6 số.
- Chuẩn hoá số gửi: `0xxxxxxxxx` → `84xxxxxxxxx`; nếu chưa `84`/`0` → thêm `84`.
- `send_otp(phone, otp)` gọi `settings.SOUTH_API_URL` (Basic Auth từ `SOUTH_API_USER/PWD`).
- Session keys:
  - `user_data`: dữ liệu form **đã “session-safe”** (date → string `dd/mm/yyyy`).
  - `otp`: giá trị OTP hiện hành (mỗi lần resend phải **xoay** OTP).
  - `otp_phone`: số sẽ gửi lại.
  - `otp_sent_at`: epoch int (để tính cooldown).
- Cooldown resend = **45s**:
  - Server: `remaining = max(0, 45 - (now - otp_sent_at))` → render vào template/JSON.
  - Nút “Gửi lại” → **AJAX POST** `{action: 'resend'}` → trả `{ ok, message, remaining }`.
  - Khi resend thành công:
    - **Xoay OTP**: `request.session['otp'] = new_otp`
    - Cập nhật `otp_sent_at = now`
    - Client reset countdown về `remaining`.

**CSRF & bảo mật**
- `@ensure_csrf_cookie` trên view render form/otp.
- `CSRF_TRUSTED_ORIGINS` chứa host dev; dùng `{% csrf_token %}` cho form; AJAX đặt header `X-CSRFToken`.
- Sau login (nếu dùng auth chuẩn), csrf token xoay → reload trang form trước khi POST.

---

## 6) Templates (tên file cố định)
- `userform/form.html`: card giữa trang, radio label-clickable, các select có placeholder mờ, số tiền có stepper, có link `{% url 'privacy_policy' %}` với text “**Chính sách bảo vệ dữ liệu cá nhân của IT-COMMUNICATIONS VIỆT NAM**”.
- `userform/otp.html`: card ~420px, hiển thị `{{ masked_phone }}`, form OTP + nút “Xác nhận OTP”, nút “Gửi lại (Xs)” (AJAX), modal progress.
- `userform/privacy_policy.html`: nội dung chính thức (style tách `privacy.css`).
- `userform/sign.html`: SignaturePad → submit `signature_data` (base64 PNG).
- `userform/sign_done.html`: thông điệp thân thiện, mã hồ sơ, thời gian.
- `userform/invalid_access.html`: báo lỗi truy cập, gợi ý quay lại form.

**Static**
- `static/css/app.css`, `otp.css`, `privacy.css`, `sign.css`.
- `static/js/form.js` (steppers, UX), `otp.js` (AJAX resend + countdown + modal).

---

## 7) Dashboard (`management`)
- URL: `/dashboard/` (namespace `management`).
- Bảo vệ:
  - Dùng Django Admin user → `@staff_member_required`
  - Hoặc dùng `ManagerAccount` → `@manager_login_required` (backend riêng)
- `dashboard_list.html`:
  - Lọc `q` (họ tên/SĐT/CCCD), `date_from/to`, `province`, `work_status`, `gender`.
  - Phân trang 25; nút **Export CSV** giữ nguyên filter.
- `customer_detail.html`: card chi tiết.
- `export_csv`: xuất UTF-8, cột: ID, Họ tên, Giới tính, SĐT, CCCD, Tỉnh/TP, Công việc, Số tiền đăng ký, Thu nhập, Trả góp/tháng, Ngày tạo (dd/mm/yyyy HH:MM).

---

## 8) Auth – 2 lựa chọn

### A) Thay hẳn User mặc định
- `accounts.User(AbstractBaseUser, PermissionsMixin)` → `AUTH_USER_MODEL = 'accounts.User'`.
- Đăng nhập bằng email, `is_staff` để vào dashboard.
- `accounts/admin.py`: `readonly_fields = ('date_joined','last_login')`.
- **Lưu ý**: đặt `AUTH_USER_MODEL` **trước** migrate đầu tiên.

### B) Giữ User mặc định, làm tài khoản dashboard riêng
- `accounts.ManagerAccount` (email, password hash, is_active/is_staff).
- `accounts.backends.ManagerBackend` + `SESSION_KEY` riêng.
- `@manager_login_required` bảo vệ view dashboard.
- `accounts/login.html` (Bootstrap).

---

## 9) Cấu hình & môi trường

**settings.py**
```python
INSTALLED_APPS = [
  'django.contrib.admin','django.contrib.auth','django.contrib.contenttypes',
  'django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles',
  'django_bootstrap5',
  'userform','management',
  'accounts',          # nếu dùng
  'django_ratelimit',
]

MIDDLEWARE = [
  'django.middleware.security.SecurityMiddleware',
  'django.contrib.sessions.middleware.SessionMiddleware',
  'django.middleware.common.CommonMiddleware',
  'django.middleware.csrf.CsrfViewMiddleware',
  'django.contrib.auth.middleware.AuthenticationMiddleware',
  'django.contrib.messages.middleware.MessageMiddleware',
]

TEMPLATES[0]['APP_DIRS'] = True
TEMPLATES[0]['OPTIONS']['context_processors'] += [
  'django.template.context_processors.request',
  'django.contrib.messages.context_processors.messages',
]

# CSRF cho dev
CSRF_TRUSTED_ORIGINS = ['http://127.0.0.1:8000','http://localhost:8000']
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Ngôn ngữ & múi giờ
LANGUAGE_CODE = 'vi'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_TZ = True
```

**ENV (ví dụ .env)**
```
DATABASE_URL=postgres://user:pass@localhost:5432/feclanding
SOUTH_API_URL=https://sms-gateway.example/api/send
SOUTH_API_USER=...
SOUTH_API_PWD=...
SOUTH_FROM=ITCOM
```

---

## 10) URL map

**project/urls.py**
```python
urlpatterns = [
  path('admin/', admin.site.urls),  # nếu bật admin
  path('auth/', include(('accounts.urls','accounts'), namespace='accounts')),  # nếu dùng
  path('dashboard/', include(('management.urls','management'), namespace='management')),
  path('', include('userform.urls')),
]
```

**userform/urls.py**
```python
urlpatterns = [
  path('', views.user_form, name='user_form'),
  path('verify/', views.verify_otp, name='verify_otp'),
  path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
  path('sign/<int:customer_id>/', views.sign_view, name='sign_view'),
  path('done/<int:signed_id>/', views.sign_done, name='sign_done'),
  path('invalid/', views.invalid_access, name='invalid_access'),
]
```

**management/urls.py**
```python
urlpatterns = [
  path('', views.DashboardListView.as_view(), name='dashboard'),
  path('customer/<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
  path('export/csv/', views.export_csv, name='export_csv'),
]
```

---

## 11) Frontend JS

**static/js/form.js**
- Gắn `data-step="1000000"` cho 3 ô tiền.
- Nút `-`/`+` cập nhật giá trị; không < 0; placeholder khi vừa vào; cảnh báo khi trống mà bấm “–”; về 0 thì tiếp tục “–” không cảnh báo.

**static/js/otp.js**
- Đếm ngược từ `{{ remaining }}` mỗi giây.
- Nút resend → **AJAX POST** `{action:'resend'}` → `{ok,message,remaining}` → reset countdown.
- Modal progress: chạy 10→90% khi pending, success lên 100% rồi ẩn.
- Thêm alert động vào `#otp-alerts`.

---

## 12) Django messages
- View:
  ```python
  messages.success(request, "Thành công ...")
  messages.error(request, "Có lỗi ...")
  ```
- Template:
  ```django
  {% if messages %}{% for m in messages %}
    <div class="alert alert-{{ m.tags }}">{{ m }}</div>
  {% endfor %}{% endif %}
  ```

---

## 13) Triển khai (Ubuntu)
- Cài Python, PostgreSQL, nginx, gunicorn.
- `pip install -r requirements.txt`
- Cập nhật `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` với domain.
- Bật HTTPS: `CSRF_COOKIE_SECURE=True`, `SESSION_COOKIE_SECURE=True`.
- `python manage.py collectstatic`
- Tạo service gunicorn + nginx reverse proxy + SSL (Let’s Encrypt).

---

## 14) Troubleshooting nhanh
- **'bootstrap5' tag error** → dùng `django-bootstrap5` + `{% load django_bootstrap5 %}`.
- **Định dạng ngày / KeyError 'invalid'** → chỉ `input_formats=['%d/%m/%Y']`, widget type `text`.
- **403 CSRF** → `@ensure_csrf_cookie`, `CSRF_TRUSTED_ORIGINS`, reload sau login, `{% csrf_token %}`.
- **'admin' namespace** → `path('admin/', admin.site.urls)` + `django.contrib.admin` trong `INSTALLED_APPS`.
- **TemplateDoesNotExist** → đúng đường dẫn `app/templates/app/...` + `APP_DIRS=True`.
- **export_csv() missing request** → trong `urls.py` dùng `views.export_csv` (không có `()`).
- **AttributeError CustomerDetailView** → đã khai báo ở urls nhưng chưa tạo view class/function.
- **UserAdmin date_joined non-editable** → để trong `readonly_fields`, không đưa vào `add_fieldsets`.
- **Resend OTP không reset** → sau JSON, JS gọi `startCountdown(remaining)`.
- **OTP cũ vẫn nhận** → khi resend phải **xoay OTP** và cập nhật `otp_sent_at`.

---

## 15) TODO / Phát triển thêm
- reCAPTCHA v3.
- Báo cáo thống kê (chart theo ngày/tỉnh).
- Export XLSX (openpyxl).
- Email xác nhận (tùy trường hợp).
- Soft deduplicate (phone+id_card theo TTL).
- Audit log ký điện tử (hash văn bản + chữ ký, IP, UA, timestamp).
