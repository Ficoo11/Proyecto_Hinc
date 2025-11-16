from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.backends import ModelBackend
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, LoginForm, ProductoForm, CategoriaForm, InventoryForm, StockTallaForm, StockTallaInlineFormSet, PedidoForm, PerfilForm
from .models import CustomUser, Producto, Categoria, Carrito, ItemCarrito, StockTalla, Pedido, DetallePedido
from django.urls import reverse
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import logging

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

# NUEVA VISTA PARA PERFIL
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
        creado_en__gte=timezone.now() - timezone.timedelta(days=7)
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
        'pedidos_recientes_lista': pedidos_recientes_lista
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
    
    if producto and action == 'edit':
        stock_tallas = StockTalla.objects.filter(producto=producto)
        stock_forms = [StockTallaForm(instance=stock) for stock in stock_tallas]
    else:
        stock_forms = []
    
    form = ProductoForm(instance=producto) if action == 'edit' else ProductoForm()
    
    if request.method == 'POST':
        if action == 'create_productos':
            form = ProductoForm(request.POST, request.FILES)
            if form.is_valid():
                producto_creado = form.save()
                messages.success(request, "Producto agregado exitosamente.")
                return redirect('productos')
            else:
                messages.error(request, "Error al agregar producto. Verifica los datos.")
                for error in form.errors.values():
                    messages.error(request, error)
        elif action == 'update_productos' and producto_id:
            form = ProductoForm(request.POST, request.FILES, instance=producto)
            if form.isvalid():
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
    return render(request, 'Pproductos.html', {
        'productos': productos, 
        'action': action, 
        'producto': producto, 
        'form': form,
        'stock_forms': stock_forms
    })

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
    
    if producto and action == 'edit':
        stock_tallas = StockTalla.objects.filter(producto=producto)
        stock_forms = [StockTallaForm(instance=stock) for stock in stock_tallas]
    else:
        stock_forms = []
    
    form = InventoryForm(instance=producto) if action == 'edit' else InventoryForm()
    
    if request.method == 'POST':
        if action == 'update_productos' and producto_id:
            form = InventoryForm(request.POST, instance=producto)
            if form.is_valid():
                form.save()
                
                stock_tallas = StockTalla.objects.filter(producto=producto)
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
                
                producto.actualizar_stock_general()
                
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
       
        carrito = get_object_or_404(Carrito, usuario=request.user)
        item = get_object_or_404(ItemCarrito, carrito=carrito, producto_id=producto_id, talla=talla)
        item.delete()
       
        return JsonResponse({
            'success': True,
            'carrito': obtener_datos_carrito(carrito)
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
        items.append({
            'id': item.id,
            'id_producto': item.producto.id,
            'nombre': item.producto.nombre,
            'precio': float(item.producto.precio),
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
                stock_talla.stock -= item.cantidad
                stock_talla.save()
                
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
            stock_talla.stock -= item.cantidad
            stock_talla.save()
            
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
    
    pedidos = Pedido.objects.all().order_by('-creado_en')
    estados = Pedido.ESTADOS_PEDIDO
    
    estado_filtro = request.GET.get('estado')
    if estado_filtro:
        pedidos = pedidos.filter(estado=estado_filtro)
    
    return render(request, 'pedidos.html', {
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

