from datetime import date
from decimal import Decimal, InvalidOperation
from django import forms
from ..models import CustomerInfo
from .widgets import PlaceholderSelect

class CustomerInfoForm(forms.ModelForm):
    gender = forms.TypedChoiceField(
        label="Giới tính *",
        choices=CustomerInfo.GENDER_CHOICES,
        widget=forms.RadioSelect,
        coerce=str,
        empty_value=None,                    
        required=True,
    )
    
    permanent_address = forms.ChoiceField(
        label='Nơi đăng ký thường trú *',
        choices=[('', 'Nơi đang sống')] + list(CustomerInfo.PROVINCES),
        required=True,
        widget=PlaceholderSelect(attrs={'class': 'form-control placeholder-light'})
    )

    work_status = forms.ChoiceField(
        label='Trạng thái công việc *',
        choices=[('', 'Chọn thông tin công việc của bạn')] + list(CustomerInfo.WORK_STATUS),
        required=True,
        widget=PlaceholderSelect(attrs={'class': 'form-control placeholder-light'})
    )

    doc_provided = forms.ChoiceField(
        label='Chứng từ cung cấp *',
        choices=[('', 'Chứng từ có thể cung cấp')] + list(CustomerInfo.DOC_TYPES),
        required=True,
        widget=PlaceholderSelect(attrs={'class': 'form-control placeholder-light'})
    )
    class Meta:
        model = CustomerInfo
        fields = [
            'permanent_address', 'full_name', 'gender', 'phone_number',
            'birth_date', 'id_card', 'work_status', 'doc_provided', 'loan_amount', 'income',
            'monthly_payment', 'agree_call', 'agree_policy', 'agree_vpb'
        ]
        labels = {
            'permanent_address': 'Nơi đang sống *',
            'full_name': 'Họ và tên *',
            'gender': 'Giới tính *',
            'phone_number': 'Số điện thoại *',
            'birth_date': 'Ngày tháng năm sinh (DD/MM/YYYY)',
            'id_card': 'CCCD gắn chip/Căn cước *',
            'work_status': 'Trạng thái công việc *',
            'doc_provided': 'Chứng từ có thể cung cấp *',
            'loan_amount': 'Số tiền đăng ký *',
            'income': 'Thu nhập *',
            'monthly_payment': 'Tổng tiền trả góp hàng tháng *',
            'agree_call': 'Tôi đồng ý nhận cuộc gọi từ CNEXT JSC về sản phẩm dịch vụ và đang đăng ký.',
            'agree_policy': 'Tôi đã đọc và đồng ý với Chính sách bảo vệ dữ liệu cá nhân của CNEXT.',
            'agree_vpb': 'Tôi đồng ý với VPB SMBC FC thu thập, xử lý thông tin, dữ liệu của tôi để phục vụ mục đích đánh giá, phê duyệt hồ sơ vay tín chấp tại VPB SMBC FC từ thời điểm nộp đơn đến khi website VPB SMBC FC thông báo kết quả.',
        }
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Họ tên đầy đủ trên CCCD', 'required': True}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Số điện thoại di động'}),
            'birth_date': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'DD/MM/YYYY', 'id': 'id_birth_date'}
            ),  
            'id_card': forms.TextInput(attrs={'class': 'form-control','placeholder': 'Nhập 12 số CCCD gắn chip/Căn cước phôi mới'}),
            'loan_amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 10000000, 'max': 100000000, 'placeholder': 'Số tiền đăng ký trả góp qua thẻ'}),
            'income': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Thu nhập của bạn'}),
            'monthly_payment': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Tổng số tiền trả góp hàng tháng (nếu có)'}),
            'agree_call': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'agree_policy': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'agree_vpb': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field.required:
                field.error_messages = {'required': f'Vui lòng nhập {self.fields[field_name].label.lower()}.'}
                
        self.fields['birth_date'].input_formats = ['%d/%m/%Y']
            
        
    def clean(self):
        cleaned_data = super().clean()
        loan = cleaned_data.get('loan_amount') or 0
        income = cleaned_data.get('income') or 0
        monthly = cleaned_data.get('monthly_payment') or 0
        
        if not (10000000 <= loan <= 100000000):
            self.add_error('loan_amount', 'Số tiền cần vay phải trong khoảng 10–100 triệu.')

        if not (3000000 <= income <= 100000000):
            self.add_error('income', 'Thu nhập phải trong khoảng 3–100 triệu.')

        if income and monthly > income * Decimal('0.5'):
            self.add_error('monthly_payment', 'Số tiền trả góp không vượt quá 50% thu nhập.')
            
        if not cleaned_data.get('agree_call') or not cleaned_data.get('agree_policy') or not cleaned_data.get('agree_vpb'):
                raise forms.ValidationError("Bạn phải đồng ý với các điều khoản để tiếp tục.")
            
        return cleaned_data
    
    # Validation cho ngày sinh
    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if not birth_date:
            raise forms.ValidationError('Vui lòng nhập ngày tháng năm sinh.')
        if birth_date > date.today():  # So sánh trực tiếp ngày
            raise forms.ValidationError('Ngày sinh không được là ngày trong tương lai.')
        # Tính tuổi
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        if age < 18:
            raise forms.ValidationError('Bạn phải trên 18 tuổi.')
        return birth_date
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone and not phone.isdigit():
            raise forms.ValidationError('Số điện thoại không hợp lệ.')
        return phone
    
    def clean_id_card(self):
        id_card = self.cleaned_data.get('id_card')
        if not id_card:
            raise forms.ValidationError('Vui lòng nhập CCCD/CMND/Căn cước.')
        if not id_card.isdigit() or len(id_card) !=12:
            raise forms.ValidationError('CCCD/CMND/Căn cước phải là 12 số.')
        return id_card
    
    def clean_loan_amount(self):
        loan_amount = self.cleaned_data.get('loan_amount')
        if loan_amount is None or loan_amount == '':
            raise forms.ValidationError('Vui lòng nhập số tiền đăng ký.')
        try:
            if loan_amount < Decimal('10000000') or loan_amount > Decimal('100000000'):
                raise forms.ValidationError('Số tiền đăng ký phải từ 10,000,000 đến 100,000,000.')
            return loan_amount
        except (InvalidOperation, ValueError):
            raise forms.ValidationError('Số tiền đăng ký phải là số hợp lệ.')
    
class OTPForm(forms.Form):
    otp = forms.CharField(max_length=6, label='Mã OTP')