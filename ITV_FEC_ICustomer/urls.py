from django.conf import settings
from django.conf.urls.static import static

"""
URL configuration for ITV_FEC_ICustomer project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from userform.views.views import user_form, verify_otp

urlpatterns = [
    path('', user_form, name='user_form'),
    path('', include('userform.urls')),
    path('verify/', verify_otp, name='verify_otp'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler404 ='userform.views.views.error_404'
handler404 ='userform.views.views.error_403'
handler404 ='userform.views.views.error_500'
