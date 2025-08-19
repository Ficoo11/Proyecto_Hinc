from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
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

@login_required
def paneladmin_view(request):
    users = CustomUser.objects.all()
    return render(request, 'paneladmin.html', {'users': users})

@login_required
def add_user(request):
    if request.method == 'POST':
        name = request.POST['name']
        email = request.POST['email']
        role = request.POST['role']
        if not CustomUser.objects.filter(email=email).exists():
            user = CustomUser.objects.create_user(
                username=email.split('@')[0],
                email=email,
                first_name=name,
                password='default_password',  # Cambia esto por un formulario seguro
                role=role
            )
            messages.success(request, "Usuario agregado exitosamente.")
        else:
            messages.error(request, "El correo ya está registrado.")
        return redirect('paneladmin')
    return redirect('paneladmin')

@login_required
def edit_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        user.first_name = request.POST['name']
        user.email = request.POST['email']
        user.role = request.POST['role']
        user.save()
        messages.success(request, "Usuario actualizado exitosamente.")
        return redirect('paneladmin')
    return render(request, 'paneladmin.html', {'user': user})

@login_required
def delete_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        user.delete()
        messages.success(request, "Usuario eliminado exitosamente.")
        return redirect('paneladmin')
    return render(request, 'paneladmin.html', {'user': user})

def adminpanel(request):
    return render(request, 'paenladmin2.html')