from django.contrib import admin

from .models import Cita, Paciente


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "apellido", "edad", "telefono", "correo")
    search_fields = ("nombre", "apellido")


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ("paciente", "fecha", "hora", "motivo", "estado")
    list_filter = ("estado", "fecha")
    search_fields = ("paciente__nombre", "paciente__apellido", "motivo")
