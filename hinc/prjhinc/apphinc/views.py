from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages


def index(request):
    return render(request, 'index.html')


def login_view(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Django no autentica por email por defecto, obtenemos username primero
        try:
            user = User.objects.get(email=email)
            user_auth = authenticate(request, username=user.username, password=password)
        except User.DoesNotExist:
            user_auth = None

        if user_auth is not None:
            login(request, user_auth)
            return redirect('index')
        else:
            messages.error(request, "Correo o contraseña incorrectos.")

    return render(request, 'login.html')


def register_view(request):
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirmPassword')

        if password != confirm_password:
            messages.error(request, "Las contraseñas no coinciden.")
            return render(request, 'register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "El correo ya está registrado.")
            return render(request, 'register.html')

        # Crear usuario con username igual al email antes de la @ para simplificar
        username = email.split('@')[0]

        user = User.objects.create_user(username=username, email=email, password=password, first_name=name)
        user.save()
        messages.success(request, "Registro exitoso. Ahora puedes iniciar sesión.")
        return redirect('login')

    return render(request, 'register.html')


def logout_view(request):
    logout(request)
    return redirect('login')