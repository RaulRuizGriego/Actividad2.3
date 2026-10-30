from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("pacientes/", views.lista_pacientes, name="lista_pacientes"),
    path("pacientes/nuevo/", views.nuevo_paciente, name="nuevo_paciente"),
    path("pacientes/<int:id>/", views.detalle_paciente, name="detalle_paciente"),
    path("pacientes/<int:id>/editar/", views.editar_paciente, name="editar_paciente"),
    path("citas/", views.lista_citas, name="lista_citas"),
    path("citas/pendientes/", views.citas_pendientes, name="citas_pendientes"),
    path("citas/nueva/", views.nueva_cita, name="nueva_cita"),
    path("citas/<int:id>/editar/", views.editar_cita, name="editar_cita"),
    path("citas/<int:id>/cancelar/", views.cancelar_cita, name="cancelar_cita"),
    path("citas/<int:id>/eliminar/", views.eliminar_cita, name="eliminar_cita"),
]
