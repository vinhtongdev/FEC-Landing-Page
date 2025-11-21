from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib import admin
from django.urls import path, include
from userform.views.views import user_form, verify_otp, consent_info

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include(('accounts.urls','accounts'), namespace='accounts')),
    path('', user_form, name='user_form'),
    path('', include('userform.urls')),
    path('verify/', verify_otp, name='verify_otp'),
    path('dashboard/', include(('management.urls', 'management'), namespace='management')),
    path("reports/", include("report.urls", namespace="report")),
    path('consent/', consent_info, name='consent_info'),
    path('sw.js', TemplateView.as_view(template_name="sw.js", content_type='application/javascript'), name='service_worker'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler404 ='userform.views.views.error_404'
handler404 ='userform.views.views.error_403'
handler404 ='userform.views.views.error_500'
