from datetime import date
from django.shortcuts import render, redirect
from django.http import HttpResponse
from ..forms.forms import CustomerInfoForm, OTPForm
from django.contrib import messages
import pyotp
from twilio.rest import Client
from django.conf import settings
from django.core.mail import send_mail
import logging

logger = logging.getLogger(__name__)

def generate_otp():
    totp = pyotp.TOTP(pyotp.random_base32())
    return totp.now()


def send_otp(phone, otp): # Twilio SMS
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        messages = client.messages.create(
        body=f"Mã OTP của bạn là: {otp}",
        from_=settings.TWILIO_PHONE_NUMBER,
        to=phone
    )
        logger.info(f"OTP sent successfully. Message SID: {messages.sid}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP to {phone}: {str(e)}")
        return False
    

def user_form(request):
    if request.method == 'POST':
        form = CustomerInfoForm(request.POST)
        if form.is_valid():
            try:
                # Chuyển đổi birth_date thành chuỗi trước khi lưu vào session
                cleaned_data = form.cleaned_data.copy()  # Tạo bản sao
                if 'birth_date' in cleaned_data and isinstance(cleaned_data['birth_date'], date):
                    cleaned_data['birth_date'] = cleaned_data['birth_date'].strftime('%d/%m/%Y')
                    
                request.session['user_data'] = form.cleaned_data
                otp = generate_otp()
                request.session['otp'] = otp
                if send_otp(form.cleaned_data['phone_number'], otp):
                    return redirect('verify_otp')
                else:
                    return HttpResponse("Gửi OTP thất bại. Vui lòng thử lại!")
            except Exception as e:
                logger.error(f"Error in user_form view: {str(e)}")

    else:
        form = CustomerInfoForm()
    return render(request, 'userform/form.html', {'form': form})


def verify_otp(request):
    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['otp'] == request.session.get('otp'):
                user_data = request.session.get('user_data')
                CustomerInfoForm.objects.create(**user_data)
                del request.session['user_data']
                del request.session['otp']
                return HttpResponse('Đăng ký thành công!')
            else:
                return HttpResponse('Mã OTP không đúng!')
    else:
        form = OTPForm()
        
    return render(request, 'userform/otp.html', {'form': form})
                

