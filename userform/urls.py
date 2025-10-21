from django.urls import path

from userform.views import views as v


urlpatterns = [
    path('privacy-policy/', v.privacy_policy, name='privacy_policy'),
]
