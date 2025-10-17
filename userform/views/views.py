from django.shortcuts import render, redirect
from django.http import HttpResponse
from ..forms.forms import CustomerInfoForm, OTPForm
from django.contrib import messages
from django.conf import settings
import requests
import base64
import logging
import time
from ..helper.utils import session_safe, mask_phone
import base64
import logging
import time
from ..helper.utils import session_safe, mask_phone
import random
from ..models import CustomerInfo
from django.utils import timesince
from django_ratelimit.decorators import ratelimit


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

        # Ngược lại là submit OTP
        form = OTPForm(request.POST)
        if form.is_valid():
            if str(form.cleaned_data['otp']) == str(request.session.get('otp')):
                user_data = request.session.get('user_data')

                # Bind lại vào ModelForm để lưu model chính xác
                mf = CustomerInfoForm(user_data)
                if mf.is_valid():
                    mf.save()
                    # dọn session
                    for k in ('user_data','otp','otp_sent_at','otp_phone'):
                        request.session.pop(k, None)
                    return HttpResponse('Đăng ký thành công!')
                else:
                    # Trường hợp hiếm: dữ liệu parse lại lỗi → quay về form nhập liệu
                    return render(request, 'userform/form.html', {'form': mf})
            else:
                messages.error(request, 'Mã OTP không đúng!')

        # Fallthrough: render lại trang OTP với lỗi
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

