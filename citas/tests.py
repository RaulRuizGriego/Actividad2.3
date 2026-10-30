from datetime import timedelta

from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Cita, Paciente


def datos_paciente(**cambios):
    datos = {
        "nombre": "Mariana",
        "apellido": "Salinas",
        "edad": "30",
        "telefono": "6641234567",
        "correo": "mariana@correo.com",
    }
    datos.update(cambios)
    return datos


class BaseCitas(TestCase):
    def setUp(self):
        self.paciente = Paciente.objects.create(
            nombre="Ana", apellido="López", edad=34,
            telefono="6641000001", correo="ana@correo.com",
        )
        self.manana = timezone.localdate() + timedelta(days=1)

    def datos_cita(self, **cambios):
        datos = {
            "paciente": self.paciente.id,
            "fecha": self.manana.isoformat(),
            "hora": "10:00",
            "motivo": "Consulta general de rutina",
            "estado": Cita.PENDIENTE,
        }
        datos.update(cambios)
        return datos

    def crear_cita(self, **cambios):
        campos = {
            "paciente": self.paciente,
            "fecha": self.manana,
            "hora": "10:00",
            "motivo": "Consulta general de rutina",
            "estado": Cita.CONFIRMADA,
        }
        campos.update(cambios)
        return Cita.objects.create(**campos)

    def mensajes(self, respuesta):
        return [str(m) for m in get_messages(respuesta.wsgi_request)]


class PruebasPacientes(BaseCitas):
    # Prueba 1
    def test_registrar_paciente_valido(self):
        r = self.client.post(reverse("nuevo_paciente"), datos_paciente())
        self.assertEqual(Paciente.objects.count(), 2)
        self.assertEqual(r.status_code, 302)
        self.assertIn("Paciente registrado correctamente.", self.mensajes(r))

    # Prueba 2
    def test_edad_negativa_muestra_error(self):
        r = self.client.post(reverse("nuevo_paciente"), datos_paciente(edad="-5"))
        self.assertEqual(Paciente.objects.count(), 1)
        self.assertContains(r, "La edad debe estar entre 1 y 120 años.")

    # Prueba 3
    def test_telefono_de_8_digitos_muestra_error(self):
        r = self.client.post(reverse("nuevo_paciente"), datos_paciente(telefono="66412345"))
        self.assertEqual(Paciente.objects.count(), 1)
        self.assertContains(r, "exactamente 10 dígitos numéricos")

    def test_telefono_con_letras_muestra_error(self):
        r = self.client.post(reverse("nuevo_paciente"), datos_paciente(telefono="66412345ab"))
        self.assertContains(r, "exactamente 10 dígitos numéricos")

    def test_edad_mayor_a_120_muestra_error(self):
        r = self.client.post(reverse("nuevo_paciente"), datos_paciente(edad="121"))
        self.assertContains(r, "La edad debe estar entre 1 y 120 años.")

    def test_nombre_y_apellido_minimo_3_caracteres(self):
        r = self.client.post(
            reverse("nuevo_paciente"), datos_paciente(nombre="Al", apellido=" Z ")
        )
        self.assertContains(r, "El nombre debe tener al menos 3 caracteres.")
        self.assertContains(r, "El apellido debe tener al menos 3 caracteres.")

    def test_correo_invalido_muestra_error(self):
        r = self.client.post(reverse("nuevo_paciente"), datos_paciente(correo="no-es-correo"))
        self.assertContains(r, "formato válido")

    def test_campos_obligatorios(self):
        r = self.client.post(reverse("nuevo_paciente"), {})
        self.assertContains(r, "El nombre es obligatorio.")
        self.assertContains(r, "El apellido es obligatorio.")
        self.assertContains(r, "La edad es obligatoria.")
        self.assertContains(r, "El teléfono es obligatorio.")

    def test_editar_paciente(self):
        r = self.client.post(
            reverse("editar_paciente", args=[self.paciente.id]),
            datos_paciente(nombre="Anita"),
        )
        self.paciente.refresh_from_db()
        self.assertEqual(self.paciente.nombre, "Anita")
        self.assertIn("Paciente actualizado correctamente.", self.mensajes(r))


class PruebasCitas(BaseCitas):
    # Prueba 4
    def test_cita_con_fecha_anterior_muestra_error(self):
        ayer = timezone.localdate() - timedelta(days=1)
        r = self.client.post(reverse("nueva_cita"), self.datos_cita(fecha=ayer.isoformat()))
        self.assertEqual(Cita.objects.count(), 0)
        self.assertContains(r, "No se pueden registrar citas en fechas anteriores a la actual.")

    # Prueba 5
    def test_cita_con_horario_ocupado_muestra_error(self):
        self.crear_cita(estado=Cita.CONFIRMADA)
        r = self.client.post(reverse("nueva_cita"), self.datos_cita(estado=Cita.PENDIENTE))
        self.assertEqual(Cita.objects.count(), 1)
        self.assertIn(
            "No es posible registrar la cita: el horario seleccionado ya está ocupado.",
            self.mensajes(r),
        )
        self.assertContains(r, "Ese horario ya tiene una cita activa")

    # Prueba 6
    def test_registrar_cita_valida(self):
        r = self.client.post(reverse("nueva_cita"), self.datos_cita())
        self.assertEqual(Cita.objects.count(), 1)
        self.assertRedirects(r, reverse("lista_citas"))
        self.assertIn("Cita médica registrada correctamente.", self.mensajes(r))

    # Prueba 7
    def test_editar_cita_existente(self):
        cita = self.crear_cita(estado=Cita.PENDIENTE)
        r = self.client.post(
            reverse("editar_cita", args=[cita.id]),
            self.datos_cita(hora="11:30", motivo="Seguimiento del tratamiento", estado=Cita.CONFIRMADA),
        )
        cita.refresh_from_db()
        self.assertEqual(cita.hora.strftime("%H:%M"), "11:30")
        self.assertEqual(cita.estado, Cita.CONFIRMADA)
        self.assertIn("Cita médica actualizada correctamente.", self.mensajes(r))

    def test_editar_cita_sin_cambiar_horario_no_choca_consigo_misma(self):
        cita = self.crear_cita()
        r = self.client.post(
            reverse("editar_cita", args=[cita.id]),
            self.datos_cita(motivo="Motivo actualizado de la cita"),
        )
        self.assertEqual(r.status_code, 302)

    # Prueba 8
    def test_cancelar_cita_cambia_estado(self):
        cita = self.crear_cita()
        r = self.client.post(reverse("cancelar_cita", args=[cita.id]))
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.CANCELADA)
        self.assertIn("La cita ha sido cancelada correctamente.", self.mensajes(r))

    # Prueba 9
    def test_eliminar_cita_borra_registro(self):
        cita = self.crear_cita()
        r = self.client.post(reverse("eliminar_cita", args=[cita.id]))
        self.assertFalse(Cita.objects.filter(id=cita.id).exists())
        self.assertIn("La cita ha sido eliminada correctamente.", self.mensajes(r))

    # ---- Validaciones adicionales ----
    def test_cita_cancelada_no_bloquea_horario(self):
        self.crear_cita(estado=Cita.CANCELADA)
        r = self.client.post(reverse("nueva_cita"), self.datos_cita())
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Cita.objects.count(), 2)

    def test_dos_citas_pendientes_mismo_horario_no_se_permiten(self):
        self.crear_cita(estado=Cita.PENDIENTE)
        self.client.post(reverse("nueva_cita"), self.datos_cita(estado=Cita.CONFIRMADA))
        self.assertEqual(Cita.objects.count(), 1)

    def test_reactivar_cita_cancelada_en_horario_ocupado_se_rechaza(self):
        self.crear_cita(estado=Cita.CONFIRMADA)
        cancelada = self.crear_cita(estado=Cita.CANCELADA)
        self.client.post(
            reverse("editar_cita", args=[cancelada.id]),
            self.datos_cita(estado=Cita.PENDIENTE),
        )
        cancelada.refresh_from_db()
        self.assertEqual(cancelada.estado, Cita.CANCELADA)

    def test_hora_fuera_de_horario(self):
        for hora in ("07:59", "18:01", "22:00"):
            r = self.client.post(reverse("nueva_cita"), self.datos_cita(hora=hora))
            self.assertContains(r, "8:00 a 18:00")
        self.assertEqual(Cita.objects.count(), 0)

    def test_hora_limites_permitidos(self):
        for hora in ("08:00", "18:00"):
            self.client.post(reverse("nueva_cita"), self.datos_cita(hora=hora))
        self.assertEqual(Cita.objects.count(), 2)

    def test_motivo_menor_a_10_caracteres(self):
        r = self.client.post(reverse("nueva_cita"), self.datos_cita(motivo="Dolor"))
        self.assertContains(r, "al menos 10 caracteres")

    def test_paciente_inexistente(self):
        r = self.client.post(reverse("nueva_cita"), self.datos_cita(paciente=9999))
        self.assertContains(r, "previamente registrado")
        self.assertEqual(Cita.objects.count(), 0)

    def test_estado_invalido(self):
        r = self.client.post(reverse("nueva_cita"), self.datos_cita(estado="Reprogramada"))
        self.assertContains(r, "Pendiente, Confirmada o Cancelada")
        self.assertEqual(Cita.objects.count(), 0)


class PruebasSeguridad(BaseCitas):
    def test_cancelar_y_eliminar_exigen_post(self):
        cita = self.crear_cita()
        for nombre in ("cancelar_cita", "eliminar_cita"):
            self.assertEqual(self.client.get(reverse(nombre, args=[cita.id])).status_code, 405)
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.CONFIRMADA)

    def test_proteccion_csrf(self):
        cita = self.crear_cita()
        seguro = Client(enforce_csrf_checks=True)
        for nombre in ("cancelar_cita", "eliminar_cita"):
            self.assertEqual(seguro.post(reverse(nombre, args=[cita.id])).status_code, 403)
        self.assertEqual(
            seguro.post(reverse("nuevo_paciente"), datos_paciente()).status_code, 403
        )
        self.assertTrue(Cita.objects.filter(id=cita.id).exists())

    def test_formularios_incluyen_token_csrf(self):
        for url in (reverse("nuevo_paciente"), reverse("nueva_cita")):
            self.assertContains(self.client.get(url), "csrfmiddlewaretoken")

    def test_redireccion_next_no_permite_sitios_externos(self):
        cita = self.crear_cita()
        r = self.client.post(
            reverse("cancelar_cita", args=[cita.id]), {"next": "https://sitio-malicioso.com/"}
        )
        self.assertEqual(r["Location"], reverse("lista_citas"))
