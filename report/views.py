from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncDate, TruncMonth, ExtractQuarter

from userform.models import CustomerInfo
from report.models import ReportStub
from webstats.models import PageView 

@login_required
@permission_required("report.view_reports", raise_exception=True)
def report_dashboard(request):
    return render(request, "report/dashboard.html", {})

# --------- Helpers ----------
def _json_series(qs, x_key, y_key="count"):
    # Trả data [{x:..., y:...}, ...] cho Chart.js (labels & datasets)
    labels = []
    values = []
    for row in qs:
        labels.append(str(row[x_key]))
        values.append(row[y_key])
    return JsonResponse({"labels": labels, "values": values})

# --------- Customer registrations ----------
@login_required
@permission_required("report.view_reports", raise_exception=True)
def api_reg_daily(request):
    qs = (CustomerInfo.objects.
            annotate(d=TruncDate("created_at", tzinfo=timezone.get_current_timezone()))
            .values("d")
            .annotate(count=Count("id"))
            .order_by("d") 
        )
    return _json_series(qs, "d")

@login_required
@permission_required("report.view_reports", raise_exception=True)
def api_reg_monthly(request):
    qs = (CustomerInfo.objects
            .annotate(m=TruncMonth("created_at", tzinfo=timezone.get_current_timezone()))
            .values("m")
            .annotate(count=Count("id"))
            .order_by("m"))
    return _json_series(qs, "m")

@login_required
@permission_required("report.view_reports", raise_exception=True)
def api_reg_quarterly(request):
    qs = (CustomerInfo.objects
            .annotate(y=ExtractQuarter("created_at"))
            .values("y")
            .annotate(count=Count("id"))
            .order_by("y"))
    # labels kiểu "Q1", "Q2"
    labels = [f"Q{row['y']}" for row in qs]
    values = [row["count"] for row in qs]
    return JsonResponse({"labels": labels, "values": values})

# --------- Page visits ----------
@login_required
@permission_required("report.view_reports", raise_exception=True)
def api_visits_daily(request):
    qs = (PageView.objects
            .annotate(d=TruncDate("created_at", tzinfo=timezone.get_current_timezone()))
            .values("d")
            .annotate(count=Count("id"))
            .order_by("d"))
    return _json_series(qs, "d")

@login_required
@permission_required("report.view_reports", raise_exception=True)
def api_visits_monthly(request):
    qs = (PageView.objects
            .annotate(m=TruncMonth("created_at", tzinfo=timezone.get_current_timezone()))
            .values("m")
            .annotate(count=Count("id"))
            .order_by("m"))
    return _json_series(qs, "m")

@login_required
@permission_required("report.view_reports", raise_exception=True)
def api_visits_quarterly(request):
    qs = (PageView.objects
            .annotate(y=ExtractQuarter("created_at"))
            .values("y")
            .annotate(count=Count("id"))
            .order_by("y"))
    labels = [f"Q{row['y']}" for row in qs]
    values = [row["count"] for row in qs]
    return JsonResponse({"labels": labels, "values": values})