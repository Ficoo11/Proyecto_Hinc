from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.backends import ModelBackend
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, LoginForm, ProductoForm  # Añadido ProductoForm aquí
from .models import CustomUser, Producto
import logging

# Configurar logging para depuración
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def index(request):
    return render(request, 'index.html', {'user': request.user if request.user.is_authenticated else None})

def register_view(request):
    if request.method == 'POST':
        # Crear una copia de request.POST y añadir role y estado por defecto
        post_data = request.POST.copy()
        post_data['role'] = 'Usuario'  # Valor por defecto para role
        post_data['estado'] = 'Habilitado'  # Valor por defecto para estado
        form = CustomUserCreationForm(post_data)
        logger.debug(f"Datos recibidos en registro: {post_data}")
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password1')  # Obtener la contraseña del formulario
            if password:  # Si se proporcionó una contraseña
                user.set_password(password)
            user.save()
            messages.success(request, "Registro exitoso. Ahora puedes iniciar sesión.")
            return redirect('login')
        else:
            logger.debug(f"Errores de validación: {form.errors}")
            messages.error(request, "Error en el registro. Por favor, corrige los siguientes problemas:")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label}: {error}")
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = CustomUser.objects.filter(email=email).first()
            if user and user.check_password(password) and user.estado == 'Habilitado':
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
                messages.success(request, "Inicio de sesión exitoso.")
                return redirect('index')
            else:
                messages.error(request, "Correo o contraseña incorrectos, o usuario inhabilitado.")
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('index')

@login_required
def paneladmin_view(request):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para acceder al panel de administración.")
        return redirect('index')
    users = CustomUser.objects.all()
    action = request.GET.get('action')
    user_id = request.GET.get('user_id')
    user = None
    if action == 'edit' and user_id:
        user = get_object_or_404(CustomUser, id=user_id)
    elif action == 'delete' and user_id:
        user = get_object_or_404(CustomUser, id=user_id)
    return render(request, 'paneladmin.html', {'users': users, 'action': action, 'user': user})

@login_required
def add_user(request):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para agregar usuarios.")
        return redirect('paneladmin')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            if request.POST.get('password1'):  # Solo actualizar contraseña si se proporciona
                user.set_password(request.POST.get('password1'))
            user.save()
            messages.success(request, "Usuario agregado exitosamente.")
            return redirect('paneladmin')
        else:
            messages.error(request, "Error al agregar usuario. Verifica los datos.")
            for error in form.errors.values():
                messages.error(request, error)
    return redirect('paneladmin')

@login_required
def edit_user(request, user_id):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para editar usuarios.")
        return redirect('paneladmin')
    user = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, instance=user)
        logger.debug(f"Datos recibidos: {request.POST}")
        if form.is_valid():
            logger.debug(f"Datos validados: {form.cleaned_data}")
            user = form.save(commit=False)
            password = form.cleaned_data.get('password1')
            if password:  # Solo actualizar contraseña si se proporciona
                user.set_password(password)
            # Depurar y manejar los campos role y estado
            try:
                user.role = form.cleaned_data['role']
                user.estado = form.cleaned_data['estado']
            except KeyError as e:
                messages.error(request, f"Error al procesar el campo '{e}'. Verifica el formulario. Datos validados: {form.cleaned_data}")
                return render(request, 'paneladmin.html', {'users': CustomUser.objects.all(), 'action': 'edit', 'user': user})
            user.save()
            messages.success(request, "Usuario actualizado exitoso.")
            return redirect('paneladmin')
        else:
            messages.error(request, f"Error al actualizar usuario. Verifica los datos. Errores: {form.errors}")
            for error in form.errors.values():
                messages.error(request, error)
    return render(request, 'paneladmin.html', {'users': CustomUser.objects.all(), 'action': 'edit', 'user': user})

@login_required
def delete_user(request, user_id):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para eliminar usuarios.")
        return redirect('paneladmin')
    user = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        user.delete()
        messages.success(request, "Usuario eliminado exitosamente.")
        return redirect('paneladmin')
    return redirect('paneladmin')

@login_required
def user_dashboard(request):
    if request.user.role == 'Admin':
        return redirect('paneladmin')
    return render(request, 'user_dashboard.html', {'user': request.user})

@login_required
def productos_list(request):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para acceder al panel de productos.")
        return redirect('index')
    productos = Producto.objects.all()
    return render(request, 'paneladmin.html', {'productos': productos, 'action': 'list_productos'})

@login_required
def productos_create(request):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para crear productos.")
        return redirect('paneladmin')
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Producto agregado exitosamente.")
            return redirect('paneladmin')
        else:
            messages.error(request, "Error al agregar producto. Verifica los datos.")
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = ProductoForm()
    return render(request, 'paneladmin.html', {'form': form, 'action': 'create_productos'})

@login_required
def productos_update(request, producto_id):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para editar productos.")
        return redirect('paneladmin')
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, "Producto actualizado exitosamente.")
            return redirect('paneladmin')
        else:
            messages.error(request, "Error al actualizar producto. Verifica los datos.")
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = ProductoForm(instance=producto)
    return render(request, 'paneladmin.html', {'form': form, 'action': 'update_productos', 'producto': producto})

@login_required
def productos_delete(request, producto_id):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para eliminar productos.")
        return redirect('paneladmin')
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        producto.delete()
        messages.success(request, "Producto eliminado exitosamente.")
        return redirect('paneladmin')
    return render(request, 'paneladmin.html', {'action': 'delete_productos', 'producto': producto})

def catalogo_view(request):
    productos = Producto.objects.all()
    return render(request, 'catalogo.html', {'productos': productos})