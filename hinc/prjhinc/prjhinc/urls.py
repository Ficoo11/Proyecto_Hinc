"""
URL configuration for prjhinc project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Define las rutas URL principales del proyecto Django 'prjhinc', actuando como el punto de entrada para el enrutamiento de URLs. Mapea URLs a vistas o incluye otras configuraciones de URLs de aplicaciones específicas. Incluye rutas para el panel de administración de Django, autenticación con django-allauth (como inicio de sesión con Google), y las rutas de la aplicación 'apphinc' (que contiene la lógica de la tienda en línea). En modo DEBUG, sirve archivos multimedia y estáticos directamente desde las rutas configuradas en settings.py, facilitando el desarrollo al mostrar imágenes y estilos sin necesidad de un servidor externo.
urlpatterns = [
    # Ruta para el panel de administración de Django ('admin/'), que proporciona una interfaz para gestionar modelos (como CustomUser, Producto, Categoria) directamente en la base de datos. Accesible solo para superusuarios.
    path('admin/', admin.site.urls),
    
    # Ruta para las URLs de django-allauth ('accounts/'), que maneja autenticación social (como Google) y otras funcionalidades de autenticación avanzadas. Incluye rutas como /accounts/google/login/ para inicio de sesión con cuentas externas.
    path('accounts/', include('allauth.urls')),
    
    # Ruta raíz ('') que incluye todas las URLs definidas en apphinc/urls.py, delegando el enrutamiento de la tienda en línea (página principal, autenticación, panel de administración, catálogo, carrito) a la aplicación apphinc.
    path('', include('apphinc.urls')),
]

# En modo DEBUG, agrega rutas para servir archivos multimedia (como imágenes de productos y categorías) desde MEDIA_URL y MEDIA_ROOT, y archivos estáticos (como CSS y JavaScript) desde STATIC_URL y el directorio apphinc/static. Esto simplifica el desarrollo al evitar la configuración de un servidor externo para estos archivos.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / 'apphinc' / 'static')