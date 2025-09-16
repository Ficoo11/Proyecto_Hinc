from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('paneladmin/', views.paneladmin_view, name='paneladmin'),
    path('paneladmin/add/', views.add_user, name='add_user'),
    path('paneladmin/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('paneladmin/delete/<int:user_id>/', views.delete_user, name='delete_user'),
    path('paneladmin/user-dashboard/', views.user_dashboard, name='user_dashboard'),
    path('paneladmin/productos/', views.productos_list, name='productos_list'),
    path('paneladmin/productos/create/', views.productos_create, name='productos_create'),
    path('paneladmin/productos/update/<int:producto_id>/', views.productos_update, name='productos_update'),
    path('paneladmin/productos/delete/<int:producto_id>/', views.productos_delete, name='productos_delete'),
    path('paneladmin/categorias/create/', views.categorias_create, name='categorias_create'),
    path('paneladmin/categorias/update/<int:categoria_id>/', views.categorias_update, name='categorias_update'),
    path('paneladmin/categorias/delete/<int:categoria_id>/', views.categorias_delete, name='categorias_delete'),
    path('catalogo/', views.catalogo_view, name='catalogo'),
    path('carrito/agregar/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/quitar/', views.quitar_del_carrito, name='quitar_del_carrito'),
    path('carrito/obtener/', views.obtener_carrito, name='obtener_carrito'),
    path('carrito/', views.ver_carrito, name='ver_carrito'),
    path('index2/', views.index2, name='index2'),
]