from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('paneladmin/', views.paneladmin_view, name='paneladmin'),
    path('paneladmin/add/', views.add_user, name='add_user'),
    path('paneladmin/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('paneladmin/delete/<int:user_id>/', views.delete_user, name='delete_user'),
    path('user-dashboard/', views.user_dashboard, name='user_dashboard'),
    path('paneladmin/productos/create/', views.productos_create, name='productos_create'),
    path('paneladmin/productos/update/<int:producto_id>/', views.productos_update, name='productos_update'),
    path('paneladmin/productos/delete/<int:producto_id>/', views.productos_delete, name='productos_delete'),
    path('catalogo/', views.catalogo_view, name='catalogo'),
]