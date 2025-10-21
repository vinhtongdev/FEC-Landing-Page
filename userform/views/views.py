from io import BytesIO
from urllib.parse import urlencode
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse
from django.core.files.base import ContentFile
from django.urls import reverse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from PIL import Image
from ..forms.forms import CustomerInfoForm, OTPForm
from django.contrib import messages
from django.conf import settings
import requests
import base64
import logging
import time
from ..helper.utils import normalize_id, normalize_phone, session_safe, mask_phone
import base64
import time
from ..helper.utils import session_safe, mask_phone, format_vn_phone, format_vn_currency
import random
from ..models import CustomerInfo
from django_ratelimit.decorators import ratelimit
from django.db import IntegrityError
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


logger = logging.getLogger(__name__)

RESEND_COOLDOWN = 45  # giây

def seconds_remaining(session) -> int:
    """Số giây còn lại trước khi được gửi lại OTP."""
    sent = session.get("otp_sent_at")
    if not sent:
        return 0

    try:
        elapsed = int(time.time()) - int(sent)
        left = RESEND_COOLDOWN - elapsed
        return left if left > 0 else 0
    except Exception:
        return 0


def generate_otp():
    return f"{random.randint(0, 999999):06d}"


# def send_otp(phone, otp): # Twilio SMS
#     try:
#         client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
#         messages = client.messages.create(
#         body=f"Mã OTP của bạn là: {otp}",
#         from_=settings.TWILIO_PHONE_NUMBER,
#         to=phone
#     )
#         logger.info(f"OTP sent successfully. Message SID: {messages.sid}")
#         return True
#     except Exception as e:
#         logger.error(f"Failed to send OTP to {phone}: {str(e)}")
#         return False
    
def send_otp(phone, otp): # South Telecom
    try:
        auth_key = base64.b64encode(f"{settings.SOUTH_API_USER}:{settings.SOUTH_API_PWD}".encode()).decode('utf-8')
        
        if phone.startswith('0'):
            phone = '84' + phone[1:]
        elif not phone.startswith('84'):
            phone = '84' + phone;
        
        payload = {
            "from": settings.SOUTH_FROM,
            "to": phone,
            "text": f"Mã OTP của bạn là: {otp}",
            "unicode": 0, # 0: text thông thường (nếu nội dung tiếng Việt, dùng 1),
            "dlr": 1, # 1: Yêu cầu report DLR (nếu cần)
            # "smsid": "your_unique_sms_id",  # Tùy chọn, dùng để theo dõi DLR
            # "campaignid": "your_campaign_id",  # Tùy chọn
            "contentid": 1 # 1: Tin OTP (theo tài liệu)
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Basic {auth_key}"
        }
        
        # Gửi POSt request
        response = requests.post(settings.SOUTH_API_URL, json=payload, headers=headers)
        
        # Check response
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 1:
                logger.info(f"OTP sent successfully to {phone}. Errorcode: {data.get('errorcode')}")
                return True
            else:
                logger.error(f"Failed to send OTP to {phone}. Errorcode: {data.get('errorcode')}")
                return False
        else:
            logger.error(f"Failed to send OTP to {phone}: HTTP {response.status_code} - {response.text}")
            return False
        
    except Exception as e:
        logger.error(f"Failed to send OTP to {phone}: {str(e)}")
        return False

def user_form(request):
    if request.method == 'POST':
        form = CustomerInfoForm(request.POST)
        if form.is_valid():
            try:
                cleaned = session_safe(form.cleaned_data.copy())
                request.session['user_data'] = cleaned
                
                otp = generate_otp() 
                request.session['otp'] = str(otp)
                
                request.session['otp_phone'] = form.cleaned_data.get('phone_number')
                
                if send_otp(form.cleaned_data['phone_number'], otp):
                    request.session['otp_sent_at'] = int(time.time()) # Lưu thời điểm gửi
                    return redirect('verify_otp')
                else:
                    form.add_error("phone_number", "Không gửi được OTP. Vui lòng kiểm tra số điện thoại hoặc thử lại sau.")
                    messages.error(request, "Gửi OTP thất bại. Bạn hãy thử lại hoặc chọn kênh khác.")
                    # dọn những biến OTP đã tạo dở
                    for k in ('otp', 'otp_sent_at'):
                        request.session.pop(k, None)
                    return render(request, 'userform/form.html', {'form': form})
            except Exception as e:
                logger.error(f"Error in user_form view: {str(e)}")
                messages.error(request, "Có lỗi hệ thống. Vui lòng thử lại sau ít phút.")
                return HttpResponse("Có lỗi xảy ra. Vui lòng thử lại sau.")

        else:
            return render(request, 'userform/form.html', {'form': form})
    initial = request.session.get('user_data') or None
    form = CustomerInfoForm(initial)
    return render(request, 'userform/form.html', {'form': form})

@ratelimit(key='ip', rate='5/m', block=False) # Giới hạn 5 lần/phút theo IP
def verify_otp(request):
    # Tính còn bao nhiêu giây cooldown (để hiển thị và disable nút)
    remaining = seconds_remaining(request.session)

    if request.method == 'POST':
        # Nếu bấm "Gửi lại"
        if request.POST.get('action') == 'resend':
            if remaining > 0:
                messages.warning(request, f"Vui lòng đợi {remaining}s rồi mới gửi lại mã.")
            else:
                otp = generate_otp()
                
                # Kiểm tra nếu bị rate-limit
                if getattr(request, 'limited', False):
                    messages.error(request, "Bạn đã gửi lại quá nhiều lần. Vui lòng thử lại sau.")
                    return redirect('verify_otp')
                
                request.session['otp'] = str(otp)
                phone = request.session.get('otp_phone')
                if phone and send_otp(phone, otp):
                    request.session['otp_sent_at'] = int(time.time())
                    messages.success(request, "Đã gửi lại OTP.")
                else:
                    messages.error(request, "Gửi lại OTP thất bại. Vui lòng thử lại.")
                    
            # Sau khi xử lý resend, tính lại remaining và render trang
            remaining = seconds_remaining(request.session)
            masked_phone = mask_phone(request.session.get('otp_phone'))
            return render(request, 'userform/otp.html', {
                'form': OTPForm(),
                'remaining': remaining,
                'masked_phone': masked_phone,
            })

        # Submit OTP
        form = OTPForm(request.POST)
        if form.is_valid():
            if str(form.cleaned_data['otp']) == str(request.session.get('otp')):
                user_data = request.session.get('user_data') or {}

                # Bind lại vào ModelForm để lưu model chính xác
                mf = CustomerInfoForm(user_data)
                if mf.is_valid():
                    
                    phone = mf.cleaned_data['phone_number']
                    idno = mf.cleaned_data['id_card']
                    exists_open = CustomerInfo.objects.filter(
                        phone_number = normalize_phone(phone),
                        id_card = normalize_id(idno),
                        status = 'OPEN'
                    ).exists()
                    
                    if exists_open:
                        messages.info(request,
                            "Hồ sơ của bạn đã được ghi nhận và đang xử lý. "
                            "Vui lòng chờ kết quả hoặc liên hệ tổng đài để cập nhật.")
                        # có thể chuyển tới 1 trang 'status' nếu bạn có
                        masked_phone = mask_phone(request.session.get('otp_phone'))
                        return render(request, 'userform/otp.html', {
                            'form': OTPForm(),
                            'remaining': seconds_remaining(request.session),
                            'masked_phone': masked_phone,
                        })
                    
                    try:
                        obj = mf.save()
                        request.session['otp_ok_for_customer_id'] = obj.id
                        # save successfully -> clean session
                        for k in ('user_data','otp','otp_sent_at','otp_phone'):
                            request.session.pop(k, None)
                        return redirect('confirm_and_sign', customer_id=obj.id)
                    
                    except IntegrityError:
                        messages.info(request,
                            "Hồ sơ của bạn đã tồn tại và đang xử lý. "
                            "Vui lòng chờ kết quả.")
                        masked_phone = mask_phone(request.session.get('otp_phone'))
                        return render(request, 'userform/otp.html', {
                            'form': OTPForm(),
                            'remaining': seconds_remaining(request.session),
                            'masked_phone': masked_phone,
                        })
                    
                else:
                    # Trường hợp hiếm: dữ liệu parse lại lỗi → quay về form nhập liệu
                    return render(request, 'userform/form.html', {'form': mf})
            else:
                messages.error(request, 'Mã OTP không đúng!')

        remaining = seconds_remaining(request.session)
        masked_phone = mask_phone(request.session.get('otp_phone'))
        return render(request, 'userform/otp.html', {
            'form': form,
            'remaining': remaining,
            'masked_phone': masked_phone,
        })

    # GET: render trang OTP
    masked_phone = mask_phone(request.session.get('otp_phone'))
    return render(request, 'userform/otp.html', {
        'form': OTPForm(),
        'remaining': remaining,
        'masked_phone': masked_phone,
    })            

def privacy_policy(request):
    return render(request, 'userform/privacy_policy.html')

@ratelimit(key='ip', rate='5/m', block=True)
def confirm_and_sign(request, customer_id):
    customer = get_object_or_404(CustomerInfo, id=customer_id)
    
    if request.session.get('otp_ok_for_customer_id') != customer.id:
        url = f"{reverse('invalid_access')}?{urlencode({'msg':'Phiên ký đã hết hạn. Vui lòng xác thực lại OTP.'})}"
        return redirect(url)
    
    if request.method == 'POST':
        signature_data = request.POST.get('signature_data')
        if signature_data:
            try:
                # handle signed Base64 -> ImageField
                format, imgstr = signature_data.split(';base64,')
                ext = format.split('/')[-1]
                data = ContentFile(base64.b64decode(imgstr), name=f'signature_{customer.id}.{ext}')
                customer.signature = data
                customer.save()
                
                # Generate PDF with auto-fill and signed image
                buffer = BytesIO()
                p = canvas.Canvas(buffer, pagesize=A4)
                width, height = A4
                
                # Register font
                font_path = 'fonts/NotoSans-Regular.ttf'
                pdfmetrics.registerFont(TTFont('NotoSans', font_path))
                
                # Set font
                p.setFont("NotoSans", 12)
                
                # Auto fill text into PDF(Optional Positions)
                p.drawString(100,height - 100, f"Họ tên: {customer.full_name}")
                p.drawString(100, height - 120, f"Giới tính: {customer.get_gender_display()}")
                p.drawString(100, height - 140, f"Số điện thoại: {customer.phone_number}")
                p.drawString(100, height - 160, f"Ngày sinh: {customer.birth_date.strftime('%d/%m/%Y')}")
                # ... (thêm các field khác tương tự)
                p.drawString(100, height - 300, "Điều khoản: Bằng việc ký, tôi xác nhận... (thêm nội dung đầy đủ)")
                
                # embed signature image
                signature_path = customer.signature.path # đường dẫn file tạm thời
                img = Image.open(signature_path)
                img_width, img_height = img.size
                p.drawInlineImage(signature_path,100, height - 500, width=img_width*0.5, height=img_height*0.5) # scale 50%
                
                p.save()
                pdf_data = buffer.getvalue()
                buffer.close()
                
                # Save PDF to FileField
                pdf_file = ContentFile(pdf_data, name=f'signed_document_{customer.id}.pdf')
                customer.signature_document = pdf_file
                customer.save()

                
                messages.success(request, 'Đã ký thành công và lưu văn bản xác nhận.')
                return redirect('sign_done', customer_id=customer.id)
            
            except Exception as e:
                logger.error(f'Error in signing: {str(e)}')
                messages.error(request, ' Có lỗi khi ký. Vui lòng thử lại.')
    
    context = {
        'customer': customer,
        'formatted_phone': format_vn_phone(customer.phone_number),
        'formatted_loan': format_vn_currency(customer.loan_amount),
        'formatted_income': format_vn_currency(customer.income),
        'formatted_monthly': format_vn_currency(customer.monthly_payment),
    }            
    return render(request, 'userform/confirmation.html', context)

def sign_done(request, customer_id:int):
    customer = get_object_or_404(CustomerInfo, id=customer_id)
    
    if request.session.get('otp_ok_for_customer_id') != customer.id:
        return redirect(f"{reverse('invalid_access')}?{urlencode({'status':403,'msg':'Phiên truy cập không hợp lệ.'})}")
    
    request.session.pop('otp_ok_for_customer_id', None)
    return render(request, 'userform/done.html', {'customer': customer})

def invalid_access(request):
    msg = request.GET.get('msg') or "Liên kết bạn truy cập không hợp lệ hoặc đã hết hạn."
    return render(request, "errors/invalid_access.html", {'message': msg}, status=400)

def _get_client_ip(request):
    ip = request.META.get("HTTP_X_FORWARDED_FOR")
    return ip.split(",")[0].strip() if ip else request.META.get("REMOTE_ADDR")


def error_404(request, exception):
    return render(request, 'errors/404.html', status=404)

def error_403(request, exception):
    return render(request, 'errors/403.html', status=403)

def error_500(request, exception):
    return render(request, 'errors/500.html', status=500)
