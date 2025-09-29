from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

# Define un backend de autenticación personalizado para permitir el inicio de sesión con correo electrónico en lugar de nombre de usuario, extendiendo ModelBackend. Se integra con el modelo CustomUser para autenticar usuarios y recuperar información de usuario por ID, soportando el sistema de autenticación de la tienda en línea.
class EmailAuthBackend(ModelBackend):
    # Autentica a un usuario verificando su correo electrónico y contraseña. Busca un usuario en el modelo CustomUser por el correo proporcionado, verifica la contraseña con check_password, y devuelve el usuario si es válido. Retorna None si el usuario no existe o la contraseña es incorrecta. Usado por la vista login_view para autenticar usuarios.
    def authenticate(self, request, email=None, password=None, **kwargs):
        CustomUser = get_user_model()
        try:
            user = CustomUser.objects.get(email=email)
            if user.check_password(password):
                return user
        except CustomUser.DoesNotExist:
            return None
    
    # Recupera un usuario por su ID desde el modelo CustomUser. Devuelve el usuario si existe, o None si no se encuentra. Requerido por Django para mantener la sesión del usuario autenticado. Usado por el sistema de autenticación para verificar usuarios activos.
    def get_user(self, user_id):
        CustomUser = get_user_model()
        try:
            return CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return None