from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Producto, Categoria, StockTalla, Pedido

CustomUser = get_user_model()

class CustomUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput, required=False, help_text="Deje en blanco para no cambiar la contraseña. Debe tener al menos 8 caracteres si se modifica.")
    password2 = forms.CharField(label="Confirmar Contraseña", widget=forms.PasswordInput, required=False, help_text="Confirme la nueva contraseña o déjelo en blanco.")
    role = forms.ChoiceField(choices=[('Admin', 'Admin'), ('Usuario', 'Usuario')], required=True)
    estado = forms.ChoiceField(choices=[('Habilitado', 'Habilitado'), ('Inhabilitado', 'Inhabilitado')], required=True)
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2', 'role', 'estado')
    
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
        
        if self.instance.pk:
            if password1 or password2:
                if password1 != password2:
                    raise ValidationError("Las contraseñas no coinciden.")
                if len(password1) < 8:
                    raise ValidationError("La contraseña debe tener al menos 8 caracteres.")
        else:
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
        if password:
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

# NUEVO FORMULARIO PARA PERFIL
class PerfilForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'documento', 'genero', 'fecha_nacimiento', 'telefono_personal', 'foto_perfil']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:ring-black focus:border-black',
                'placeholder': 'Nombre'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:ring-black focus:border-black',
                'placeholder': 'Apellidos'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:ring-black focus:border-black',
                'placeholder': 'correo@ejemplo.com'
            }),
            'documento': forms.TextInput(attrs={
                'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:ring-black focus:border-black',
                'placeholder': 'Número de documento'
            }),
            'genero': forms.Select(attrs={
                'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:ring-black focus:border-black'
            }),
            'fecha_nacimiento': forms.DateInput(attrs={
                'type': 'date',
                'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:ring-black focus:border-black'
            }),
            'telefono_personal': forms.TextInput(attrs={
                'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:ring-black focus:border-black',
                'placeholder': '+57 300 123 4567'
            }),
            'foto_perfil': forms.FileInput(attrs={
                'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:ring-black focus:border-black'
            })
        }
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email=email).exclude(id=self.instance.id).exists():
            raise ValidationError("Este correo ya está registrado.")
        return email

class ProductoForm(forms.ModelForm):
    TALLAS_CHOICES = [
        ('XS', 'XS'),
        ('S', 'S'),
        ('M', 'M'),
        ('L', 'L'),
        ('XL', 'XL'),
        ('XXL', 'XXL'),
    ]
    tallas = forms.MultipleChoiceField(choices=TALLAS_CHOICES, widget=forms.CheckboxSelectMultiple, required=False)
    categoria = forms.ModelChoiceField(queryset=Categoria.objects.all(), required=False, empty_label="Seleccionar categoría")
    
    class Meta:
        model = Producto
        fields = ('nombre', 'precio', 'tallas', 'imagen', 'descripcion', 'categoria', 'descuento', 'estado', 'is_destacado')
    
    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        if precio < 0:
            raise ValidationError("El precio no puede ser negativo.")
        return precio
    
    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')
        if imagen:
            if not imagen.name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                raise ValidationError("Solo se permiten archivos de imagen (jpg, jpeg, png, gif).")
        return imagen
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.tallas = ','.join(self.cleaned_data['tallas'])
        if commit:
            instance.save()
            for talla in self.cleaned_data['tallas']:
                StockTalla.objects.get_or_create(
                    producto=instance,
                    talla=talla,
                    defaults={'stock': 0}
                )
        return instance

class StockTallaForm(forms.ModelForm):
    stock_inicial = forms.IntegerField(
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'mt-1 p-2 w-full border border-gray-300 rounded-md focus:ring-black focus:border-black',
            'placeholder': 'Stock inicial'
        })
    )
    
    class Meta:
        model = StockTalla
        fields = ('stock', 'stock_inicial')
        widgets = {
            'stock': forms.NumberInput(attrs={
                'min': 0, 
                'class': 'mt-1 p-2 w-full border border-gray-300 rounded-md focus:ring-black focus:border-black'
            })
        }
    
    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock < 0:
            raise ValidationError("El stock no puede ser negativo.")
        return stock
    
    def clean_stock_inicial(self):
        stock_inicial = self.cleaned_data.get('stock_inicial')
        if stock_inicial is not None and stock_inicial < 0:
            raise ValidationError("El stock inicial no puede ser negativo.")
        return stock_inicial

class StockTallaInlineFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                stock = form.cleaned_data.get('stock')
                if stock is not None and stock < 0:
                    form.add_error('stock', "El stock no puede ser negativo.")

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ('nombre', 'descripcion', 'imagen')
    
    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if not nombre:
            raise ValidationError("El nombre no puede estar vacío.")
        return nombre
    
    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')
        if imagen:
            if not imagen.name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                raise ValidationError("Solo se permiten archivos de imagen (jpg, jpeg, png, gif).")
        return imagen

class InventoryForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ('descuento', 'estado')

class PedidoForm(forms.ModelForm):
    nombre_completo = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:ring-black focus:border-black',
            'placeholder': 'Nombre completo'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:ring-black focus:border-black',
            'placeholder': 'correo@ejemplo.com'
        })
    )
    telefono = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:ring-black focus:border-black',
            'placeholder': '+57 300 123 4567'
        })
    )
    direccion = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:ring-black focus:border-black',
            'placeholder': 'Dirección completa de envío',
            'rows': 3
        })
    )
    ciudad = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 p-3 w-full border border-gray-300 rounded-lg focus:ring-black focus:border-black',
            'placeholder': 'Ciudad'
        })
    )
    
    class Meta:
        model = Pedido
        fields = ['nombre_completo', 'email', 'telefono', 'direccion', 'ciudad']

        