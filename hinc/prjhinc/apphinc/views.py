from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.backends import ModelBackend
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, LoginForm, ProductoForm, CategoriaForm, InventoryForm
from .models import CustomUser, Producto, Categoria, Carrito, ItemCarrito
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import logging

# Configurar logging para depuración
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def index(request):
    productos_destacados = Producto.objects.filter(estado='Habilitado', stock__gt=0)[:4]
    return render(request, 'index.html', {
        'user': request.user if request.user.is_authenticated else None,
        'productos_destacados': productos_destacados
    })

def register_view(request):
    if request.method == 'POST':
        post_data = request.POST.copy()
        post_data['role'] = 'Usuario'
        post_data['estado'] = 'Habilitado'
        form = CustomUserCreationForm(post_data)
        logger.debug(f"Datos recibidos en registro: {post_data}")
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password1')
            if password:
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
    productos = Producto.objects.all()
    categorias = Categoria.objects.all()
    return render(request, 'paneladmin.html', {
        'users': users,
        'productos': productos,
        'categorias': categorias
    })

@login_required
def usuarios_view(request):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect('paneladmin')
    users = CustomUser.objects.all()
    action = request.GET.get('action')
    user_id = request.GET.get('user_id')
    user = get_object_or_404(CustomUser, id=user_id) if action in ['edit', 'delete'] and user_id else None
    user_form = CustomUserCreationForm(instance=user) if action == 'edit' else CustomUserCreationForm()
    if request.method == 'POST':
        if action == 'add':
            form = CustomUserCreationForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Usuario agregado exitosamente.")
                return redirect('usuarios')
            else:
                messages.error(request, "Error al agregar usuario. Verifica los datos.")
                for error in form.errors.values():
                    messages.error(request, error)
        elif action == 'edit' and user_id:
            form = CustomUserCreationForm(request.POST, instance=user)
            if form.is_valid():
                form.save()
                messages.success(request, "Usuario actualizado exitosamente.")
                return redirect('usuarios')
            else:
                messages.error(request, "Error al actualizar usuario. Verifica los datos.")
                for error in form.errors.values():
                    messages.error(request, error)
        elif action == 'delete' and user_id:
            user.delete()
            messages.success(request, "Usuario eliminado exitosamente.")
            return redirect('usuarios')
    return render(request, 'PAusuarios.html', {'users': users, 'action': action, 'user': user, 'user_form': user_form})

@login_required
def add_user(request):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para agregar usuarios.")
        return redirect('usuarios')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Usuario agregado exitosamente.")
            return redirect('usuarios')
        else:
            messages.error(request, "Error al agregar usuario. Verifica los datos.")
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = CustomUserCreationForm()
    return render(request, 'PAusuarios.html', {'user_form': form, 'action': 'add'})

@login_required
def edit_user(request, user_id):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para editar usuarios.")
        return redirect('usuarios')
    user = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Usuario actualizado exitosamente.")
            return redirect('usuarios')
        else:
            messages.error(request, "Error al actualizar usuario. Verifica los datos.")
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = CustomUserCreationForm(instance=user)
    return render(request, 'PAusuarios.html', {'user_form': form, 'action': 'edit', 'user': user})

@login_required
def delete_user(request, user_id):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para eliminar usuarios.")
        return redirect('usuarios')
    user = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        user.delete()
        messages.success(request, "Usuario eliminado exitosamente.")
        return redirect('usuarios')
    return render(request, 'PAusuarios.html', {'action': 'delete', 'user': user})

@login_required
def productos_view(request):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect('paneladmin')
    productos = Producto.objects.all()
    action = request.GET.get('action')
    producto_id = request.GET.get('producto_id')
    producto = get_object_or_404(Producto, id=producto_id) if action in ['edit', 'delete'] and producto_id else None
    form = ProductoForm(instance=producto) if action == 'edit' else ProductoForm()
    if request.method == 'POST':
        if action == 'create_productos':
            form = ProductoForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, "Producto agregado exitosamente.")
                return redirect('productos')
            else:
                messages.error(request, "Error al agregar producto. Verifica los datos.")
                for error in form.errors.values():
                    messages.error(request, error)
        elif action == 'update_productos' and producto_id:
            form = ProductoForm(request.POST, request.FILES, instance=producto)
            if form.is_valid():
                form.save()
                messages.success(request, "Producto actualizado exitosamente.")
                return redirect('productos')
            else:
                messages.error(request, "Error al actualizar producto. Verifica los datos.")
                for error in form.errors.values():
                    messages.error(request, error)
        elif action == 'delete_productos' and producto_id:
            producto.delete()
            messages.success(request, "Producto eliminado exitosamente.")
            return redirect('productos')
    return render(request, 'Pproductos.html', {'productos': productos, 'action': action, 'producto': producto, 'form': form})

@login_required
def productos_create(request):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para crear productos.")
        return redirect('productos')
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Producto agregado exitosamente.")
            return redirect('productos')
        else:
            messages.error(request, "Error al agregar producto. Verifica los datos.")
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = ProductoForm()
    return render(request, 'Pproductos.html', {'form': form, 'action': 'create_productos'})

@login_required
def productos_update(request, producto_id):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para editar productos.")
        return redirect('productos')
    producto = get_object_or_404(Producto, id=producto_id)
    form = ProductoForm(request.POST or None, request.FILES or None, instance=producto, initial={'tallas': producto.tallas.split(',') if producto.tallas else []})
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, "Producto actualizado exitosamente.")
            return redirect('productos')
        else:
            messages.error(request, "Error al actualizar producto. Verifica los datos.")
            for error in form.errors.values():
                messages.error(request, error)
    return render(request, 'Pproductos.html', {'form': form, 'action': 'update_productos', 'producto': producto})

@login_required
def productos_delete(request, producto_id):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para eliminar productos.")
        return redirect('productos')
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        producto.delete()
        messages.success(request, "Producto eliminado exitosamente.")
        return redirect('productos')
    return render(request, 'Pproductos.html', {'action': 'delete_productos', 'producto': producto})

@login_required
def categorias_view(request):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect('paneladmin')
    categorias = Categoria.objects.all()
    action = request.GET.get('action')
    categoria_id = request.GET.get('categoria_id')
    categoria = get_object_or_404(Categoria, id=categoria_id) if action in ['edit', 'delete'] and categoria_id else None
    form = CategoriaForm(instance=categoria) if action == 'edit' else CategoriaForm()
    if request.method == 'POST':
        if action == 'create_categorias':
            form = CategoriaForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, "Categoría agregada exitosamente.")
                return redirect('categorias')
            else:
                messages.error(request, "Error al agregar categoría. Verifica los datos.")
                for error in form.errors.values():
                    messages.error(request, error)
        elif action == 'update_categorias' and categoria_id:
            form = CategoriaForm(request.POST, request.FILES, instance=categoria)
            if form.is_valid():
                form.save()
                messages.success(request, "Categoría actualizada exitosamente.")
                return redirect('categorias')
            else:
                messages.error(request, "Error al actualizar categoría. Verifica los datos.")
                for error in form.errors.values():
                    messages.error(request, error)
        elif action == 'delete_categorias' and categoria_id:
            categoria.delete()
            messages.success(request, "Categoría eliminada exitosamente.")
            return redirect('categorias')
    return render(request, 'PAcategorias.html', {'categorias': categorias, 'action': action, 'categoria': categoria, 'form': form})

@login_required
def categorias_create(request):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para crear categorías.")
        return redirect('categorias')
    if request.method == 'POST':
        form = CategoriaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Categoría agregada exitosamente.")
            return redirect('categorias')
        else:
            messages.error(request, "Error al agregar categoría. Verifica los datos.")
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = CategoriaForm()
    return render(request, 'PAcategorias.html', {'form': form, 'action': 'create_categorias'})

@login_required
def categorias_update(request, categoria_id):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para editar categorías.")
        return redirect('categorias')
    categoria = get_object_or_404(Categoria, id=categoria_id)
    form = CategoriaForm(request.POST or None, request.FILES or None, instance=categoria)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, "Categoría actualizada exitosamente.")
            return redirect('categorias')
        else:
            messages.error(request, "Error al actualizar categoría. Verifica los datos.")
            for error in form.errors.values():
                messages.error(request, error)
    return render(request, 'PAcategorias.html', {'form': form, 'action': 'update_categorias', 'categoria': categoria})

@login_required
def categorias_delete(request, categoria_id):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para eliminar categorías.")
        return redirect('categorias')
    categoria = get_object_or_404(Categoria, id=categoria_id)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, "Categoría eliminada exitosamente.")
        return redirect('categorias')
    return render(request, 'PAcategorias.html', {'action': 'delete_categorias', 'categoria': categoria})

@login_required
def inventario_view(request):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect('paneladmin')
    productos = Producto.objects.all()
    action = request.GET.get('action')
    producto_id = request.GET.get('producto_id')
    producto = get_object_or_404(Producto, id=producto_id) if action in ['edit', 'delete'] and producto_id else None
    form = InventoryForm(instance=producto) if action == 'edit' else InventoryForm()
    if request.method == 'POST':
        if action == 'update_productos' and producto_id:
            form = InventoryForm(request.POST, instance=producto)
            if form.is_valid():
                form.save()
                messages.success(request, "Inventario actualizado exitosamente.")
                return redirect('inventario')
            else:
                messages.error(request, "Error al actualizar inventario. Verifica los datos.")
                for error in form.errors.values():
                    messages.error(request, error)
        elif action == 'delete_productos' and producto_id:
            producto.delete()
            messages.success(request, "Producto eliminado del inventario exitosamente.")
            return redirect('inventario')
    return render(request, 'Pinventario.html', {'productos': productos, 'action': action, 'producto': producto, 'form': form})

def catalogo_view(request):
    productos = Producto.objects.all()
    categorias = Categoria.objects.all()
    return render(request, 'catalogo.html', {'productos': productos, 'categorias': categorias})

@csrf_exempt
@require_POST
def agregar_al_carrito(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Debes iniciar sesión para agregar productos al carrito.'})
    data = json.loads(request.body)
    producto_id = data.get('producto_id')
    cantidad = data.get('cantidad', 1)
    try:
        producto = Producto.objects.get(id=producto_id, estado='Habilitado', stock__gt=0)
        carrito, created = Carrito.objects.get_or_create(usuario=request.user)
        item, item_created = ItemCarrito.objects.get_or_create(carrito=carrito, producto=producto)
        if not item_created:
            item.cantidad += int(cantidad)
        else:
            item.cantidad = int(cantidad)
        if item.cantidad > producto.stock:
            item.cantidad = producto.stock
        item.save()
        return JsonResponse({'success': True, 'message': 'Producto agregado al carrito.', 'cantidad': item.cantidad})
    except Producto.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Producto no encontrado o no disponible.'})

@csrf_exempt
@require_POST
def quitar_del_carrito(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Debes iniciar sesión para modificar el carrito.'})
    data = json.loads(request.body)
    producto_id = data.get('producto_id')
    try:
        carrito = Carrito.objects.get(usuario=request.user)
        item = ItemCarrito.objects.get(carrito=carrito, producto_id=producto_id)
        item.delete()
        return JsonResponse({'success': True, 'message': 'Producto eliminado del carrito.'})
    except (Carrito.DoesNotExist, ItemCarrito.DoesNotExist):
        return JsonResponse({'success': False, 'message': 'Producto no encontrado en el carrito.'})

@csrf_exempt
def obtener_carrito(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Debes iniciar sesión para ver el carrito.', 'items': [], 'total': 0, 'cantidad_total': 0})
    try:
        carrito = Carrito.objects.get(usuario=request.user)
        items = [
            {
                'id': item.producto.id,
                'nombre': item.producto.nombre,
                'precio': float(item.producto.precio),
                'cantidad': item.cantidad,
                'imagen': item.producto.imagen.url if item.producto.imagen else None,
                'total': float(item.obtener_total())
            } for item in carrito.items.all()
        ]
        total = float(carrito.obtener_total())
        cantidad_total = carrito.obtener_cantidad_total()
        return JsonResponse({'success': True, 'items': items, 'total': total, 'cantidad_total': cantidad_total})
    except Carrito.DoesNotExist:
        return JsonResponse({'success': True, 'items': [], 'total': 0, 'cantidad_total': 0})

@login_required
def ver_carrito(request):
    if not request.user.is_authenticated:
        messages.error(request, "Debes iniciar sesión para ver el carrito.")
        return redirect('login')
    carrito = Carrito.objects.get_or_create(usuario=request.user)[0]
    items = carrito.items.all()
    total = carrito.obtener_total()
    return render(request, 'carrito.html', {'items': items, 'total': total})

def index2(request):
    productos_destacados = Producto.objects.filter(is_destacado=True, estado='Habilitado', stock__gt=0)[:4]
    categorias = Categoria.objects.all()
    ofertas = Producto.objects.filter(descuento__gt=0, estado='Habilitado', stock__gt=0)[:4]
    return render(request, 'index2.html', {
        'user': request.user if request.user.is_authenticated else None,
        'productos_destacados': productos_destacados,
        'categorias': categorias,
        'ofertas': ofertas
    })