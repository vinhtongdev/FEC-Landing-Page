from django.urls import path
from . import views

app_name = "report"

urlpatterns = [
    path("", views.report_dashboard, name="dashboard"),
    path("api/registrations/daily/", views.api_reg_daily, name="api_reg_daily"),
    path("api/registrations/monthly/", views.api_reg_monthly, name="api_reg_monthly"),
    path("api/registrations/quarterly/", views.api_reg_quarterly, name="api_reg_quarterly"),
    path("api/visits/daily/", views.api_visits_daily, name="api_visits_daily"),
    path("api/visits/monthly/", views.api_visits_monthly, name="api_visits_monthly"),
    path("api/visits/quarterly/", views.api_visits_quarterly, name="api_visits_quarterly"),
]
