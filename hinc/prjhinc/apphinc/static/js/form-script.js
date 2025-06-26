const contenedor = document.getElementById('contenedor');
const botonRegistrar = document.getElementById('registrar');
const botonIniciar = document.getElementById('iniciar');

botonRegistrar.addEventListener('click', () => {
    contenedor.classList.add("activo");
});

botonIniciar.addEventListener('click', () => {
    contenedor.classList.remove("activo");
});

// Validaciones en tiempo real con mensajes
document.addEventListener('DOMContentLoaded', () => {
    const registroForm = document.querySelector('.registro form');
    const inputs = registroForm.querySelectorAll('input');

    const validadores = {
        'Usuario': {
            test: valor => /^[a-zA-Z0-9]+$/.test(valor),
            mensaje: 'Solo letras y números, sin espacios ni símbolos.'
        },
        'Correo': {
            test: valor => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(valor),
            mensaje: 'Debe tener el formato ejemplo@correo.com.'
        },
        'Contraseña': {
            test: valor => /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/.test(valor),
            mensaje: 'Mínimo 8 caracteres, una mayúscula, una minúscula y un número.'
        }
    };

    inputs.forEach(input => {
        // Crear elemento de mensaje si no existe
        let mensaje = document.createElement('div');
        mensaje.className = 'mensaje-error';
        input.insertAdjacentElement('afterend', mensaje);

        input.addEventListener('input', () => {
            const placeholder = input.placeholder;
            const validador = validadores[placeholder];
            const esValido = validador.test(input.value);

            if (input.value === '') {
                input.classList.remove('valido', 'invalido');
                mensaje.style.display = 'none';
                return;
            }

            if (esValido) {
                input.classList.add('valido');
                input.classList.remove('invalido');
                mensaje.style.display = 'none';
            } else {
                input.classList.add('invalido');
                input.classList.remove('valido');
                mensaje.textContent = validador.mensaje;
                mensaje.style.display = 'block';
            }
        });
    });

    registroForm.addEventListener('submit', e => {
        e.preventDefault();
        let todosValidos = true;

        inputs.forEach(input => {
            const placeholder = input.placeholder;
            const validador = validadores[placeholder];
            const esValido = validador.test(input.value);

            if (!esValido) {
                input.classList.add('invalido');
                input.nextElementSibling.textContent = validador.mensaje;
                input.nextElementSibling.style.display = 'block';
                todosValidos = false;
            } else {
                input.classList.add('valido');
                input.nextElementSibling.style.display = 'none';
            }
        });

        if (todosValidos) {
            Swal.fire({
                icon: 'success',
                title: 'Registro exitoso',
                text: '¡Bienvenido a Hinc!',
                confirmButtonColor: '#000'
            });
            registroForm.reset();
            inputs.forEach(input => {
                input.classList.remove('valido', 'invalido');
                input.nextElementSibling.style.display = 'none';
            });
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Campos inválidos',
                text: 'Revisa los datos e inténtalo de nuevo',
                confirmButtonColor: '#000'
            });
        }
    });
});