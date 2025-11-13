from datetime import timedelta,date
from decimal import Decimal
from django.utils import timezone
import mimetypes
from django.contrib import messages
import random
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView
from django.shortcuts import render
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.db.models import Q
from django.db import transaction
from management.utils import is_manager
from .forms import CustomerQuickEditForm, FilterForm
from userform.models import CustomerInfo
import csv
from django.utils.encoding import smart_str
from .models import EditApproval

staff_only = [login_required, user_passes_test(lambda u: u.is_staff)]

def json_safe(data: dict) -> dict:
    """Chuyển đổi các kiểu dữ liệu không an toàn cho JSON (date, Decimal) thành chuỗi."""
    safe_data = {}
    for key, value in data.items():
        if isinstance(value, date):
            safe_data[key] = value.isoformat()  # Chuyển date thành 'YYYY-MM-DD'
        elif isinstance(value, Decimal):
            safe_data[key] = str(value) # Chuyển Decimal thành chuỗi
        else:
            safe_data[key] = value
    return safe_data

def is_manage(user):
    return user.is_active and user.groups.filter(name="manage").exists()

# @login_required(login_url='login')                # hoặc đường dẫn login của bạn
# @user_passes_test(is_manager)                     # chỉ nhóm 'manage' mới vào được
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
        ctx['is_manager'] = is_manager(self.request.user)
        
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
    
    
def  notify_manages(payload: dict):
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    layer = get_channel_layer()
    if not layer:
        return
    async_to_sync(layer.group_send)("managers", {"type":"approval.request", "data":payload})
    
@login_required
@require_GET
def customer_edit(request, pk):
    customer = get_object_or_404(CustomerInfo, pk=pk)
    form = CustomerQuickEditForm(instance=customer)
    
    action_url = reverse('management:customer_save_changes', kwargs={'pk': pk})
    
    # Trả về HTML partial cho modal
    return render(request, "management/_customer_edit_modal.html", {"customer": customer, "form": form, "action_url": action_url})
    

@login_required
@require_POST
@transaction.atomic
def customer_save_changes(request, pk):
    customer = get_object_or_404(CustomerInfo, pk=pk)
    form = CustomerQuickEditForm(request.POST, instance=customer)
    
    if not form.is_valid():
        return JsonResponse({'ok': False, "errors_html": form.as_bootstrap()}, status=400)
    
    if is_manager(request.user):
        form.save()
        messages.success(request, "Đã cập nhật khách hàng")
        return JsonResponse({'ok': True})
    
    if not form.has_changed():
        return JsonResponse({'ok': True, "message": "Không có sự thay đổi."})
    
    # Chỉ lấy những trường có giá trị đã thay đổi so với ban đầu.
    # form.changed_data chứa danh sách tên các trường đã thay đổi.
    changes = {name: form.cleaned_data.get(name) for name in form.changed_data}

    # Có thể trường hợp người dùng thay đổi rồi lại nhập về giá trị cũ
    if not changes:
        return JsonResponse({'ok': True, "message": "Không có sự thay đổi."})
    
    code = f"{random.randint(0, 999999):06d}"
    print(code)
    approval = EditApproval.objects.create(
        customer=customer,
        requested_by=request.user,
        code=code,
        payload=json_safe(changes), # <-- Áp dụng chuyển đổi an toàn cho JSON
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    
    notify_manages({
        "approval_id": approval.id,
        "customer_id": customer.id,
        "customer_name": customer.full_name,
        "requested_by": request.user.get_username(),
        "code": code,  # luồng nghiệp vụ yêu cầu manager đọc mã cho staff
        "expires_at": approval.expires_at.isoformat(),
        "changes": json_safe(changes), # <-- Gửi payload đã được xử lý
    })
    
    return JsonResponse({
        "ok": False,
        "requires_approval": True,
        "approval_id": approval.id,
        "message": "Yêu cầu phê duyệt đã gửi tới Quản lý. Vui lòng nhập mã 6 số."
    }, status=202)
    
@login_required
@require_POST
@transaction.atomic
def approval_verify_and_apply(request, approval_id):
    approval = get_object_or_404(EditApproval, pk=approval_id)
    
    if approval.status != "pending":
        return JsonResponse({"ok": False, "message": "Yêu cầu không còn hiệu lực."}, status=400)
    
    if approval.is_expired():
        approval.status = "expired"
        approval.save(update_fields=["status"])
        return JsonResponse({"ok": False, "message": "Mã đã hết hạn."}, status=400)
    
    input_code = (request.POST.get("code") or "").strip()
    if input_code != approval.code:
        return JsonResponse({"ok": False, "message": "Mã không đúng."}, status=400)
    
    # Apply Save
    customer = approval.customer
    for k, v in approval.payload.items():
        setattr(customer, k, v)
        
    customer.save()
    
    approval.status = "used"
    approval.used_at = timezone.now()
    approval.save(update_fields=["status", "used_at"])

    messages.success(request, "Đã lưu thay đổi sau khi xác thực quản lý.")
    
    # Gửi thông tin cho manager khi đã cập nhật thành công
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    layer = get_channel_layer()
    if not layer:
        return
    async_to_sync(layer.group_send)("update_customers", {"type":"update_customer", "data":{"result_update": "success", "customer_id": customer.id, "kind": "update_customer"}})
    
    return JsonResponse({"ok": True})
