from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('form/', views.form_view, name='form'),
    path('logout/', views.logout_view, name='logout'),
    path('paneladmin', views.paneladmin_view, name='paneladmin'),
]