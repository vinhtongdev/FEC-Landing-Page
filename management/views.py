import mimetypes
from pyexpat.errors import messages
from django.shortcuts import get_object_or_404, redirect, render

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView
from django.shortcuts import render
from django.http import FileResponse, Http404, HttpResponse
from django.db.models import Q
from .forms import FilterForm
from userform.models import CustomerInfo
import csv
from django.utils.encoding import smart_str

staff_only = [login_required, user_passes_test(lambda u: u.is_staff)]

@method_decorator(staff_only, name='dispatch')
class DashboardListView(ListView):
    model = CustomerInfo
    template_name = 'management/dashboard.html'
    
    # danh sách đối tượng trong template
    context_object_name = 'rows'
    
    paginate_by = 25
    ordering = ['-created_at']

    #lấy danh sách các đối tượng cần hiển thị 
    def get_queryset(self):
        qs = CustomerInfo.objects.all().order_by('-created_at')
        self.form = FilterForm(self.request.GET or None)
        
        if self.form.is_valid():
            q = self.form.cleaned_data.get('q')
            if q:
                qs = qs.filter(
                    Q(full_name__icontains=q) |
                    Q(phone_number__icontains=q) |
                    Q(id_card__icontains=q)
                )
                
            df = self.form.cleaned_data.get('date_from')
            dt = self.form.cleaned_data.get('date_to')
            
            if df: qs = qs.filter(created_at__date__gte=df)
            if dt: qs = qs.filter(created_at__date__lte=dt)
            
            province = self.form.cleaned_data.get('province')
            if province:
                qs = qs.filter(permanent_address=province)
                
            work = self.form.cleaned_data.get('work_status')
            if work:
                qs = qs.filter(work_status=work)
                
            gender = self.form.cleaned_data.get('gender')
            if gender:
                qs = qs.filter(gender=gender)
                
        return qs 
    
    # chuẩn bị và gửi thêm dữ liệu (context) tới file HTML template
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = getattr(self, 'form', FilterForm())
        # giữ querystring cho phân trang
        qd = self.request.GET.copy()
        qd.pop('page', None)
        ctx['querystring'] = qd.urlencode()
        
        # Trả về ctx (nay đã chứa rows, page_obj, form, và querystring) để Django render ra file HTML.
        return ctx
    
@method_decorator(staff_only, name='dispatch')
class CustomerDetailView(DetailView):
        model = CustomerInfo
        template_name = 'management/customer_detail.html'
        context_object_name = 'c'
        
@staff_member_required
def export_csv(request):
        """Xuất CSV theo bộ lọc hiện tại."""
        # Lấy lại queryset như ListView để đồng nhất
        view = DashboardListView()
        view.request = request
        qs = view.get_queryset()
        
        resp = HttpResponse(content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename=customer_data.csv; filename*=UTF-8''{quote(filename)}'
        
        # BOM
        resp.write(u'\ufeff'.encode('utf8'))
        
        writer = csv.writer(resp)
        writer.writerow([
            'ID','Họ tên','Giới tính','SĐT','CCCD','Tỉnh/TP','Công việc',
            'Số tiền đăng ký','Thu nhập','Trả góp/tháng','Ngày tạo'
        ])
        
        for r in qs:
            writer.writerow([
                r.id, r.full_name, dict(CustomerInfo.GENDER_CHOICES).get(r.gender, r.gender), r.phone_number, r.id_card,
                dict(CustomerInfo.PROVINCES).get(r.permanent_address, r.permanent_address),
                dict(CustomerInfo.WORK_STATUS).get(r.work_status, r.work_status),
                int(r.loan_amount), int(r.income), int(r.monthly_payment or 0),
                r.created_at.strftime('%d/%m/%Y %H:%M')
            ])
        return resp
        
@staff_member_required
def download_file(request, pk):
    obj = get_object_or_404(CustomerInfo, pk=pk)
    
    if not obj.signature_document:
        messages.warning(request, "Khách hàng này chưa có file PDF để tải.")
        return redirect('management:dashboard')
    try:
        f = obj.signature_document
        # open file ở chế độ nhị phân
        file_handle = f.open('rb')
        
        # Đoán content type, fallback PDF
        content_type = mimetypes.guess_type(f.name)[0] or 'application/pdf'
        
        # Trả stream về trình duyệt
        resp = FileResponse(file_handle, content_type=content_type)
        resp['Content-Disposition'] = f'attachment; filename="{smart_str(f"confirm_{obj.id}.pdf")}"'
        
        return resp
        
    except FileNotFoundError:
        # FileField trỏ đến file không còn trên đĩa
        messages.error(request, "Không tìm thấy file PDF trên máy chủ.")
        return redirect('management:dashboard')
    
    except Exception as e:
        messages.error(request, f"Lỗi tải file: {e}")
        return redirect('management:dashboard')
    
    