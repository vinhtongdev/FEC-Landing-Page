from datetime import datetime
from io import BytesIO
from urllib.parse import urlencode
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse, JsonResponse
from django.core.files.base import ContentFile
from django.urls import reverse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from ..forms.forms import CustomerInfoForm, OTPForm
from django.contrib import messages
from django.conf import settings
import requests
import base64
import logging
import time
from ..helper.utils import OTP_TTL, make_checkbox_paragraph, normalize_id, normalize_phone, otp_seconds_left, session_safe, mask_phone, format_vn_phone, format_vn_currency
import base64
import time
import random
from ..models import CustomerInfo
from django_ratelimit.decorators import ratelimit
from django.db import IntegrityError
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, KeepInFrame, CondPageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import json


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
                request.session['otp_phone'] = form.cleaned_data.get('phone_number')
                # ok = send_otp(form.cleaned_data['phone_number'], otp)
                ok = True
                print("OTP: ", otp)
                if ok:
                    request.session['otp'] = str(otp)
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
        if request.method == 'POST' and request.POST.get('action') == 'resend':
            is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
            if remaining > 0:
                msg = f"Vui lòng đợi {remaining}s rồi mới gửi lại mã."
                if is_ajax:
                    return JsonResponse({'ok': False, 'remaining': remaining, 'message': msg})
                messages.warning(request, msg)
                masked_phone = mask_phone(request.session.get('otp_phone'))
                return render(request, 'userform/otp.html', {
                    'form': OTPForm(),
                    'remaining': remaining,
                    'masked_phone': masked_phone,
                })
            # qua cooldown
            if getattr(request, 'limited', False):
                msg = "Bạn đã gửi lại quá nhiều lần. Vui lòng thử lại sau."
                if is_ajax:
                    return JsonResponse({'ok': False, 'remaining': remaining, 'message': msg})
                messages.error(request, msg)
                return redirect('verify_otp')
            
            otp = generate_otp()
            request.session['otp'] = str(otp)
            phone = request.session.get('otp_phone')
            # ok = phone and send_otp(phone, otp)
            # TEST
            print("OTP: ", otp)
            ok = True
            if ok:
                request.session['otp'] = str(otp)
                request.session['otp_sent_at'] = int(time.time())
                remaining = seconds_remaining(request.session)
                if is_ajax:
                    return JsonResponse({'ok': True, 'remaining': OTP_TTL, 'message': "Đã gửi lại OTP."})
                messages.success(request, "Đã gửi lại OTP.")
            else:
                if is_ajax:
                    return JsonResponse({'ok': False, 'remaining': remaining, 'message': "Gửi lại OTP thất bại. Vui lòng thử."})
                messages.error(request, "Gửi lại OTP thất bại. Vui lòng thử lại.")
                    
            masked_phone = mask_phone(request.session.get('otp_phone'))
            return render(request, 'userform/otp.html', {
                'form': OTPForm(),
                'remaining': remaining,
                'masked_phone': masked_phone,
            })

        # Submit OTP
        form = OTPForm(request.POST)
        if form.is_valid():
            if otp_seconds_left(request.session) <= 0:
                messages.error(request, "Mã OTP đã hết hạn. Vui lòng bấm Gửi lại.")
                masked_phone = mask_phone(request.session.get('otp_phone'))
                return render(request, 'userform/otp.html', {
                    'form': OTPForm(),
                    'remaining': otp_seconds_left(request.session),  # thường = 0
                    'masked_phone': masked_phone,
                })
                
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

    # OTP hết hạn
    if request.session.get('otp_ok_for_customer_id') != customer.id:
        url = f"{reverse('invalid_access')}?{urlencode({'msg':'Phiên ký đã hết hạn. Vui lòng xác thực lại OTP.'})}"
        return redirect(url)

    if request.method == 'POST':
        signature_data = request.POST.get('signature_data')
        if signature_data:
            try:
                # 1) Lưu ảnh chữ ký
                fmt, imgstr = signature_data.split(';base64,')
                ext = fmt.split('/')[-1]
                data = ContentFile(base64.b64decode(imgstr), name=f'signature_{customer.id}.{ext}')
                customer.signature = data
                customer.save(update_fields=['signature'])

                # 2) Nạp nội dung PDF
                json_path = settings.BASE_DIR / 'userform' / 'helper' / 'pdf_content.json'
                with open(json_path, 'r', encoding='utf-8') as f:
                    pdf_content = json.load(f)

                # 3) Khởi tạo PDF
                buffer = BytesIO()
                doc = SimpleDocTemplate(
                    buffer, pagesize=A4,
                    rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=40
                )

                # --- FONT/STYLE ---
                font_regular_path = settings.BASE_DIR / 'fonts' / 'times.ttf'
                font_bold_path    = settings.BASE_DIR / 'fonts' / 'timesbd.ttf'
                checkbox_font_path = settings.BASE_DIR / 'fonts' / 'DejaVuSans.ttf'
                pdfmetrics.registerFont(TTFont('TimesNewRoman', str(font_regular_path)))
                pdfmetrics.registerFont(TTFont('TimesNewRoman-Bold', str(font_bold_path)))
                pdfmetrics.registerFont(TTFont('DejaVuSans', str(checkbox_font_path)))

                styles = getSampleStyleSheet()
                style_header  = ParagraphStyle('header',  fontName='TimesNewRoman',      fontSize=10, leading=13, alignment=0)
                style_title   = ParagraphStyle('title',   fontName='TimesNewRoman-Bold', fontSize=15, leading=19, alignment=1, spaceBefore=6, spaceAfter=16)
                style_label   = ParagraphStyle('label',   fontName='TimesNewRoman-Bold', fontSize=11, leading=15, spaceBefore=6, spaceAfter=2)
                style_normal  = ParagraphStyle('normal',  fontName='TimesNewRoman',      fontSize=11, leading=15, spaceAfter=6)
                style_bullet  = ParagraphStyle('bullet',  fontName='TimesNewRoman',      fontSize=11, leading=15, leftIndent=16, firstLineIndent=-8, spaceAfter=2)
                style_right   = ParagraphStyle('right',   fontName='TimesNewRoman',      fontSize=11, leading=15, alignment=2, spaceBefore=6, spaceAfter=8)
                style_sign    = ParagraphStyle('sign',    fontName='TimesNewRoman',      fontSize=11, leading=16, alignment=2, spaceBefore=10)
                
                style_checkbox = ParagraphStyle(
                'checkbox',
                fontName='DejaVuSans',   # dùng DejaVuSans để hiển thị ☑ / ☐
                fontSize=11,
                leading=15,
                spaceAfter=2)

                Story = []

                # --- HEADER (trái) + LOGO (phải) ---
                company_header = Paragraph(pdf_content.get('company_header','').replace('\n','<br/>'), style_header)
                logo_path = settings.BASE_DIR / 'static' / 'images' / 'fec-logo.png'
                if logo_path.exists():
                    logo = RLImage(str(logo_path), width=140, height=35)
                else:
                    logo = Paragraph("FE CREDIT", style_title)

                header_tbl = Table([[company_header, logo]], colWidths=[350, 120])
                header_tbl.setStyle([
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('ALIGN', (1,0), (1,0), 'RIGHT')
                ])
                Story.append(header_tbl)
                Story.append(Spacer(1, 8)) 

                # --- TIÊU ĐỀ ---
                Story.append(Paragraph(pdf_content.get('title', 'VĂN BẢN XÁC NHẬN'), style_title))

                # --- KHỐI THÔNG TIN KHÁCH HÀNG ---
                email = getattr(customer, 'email', '') or ''  # nếu chưa có field email thì để rỗng
                customer_block = pdf_content.get('customer_block_label','').format(
                    full_name = customer.full_name,
                    id_card   = customer.id_card,
                    phone     = format_vn_phone(customer.phone_number),
                    email     = email
                ).replace('\n','<br/>')
                Story.append(Paragraph(customer_block, style_normal))

                # --- LỜI MỞ ĐẦU ---
                intro_ack = pdf_content.get('intro_ack','')
                if intro_ack:
                    Story.append(Paragraph(intro_ack.replace('\n','<br/>'), style_normal))

                # --- MỤC 1: Loại dữ liệu cá nhân ---
                s1_title = pdf_content.get('section_1_title','')
                if s1_title:
                    Story.append(Paragraph("1. " + s1_title, style_label))
                for key in ('section_1_body','section_1_basic','section_1_sensitive'):
                    txt = pdf_content.get(key,'')
                    if txt:
                        Story.append(Paragraph(txt.replace('\n','<br/>'), style_normal))

                # --- MỤC 2: Mục đích/cách thức/đối tượng xử lý ---
                s2_title = pdf_content.get('section_2_title','')
                if s2_title:
                    Story.append(Paragraph("2. " + s2_title, style_label))
                for li in pdf_content.get('section_2_list', []):
                    txt = li.strip()
                    if not txt.startswith('•'):
                        txt = '• ' + txt
                    Story.append(Paragraph(txt, style_bullet))

                # --- MỤC 3: Hậu quả ---
                s3_title = pdf_content.get('section_3_title','')
                if s3_title:
                    Story.append(Paragraph("3. " + s3_title, style_label))
                s3_body = pdf_content.get('section_3_body','')
                if s3_body:
                    Story.append(Paragraph(s3_body.replace('\n','<br/>'), style_normal))

                # --- MỤC 4: Thời gian xử lý ---
                s4_title = pdf_content.get('section_4_title','')
                if s4_title:
                    Story.append(Paragraph("4. " + s4_title, style_label))
                s4_body = pdf_content.get('section_4_body','')
                if s4_body:
                    Story.append(Paragraph(s4_body.replace('\n','<br/>'), style_normal))

                # --- MỤC 5: Quyền & Nghĩa vụ ---
                s5_title = pdf_content.get('section_5_title','')
                if s5_title:
                    Story.append(Paragraph("5. " + s5_title, style_label))
                for li in pdf_content.get('section_5_list', []):
                    txt = li.strip()
                    if not txt.startswith('•'):
                        txt = '• ' + txt
                    Story.append(Paragraph(txt, style_bullet))

                # --- MỤC 6 ---
                s6_title = pdf_content.get('section_6_title','')
                if s6_title:
                    Story.append(Paragraph("6. " + s6_title, style_label))
                s6_body = pdf_content.get('section_6_body','')
                if s6_body:
                    Story.append(Paragraph(s6_body.replace('\n','<br/>'), style_normal))

                # --- MỤC 7 ---
                s7_title = pdf_content.get('section_7_title','')
                if s7_title:
                    Story.append(Paragraph("7. " + s7_title, style_label))
                s7_body = pdf_content.get('section_7_body','')
                if s7_body:
                    Story.append(Paragraph(s7_body.replace('\n','<br/>'), style_normal))

                # --- Mục 8 ---
                sec8_title    = pdf_content.get('section_8_title')
                sec8_body     = (pdf_content.get('section_8_body') or '').replace('\n', '<br/>')
                sec8_choices  = pdf_content.get('section_8_choices', [])
                sec8_selected = pdf_content.get('section_8_selected', [])

                if sec8_title:
                    Story.append(Paragraph("8. " + sec8_title, style_label))
                if sec8_body:
                    Story.append(Paragraph(sec8_body, style_normal))

                # Bù độ dài để tránh IndexError
                if len(sec8_selected) < len(sec8_choices):
                    sec8_selected += [False] * (len(sec8_choices) - len(sec8_selected))

                for i, line in enumerate(sec8_choices):
                    checked = bool(sec8_selected[i])
                    Story.append(make_checkbox_paragraph(line, checked, style_normal))

                Story.append(Spacer(1, 6))

                # --- Khối yêu cầu gửi hyperlink (nếu có) ---
                hyper = pdf_content.get('hyperlink_block','')
                if hyper:
                    Story.append(Paragraph(hyper.replace('\n','<br/>'), style_normal))

                # --- NGÀY/ĐỊA ĐIỂM ---
                now = datetime.now()
                date_str = f"TP.HCM, ngày {now.day} tháng {now.month} năm {now.year}"
                Story.append(Paragraph(date_str, style_right))
                Story.append(Spacer(1, 6))

                # --- KHỐI CHỮ KÝ ---
                sign_title = pdf_content.get('sign_title', 'Khách hàng xác nhận')
                sign_note  = pdf_content.get('sign_note', '(ký, ghi rõ họ tên)')
                sign_name  = pdf_content.get('sign_name_template', '[{full_name}]').format(full_name=customer.full_name)

                # Tiêu đề
                Story.append(Paragraph(sign_title, style_sign))
                Story.append(Spacer(1, 6))

                # Ảnh chữ ký NẰM TRÊN
                if customer.signature:
                    sig_img = RLImage(customer.signature.path, width=180, height=80)
                    sig_img.hAlign = 'RIGHT'
                    Story.append(sig_img)
                    Story.append(Spacer(1, 4))

                # Ghi chú + Tên
                Story.append(Paragraph(sign_note, style_sign))
                Story.append(Paragraph(sign_name, style_sign))

                # --- XUẤT FILE ---
                doc.build(Story)
                pdf_data = buffer.getvalue()
                buffer.close()

                pdf_file = ContentFile(pdf_data, name=f'signed_document_{customer.id}.pdf')
                customer.signature_document = pdf_file
                customer.save(update_fields=['signature_document'])

                messages.success(request, 'Đã ký thành công và lưu văn bản xác nhận.')
                return redirect('sign_done', customer_id=customer.id)

            except Exception as e:
                logger.error(f'Error in signing: {str(e)}')
                messages.error(request, 'Có lỗi khi ký. Vui lòng thử lại.')

    # GET hoặc lỗi
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
