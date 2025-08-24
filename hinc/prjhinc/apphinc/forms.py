from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

CustomUser = get_user_model()

class CustomUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput, required=False, help_text="Deje en blanco para no cambiar la contraseña. Debe tener al menos 8 caracteres si se modifica.")
    password2 = forms.CharField(label="Confirmar Contraseña", widget=forms.PasswordInput, required=False, help_text="Confirme la nueva contraseña o déjelo en blanco.")

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email=email).exclude(id=self.instance.id if self.instance else None).exists():
            raise ValidationError("Este correo ya está registrado.")
        return email

    def clean_username(self):
        username = self.cleaned_data['username']
        if CustomUser.objects.filter(username=username).exclude(id=self.instance.id if self.instance else None).exists():
            raise ValidationError("Este usuario ya está registrado.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if self.instance.pk:  # Edición
            if password1 or password2:  # Si se proporciona alguna contraseña
                if password1 != password2:
                    raise ValidationError("Las contraseñas no coinciden.")
                if len(password1) < 8:
                    raise ValidationError("La contraseña debe tener al menos 8 caracteres.")
        else:  # Registro
            if not password1 or not password2:
                raise ValidationError("Debes proporcionar y confirmar una contraseña.")
            if password1 != password2:
                raise ValidationError("Las contraseñas no coinciden.")
            if len(password1) < 8:
                raise ValidationError("La contraseña debe tener al menos 8 caracteres.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password1")
        if password:  # Solo actualizar contraseña si se proporciona
            user.set_password(password)
        if commit:
            user.save()
        return user

class LoginForm(forms.Form):
    email = forms.EmailField(label="Correo", max_length=254)
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:ring-black focus:border-black'})
        self.fields['password'].widget.attrs.update({'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:ring-black focus:border-black'})

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            user = CustomUser.objects.filter(email=email).first()
            if not user:
                raise ValidationError("Correo no encontrado.")
            elif not user.check_password(password):
                raise ValidationError("Contraseña incorrecta.")
            elif user.estado != 'Habilitado':
                raise ValidationError("El usuario está inhabilitado.")
        return cleaned_data