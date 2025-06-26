from django.urls import path
from . import views 
from .views import index, login_view, register_view, logout_view, form_view

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),      # Login
    path('register/', views.register_view, name='register'),  # Registro
    path('logout/', views.logout_view, name='logout'),   # Logout
    path('form/', form_view, name='form')
]