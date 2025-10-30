from django import forms
from userform.models import CustomerInfo

class FilterForm(forms.Form):
    q = forms.CharField(label='Tìm kiếm', required=False, widget=forms.TextInput(
        attrs={'placeholder': 'Họ tên / SĐT / CCCD', 'class': 'form-control'}
    ))
    date_from = forms.DateField(label='Từ ngày', required=False,
                                input_formats=['%d/%m/%Y', '%Y-%m-%d'],
                                widget=forms.TextInput(attrs={'placeholder':'dd/mm/yyyy','class':'form-control'}))
    date_to   = forms.DateField(label='Đến ngày', required=False,
                                input_formats=['%d/%m/%Y', '%Y-%m-%d'],
                                widget=forms.TextInput(attrs={'placeholder':'dd/mm/yyyy','class':'form-control'}))
    province  = forms.ChoiceField(label='Tỉnh/Thành', required=False,
                                    choices=[('', 'Tất cả')] + list(CustomerInfo.PROVINCES),
                                    widget=forms.Select(attrs={'class':'form-select'}))
    work_status = forms.ChoiceField(label='Trạng thái công việc', required=False,
                                    choices=[('', 'Tất cả')] + list(CustomerInfo.WORK_STATUS),
                                    widget=forms.Select(attrs={'class':'form-select'}))
    gender = forms.ChoiceField(label='Giới tính', required=False,
                                choices=[('', 'Tất cả')] + list(CustomerInfo.GENDER_CHOICES),
                                widget=forms.Select(attrs={'class':'form-select'}))