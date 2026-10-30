import re
from datetime import time

from django import forms
from django.utils import timezone

from .models import Cita, Paciente

HORA_APERTURA = time(8, 0)
HORA_CIERRE = time(18, 0)
ESTADOS_ACTIVOS = [Cita.PENDIENTE, Cita.CONFIRMADA]


class PacienteForm(forms.ModelForm):
    """Formulario para registrar y modificar pacientes (ModelForm)."""

    class Meta:
        model = Paciente
        fields = ["nombre", "apellido", "edad", "telefono", "correo"]
        labels = {
            "nombre": "Nombre",
            "apellido": "Apellido",
            "edad": "Edad",
            "telefono": "Teléfono",
            "correo": "Correo electrónico",
        }
        widgets = {
            "nombre": forms.TextInput(attrs={"placeholder": "Ej. Ana"}),
            "apellido": forms.TextInput(attrs={"placeholder": "Ej. López"}),
            "edad": forms.NumberInput(attrs={"placeholder": "1 a 120"}),
            "telefono": forms.TextInput(
                attrs={"type": "tel", "placeholder": "10 dígitos, ej. 6641234567"}
            ),
            "correo": forms.EmailInput(attrs={"placeholder": "nombre@correo.com"}),
        }
        error_messages = {
            "nombre": {"required": "El nombre es obligatorio."},
            "apellido": {"required": "El apellido es obligatorio."},
            "edad": {
                "required": "La edad es obligatoria.",
                "invalid": "Ingresa una edad válida (número entero).",
            },
            "telefono": {"required": "El teléfono es obligatorio."},
            "correo": {
                "required": "El correo electrónico es obligatorio.",
                "invalid": "Ingresa un correo electrónico con formato válido.",
            },
        }

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if len(nombre) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 caracteres.")
        return nombre

    def clean_apellido(self):
        apellido = self.cleaned_data["apellido"].strip()
        if len(apellido) < 3:
            raise forms.ValidationError("El apellido debe tener al menos 3 caracteres.")
        return apellido

    def clean_edad(self):
        edad = self.cleaned_data["edad"]
        if edad < 1 or edad > 120:
            raise forms.ValidationError("La edad debe estar entre 1 y 120 años.")
        return edad

    def clean_telefono(self):
        telefono = self.cleaned_data["telefono"].strip()
        # [0-9] (y no \d) para aceptar únicamente dígitos ASCII.
        if not re.fullmatch(r"[0-9]{10}", telefono):
            raise forms.ValidationError(
                "El teléfono debe tener exactamente 10 dígitos numéricos."
            )
        return telefono


class CitaForm(forms.ModelForm):
    """Formulario para registrar y modificar citas médicas (ModelForm)."""

    class Meta:
        model = Cita
        fields = ["paciente", "fecha", "hora", "motivo", "estado"]
        labels = {
            "paciente": "Paciente",
            "fecha": "Fecha",
            "hora": "Hora",
            "motivo": "Motivo de consulta",
            "estado": "Estado",
        }
        widgets = {
            "fecha": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "hora": forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
            "motivo": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Describe el motivo (mínimo 10 caracteres)"}
            ),
        }
        error_messages = {
            "paciente": {
                "required": "Selecciona un paciente.",
                "invalid_choice": "Selecciona un paciente previamente registrado.",
            },
            "fecha": {
                "required": "La fecha es obligatoria.",
                "invalid": "Ingresa una fecha válida.",
            },
            "hora": {
                "required": "La hora es obligatoria.",
                "invalid": "Ingresa una hora válida.",
            },
            "motivo": {"required": "El motivo de consulta es obligatorio."},
            "estado": {
                "required": "Selecciona un estado.",
                "invalid_choice": "El estado debe ser Pendiente, Confirmada o Cancelada.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.horario_ocupado = False
        self.fields["paciente"].empty_label = "— Selecciona un paciente —"
        self.fields["estado"].initial = Cita.PENDIENTE

    # ---- Validaciones por campo ----
    def clean_fecha(self):
        fecha = self.cleaned_data["fecha"]
        hoy = timezone.localdate()
        # Al editar, se permite conservar la fecha original aunque ya haya pasado;
        # solo se bloquea elegir una fecha anterior a hoy.
        fecha_original = self.instance.fecha if self.instance.pk else None
        if fecha < hoy and fecha != fecha_original:
            raise forms.ValidationError(
                "No se pueden registrar citas en fechas anteriores a la actual."
            )
        return fecha

    def clean_hora(self):
        hora = self.cleaned_data["hora"]
        if hora < HORA_APERTURA or hora > HORA_CIERRE:
            raise forms.ValidationError(
                "El horario de atención es de 8:00 a 18:00 horas."
            )
        return hora

    def clean_motivo(self):
        motivo = self.cleaned_data["motivo"].strip()
        if len(motivo) < 10:
            raise forms.ValidationError(
                "El motivo debe contener al menos 10 caracteres."
            )
        return motivo

    # ---- Validación de disponibilidad (ORM) ----
    def clean(self):
        cleaned = super().clean()
        fecha = cleaned.get("fecha")
        hora = cleaned.get("hora")
        estado = cleaned.get("estado")

        # Solo las citas activas (Pendiente / Confirmada) ocupan horario;
        # una cita Cancelada no bloquea ni es bloqueada.
        if fecha and hora and estado in ESTADOS_ACTIVOS:
            conflicto = Cita.objects.filter(
                fecha=fecha, hora=hora, estado__in=ESTADOS_ACTIVOS
            )
            if self.instance.pk:
                conflicto = conflicto.exclude(pk=self.instance.pk)
            if conflicto.exists():
                self.horario_ocupado = True
                self.add_error(
                    "hora", "Ese horario ya tiene una cita activa en la misma fecha."
                )
        return cleaned
