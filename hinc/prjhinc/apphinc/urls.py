from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Perfil
    path('perfil/', views.perfil_view, name='perfil'),
    
    # Panel Admin
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
    
    # Registro de Ventas
    path('paneladmin/registro-ventas/', views.registro_ventas_view, name='registro_ventas'),
    path('paneladmin/registro-ventas/producto/<int:producto_id>/', views.detalle_producto_ventas_view, name='detalle_producto_ventas'),
    path('paneladmin/registro-ventas/reporte-pdf/', views.reporte_ventas_pdf, name='reporte_ventas_pdf'),
    
    # Pedidos
    path('paneladmin/pedidos/', views.pedidos_view, name='pedidos'),
    path('paneladmin/pedidos/detalle/<int:pedido_id>/', views.pedido_detalle_view, name='pedido_detalle'),
    path('paneladmin/pedidos/cambiar_estado/<int:pedido_id>/', views.cambiar_estado_pedido, name='cambiar_estado_pedido'),
    path('paneladmin/pedidos/actualizar_estado/<int:pedido_id>/', views.actualizar_estado_pedido, name='actualizar_estado_pedido'),
    
    # Catálogo y Carrito
    path('catalogo/', views.catalogo_view, name='catalogo'),
    path('producto/<int:producto_id>/', views.producto_detalle_view, name='producto_detalle'),
    path('carrito/agregar/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/quitar/', views.quitar_del_carrito, name='quitar_del_carrito'),
    path('carrito/obtener/', views.obtener_carrito, name='obtener_carrito'),
    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('procesar-pago/', views.procesar_pago, name='procesar_pago'),
    path('confirmacion-pedido/<int:pedido_id>/', views.confirmacion_pedido_view, name='confirmacion_pedido'),
    
    # Mis Pedidos
    path('mis-pedidos/', views.mis_pedidos_view, name='mis_pedidos'),
    path('mis-pedidos/detalle/<int:pedido_id>/', views.mis_pedidos_detalle_view, name='mis_pedidos_detalle'),
    
    # Inventario
    path('paneladmin/inventario/actualizar_stock/', views.actualizar_stock_general, name='actualizar_stock_general'),
    path('paneladmin/inventario/actualizar_stock_manual/', views.actualizar_stock_manual, name='actualizar_stock_manual'),
    path('paneladmin/registro-ventas/registrar-manual/', views.registrar_venta_manual, name='registrar_venta_manual'),
    path('paneladmin/registro-ventas/reparar/', views.reparar_registros_ventas, name='reparar_registros_ventas'),

    #stripe
    path('crear-sesion-pago/', views.crear_sesion_pago_stripe, name='crear_sesion_pago'),
    path('pago-exitoso/<int:pedido_id>/', views.pago_exitoso, name='pago_exitoso'),
    path('pago-cancelado/<int:pedido_id>/', views.pago_cancelado, name='pago_cancelado'),
    path('stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('paneladmin/registro-ventas/sincronizar-stripe/', views.sincronizar_ventas_stripe, name='sincronizar_ventas_stripe'),
    path('paneladmin/registro-ventas/registrar-manual/', views.registrar_venta_manual, name='registrar_venta_manual'),
]