from django.urls import path
from . import views
# Define las rutas URL de la aplicación, mapeando URLs a vistas en views.py para gestionar la navegación del sitio web de la tienda en línea. Organiza el acceso a funcionalidades clave: página principal (index), autenticación (registro, inicio y cierre de sesión), gestión administrativa (panel de administración, usuarios, productos, categorías e inventario) y carrito de compras (agregar, quitar, obtener y ver carrito). Cada ruta tiene un nombre único para su uso en templates y redirecciones, soportando tanto acciones públicas (como el catálogo) como protegidas para administradores (requieren autenticación y rol Admin) y usuarios autenticados (carrito).
urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('paneladmin/', views.paneladmin_view, name='paneladmin'),
    path('paneladmin/usuarios/', views.usuarios_view, name='usuarios'),
    path('paneladmin/usuarios/add/', views.add_user, name='add_user'),
    path('paneladmin/usuarios/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('paneladmin/usuarios/delete/<int:user_id>/', views.delete_user, name='delete_user'),
    path('paneladmin/productos/', views.productos_view, name='productos'),
    path('paneladmin/productos/create/', views.productos_create, name='productos_create'),
    path('paneladmin/productos/update/<int:producto_id>/', views.productos_update, name='productos_update'),
    path('paneladmin/productos/delete/<int:producto_id>/', views.productos_delete, name='productos_delete'),
    path('paneladmin/categorias/', views.categorias_view, name='categorias'),
    path('paneladmin/categorias/create/', views.categorias_create, name='categorias_create'),
    path('paneladmin/categorias/update/<int:categoria_id>/', views.categorias_update, name='categorias_update'),
    path('paneladmin/categorias/delete/<int:categoria_id>/', views.categorias_delete, name='categorias_delete'),
    path('paneladmin/inventario/', views.inventario_view, name='inventario'),
    path('catalogo/', views.catalogo_view, name='catalogo'),
    path('producto/<int:producto_id>/', views.producto_detalle_view, name='producto_detalle'),
    path('carrito/agregar/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/quitar/', views.quitar_del_carrito, name='quitar_del_carrito'),
    path('carrito/obtener/', views.obtener_carrito, name='obtener_carrito'),
    path('carrito/', views.ver_carrito, name='ver_carrito'),
    # Nuevas URLs para el sistema de pagos
    path('checkout/', views.checkout_view, name='checkout'),
    path('procesar-pago/', views.procesar_pago, name='procesar_pago'),
    path('confirmacion-pedido/<int:pedido_id>/', views.confirmacion_pedido_view, name='confirmacion_pedido'),
]