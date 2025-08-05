from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import CustomUserCreationForm, LoginForm
from .models import CustomUser

def index(request):
    return render(request, 'index.html')

def form_view(request):
    if request.method == 'POST':
        if 'register_submit' in request.POST:
            form = CustomUserCreationForm(request.POST)
            if form.is_valid():
                user = form.save()
                messages.success(request, "Registro exitoso. Ahora puedes iniciar sesión.")
            else:
                messages.error(request, "Error en el registro. Verifica los datos.")
        elif 'login_submit' in request.POST:
            form = LoginForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data['email']
                password = form.cleaned_data['password']
                user = authenticate(request, email=email, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('index')
                else:
                    messages.error(request, "Correo o contraseña incorrectos.")
    else:
        form = LoginForm()
    return render(request, 'form.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('form')