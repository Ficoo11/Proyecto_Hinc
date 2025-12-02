from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.backends import ModelBackend
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from .forms import CustomUserCreationForm, LoginForm, ProductoForm, CategoriaForm, InventoryForm, StockTallaForm, StockTallaInlineFormSet, PedidoForm, PerfilForm
from .models import CustomUser, Producto, Categoria, Carrito, ItemCarrito, StockTalla, Pedido, DetallePedido, RegistroVenta, MovimientoInventario, TipoMovimiento  # ¡Agregar TipoMovimiento aquí!
from django.urls import reverse
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm
import logging, stripe, requests, random, string, json

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def index(request):
    productos_destacados = Producto.objects.filter(is_destacado=True, estado='Habilitado', stock__gt=0)[:4]
    categorias = Categoria.objects.all()
    ofertas = Producto.objects.filter(descuento__gt=0, estado='Habilitado', stock__gt=0)[:4]
    return render(request, 'index2.html', {
        'user': request.user if request.user.is_authenticated else None,
        'productos_destacados': productos_destacados,
        'categorias': categorias,
        'ofertas': ofertas
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
def perfil_view(request):
    if request.method == 'POST':
        form = PerfilForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil actualizado exitosamente.")
            return redirect('perfil')
        else:
            messages.error(request, "Error al actualizar el perfil. Verifica los datos.")
    else:
        form = PerfilForm(instance=request.user)
    
    return render(request, 'perfil.html', {'form': form})

@login_required
def paneladmin_view(request):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para acceder al panel de administración.")
        return redirect('index')
    
    users = CustomUser.objects.all()
    productos = Producto.objects.all()
    categorias = Categoria.objects.all()
    pedidos = Pedido.objects.all()
    
    pedidos_pendientes = pedidos.filter(estado='pendiente').count()
    pedidos_procesando = pedidos.filter(estado='procesando').count()
    pedidos_enviados = pedidos.filter(estado='enviado').count()
    pedidos_recientes = pedidos.filter(creado_en__date=timezone.now().date()).count()
    
    # Estadísticas de Ventas para el Dashboard
    hoy = timezone.now().date()
    ventas_hoy = RegistroVenta.objects.filter(fecha_venta__date=hoy)
    total_ventas_hoy = ventas_hoy.aggregate(total=Sum('total'))['total'] or 0
    unidades_vendidas_hoy = ventas_hoy.aggregate(total=Sum('cantidad'))['total'] or 0
    productos_vendidos_hoy = ventas_hoy.values('producto').distinct().count()
    
    # Ventas recientes (últimas 10)
    ventas_recientes = RegistroVenta.objects.select_related('producto', 'pedido').order_by('-fecha_venta')[:10]
    
    # Productos más vendidos este mes - CORREGIDO: usar Q importado correctamente
    inicio_mes = hoy.replace(day=1)
    productos_mas_vendidos_mes = Producto.objects.annotate(
        total_vendido=Sum('registroventa__cantidad', filter=Q(registroventa__fecha_venta__gte=inicio_mes)),
        ingresos_totales=Sum('registroventa__total', filter=Q(registroventa__fecha_venta__gte=inicio_mes))
    ).filter(total_vendido__gt=0).order_by('-total_vendido')[:5]
    
    productos_stock_bajo = []
    for producto in productos:
        alertas_tallas = []
        for stock_talla in producto.stocktalla_set.all():
            estado, estado_texto, color = stock_talla.obtener_estado_stock()
            if estado in ['critico', 'bajo', 'medio']:
                alertas_tallas.append({
                    'talla': stock_talla.talla,
                    'stock_actual': stock_talla.stock,
                    'stock_inicial': stock_talla.stock_inicial,
                    'porcentaje': stock_talla.obtener_porcentaje_stock(),
                    'estado': estado,
                    'estado_texto': estado_texto,
                    'color': color
                })
        
        if alertas_tallas:
            productos_stock_bajo.append({
                'producto': producto,
                'alertas_tallas': alertas_tallas
            })
    
    contadores_estados = {
        'normal': 0,
        'medio': 0,
        'bajo': 0,
        'critico': 0
    }
    
    for producto in productos:
        for stock_talla in producto.stocktalla_set.all():
            porcentaje = stock_talla.obtener_porcentaje_stock()
            if porcentaje > 50:
                contadores_estados['normal'] += 1
            elif porcentaje <= 50 and porcentaje > 25:
                contadores_estados['medio'] += 1
            elif porcentaje <= 25 and porcentaje > 10:
                contadores_estados['bajo'] += 1
            elif porcentaje <= 10 and porcentaje > 0:
                contadores_estados['critico'] += 1
    
    pedidos_recientes_lista = Pedido.objects.filter(
        creado_en__gte=timezone.now() - timedelta(days=7)
    ).order_by('-creado_en')[:5]
    
    return render(request, 'paneladmin.html', {
        'users': users,
        'productos': productos,
        'categorias': categorias,
        'pedidos': pedidos,
        'pedidos_pendientes': pedidos_pendientes,
        'pedidos_procesando': pedidos_procesando,
        'pedidos_enviados': pedidos_enviados,
        'pedidos_recientes': pedidos_recientes,
        'productos_stock_bajo': productos_stock_bajo,
        'contadores_estados': contadores_estados,
        'pedidos_recientes_lista': pedidos_recientes_lista,
        # Nuevos datos de ventas
        'total_ventas_hoy': total_ventas_hoy,
        'unidades_vendidas_hoy': unidades_vendidas_hoy,
        'productos_vendidos_hoy': productos_vendidos_hoy,
        'ventas_recientes': ventas_recientes,
        'productos_mas_vendidos_mes': productos_mas_vendidos_mes,
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
    producto = get_object_or_404(Producto, id=producto_id) if action in ['update', 'delete'] and producto_id else None
    
    if request.method == 'POST':
        action = request.POST.get('action')
        producto_id = request.POST.get('producto_id')
        
        if action == 'create':
            form = ProductoForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    # Guardar el producto primero
                    producto_creado = form.save(commit=False)
                    producto_creado.save()
                    
                    # Crear stocks por talla automáticamente
                    tallas = request.POST.getlist('tallas')
                    total_stock = 0
                    
                    for talla in tallas:
                        if talla.strip():  # Solo procesar tallas no vacías
                            stock_inicial = request.POST.get(f'stock_inicial_{talla}', 0)
                            stock_actual = request.POST.get(f'stock_{talla}', 0)
                            
                            # Si se ingresó stock inicial pero no stock actual, autocompletar
                            if stock_inicial and not stock_actual:
                                stock_actual = stock_inicial
                            
                            stock_inicial_val = int(stock_inicial) if stock_inicial else 0
                            stock_actual_val = int(stock_actual) if stock_actual else 0
                            
                            StockTalla.objects.create(
                                producto=producto_creado,
                                talla=talla.strip(),
                                stock_inicial=stock_inicial_val,
                                stock=stock_actual_val
                            )
                            
                            total_stock += stock_actual_val
                    
                    # Actualizar stock general del producto inmediatamente
                    producto_creado.stock = total_stock
                    
                    # Forzar la actualización del estado basado en el stock
                    if producto_creado.stock > 0:
                        producto_creado.estado = 'Habilitado'
                    else:
                        producto_creado.estado = 'Agotado'
                    
                    producto_creado.save()
                    
                    messages.success(request, "Producto agregado exitosamente.")
                    return redirect('productos')
                    
                except Exception as e:
                    messages.error(request, f"Error al crear el producto: {str(e)}")
            else:
                messages.error(request, "Error al agregar producto. Verifica los datos.")
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{form.fields[field].label if field in form.fields else field}: {error}")
                        
        elif action == 'update' and producto_id:
            producto = get_object_or_404(Producto, id=producto_id)
            form = ProductoForm(request.POST, request.FILES, instance=producto)
            if form.is_valid():
                try:
                    producto_actualizado = form.save()
                    total_stock = 0
                    
                    # Actualizar stocks por talla
                    stock_tallas = StockTalla.objects.filter(producto=producto)
                    for stock_talla in stock_tallas:
                        stock_field = f'stock_{stock_talla.talla}'
                        stock_inicial_field = f'stock_inicial_{stock_talla.talla}'
                        
                        if stock_field in request.POST:
                            try:
                                nuevo_stock = int(request.POST[stock_field])
                                if nuevo_stock >= 0:
                                    stock_talla.stock = nuevo_stock
                                    total_stock += nuevo_stock
                                    
                                    if stock_inicial_field in request.POST:
                                        nuevo_stock_inicial = int(request.POST[stock_inicial_field])
                                        if nuevo_stock_inicial >= 0:
                                            stock_talla.stock_inicial = nuevo_stock_inicial
                                    
                                    stock_talla.save()
                            except ValueError:
                                pass
                    
                    # Actualizar stock general del producto inmediatamente
                    producto_actualizado.stock = total_stock
                    
                    # Actualizar estado basado en el stock
                    if producto_actualizado.stock > 0 and producto_actualizado.estado == 'Agotado':
                        producto_actualizado.estado = 'Habilitado'
                    elif producto_actualizado.stock == 0 and producto_actualizado.estado != 'Agotado':
                        producto_actualizado.estado = 'Agotado'
                    
                    producto_actualizado.save()
                    
                    messages.success(request, "Producto actualizado exitosamente.")
                    return redirect('productos')
                    
                except Exception as e:
                    messages.error(request, f"Error al actualizar el producto: {str(e)}")
            else:
                messages.error(request, "Error al actualizar producto. Verifica los datos.")
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{form.fields[field].label if field in form.fields else field}: {error}")
                        
        elif action == 'delete' and producto_id:
            try:
                producto = get_object_or_404(Producto, id=producto_id)
                producto_nombre = producto.nombre
                producto.delete()
                messages.success(request, f"Producto '{producto_nombre}' eliminado exitosamente.")
                return redirect('productos')
            except Exception as e:
                messages.error(request, f"Error al eliminar el producto: {str(e)}")
    
    # GET request - mostrar formularios o lista
    if action == 'create':
        form = ProductoForm()
    elif action == 'update' and producto:
        form = ProductoForm(instance=producto)
    else:
        form = ProductoForm()
    
    return render(request, 'Pproductos.html', {
        'productos': productos, 
        'action': action, 
        'producto': producto, 
        'form': form
    })

@login_required
def productos_create(request):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para crear productos.")
        return redirect('productos')
    
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            # Guardar el producto primero
            producto = form.save(commit=False)
            producto.save()
            
            # Crear stocks por talla automáticamente
            tallas = request.POST.getlist('tallas')
            for talla in tallas:
                if talla.strip():  # Solo procesar tallas no vacías
                    stock_inicial = request.POST.get(f'stock_inicial_{talla}', 0)
                    stock_actual = request.POST.get(f'stock_{talla}', 0)
                    
                    # Si se ingresó stock inicial pero no stock actual, autocompletar
                    if stock_inicial and not stock_actual:
                        stock_actual = stock_inicial
                    
                    StockTalla.objects.create(
                        producto=producto,
                        talla=talla.strip(),
                        stock_inicial=int(stock_inicial) if stock_inicial else 0,
                        stock=int(stock_actual) if stock_actual else 0
                    )
            
            # Actualizar stock general del producto
            producto.actualizar_stock_general()
            
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
    
    stock_tallas = StockTalla.objects.filter(producto=producto)
    
    if request.method == 'POST':
        if form.is_valid():
            producto_actualizado = form.save()
            
            for stock_talla in stock_tallas:
                stock_field = f'stock_{stock_talla.talla}'
                stock_inicial_field = f'stock_inicial_{stock_talla.talla}'
                
                if stock_field in request.POST:
                    try:
                        nuevo_stock = int(request.POST[stock_field])
                        if nuevo_stock >= 0:
                            stock_talla.stock = nuevo_stock
                            if stock_inicial_field in request.POST:
                                nuevo_stock_inicial = int(request.POST[stock_inicial_field])
                                if nuevo_stock_inicial >= 0:
                                    stock_talla.stock_inicial = nuevo_stock_inicial
                            stock_talla.save()
                    except ValueError:
                        pass
            
            producto_actualizado.actualizar_stock_general()
            
            messages.success(request, "Producto actualizado exitosamente.")
            return redirect('productos')
        else:
            messages.error(request, "Error al actualizar producto. Verifica los datos.")
            for error in form.errors.values():
                messages.error(request, error)
    
    stock_forms = []
    for stock_talla in stock_tallas:
        stock_forms.append({
            'talla': stock_talla.talla,
            'form': StockTallaForm(instance=stock_talla),
            'instance': stock_talla,
            'porcentaje': stock_talla.obtener_porcentaje_stock(),
            'estado': stock_talla.obtener_estado_stock()
        })
    
    return render(request, 'Pproductos.html', {
        'form': form, 
        'action': 'update_productos', 
        'producto': producto,
        'stock_forms': stock_forms
    })

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

def categorias_create(request):
    if request.method != "POST":
        return redirect("categorias")

    data = {
        "nombre": request.POST.get("nombre"),
        "descripcion": request.POST.get("descripcion"),
        "imagen": None
    }

    try:
        response = requests.post(settings.JAVA_CATEGORIAS_CREAR, json=data)

        if response.status_code not in [200, 201]:
            messages.error(request, "Error creando la categoría en Java.")
            return redirect("categorias")

        messages.success(request, "Categoría creada correctamente.")
        return redirect("categorias")

    except requests.exceptions.ConnectionError:
        messages.error(request, "No se pudo conectar con el microservicio Java.")
        return redirect("categorias")
    
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
    producto = get_object_or_404(Producto, id=producto_id) if action in ['update_productos', 'delete_productos'] and producto_id else None
    
    print(f"=== INVENTARIO_VIEW ===")
    print(f"Action: {action}, Producto ID: {producto_id}")
    print(f"Method: {request.method}")
    
    # Procesar actualización manual de stocks (formulario de agregar unidades) - MODIFICADO
    if request.method == 'POST' and any(key.startswith('nuevas_unidades[') for key in request.POST.keys()):
        print("Procesando formulario de ACTUALIZACIÓN DE STOCK")
        try:
            productos_actualizados = set()
            tallas_actualizadas = 0
            total_unidades_agregadas = 0
            
            # Recorrer todos los parámetros del POST para nuevas unidades
            for key, value in request.POST.items():
                if key.startswith('nuevas_unidades['):
                    try:
                        # Extraer el ID del stock_talla del formato: nuevas_unidades[1]
                        stock_talla_id = key.split('[')[1].split(']')[0]
                        nuevas_unidades = int(value) if value else 0
                        
                        print(f"Procesando: {key} = {nuevas_unidades} unidades")
                        
                        if nuevas_unidades > 0:
                            stock_talla = get_object_or_404(StockTalla, id=stock_talla_id)
                            
                            # MODIFICADO: Actualizar tanto stock_inicial como stock
                            stock_anterior_inicial = stock_talla.stock_inicial
                            stock_anterior_actual = stock_talla.stock
                            
                            # SUMAR las nuevas unidades tanto al stock inicial como al actual
                            stock_talla.stock_inicial += nuevas_unidades
                            stock_talla.stock += nuevas_unidades
                            stock_talla.save()
                            
                            # Registrar movimiento de inventario
                            MovimientoInventario.objects.create(
                                producto=stock_talla.producto,
                                talla=stock_talla.talla,
                                tipo_movimiento=TipoMovimiento.COMPRA,
                                cantidad=nuevas_unidades,
                                stock_anterior=stock_anterior_actual,
                                stock_posterior=stock_talla.stock,
                                usuario=request.user,
                                observaciones=f"Actualización manual de stock - Agregadas {nuevas_unidades} unidades (Stock inicial: {stock_anterior_inicial} → {stock_talla.stock_inicial})"
                            )
                            
                            tallas_actualizadas += 1
                            total_unidades_agregadas += nuevas_unidades
                            productos_actualizados.add(stock_talla.producto.id)
                            
                    except (ValueError, IndexError, StockTalla.DoesNotExist) as e:
                        print(f"Error procesando {key}: {e}")
                        continue
            
            # Actualizar stock general de todos los productos afectados
            for producto_id in productos_actualizados:
                try:
                    producto = Producto.objects.get(id=producto_id)
                    producto.actualizar_stock_general()
                except Producto.DoesNotExist:
                    continue
            
            if tallas_actualizadas > 0:
                messages.success(request, f"Stock actualizado correctamente. Se agregaron {total_unidades_agregadas} unidades en {tallas_actualizadas} tallas de {len(productos_actualizados)} productos.")
            else:
                messages.warning(request, "No se realizaron actualizaciones. Verifica que las cantidades sean mayores a 0.")
                
            return redirect('inventario')
            
        except Exception as e:
            messages.error(request, f"Error al actualizar el stock: {str(e)}")
            return redirect('inventario')
    
    # Procesar ACTUALIZACIÓN DE PRODUCTO (formulario de edición)
    elif request.method == 'POST' and action == 'update_productos' and producto_id:
        print("Procesando formulario de ACTUALIZACIÓN DE PRODUCTO")
        producto = get_object_or_404(Producto, id=producto_id)
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        
        if form.is_valid():
            try:
                print("Formulario válido, guardando producto...")
                producto_actualizado = form.save(commit=False)
                total_stock = 0
                
                # Actualizar stocks por talla
                stock_tallas = StockTalla.objects.filter(producto=producto)
                for stock_talla in stock_tallas:
                    stock_field = f'stock_{stock_talla.talla}'
                    stock_inicial_field = f'stock_inicial_{stock_talla.talla}'
                    
                    print(f"Procesando talla {stock_talla.talla}: {stock_field}, {stock_inicial_field}")
                    
                    if stock_field in request.POST:
                        try:
                            nuevo_stock = int(request.POST[stock_field])
                            print(f"  Nuevo stock: {nuevo_stock}")
                            if nuevo_stock >= 0:
                                stock_talla.stock = nuevo_stock
                                total_stock += nuevo_stock
                                
                                if stock_inicial_field in request.POST:
                                    nuevo_stock_inicial = int(request.POST[stock_inicial_field])
                                    print(f"  Nuevo stock inicial: {nuevo_stock_inicial}")
                                    if nuevo_stock_inicial >= 0:
                                        stock_talla.stock_inicial = nuevo_stock_inicial
                                
                                stock_talla.save()
                                print(f"  Stock guardado: {stock_talla.stock} (inicial: {stock_talla.stock_inicial})")
                        except ValueError as e:
                            print(f"  Error en valores: {e}")
                            pass
                
                # Actualizar stock general del producto inmediatamente
                producto_actualizado.stock = total_stock
                print(f"Stock total actualizado: {total_stock}")
                
                # Actualizar estado basado en el stock
                if producto_actualizado.stock > 0 and producto_actualizado.estado == 'Agotado':
                    producto_actualizado.estado = 'Habilitado'
                    print("Estado cambiado a Habilitado")
                elif producto_actualizado.stock == 0 and producto_actualizado.estado != 'Agotado':
                    producto_actualizado.estado = 'Agotado'
                    print("Estado cambiado a Agotado")
                
                producto_actualizado.save()
                print("Producto guardado exitosamente")
                
                messages.success(request, "Producto actualizado exitosamente.")
                return redirect('inventario')
                
            except Exception as e:
                print(f"Error al actualizar el producto: {str(e)}")
                messages.error(request, f"Error al actualizar el producto: {str(e)}")
        else:
            print("Formulario inválido")
            messages.error(request, "Error al actualizar producto. Verifica los datos.")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label if field in form.fields else field}: {error}")
    
    # Procesar ELIMINACIÓN DE PRODUCTO
    elif request.method == 'POST' and action == 'delete_productos' and producto_id:
        print("Procesando ELIMINACIÓN DE PRODUCTO")
        try:
            producto = get_object_or_404(Producto, id=producto_id)
            producto_nombre = producto.nombre
            producto.delete()
            messages.success(request, f"Producto '{producto_nombre}' eliminado exitosamente.")
            return redirect('inventario')
        except Exception as e:
            messages.error(request, f"Error al eliminar el producto: {str(e)}")
    
    # GET request - mostrar formularios o lista
    print("Renderizando template...")
    
    # PREPARAR LOS DATOS PARA EL TEMPLATE
    if producto and action == 'update_productos':
        stock_tallas = StockTalla.objects.filter(producto=producto)
        stock_forms = [StockTallaForm(instance=stock) for stock in stock_tallas]
        form = ProductoForm(instance=producto)
        print(f"Modo edición para producto: {producto.nombre}")
        
        return render(request, 'Pinventario.html', {
            'productos': productos, 
            'action': action, 
            'producto': producto, 
            'form': form,
            'stock_forms': stock_forms
        })
        
    elif producto and action == 'delete_productos':
        return render(request, 'Pinventario.html', {
            'productos': productos, 
            'action': action, 
            'producto': producto
        })
        
    else:
        # Vista normal del inventario
        stock_forms = []
        form = InventoryForm()
        
        return render(request, 'Pinventario.html', {
            'productos': productos, 
            'action': action, 
            'producto': producto, 
            'form': form,
            'stock_forms': stock_forms
        })
        
def catalogo_view(request):
    productos = Producto.objects.all()
    categorias = Categoria.objects.all()
    return render(request, 'catalogo.html', {'productos': productos, 'categorias': categorias})

def producto_detalle_view(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    
    stock_info = []
    for stock_talla in producto.stocktalla_set.all():
        estado, estado_texto, color = stock_talla.obtener_estado_stock()
        stock_info.append({
            'talla': stock_talla.talla,
            'stock_actual': stock_talla.stock,
            'stock_inicial': stock_talla.stock_inicial,
            'porcentaje': stock_talla.obtener_porcentaje_stock(),
            'estado': estado,
            'estado_texto': estado_texto,
            'color': color
        })
    
    return render(request, 'producto.html', {
        'producto': producto,
        'user': request.user if request.user.is_authenticated else None,
        'stock_info': stock_info
    })

@login_required
@require_POST
@csrf_exempt
def agregar_al_carrito(request):
    try:
        data = json.loads(request.body)
        producto_id = data.get('producto_id')
        cantidad = int(data.get('cantidad', 1))
        talla = data.get('talla')
       
        producto = get_object_or_404(Producto, id=producto_id)
        
        stock_talla = get_object_or_404(StockTalla, producto=producto, talla=talla)
        stock_disponible = stock_talla.stock
        
        if stock_disponible < cantidad:
            return JsonResponse({
                'success': False, 
                'error': f'Stock insuficiente para la talla {talla}. Solo quedan {stock_disponible} unidades.'
            })
        
        carrito, created = Carrito.objects.get_or_create(usuario=request.user)
       
        item, created = ItemCarrito.objects.get_or_create(
            carrito=carrito,
            producto=producto,
            talla=talla,
            defaults={'cantidad': cantidad}
        )
       
        if not created:
            nueva_cantidad = item.cantidad + cantidad
            if nueva_cantidad > stock_disponible:
                return JsonResponse({
                    'success': False, 
                    'error': f'No hay suficiente stock. Máximo disponible: {stock_disponible} unidades.'
                })
            item.cantidad = nueva_cantidad
            item.save()
       
        return JsonResponse({
            'success': True,
            'carrito': obtener_datos_carrito(carrito)
        })
       
    except Exception as e:
        logger.error(f"Error al agregar al carrito: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
@csrf_exempt
def quitar_del_carrito(request):
    try:
        data = json.loads(request.body)
        producto_id = data.get('producto_id')
        talla = data.get('talla')
        item_id = data.get('item_id')
       
        print(f"DEBUG: Datos recibidos - Item ID: {item_id}, Producto ID: {producto_id}, Talla: {talla}")
        
        carrito = get_object_or_404(Carrito, usuario=request.user)
        
        item = None
        
        # PRIMERO: Buscar por item_id si está disponible (es la forma más precisa)
        if item_id and item_id != 'None':
            try:
                item = ItemCarrito.objects.get(id=int(item_id), carrito=carrito)
                print(f"DEBUG: Item encontrado por ID: {item_id}")
            except (ItemCarrito.DoesNotExist, ValueError) as e:
                print(f"DEBUG: No se encontró item con ID {item_id}: {e}")
                item = None
        
        # SEGUNDO: Si no tenemos item_id, buscar por producto_id y talla
        if not item and producto_id and producto_id != 'None' and talla and talla != 'None':
            try:
                # Si hay múltiples items, tomar el primero
                items = ItemCarrito.objects.filter(
                    carrito=carrito, 
                    producto_id=int(producto_id), 
                    talla=talla
                )
                if items.exists():
                    item = items.first()  # Tomar el primer item encontrado
                    print(f"DEBUG: Se encontraron {items.count()} items. Eliminando el primero: {item.id}")
            except ValueError as e:
                print(f"DEBUG: Error en los datos: {e}")
                item = None
        
        # TERCERO: Si aún no tenemos item, buscar solo por producto_id
        if not item and producto_id and producto_id != 'None':
            try:
                items = ItemCarrito.objects.filter(
                    carrito=carrito, 
                    producto_id=int(producto_id)
                )
                if items.exists():
                    item = items.first()  # Tomar el primer item encontrado
                    print(f"DEBUG: Se encontraron {items.count()} items por producto. Eliminando el primero: {item.id}")
            except ValueError as e:
                print(f"DEBUG: Error en los datos: {e}")
                item = None
        
        if not item:
            print(f"DEBUG: No se pudo encontrar ningún item con los datos proporcionados")
            return JsonResponse({
                'success': False, 
                'error': 'No se encontró el producto en el carrito'
            })
        
        print(f"DEBUG: Eliminando item: {item.id} - {item.producto.nombre} - {item.talla} - Cantidad: {item.cantidad}")
        item.delete()
        
        # Obtener datos actualizados del carrito
        carrito_data = obtener_datos_carrito(carrito)
       
        return JsonResponse({
            'success': True,
            'carrito': carrito_data
        })
       
    except Exception as e:
        logger.error(f"Error al quitar del carrito: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})
    
@login_required
def obtener_carrito(request):
    try:
        carrito, created = Carrito.objects.get_or_create(usuario=request.user)
        return JsonResponse({
            'success': True,
            'carrito': obtener_datos_carrito(carrito)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def obtener_datos_carrito(carrito):
    items = []
    for item in carrito.items.all():
        # Calcular precio con descuento
        if item.producto.descuento > 0:
            precio_final = float(item.producto.precio_con_descuento())
        else:
            precio_final = float(item.producto.precio)
            
        items.append({
            'id': item.id,
            'id_producto': item.producto.id,
            'nombre': item.producto.nombre,
            'precio': precio_final,  # Usar precio con descuento
            'precio_original': float(item.producto.precio),  # Precio original para comparación
            'descuento': item.producto.descuento,  # Porcentaje de descuento
            'cantidad': item.cantidad,
            'talla': item.talla,
            'imagen': item.producto.imagen.url if item.producto.imagen else ''
        })
   
    return {
        'items': items,
        'total': float(carrito.obtener_total()),
        'cantidad_total': carrito.obtener_cantidad_total()
    }

@login_required
def ver_carrito(request):
    carrito, created = Carrito.objects.get_or_create(usuario=request.user)
    return render(request, 'carrito.html', {'carrito': carrito})

@login_required
def checkout_view(request):
    carrito, created = Carrito.objects.get_or_create(usuario=request.user)
    
    if not carrito.items.exists():
        messages.error(request, "Tu carrito está vacío.")
        return redirect('ver_carrito')
    
    for item in carrito.items.all():
        try:
            stock_talla = StockTalla.objects.get(producto=item.producto, talla=item.talla)
            if stock_talla.stock < item.cantidad:
                messages.error(request, f"No hay suficiente stock para {item.producto.nombre} en talla {item.talla}. Solo quedan {stock_talla.stock} unidades.")
                return redirect('ver_carrito')
        except StockTalla.DoesNotExist:
            messages.error(request, f"El producto {item.producto.nombre} en talla {item.talla} no está disponible.")
            return redirect('ver_carrito')
    
    if request.method == 'POST':
        form = PedidoForm(request.POST)
        if form.is_valid():
            pedido = form.save(commit=False)
            pedido.usuario = request.user
            pedido.total = carrito.obtener_total()
            pedido.numero_pedido = pedido.generar_numero_pedido()
            # IMPORTANTE: Cambiar estado a confirmado inmediatamente
            pedido.estado = 'confirmado'
            pedido.save()
            
            for item in carrito.items.all():
                DetallePedido.objects.create(
                    pedido=pedido,
                    producto=item.producto,
                    talla=item.talla,
                    cantidad=item.cantidad,
                    precio=item.producto.precio
                )
                
                stock_talla = StockTalla.objects.get(producto=item.producto, talla=item.talla)
                
                # Registrar movimiento de inventario
                MovimientoInventario.objects.create(
                    producto=item.producto,
                    talla=item.talla,
                    tipo_movimiento=TipoMovimiento.VENTA,
                    cantidad=-item.cantidad,
                    stock_anterior=stock_talla.stock,
                    stock_posterior=stock_talla.stock - item.cantidad,
                    precio_unitario=item.producto.precio,
                    total=item.obtener_total(),
                    usuario=request.user,
                    pedido=pedido,
                    observaciones=f"Venta - Pedido {pedido.numero_pedido}"
                )
                
                # Registrar venta - ¡ESTO ES CLAVE!
                RegistroVenta.objects.create(
                    pedido=pedido,
                    producto=item.producto,
                    talla=item.talla,
                    cantidad=item.cantidad,
                    precio_unitario=item.producto.precio,
                    total=item.obtener_total(),
                    usuario=request.user,
                    fecha_venta=timezone.now()
                )
                
                # Actualizar stock
                stock_talla.stock -= item.cantidad
                stock_talla.save()
                
                item.producto.actualizar_stock_general()
            
            carrito.items.all().delete()
            
            # Crear registros de venta automáticamente
            crear_registro_venta_desde_pedido(pedido)
            
            messages.success(request, f"¡Pedido realizado exitosamente! Número de pedido: {pedido.numero_pedido}")
            return redirect('confirmacion_pedido', pedido_id=pedido.id)
    else:
        initial_data = {}
        if request.user.first_name and request.user.last_name:
            initial_data['nombre_completo'] = f"{request.user.first_name} {request.user.last_name}"
        if request.user.email:
            initial_data['email'] = request.user.email
        
        form = PedidoForm(initial=initial_data)
    
    return render(request, 'checkout.html', {
        'carrito': carrito,
        'form': form
    })

@login_required
def confirmacion_pedido_view(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    return render(request, 'confirmacion_pedido.html', {'pedido': pedido})

@login_required
@require_POST
@csrf_exempt
def procesar_pago(request):
    try:
        data = json.loads(request.body)
        carrito, created = Carrito.objects.get_or_create(usuario=request.user)
        
        if not carrito.items.exists():
            return JsonResponse({'success': False, 'error': 'El carrito está vacío'})
        
        for item in carrito.items.all():
            try:
                stock_talla = StockTalla.objects.get(producto=item.producto, talla=item.talla)
                if stock_talla.stock < item.cantidad:
                    return JsonResponse({
                        'success': False, 
                        'error': f"No hay suficiente stock para {item.producto.nombre} en talla {item.talla}"
                    })
            except StockTalla.DoesNotExist:
                return JsonResponse({
                    'success': False, 
                    'error': f"El producto {item.producto.nombre} en talla {item.talla} no está disponible"
                })
        
        import time
        time.sleep(2)
        
        pedido = Pedido.objects.create(
            usuario=request.user,
            total=carrito.obtener_total(),
            nombre_completo=data.get('nombre_completo'),
            email=data.get('email'),
            direccion_envio=data.get('direccion'),
            ciudad=data.get('ciudad'),
            telefono=data.get('telefono'),
            metodo_pago=data.get('metodo_pago'),
            estado='pendiente'
        )
        
        for item in carrito.items.all():
            DetallePedido.objects.create(
                pedido=pedido,
                producto=item.producto,
                talla=item.talla,
                cantidad=item.cantidad,
                precio=item.producto.precio
            )
            
            stock_talla = StockTalla.objects.get(producto=item.producto, talla=item.talla)
            
            # Registrar movimiento de inventario
            MovimientoInventario.objects.create(
                producto=item.producto,
                talla=item.talla,
                tipo_movimiento=TipoMovimiento.VENTA,
                cantidad=-item.cantidad,
                stock_anterior=stock_talla.stock,
                stock_posterior=stock_talla.stock - item.cantidad,
                precio_unitario=item.producto.precio,
                total=item.obtener_total(),
                usuario=request.user,
                pedido=pedido,
                observaciones=f"Venta - Pedido {pedido.numero_pedido}"
            )
            
            # Actualizar stock
            stock_talla.stock -= item.cantidad
            stock_talla.save()
            
            # Registrar venta
            RegistroVenta.objects.create(
                pedido=pedido,
                producto=item.producto,
                talla=item.talla,
                cantidad=item.cantidad,
                precio_unitario=item.producto.precio,
                total=item.obtener_total(),
                usuario=request.user,
                fecha_venta=timezone.now()
            )
            
            item.producto.actualizar_stock_general()
        
        carrito.items.all().delete()
        
        return JsonResponse({
            'success': True,
            'pedido_id': pedido.id,
            'numero_pedido': pedido.numero_pedido,
            'mensaje': '¡Pago procesado exitosamente!'
        })
        
    except Exception as e:
        logger.error(f"Error al procesar pago: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

    
@login_required
def pedidos_view(request):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect('paneladmin')
    
    # Filtrar solo pedidos con ID válido y ordenar
    pedidos = Pedido.objects.all().order_by('-creado_en')
    
    # Debug: Verificar los pedidos
    print("=== DEBUG PEDIDOS ===")
    for pedido in pedidos:
        print(f"ID: {pedido.id}, Número: {pedido.numero_pedido}")
    print("=====================")
    
    estados = Pedido.ESTADOS_PEDIDO
    
    estado_filtro = request.GET.get('estado')
    if estado_filtro:
        pedidos = pedidos.filter(estado=estado_filtro)
    
    # Cambia 'pedidos.html' por 'lista_pedidos.html'
    return render(request, 'lista_pedidos.html', {
        'pedidos': pedidos,
        'estados': estados,
        'estado_filtro': estado_filtro
    })

@login_required
def pedido_detalle_view(request, pedido_id):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect('paneladmin')
    
    pedido = get_object_or_404(Pedido, id=pedido_id)
    return render(request, 'pedido_detalle.html', {'pedido': pedido})

@login_required
@require_POST
def actualizar_estado_pedido(request, pedido_id):
    if request.user.role != 'Admin':
        return JsonResponse({'success': False, 'error': 'No tienes permiso para realizar esta acción.'})
    
    pedido = get_object_or_404(Pedido, id=pedido_id)
    nuevo_estado = request.POST.get('estado')
    
    if nuevo_estado in dict(Pedido.ESTADOS_PEDIDO):
        estado_anterior = pedido.estado
        pedido.estado = nuevo_estado
        pedido.save()
        
        messages.success(request, f"Estado del pedido {pedido.numero_pedido} actualizado a {pedido.get_estado_display()}.")
        return JsonResponse({'success': True, 'nuevo_estado': nuevo_estado, 'estado_display': pedido.get_estado_display()})
    
    return JsonResponse({'success': False, 'error': 'Estado inválido.'})

@login_required
def mis_pedidos_view(request):
    pedidos = Pedido.objects.filter(usuario=request.user).order_by('-creado_en')
    return render(request, 'mis_pedidos.html', {'pedidos': pedidos})

@login_required
def pedido_detalle_view(request, pedido_id):
    """Vista para ver el detalle de un pedido específico"""
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect('paneladmin')
    
    pedido = get_object_or_404(Pedido, id=pedido_id)
    return render(request, 'pedido_detalle.html', {'pedido': pedido})

@login_required
def mis_pedidos_detalle_view(request, pedido_id):
    """Vista para que los usuarios vean el detalle de sus propios pedidos"""
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    return render(request, 'pedido_detalle.html', {'pedido': pedido})

def producto_detalle(request, producto_id):
    """
    Vista para mostrar los detalles de un producto específico
    """
    producto = get_object_or_404(Producto, id=producto_id, disponible=True)
    
    # Productos relacionados (misma categoría)
    productos_relacionados = Producto.objects.filter(
        categoria=producto.categoria, 
        disponible=True
    ).exclude(id=producto.id)[:4]  # Limita a 4 productos
    
    context = {
        'producto': producto,
        'productos_relacionados': productos_relacionados,
    }
    
    return render(request, 'producto_detalle.html', context)

def cambiar_estado_pedido(request, pedido_id):
    """
    Vista para cambiar el estado de un pedido
    """
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('nuevo_estado')
        if nuevo_estado:
            pedido.estado = nuevo_estado
            pedido.save()
            messages.success(request, f'Estado del pedido #{pedido.id} actualizado a: {nuevo_estado}')
        return redirect('detalle_pedido', pedido_id=pedido.id)
    
    # Si es GET, mostrar formulario de cambio de estado
    return render(request, 'cambiar_estado_pedido.html', {'pedido': pedido})

def detalle_pedido(request, pedido_id):
    """
    Vista para mostrar los detalles de un pedido específico
    """
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    context = {
        'pedido': pedido,
    }
    
    return render(request, 'pedidos/detalle_pedido.html', context)

@login_required
@require_POST
def actualizar_stock_general(request):
    """Vista para actualizar el stock general de todos los productos"""
    if request.user.role != 'Admin':
        return JsonResponse({'success': False, 'error': 'No tienes permiso para realizar esta acción.'})
    
    try:
        productos_actualizados = 0
        productos = Producto.objects.all()
        
        for producto in productos:
            # Recalcular el stock general basado en las tallas
            total_stock = sum(stock.stock for stock in producto.stocktalla_set.all())
            
            # Actualizar el stock del producto
            if producto.stock != total_stock:
                producto.stock = total_stock
                
                # Actualizar estado si es necesario
                if total_stock == 0 and producto.estado != 'Agotado':
                    producto.estado = 'Agotado'
                elif total_stock > 0 and producto.estado == 'Agotado':
                    producto.estado = 'Habilitado'
                
                producto.save()
                productos_actualizados += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Stock actualizado correctamente para {productos_actualizados} productos.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al actualizar el stock: {str(e)}'
        })

@login_required
@require_POST
def actualizar_stock_manual(request):
    """Vista para actualizar stock manualmente desde el formulario"""
    if request.user.role != 'Admin':
        return JsonResponse({'success': False, 'error': 'No tienes permiso para realizar esta acción.'})
    
    try:
        data = json.loads(request.body)
        producto_id = data.get('producto_id')
        talla = data.get('talla')
        nuevo_stock = data.get('nuevo_stock')
        nuevo_stock_inicial = data.get('nuevo_stock_inicial')
        
        producto = get_object_or_404(Producto, id=producto_id)
        stock_talla = get_object_or_404(StockTalla, producto=producto, talla=talla)
        
        # Actualizar stock
        if nuevo_stock is not None:
            stock_talla.stock = int(nuevo_stock)
        
        # Actualizar stock inicial si se proporciona
        if nuevo_stock_inicial is not None:
            stock_talla.stock_inicial = int(nuevo_stock_inicial)
        
        stock_talla.save()
        
        # Actualizar stock general del producto
        producto.actualizar_stock_general()
        
        # Calcular nuevo porcentaje y estado
        porcentaje = stock_talla.obtener_porcentaje_stock()
        estado, estado_texto, color = stock_talla.obtener_estado_stock()
        
        return JsonResponse({
            'success': True,
            'message': f'Stock actualizado para {producto.nombre} - Talla {talla}',
            'porcentaje': porcentaje,
            'estado': estado,
            'estado_texto': estado_texto,
            'color': color,
            'stock_actual': stock_talla.stock,
            'stock_inicial': stock_talla.stock_inicial
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al actualizar el stock: {str(e)}'
        })
    
@login_required
def registro_ventas_view(request):
    """Vista principal del registro de ventas - VERSIÓN CORREGIDA PARA STRIPE"""
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect('paneladmin')
    
    # Filtros
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    producto_id = request.GET.get('producto_id')
    tipo_movimiento = request.GET.get('tipo_movimiento')
    
    # Obtener TODOS los movimientos y ventas (incluyendo pedidos pendientes)
    movimientos = MovimientoInventario.objects.select_related('producto', 'usuario', 'pedido').all()
    ventas = RegistroVenta.objects.select_related('producto', 'usuario', 'pedido').all()
    
    # Aplicar filtros a MOVIMIENTOS - INCLUIR PEDIDOS PENDIENTES
    movimientos_filtrados = movimientos
    if fecha_inicio:
        movimientos_filtrados = movimientos_filtrados.filter(fecha_movimiento__date__gte=fecha_inicio)
    if fecha_fin:
        movimientos_filtrados = movimientos_filtrados.filter(fecha_movimiento__date__lte=fecha_fin)
    if producto_id:
        movimientos_filtrados = movimientos_filtrados.filter(producto_id=producto_id)
    if tipo_movimiento:
        movimientos_filtrados = movimientos_filtrados.filter(tipo_movimiento=tipo_movimiento)
    
    # Aplicar filtros a VENTAS (para estadísticas) - INCLUIR TODOS LOS ESTADOS
    ventas_filtradas = ventas
    if fecha_inicio:
        ventas_filtradas = ventas_filtradas.filter(fecha_venta__date__gte=fecha_inicio)
    if fecha_fin:
        ventas_filtradas = ventas_filtradas.filter(fecha_venta__date__lte=fecha_fin)
    if producto_id:
        ventas_filtradas = ventas_filtradas.filter(producto_id=producto_id)
    
    # Estadísticas - usar VENTAS para estadísticas de ventas
    total_ventas = ventas_filtradas.aggregate(total=Sum('total'))['total'] or 0
    total_unidades_vendidas = ventas_filtradas.aggregate(total=Sum('cantidad'))['total'] or 0
    total_movimientos = movimientos_filtrados.count()
    
    # Productos más vendidos (basado en RegistroVenta) - PERÍODO MÁS AMPLIO
    desde = timezone.now() - timedelta(days=90)  # 3 meses en lugar de 30 días
    productos_mas_vendidos = Producto.objects.annotate(
        total_vendido=Sum('registroventa__cantidad', 
                         filter=Q(registroventa__fecha_venta__gte=desde)),
        ingresos_totales=Sum('registroventa__total',
                           filter=Q(registroventa__fecha_venta__gte=desde))
    ).filter(total_vendido__gt=0).order_by('-total_vendido')[:10]
    
    # Movimientos recientes (últimos 100)
    movimientos_recientes = movimientos_filtrados.order_by('-fecha_movimiento')[:100]
    
    # Datos para filtros
    productos = Producto.objects.all()
    tipos_movimiento = TipoMovimiento.choices
    
    # DEBUG: Verificar datos
    print("=== DEBUG REGISTRO VENTAS - STRIPE ===")
    print(f"Total ventas encontradas: {ventas_filtradas.count()}")
    print(f"Total movimientos encontrados: {movimientos_filtrados.count()}")
    print(f"Productos más vendidos: {productos_mas_vendidos.count()}")
    
    context = {
        'movimientos': movimientos_recientes,
        'total_ventas': total_ventas,
        'total_unidades_vendidas': total_unidades_vendidas,
        'total_movimientos': total_movimientos,
        'productos_mas_vendidos': productos_mas_vendidos,
        'productos': productos,
        'tipos_movimiento': tipos_movimiento,
        'filtros_aplicados': {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'producto_id': producto_id,
            'tipo_movimiento': tipo_movimiento,
        }
    }
    
    return render(request, 'registro_ventas.html', context)

@login_required
def detalle_producto_ventas_view(request, producto_id):
    """Vista detallada de ventas por producto"""
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect('paneladmin')
    
    producto = get_object_or_404(Producto, id=producto_id)
    
    # Filtros
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    # Obtener datos del producto
    movimientos = MovimientoInventario.objects.filter(producto=producto)
    ventas = RegistroVenta.objects.filter(producto=producto)
    
    # Aplicar filtros de fecha
    if fecha_inicio:
        movimientos = movimientos.filter(fecha_movimiento__date__gte=fecha_inicio)
        ventas = ventas.filter(fecha_venta__date__gte=fecha_inicio)
    
    if fecha_fin:
        movimientos = movimientos.filter(fecha_movimiento__date__lte=fecha_fin)
        ventas = ventas.filter(fecha_venta__date__lte=fecha_fin)
    
    # Estadísticas por talla
    estadisticas_tallas = []
    for stock_talla in producto.stocktalla_set.all():
        ventas_talla = ventas.filter(talla=stock_talla.talla)
        movimientos_talla = movimientos.filter(talla=stock_talla.talla)
        
        total_ventas_talla = ventas_talla.aggregate(total=Sum('total'))['total'] or 0
        unidades_vendidas_talla = ventas_talla.aggregate(total=Sum('cantidad'))['total'] or 0
        
        # Calcular tiempo promedio de venta
        primera_venta = ventas_talla.order_by('fecha_venta').first()
        ultima_venta = ventas_talla.order_by('-fecha_venta').first()
        
        tiempo_promedio = None
        if primera_venta and ultima_venta and unidades_vendidas_talla > 0:
            dias_totales = (ultima_venta.fecha_venta - primera_venta.fecha_venta).days
            if dias_totales > 0:
                tiempo_promedio = dias_totales / unidades_vendidas_talla
        
        estadisticas_tallas.append({
            'talla': stock_talla.talla,
            'stock_inicial': stock_talla.stock_inicial,
            'stock_actual': stock_talla.stock,
            'unidades_vendidas': unidades_vendidas_talla,
            'total_ventas': total_ventas_talla,
            'primera_venta': primera_venta.fecha_venta if primera_venta else None,
            'ultima_venta': ultima_venta.fecha_venta if ultima_venta else None,
            'tiempo_promedio_venta': tiempo_promedio,
            'porcentaje_vendido': (unidades_vendidas_talla / stock_talla.stock_inicial * 100) if stock_talla.stock_inicial > 0 else 0,
        })
    
    # Movimientos recientes para este producto
    movimientos_recientes = movimientos.order_by('-fecha_movimiento')[:20]
    
    context = {
        'producto': producto,
        'estadisticas_tallas': estadisticas_tallas,
        'movimientos_recientes': movimientos_recientes,
        'total_ventas_producto': ventas.aggregate(total=Sum('total'))['total'] or 0,
        'total_unidades_vendidas_producto': ventas.aggregate(total=Sum('cantidad'))['total'] or 0,
        'filtros_aplicados': {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
        }
    }
    
    return render(request, 'detalle_producto_ventas.html', context)

@login_required
def reporte_ventas_pdf(request):
    """Genera reporte de ventas en PDF"""
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect('paneladmin')
    
    # Parámetros del reporte
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    # Obtener datos
    ventas = RegistroVenta.objects.all()
    
    if fecha_inicio:
        ventas = ventas.filter(fecha_venta__date__gte=fecha_inicio)
    
    if fecha_fin:
        ventas = ventas.filter(fecha_venta__date__lte=fecha_fin)
    
    # Calcular estadísticas
    total_ventas = ventas.aggregate(total=Sum('total'))['total'] or 0
    total_unidades = ventas.aggregate(total=Sum('cantidad'))['total'] or 0
    cantidad_ventas = ventas.count()
    
    # Aquí iría la lógica para generar el PDF
    # Por ahora devolvemos un JSON con los datos
    from django.http import JsonResponse
    return JsonResponse({
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'total_ventas': float(total_ventas),
        'total_unidades': total_unidades,
        'cantidad_ventas': cantidad_ventas,
        'ventas': list(ventas.values('producto__nombre', 'talla', 'cantidad', 'precio_unitario', 'total', 'fecha_venta')[:10])
    })

def registrar_venta_automatica(pedido):
    """Función para registrar ventas automáticamente cuando se procesa un pedido"""
    try:
        # Verificar si ya existen registros de venta para este pedido
        ventas_existentes = RegistroVenta.objects.filter(pedido=pedido)
        if ventas_existentes.exists():
            logger.info(f"Ya existen registros de venta para el pedido {pedido.numero_pedido}")
            return True
        
        # Obtener todos los detalles del pedido
        detalles_pedido = DetallePedido.objects.filter(pedido=pedido)
        
        for detalle in detalles_pedido:
            # Crear registro de venta
            RegistroVenta.objects.create(
                pedido=pedido,
                producto=detalle.producto,
                talla=detalle.talla,
                cantidad=detalle.cantidad,
                precio_unitario=detalle.precio,
                total=detalle.obtener_total(),
                usuario=pedido.usuario,
                fecha_venta=pedido.creado_en
            )
            
            logger.info(f"Registro de venta creado para {detalle.producto.nombre} - Talla {detalle.talla}")
        
        return True
    except Exception as e:
        logger.error(f"Error al registrar venta automática: {str(e)}")
        return False
    
@login_required
def checkout_view(request):
    carrito, created = Carrito.objects.get_or_create(usuario=request.user)
    
    if not carrito.items.exists():
        messages.error(request, "Tu carrito está vacío.")
        return redirect('ver_carrito')
    
    for item in carrito.items.all():
        try:
            stock_talla = StockTalla.objects.get(producto=item.producto, talla=item.talla)
            if stock_talla.stock < item.cantidad:
                messages.error(request, f"No hay suficiente stock para {item.producto.nombre} en talla {item.talla}. Solo quedan {stock_talla.stock} unidades.")
                return redirect('ver_carrito')
        except StockTalla.DoesNotExist:
            messages.error(request, f"El producto {item.producto.nombre} en talla {item.talla} no está disponible.")
            return redirect('ver_carrito')
    
    if request.method == 'POST':
        form = PedidoForm(request.POST)
        if form.is_valid():
            pedido = form.save(commit=False)
            pedido.usuario = request.user
            pedido.total = carrito.obtener_total()
            pedido.numero_pedido = pedido.generar_numero_pedido()
            pedido.save()
            
            for item in carrito.items.all():
                DetallePedido.objects.create(
                    pedido=pedido,
                    producto=item.producto,
                    talla=item.talla,
                    cantidad=item.cantidad,
                    precio=item.producto.precio
                )
                
                stock_talla = StockTalla.objects.get(producto=item.producto, talla=item.talla)
                
                # Registrar movimiento ANTES de actualizar el stock
                MovimientoInventario.objects.create(
                    producto=item.producto,
                    talla=item.talla,
                    tipo_movimiento=TipoMovimiento.VENTA,
                    cantidad=-item.cantidad,
                    stock_anterior=stock_talla.stock,
                    stock_posterior=stock_talla.stock - item.cantidad,
                    precio_unitario=item.producto.precio,
                    total=item.obtener_total(),
                    usuario=request.user,
                    pedido=pedido,
                    observaciones=f"Venta - Pedido {pedido.numero_pedido}"
                )
                
                # Actualizar stock
                stock_talla.stock -= item.cantidad
                stock_talla.save()
                
                # Registrar venta
                RegistroVenta.objects.create(
                    pedido=pedido,
                    producto=item.producto,
                    talla=item.talla,
                    cantidad=item.cantidad,
                    precio_unitario=item.producto.precio,
                    total=item.obtener_total(),
                    usuario=request.user,
                    fecha_venta=timezone.now()
                )
                
                item.producto.actualizar_stock_general()
            
            carrito.items.all().delete()
            
            messages.success(request, f"¡Pedido realizado exitosamente! Número de pedido: {pedido.numero_pedido}")
            return redirect('confirmacion_pedido', pedido_id=pedido.id)
    else:
        initial_data = {}
        if request.user.first_name and request.user.last_name:
            initial_data['nombre_completo'] = f"{request.user.first_name} {request.user.last_name}"
        if request.user.email:
            initial_data['email'] = request.user.email
        
        form = PedidoForm(initial=initial_data)
    
    return render(request, 'checkout.html', {
        'carrito': carrito,
        'form': form
    })

@login_required
def registrar_venta_manual(request):
    """Vista para registrar ventas manualmente (para testing o pedidos existentes)"""
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para realizar esta acción.")
        return redirect('paneladmin')
    
    if request.method == 'POST':
        pedido_id = request.POST.get('pedido_id')
        
        try:
            pedido = Pedido.objects.get(id=pedido_id)
            
            # Verificar si ya existen registros de venta para este pedido
            ventas_existentes = RegistroVenta.objects.filter(pedido=pedido)
            if ventas_existentes.exists():
                messages.warning(request, f"Ya existen registros de venta para el pedido {pedido.numero_pedido}")
                return redirect('registro_ventas')
            
            # Registrar ventas automáticamente
            if registrar_venta_automatica(pedido):
                messages.success(request, f"Ventas registradas exitosamente para el pedido {pedido.numero_pedido}")
            else:
                messages.error(request, f"Error al registrar ventas para el pedido {pedido.numero_pedido}")
                
            return redirect('registro_ventas')
            
        except Pedido.DoesNotExist:
            messages.error(request, "Pedido no encontrado")
            return redirect('registro_ventas')
    
    # Mostrar formulario para ingresar ID de pedido
    pedidos_sin_ventas = Pedido.objects.exclude(
        id__in=RegistroVenta.objects.values('pedido_id')
    )
    
    return render(request, 'registrar_venta_manual.html', {
        'pedidos_sin_ventas': pedidos_sin_ventas
    })

    # Configurar Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
@require_POST
@csrf_exempt
def crear_sesion_pago_stripe(request):
    """Crea una sesión de checkout de Stripe"""
    try:
        data = json.loads(request.body)
        carrito, created = Carrito.objects.get_or_create(usuario=request.user)
        
        if not carrito.items.exists():
            return JsonResponse({'error': 'El carrito está vacío'}, status=400)
        
        # Verificar stock antes de crear el pedido
        for item in carrito.items.all():
            try:
                stock_talla = StockTalla.objects.get(producto=item.producto, talla=item.talla)
                if stock_talla.stock < item.cantidad:
                    return JsonResponse({
                        'error': f"No hay suficiente stock para {item.producto.nombre} en talla {item.talla}"
                    }, status=400)
            except StockTalla.DoesNotExist:
                return JsonResponse({
                    'error': f"El producto {item.producto.nombre} en talla {item.talla} no está disponible"
                }, status=400)
        
        # Crear el pedido primero
        pedido = Pedido.objects.create(
            usuario=request.user,
            total=carrito.obtener_total(),
            nombre_completo=data.get('nombre_completo', 'Cliente'),
            email=data.get('email', 'cliente@ejemplo.com'),
            direccion_envio=data.get('direccion', 'Dirección no especificada'),
            ciudad=data.get('ciudad', 'Ciudad no especificada'),
            telefono=data.get('telefono', '0000000000'),
            estado='pendiente',
            metodo_pago='tarjeta'
        )
        
        # Crear detalles del pedido
        for item in carrito.items.all():
            DetallePedido.objects.create(
                pedido=pedido,
                producto=item.producto,
                talla=item.talla,
                cantidad=item.cantidad,
                precio=item.producto.precio
            )
        
        # Crear line items para Stripe
        line_items = []
        for item in carrito.items.all():
            # Calcular precio con descuento si aplica
            precio_final = item.producto.precio
            if item.producto.descuento > 0:
                precio_final = item.producto.precio_con_descuento()
            
            line_items.append({
                'price_data': {
                    'currency': 'cop',  # Pesos colombianos
                    'product_data': {
                        'name': f"{item.producto.nombre} - Talla {item.talla}",
                        'description': item.producto.descripcion[:100] if item.producto.descripcion else "Producto de moda",
                    },
                    'unit_amount': int(precio_final * 100),  # Stripe usa centavos
                },
                'quantity': item.cantidad,
            })
        
        # Crear sesión de checkout de Stripe
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=request.build_absolute_uri(f'/pago-exitoso/{pedido.id}/'),
            cancel_url=request.build_absolute_uri(f'/pago-cancelado/{pedido.id}/'),
            customer_email=pedido.email,
            metadata={
                'pedido_id': str(pedido.id),
                'usuario_id': str(request.user.id)
            }
        )
        
        # Guardar el ID de la sesión de Stripe en el pedido
        pedido.stripe_checkout_session_id = checkout_session.id
        pedido.save()
        
        return JsonResponse({
            'sessionId': checkout_session.id,
            'url': checkout_session.url
        })
        
    except Exception as e:
        logger.error(f"Error al crear sesión de pago Stripe: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def pago_exitoso(request, pedido_id):
    """Vista cuando el pago es exitoso"""
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    
    try:
        # Verificar el pago con Stripe
        if pedido.stripe_checkout_session_id:
            session = stripe.checkout.Session.retrieve(pedido.stripe_checkout_session_id)
            
            if session.payment_status == 'paid':
                # Pago confirmado, actualizar estado
                pedido.estado = 'confirmado'
                pedido.stripe_payment_intent_id = session.payment_intent
                pedido.save()
                
                # Actualizar stock
                for detalle in pedido.detalles.all():
                    try:
                        stock_talla = StockTalla.objects.get(
                            producto=detalle.producto, 
                            talla=detalle.talla
                        )
                        stock_talla.stock -= detalle.cantidad
                        stock_talla.save()
                        detalle.producto.actualizar_stock_general()
                    except StockTalla.DoesNotExist:
                        pass
                
                # Vaciar carrito
                carrito, created = Carrito.objects.get_or_create(usuario=request.user)
                carrito.items.all().delete()
                
                messages.success(request, f"¡Pago exitoso! Tu pedido {pedido.numero_pedido} ha sido confirmado.")
            else:
                messages.warning(request, "El pago aún no ha sido confirmado. Te notificaremos cuando se complete.")
                
        return render(request, 'pago_exitoso.html', {'pedido': pedido})
        
    except Exception as e:
        logger.error(f"Error en pago exitoso: {str(e)}")
        messages.error(request, f"Error al verificar el pago: {str(e)}")
        return redirect('ver_carrito')

@login_required
def pago_cancelado(request, pedido_id):
    """Vista cuando el pago es cancelado"""
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    pedido.estado = 'cancelado'
    pedido.save()
    
    messages.warning(request, "El pago fue cancelado. Puedes intentarlo nuevamente.")
    return redirect('ver_carrito')

@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Webhook para recibir notificaciones de Stripe"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'Webhook error'}, status=400)
    
    # Manejar diferentes tipos de eventos
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_payment_success(session)
    elif event['type'] == 'checkout.session.expired':
        session = event['data']['object']
        handle_session_expired(session)
    
    return JsonResponse({'success': True})

def handle_payment_success(session):
    """Manejar pago exitoso desde webhook"""
    try:
        pedido_id = session['metadata']['pedido_id']
        pedido = Pedido.objects.get(id=pedido_id)
        
        pedido.estado = 'confirmado'
        pedido.stripe_payment_intent_id = session.get('payment_intent')
        pedido.save()
        
        # Actualizar stock desde webhook
        for detalle in pedido.detalles.all():
            try:
                stock_talla = StockTalla.objects.get(
                    producto=detalle.producto, 
                    talla=detalle.talla
                )
                stock_talla.stock -= detalle.cantidad
                stock_talla.save()
                detalle.producto.actualizar_stock_general()
            except StockTalla.DoesNotExist:
                pass
        
        logger.info(f"Pedido {pedido.numero_pedido} confirmado via webhook")
        
    except Pedido.DoesNotExist:
        logger.error(f"Pedido no encontrado en webhook: {pedido_id}")
    except Exception as e:
        logger.error(f"Error procesando webhook: {str(e)}")

def handle_session_expired(session):
    """Manejar sesión de pago expirada"""
    try:
        pedido_id = session['metadata']['pedido_id']
        pedido = Pedido.objects.get(id=pedido_id)
        
        pedido.estado = 'cancelado'
        pedido.save()
        
        logger.info(f"Pedido {pedido.numero_pedido} cancelado por expiración")
        
    except Pedido.DoesNotExist:
        logger.error(f"Pedido no encontrado en webhook de expiración: {pedido_id}")
    except Exception as e:
        logger.error(f"Error procesando webhook de expiración: {str(e)}")

@login_required
def cambiar_estado_pedido(request, pedido_id):
    """Vista para cambiar el estado de un pedido"""
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para realizar esta acción.")
        return redirect('paneladmin')
    
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('nuevo_estado')
        if nuevo_estado in dict(Pedido.ESTADOS_PEDIDO):
            pedido.estado = nuevo_estado
            pedido.save()
            
            messages.success(request, f"Estado del pedido {pedido.numero_pedido} actualizado a {pedido.get_estado_display()}.")
            return redirect('pedidos')
        else:
            messages.error(request, "Estado inválido.")
    
    return render(request, 'cambiar_estado_pedido.html', {
        'pedido': pedido,
        'estados': Pedido.ESTADOS_PEDIDO
    })

@login_required
def actualizar_estado_pedido(request, pedido_id):
    """Vista para cambiar el estado de un pedido desde el detalle"""
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para realizar esta acción.")
        return redirect('paneladmin')
    
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('nuevo_estado')
        if nuevo_estado in dict(Pedido.ESTADOS_PEDIDO):
            pedido.estado = nuevo_estado
            pedido.save()
            
            messages.success(request, f"Estado del pedido {pedido.numero_pedido} actualizado a {pedido.get_estado_display()}.")
            return redirect('pedido_detalle', pedido_id=pedido.id)
        else:
            messages.error(request, "Estado inválido.")
    
    # Si es GET, mostrar el formulario
    return render(request, 'cambiar_estado_pedido.html', {
        'pedido': pedido,
        'estados': Pedido.ESTADOS_PEDIDO
    })

@login_required
def reparar_registros_ventas(request):
    """Función para reparar registros de ventas faltantes - VERSIÓN MEJORADA"""
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para realizar esta acción.")
        return redirect('paneladmin')
    
    try:
        # Encontrar pedidos que deberían tener registros de venta
        pedidos_con_ventas = Pedido.objects.filter(
            estado__in=['confirmado', 'procesando', 'enviado', 'entregado']
        )
        
        pedidos_sin_ventas = pedidos_con_ventas.exclude(
            id__in=RegistroVenta.objects.values('pedido_id')
        )
        
        print(f"=== REPARANDO REGISTROS DE VENTA ===")
        print(f"Pedidos con ventas potenciales: {pedidos_con_ventas.count()}")
        print(f"Pedidos sin registros de venta: {pedidos_sin_ventas.count()}")
        
        registros_creados = 0
        pedidos_procesados = 0
        
        for pedido in pedidos_sin_ventas:
            if crear_registro_venta_desde_pedido(pedido):
                registros_creados += 1
            pedidos_procesados += 1
        
        # También verificar pedidos que ya tienen algunos registros pero podrían estar incompletos
        pedidos_con_detalles = Pedido.objects.filter(
            estado__in=['confirmado', 'procesando', 'enviado', 'entregado']
        )
        
        for pedido in pedidos_con_detalles:
            detalles_count = DetallePedido.objects.filter(pedido=pedido).count()
            ventas_count = RegistroVenta.objects.filter(pedido=pedido).count()
            
            if detalles_count > ventas_count:
                print(f"Pedido {pedido.numero_pedido} tiene {detalles_count} detalles pero {ventas_count} ventas")
                if crear_registro_venta_desde_pedido(pedido):
                    registros_creados += 1
        
        if registros_creados > 0:
            messages.success(request, f"¡Reparación completada! Se crearon {registros_creados} registros de venta faltantes.")
        else:
            messages.info(request, "No se encontraron registros de venta faltantes. Todo está en orden.")
            
        print(f"Reparación completada: {registros_creados} registros creados")
            
    except Exception as e:
        messages.error(request, f"Error al reparar registros: {str(e)}")
        print(f"Error en reparación: {str(e)}")
    
    return redirect('registro_ventas')

def crear_registro_venta_desde_pedido(pedido):
    """Crea registros de venta automáticamente desde un pedido - VERSIÓN MEJORADA"""
    try:
        # Verificar si ya existen registros de venta para este pedido
        ventas_existentes = RegistroVenta.objects.filter(pedido=pedido)
        if ventas_existentes.exists():
            print(f"Ya existen {ventas_existentes.count()} registros de venta para el pedido {pedido.numero_pedido}")
            return True
        
        # Obtener todos los detalles del pedido
        detalles_pedido = DetallePedido.objects.filter(pedido=pedido)
        
        if not detalles_pedido.exists():
            print(f"No hay detalles de pedido para {pedido.numero_pedido}")
            return False
        
        registros_creados = 0
        
        for detalle in detalles_pedido:
            # Crear registro de venta
            registro_venta = RegistroVenta.objects.create(
                pedido=pedido,
                producto=detalle.producto,
                talla=detalle.talla,
                cantidad=detalle.cantidad,
                precio_unitario=detalle.precio,
                total=detalle.obtener_total(),
                usuario=pedido.usuario,
                fecha_venta=pedido.creado_en
            )
            
            registros_creados += 1
            print(f"Registro de venta creado: {detalle.producto.nombre} - {detalle.talla} - {detalle.cantidad} unidades")
        
        print(f"Se crearon {registros_creados} registros de venta para el pedido {pedido.numero_pedido}")
        return True
        
    except Exception as e:
        print(f"Error al crear registros de venta para pedido {pedido.numero_pedido}: {str(e)}")
        return False
    
@login_required
def sincronizar_ventas_stripe(request):
    """Sincroniza ventas de pedidos Stripe que no tienen registros de venta"""
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para realizar esta acción.")
        return redirect('paneladmin')
        
    try:
        # Encontrar pedidos de Stripe que no tienen registros de venta
        pedidos_stripe = Pedido.objects.filter(
            stripe_checkout_session_id__isnull=False
        ).exclude(
            id__in=RegistroVenta.objects.values('pedido_id')
        )
            
        registros_creados = 0
            
        for pedido in pedidos_stripe:
            # Verificar si el pago de Stripe fue exitoso
            if pedido.stripe_checkout_session_id:
                try:
                    session = stripe.checkout.Session.retrieve(pedido.stripe_checkout_session_id)
                        
                    if session.payment_status == 'paid' and pedido.estado == 'confirmado':
                        # Crear registros de venta para este pedido
                        if crear_registro_venta_desde_pedido(pedido):
                            registros_creados += 1
                            print(f"Registros creados para pedido Stripe: {pedido.numero_pedido}")
                except Exception as e:
                    print(f"Error verificando sesión Stripe {pedido.stripe_checkout_session_id}: {str(e)}")
                    continue
            
        if registros_creados > 0:
            messages.success(request, f"Se sincronizaron {registros_creados} pedidos de Stripe con el registro de ventas.")
        else:
            messages.info(request, "No se encontraron pedidos de Stripe pendientes de sincronización.")
                
    except Exception as e:
        messages.error(request, f"Error al sincronizar ventas Stripe: {str(e)}")
        
    return redirect('registro_ventas')

def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            user = CustomUser.objects.get(email=email)
            
            # Generar código de 6 dígitos
            reset_code = ''.join(random.choices(string.digits, k=6))
            
            # Guardar código en sesión
            request.session['reset_code'] = reset_code
            request.session['reset_email'] = email
            
            # Enviar email con el código
            send_mail(
                'Código de Recuperación - Hinc',
                f'''
Hola {user.username},

Has solicitado restablecer tu contraseña en Hinc.

Tu código de verificación es: {reset_code}

Ingresa este código en la página de verificación.

Si no solicitaste este cambio, por favor ignora este mensaje.

Saludos,
El equipo de Hinc
                ''',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            
            messages.success(request, 'Se ha enviado un código de verificación a tu correo.')
            return redirect('password_reset_code')
            
        except CustomUser.DoesNotExist:
            messages.error(request, 'No existe una cuenta con este correo electrónico.')
    
    return render(request, 'password_reset.html')

def password_reset_code(request):
    # Verificar que hay una solicitud en proceso
    if 'reset_email' not in request.session:
        messages.error(request, 'Debes solicitar un código primero.')
        return redirect('password_reset')
    
    if request.method == 'POST':
        entered_code = request.POST.get('code')
        stored_code = request.session.get('reset_code')
        
        if entered_code == stored_code:
            messages.success(request, 'Código verificado correctamente.')
            return redirect('password_reset_confirm')
        else:
            messages.error(request, 'Código incorrecto. Inténtalo de nuevo.')
    
    return render(request, 'password_reset_code.html')

def password_reset_confirm(request):
    # Verificar que el código fue validado
    if 'reset_email' not in request.session:
        messages.error(request, 'Debes verificar tu código primero.')
        return redirect('password_reset')
    
    email = request.session.get('reset_email')
    
    try:
        user = CustomUser.objects.get(email=email)
        
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                # Limpiar la sesión
                if 'reset_code' in request.session:
                    del request.session['reset_code']
                if 'reset_email' in request.session:
                    del request.session['reset_email']
                
                messages.success(request, 'Tu contraseña ha sido cambiada exitosamente.')
                return redirect('password_reset_complete')
        else:
            form = SetPasswordForm(user)
        
        return render(request, 'password_reset_confirm.html', {'form': form})
    
    except CustomUser.DoesNotExist:
        messages.error(request, 'Usuario no encontrado.')
        return redirect('password_reset')

def password_reset_complete(request):
    return render(request, 'password_reset_complete.html')