from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.backends import ModelBackend
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, LoginForm, ProductoForm, CategoriaForm, InventoryForm, StockTallaForm, StockTallaInlineFormSet
from .models import CustomUser, Producto, Categoria, Carrito, ItemCarrito, StockTalla
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import logging
# Configura el sistema de logging en nivel DEBUG para capturar mensajes detallados de depuración, útiles para identificar errores en el flujo de la aplicación. Usa un logger específico para este módulo.
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
# Renderiza la página principal (index2.html), mostrando hasta 4 productos destacados y en oferta (estado='Habilitado', stock>0) del modelo Producto, y todas las categorías del modelo Categoria. Pasa el usuario autenticado, productos y categorías al template. Accesible sin autenticación.
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
# Maneja el registro de usuarios con CustomUserCreationForm. Para POST, asigna rol 'Usuario' y estado 'Habilitado', valida el formulario, guarda el usuario (modelo CustomUser) con contraseña encriptada y redirige a login. Si hay errores, muestra mensajes detallados. Para GET, renderiza register.html con el formulario vacío. Pública.
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
# Gestiona el inicio de sesión con LoginForm. Para POST, valida correo y contraseña, verifica el usuario (modelo CustomUser) y su estado ('Habilitado'), autentica con ModelBackend, inicia sesión y redirige a index. Si hay errores, muestra mensaje. Para GET, renderiza login.html con formulario vacío. Pública.
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
# Cierra la sesión del usuario autenticado con logout() y redirige a index. No requiere validaciones adicionales. Accesible para usuarios autenticados.
def logout_view(request):
    logout(request)
    return redirect('index')
# Renderiza el panel de administración (paneladmin.html) para usuarios con rol 'Admin', mostrando todos los usuarios (CustomUser), productos (Producto) y categorías (Categoria). Si el usuario no es Admin, muestra error y redirige a index. Requiere autenticación.
@login_required
def paneladmin_view(request):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para acceder al panel de administración.")
        return redirect('index')
    users = CustomUser.objects.all()
    productos = Producto.objects.all()
    categorias = Categoria.objects.all()
    
    # Obtener productos con stock bajo
    productos_stock_bajo = []
    for producto in productos:
        if producto.tiene_stock_bajo():
            tallas_bajas = producto.get_tallas_con_stock_bajo()
            productos_stock_bajo.append({
                'producto': producto,
                'tallas_bajas': tallas_bajas
            })
    
    return render(request, 'paneladmin.html', {
        'users': users,
        'productos': productos,
        'categorias': categorias,
        'productos_stock_bajo': productos_stock_bajo
    })
# Gestiona la administración de usuarios para Admins, mostrando todos los usuarios (CustomUser) en PAusuarios.html. Soporta acciones (add, edit, delete) según el parámetro 'action'. Para POST, valida CustomUserCreationForm para agregar o editar usuarios, o elimina un usuario por ID. Muestra mensajes de éxito o error y redirige a usuarios. Requiere autenticación y rol Admin.
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
# Permite a Admins agregar nuevos usuarios con CustomUserCreationForm. Para POST, valida y guarda el usuario (CustomUser), redirige a usuarios con mensaje de éxito o muestra errores. Para GET, renderiza PAusuarios.html con formulario vacío. Requiere autenticación y rol Admin.
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
# Permite a Admins editar un usuario existente (CustomUser) identificado por user_id. Para POST, valida CustomUserCreationForm, actualiza el usuario y redirige a usuarios. Para GET, renderiza PAusuarios.html con el formulario prellenado. Muestra mensajes de éxito o error. Requiere autenticación y rol Admin.
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
# Permite a Admins eliminar un usuario (CustomUser) por user_id. Para POST, elimina el usuario y redirige a usuarios con mensaje de éxito. Para GET, renderiza PAusuarios.html para confirmar la eliminación. Requiere autenticación y rol Admin.
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
# Gestiona la administración de productos para Admins, mostrando todos los productos (Producto) en Pproductos.html. Soporta acciones (create, update, delete) según 'action'. Para POST, valida ProductoForm para crear o actualizar productos (incluye archivos para imágenes), o elimina un producto por ID. Muestra mensajes y redirige a productos. Requiere autenticación y rol Admin.
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
        # Obtener stock por tallas para el producto
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
    return render(request, 'Pproductos.html', {
        'productos': productos, 
        'action': action, 
        'producto': producto, 
        'form': form,
        'stock_forms': stock_forms
    })
# Permite a Admins crear productos con ProductoForm. Para POST, valida el formulario (incluye request.FILES para imágenes), guarda el producto (modelo Producto) y redirige a productos. Para GET, renderiza Pproductos.html con formulario vacío. Muestra mensajes de éxito o error. Requiere autenticación y rol Admin.
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
# Permite a Admins editar un producto (Producto) por producto_id. Para POST, valida ProductoForm (con tallas prellenadas desde el modelo), actualiza el producto y redirige a productos. Para GET, renderiza Pproductos.html con formulario prellenado. Muestra mensajes de éxito o error. Requiere autenticación y rol Admin.
@login_required
def productos_update(request, producto_id):
    if request.user.role != 'Admin':
        messages.error(request, "No tienes permiso para editar productos.")
        return redirect('productos')
    producto = get_object_or_404(Producto, id=producto_id)
    form = ProductoForm(request.POST or None, request.FILES or None, instance=producto, initial={'tallas': producto.tallas.split(',') if producto.tallas else []})
    
    # Obtener stock por tallas para el producto
    stock_tallas = StockTalla.objects.filter(producto=producto)
    
    if request.method == 'POST':
        if form.is_valid():
            producto_actualizado = form.save()
            
            # Actualizar stock por tallas
            for stock_talla in stock_tallas:
                stock_field = f'stock_{stock_talla.talla}'
                if stock_field in request.POST:
                    try:
                        nuevo_stock = int(request.POST[stock_field])
                        if nuevo_stock >= 0:
                            stock_talla.stock = nuevo_stock
                            stock_talla.save()
                    except ValueError:
                        pass
            
            # Actualizar stock general
            producto_actualizado.actualizar_stock_general()
            
            messages.success(request, "Producto actualizado exitosamente.")
            return redirect('productos')
        else:
            messages.error(request, "Error al actualizar producto. Verifica los datos.")
            for error in form.errors.values():
                messages.error(request, error)
    
    # Crear forms para stock por talla
    stock_forms = []
    for stock_talla in stock_tallas:
        stock_forms.append({
            'talla': stock_talla.talla,
            'form': StockTallaForm(instance=stock_talla),
            'instance': stock_talla
        })
    
    return render(request, 'Pproductos.html', {
        'form': form, 
        'action': 'update_productos', 
        'producto': producto,
        'stock_forms': stock_forms
    })
# Permite a Admins eliminar un producto (Producto) por producto_id. Para POST, elimina el producto y redirige a productos con mensaje de éxito. Para GET, renderiza Pproductos.html para confirmar eliminación. Requiere autenticación y rol Admin.
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
# Gestiona la administración de categorías para Admins, mostrando todas las categorías (Categoria) en PAcategorias.html. Soporta acciones (create, update, delete) según 'action'. Para POST, valida CategoriaForm para crear o actualizar categorías (con imágenes), o elimina una categoría por ID. Muestra mensajes y redirige a categorias. Requiere autenticación y rol Admin.
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
# Permite a Admins crear categorías con CategoriaForm. Para POST, valida el formulario (incluye request.FILES para imágenes), guarda la categoría (modelo Categoria) y redirige a categorias. Para GET, renderiza PAcategorias.html con formulario vacío. Muestra mensajes de éxito o error. Requiere autenticación y rol Admin.
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
# Permite a Admins editar una categoría (Categoria) por categoria_id. Para POST, valida CategoriaForm, actualiza la categoría y redirige a categorias. Para GET, renderiza PAcategorias.html con formulario prellenado. Muestra mensajes de éxito o error. Requiere autenticación y rol Admin.
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
# Permite a Admins eliminar una categoría (Categoria) por categoria_id. Para POST, elimina la categoría y redirige a categorias con mensaje de éxito. Para GET, renderiza PAcategorias.html para confirmar eliminación. Requiere autenticación y rol Admin.
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
# Gestiona el inventario para Admins, mostrando todos los productos (Producto) en Pinventario.html. Soporta acciones (edit, delete) según 'action'. Para POST, valida InventoryForm para actualizar el stock de un producto o lo elimina por ID. Muestra mensajes y redirige a inventario. Requiere autenticación y rol Admin.
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
        # Obtener stock por tallas para el producto
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
                
                # Actualizar stock por tallas
                stock_tallas = StockTalla.objects.filter(producto=producto)
                for stock_talla in stock_tallas:
                    stock_field = f'stock_{stock_talla.talla}'
                    if stock_field in request.POST:
                        try:
                            nuevo_stock = int(request.POST[stock_field])
                            if nuevo_stock >= 0:
                                stock_talla.stock = nuevo_stock
                                stock_talla.save()
                        except ValueError:
                            pass
                
                # Actualizar stock general
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
# Renderiza el catálogo (catalogo.html), mostrando todos los productos (Producto) y categorías (Categoria). Pasa ambos al contexto del template para su visualización. Accesible sin autenticación, permite a todos los usuarios explorar los productos.
def catalogo_view(request):
    productos = Producto.objects.all()
    categorias = Categoria.objects.all()
    return render(request, 'catalogo.html', {'productos': productos, 'categorias': categorias})
# Renderiza la página de detalle de producto (producto.html), mostrando toda la información del producto, tallas disponibles, stock y permitiendo agregar al carrito. Accesible sin autenticación.
def producto_detalle_view(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    
    return render(request, 'producto.html', {
        'producto': producto,
        'user': request.user if request.user.is_authenticated else None
    })
# Agrega un producto al carrito del usuario autenticado (modelos Carrito e ItemCarrito). Recibe producto_id y cantidad en un JSON vía POST, obtiene o crea un carrito, actualiza o crea un ItemCarrito, y devuelve un JSON con los datos del carrito. Usa csrf_exempt y require_POST. Requiere autenticación.
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
        
        # Verificar stock disponible para la talla
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
            # Verificar que no exceda el stock al actualizar
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
# Elimina un producto del carrito del usuario autenticado. Recibe producto_id en un JSON vía POST, elimina el ItemCarrito correspondiente y devuelve un JSON con los datos actualizados del carrito. Usa csrf_exempt y require_POST. Requiere autenticación.
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
# Obtiene los datos del carrito del usuario autenticado (modelo Carrito). Crea o recupera el carrito y devuelve un JSON con sus datos, generados por obtener_datos_carrito. Requiere autenticación.
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
# Genera un diccionario con los datos del carrito, incluyendo los ítems (ItemCarrito) con id, nombre, precio, cantidad e imagen del producto, además del total y cantidad total del carrito. Usado por las vistas del carrito para devolver datos en formato JSON.
def obtener_datos_carrito(carrito):
    items = []
    for item in carrito.items.all():
        items.append({
            'id': item.id,  # Agregar ID del item
            'id_producto': item.producto.id,
            'nombre': item.producto.nombre,
            'precio': float(item.producto.precio),
            'cantidad': item.cantidad,
            'talla': item.talla,  # Incluir la talla
            'imagen': item.producto.imagen.url if item.producto.imagen else ''
        })
   
    return {
        'items': items,
        'total': float(carrito.obtener_total()),
        'cantidad_total': carrito.obtener_cantidad_total()
    }
# Renderiza la página del carrito (carrito.html) para el usuario autenticado, mostrando los ítems del carrito (modelo Carrito). Crea o recupera el carrito y lo pasa al template. Requiere autenticación.
@login_required
def ver_carrito(request):
    carrito, created = Carrito.objects.get_or_create(usuario=request.user)
    return render(request, 'carrito.html', {'carrito': carrito})