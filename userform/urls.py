from django.urls import path

from userform.views import views as v


urlpatterns = [
    path('privacy-policy/', v.privacy_policy, name='privacy_policy'),
    path('confirm-and-sign/<int:customer_id>/', v.confirm_and_sign, name='confirm_and_sign'),
    path('invalid/', v.invalid_access, name='invalid_access'),
    path('done/<int:customer_id>/', v.sign_done, name='sign_done'),
]
