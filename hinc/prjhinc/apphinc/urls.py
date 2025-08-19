from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('form/', views.form_view, name='form'),
    path('logout/', views.logout_view, name='logout'),
    path('paneladmin/', views.paneladmin_view, name='paneladmin'),
    path('paneladmin/add/', views.add_user, name='add_user'),
    path('paneladmin/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('paneladmin/delete/<int:user_id>/', views.delete_user, name='delete_user'),
]