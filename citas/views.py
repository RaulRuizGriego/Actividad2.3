from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import CitaForm, PacienteForm
from .models import Cita, Paciente


def inicio(request):
    pendientes = Cita.objects.select_related("paciente").filter(estado=Cita.PENDIENTE)
    contexto = {
        "total_pacientes": Paciente.objects.count(),
        "total_citas": Cita.objects.count(),
        "total_pendientes": pendientes.count(),
        "total_confirmadas": Cita.objects.filter(estado=Cita.CONFIRMADA).count(),
        "proximas": pendientes[:3],
    }
    return render(request, "citas/inicio.html", contexto)


def lista_pacientes(request):
    q = request.GET.get("q", "").strip()
    pacientes = Paciente.objects.all()
    if q:
        pacientes = pacientes.filter(Q(nombre__icontains=q) | Q(apellido__icontains=q))
    return render(
        request, "citas/pacientes_lista.html", {"pacientes": pacientes, "q": q}
    )


def detalle_paciente(request, id):
    paciente = get_object_or_404(Paciente, id=id)
    citas = paciente.citas.all()
    return render(
        request,
        "citas/paciente_detalle.html",
        {"paciente": paciente, "citas": citas},
    )


def lista_citas(request):
    citas = Cita.objects.select_related("paciente").all()
    return render(
        request,
        "citas/citas_lista.html",
        {
            "citas": citas,
            "titulo": "Agenda general",
            "descripcion": "Todas las citas programadas, agrupadas por día.",
        },
    )


def citas_pendientes(request):
    citas = Cita.objects.select_related("paciente").filter(estado=Cita.PENDIENTE)
    return render(
        request,
        "citas/citas_lista.html",
        {
            "citas": citas,
            "titulo": "Citas pendientes",
            "descripcion": "Citas que aún esperan confirmación.",
        },
    )


# ---------------------------------------------------------------------------
# CRUD de pacientes
# ---------------------------------------------------------------------------
def nuevo_paciente(request):
    if request.method == "POST":
        form = PacienteForm(request.POST)
        if form.is_valid():
            paciente = form.save()
            messages.success(request, "Paciente registrado correctamente.")
            return redirect("detalle_paciente", id=paciente.id)
        messages.error(request, "No se pudo registrar al paciente: revisa los errores.")
    else:
        form = PacienteForm()
    return render(
        request,
        "citas/paciente_form.html",
        {"form": form, "titulo": "Nuevo paciente", "boton": "Registrar paciente"},
    )


def editar_paciente(request, id):
    paciente = get_object_or_404(Paciente, id=id)
    if request.method == "POST":
        form = PacienteForm(request.POST, instance=paciente)
        if form.is_valid():
            form.save()
            messages.success(request, "Paciente actualizado correctamente.")
            return redirect("detalle_paciente", id=paciente.id)
        messages.error(request, "No se pudo actualizar al paciente: revisa los errores.")
    else:
        form = PacienteForm(instance=paciente)
    return render(
        request,
        "citas/paciente_form.html",
        {
            "form": form,
            "paciente": paciente,
            "titulo": "Editar paciente",
            "boton": "Guardar cambios",
        },
    )


# ---------------------------------------------------------------------------
# CRUD de citas
# ---------------------------------------------------------------------------
def _destino(request, por_defecto="lista_citas"):
    """Devuelve la página a la que regresar tras cancelar/eliminar (segura)."""
    siguiente = request.POST.get("next", "")
    if siguiente and url_has_allowed_host_and_scheme(
        siguiente, allowed_hosts={request.get_host()}
    ):
        return redirect(siguiente)
    return redirect(por_defecto)


def nueva_cita(request):
    if request.method == "POST":
        form = CitaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cita médica registrada correctamente.")
            return redirect("lista_citas")
        if form.horario_ocupado:
            messages.error(
                request,
                "No es posible registrar la cita: el horario seleccionado ya está ocupado.",
            )
        else:
            messages.error(request, "No se pudo registrar la cita: revisa los errores.")
    else:
        initial = {}
        paciente_id = request.GET.get("paciente")
        if paciente_id and paciente_id.isdigit():
            initial["paciente"] = paciente_id
        form = CitaForm(initial=initial)
    return render(
        request,
        "citas/cita_form.html",
        {"form": form, "titulo": "Programar cita", "boton": "Registrar cita"},
    )


def editar_cita(request, id):
    cita = get_object_or_404(Cita, id=id)
    if request.method == "POST":
        form = CitaForm(request.POST, instance=cita)
        if form.is_valid():
            form.save()
            messages.success(request, "Cita médica actualizada correctamente.")
            return redirect("lista_citas")
        if form.horario_ocupado:
            messages.error(
                request,
                "No es posible actualizar la cita: el horario seleccionado ya está ocupado.",
            )
        else:
            messages.error(request, "No se pudo actualizar la cita: revisa los errores.")
    else:
        form = CitaForm(instance=cita)
    return render(
        request,
        "citas/cita_form.html",
        {
            "form": form,
            "cita": cita,
            "titulo": "Editar cita",
            "boton": "Guardar cambios",
        },
    )


@require_POST
def cancelar_cita(request, id):
    cita = get_object_or_404(Cita, id=id)
    if cita.estado == Cita.CANCELADA:
        messages.info(request, "La cita ya se encontraba cancelada.")
    else:
        cita.estado = Cita.CANCELADA
        cita.save(update_fields=["estado"])
        messages.success(request, "La cita ha sido cancelada correctamente.")
    return _destino(request)


@require_POST
def eliminar_cita(request, id):
    cita = get_object_or_404(Cita, id=id)
    cita.delete()
    messages.success(request, "La cita ha sido eliminada correctamente.")
    return _destino(request)
