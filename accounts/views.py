from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('management:dashboard')
        messages.error(request, 'Email hoặc mật khẩu không đúng.')
    return render(request, 'accounts/login.html')

def logout_view(request):
    logout(request)
    return redirect('accounts:login')