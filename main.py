import os
import time
import requests
from datetime import datetime, timedelta

# ==========================================
# CONFIGURACIÓN Y CREDENCIALES
# ==========================================
TELEGRAM_TOKEN = os.environ.get("8679048960:AAHNy7YqRGx1Bt-oeKCr9xP29h0L-BnBE1M")
TELEGRAM_CHAT_ID = os.environ.get("8295036704")

NOMBRE_POLIDEPORTIVO = "Polideportivo Onega"
SEDE_ID = "2280"

# Rango ampliado de IDs de servicio para cubrir todas las canchas de Onega
SERVICIOS_IDS = [
    "3135", "3136", "3137", "3138", "3139", "3140",
    "3150", "3151", "3152", "3153", "3154", "3155"
]

DIAS_A_CONSULTAR = 30
TURNOS_NOTIFICADOS = set()

DIAS_SEMANA = {
    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
}


def enviar_mensaje_telegram(mensaje):
    """Envía un mensaje a Telegram en formato HTML."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Error: Faltan TELEGRAM_TOKEN o TELEGRAM_CHAT_ID en Railway.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
    try:
        res = requests.post(url, json=payload, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}")
        return False


def formatear_horarios(fecha_str, lista_iso):
    """Convierte fechas ISO a texto legible y genera claves para la memoria."""
    lineas_texto = []
    claves_turnos = []

    try:
        dt_fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
        dia_nombre = DIAS_SEMANA.get(dt_fecha.strftime("%A"), dt_fecha.strftime("%A"))
        fecha_corta = dt_fecha.strftime("%d/%m")

        horas_limpias = []
        for item in lista_iso:
            try:
                dt_hora = datetime.strptime(str(item).split(".")[0], "%Y-%m-%dT%H:%M:%S")
                hora_str = dt_hora.strftime("%H:%M hs")
                horas_limpias.append(hora_str)
                claves_turnos.append((fecha_str, hora_str))
            except Exception:
                horas_limpias.append(str(item))
                claves_turnos.append((fecha_str, str(item)))

        texto = f"📅 <b>{dia_nombre} {fecha_corta}:</b> {', '.join(horas_limpias)}"
        return texto, claves_turnos
    except Exception as e:
        return f"📅 <b>{fecha_str}:</b> {lista_iso}", [(fecha_str, str(lista_iso))]


def consultar_cancha(servicio_id):
    global TURNOS_NOTIFICADOS

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    }

    nombre_cancha = f"Cancha (ID {servicio_id})"
    url_reserva = f"https://formulario-sigeci.buenosaires.gob.ar/AgendarTramite?idPrestacion={servicio_id}"

    hoy = datetime.now()
    lineas_resumen = []
    turnos_nuevos_detectados = []
    turnos_visibles_hoy = set()
    consulta_exitosa = False

    for i in range(DIAS_A_CONSULTAR):
        fecha_str = (hoy + timedelta(days=i)).strftime("%Y-%m-%d")

        api_url = "https://formulario-sigeci.buenosaires.gob.ar/getHorasDisp"
        params = {
            "day": fecha_str,
            "sedeId": SEDE_ID,
            "servicioId": servicio_id
        }

        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                try:
                    datos = response.json()
                    if isinstance(datos, list):
                        consulta_exitosa = True
                except Exception:
                    datos = []

                if datos and isinstance(datos, list) and len(datos) > 0:
                    texto_linea, claves = formatear_horarios(fecha_str, datos)

                    for f, h in claves:
                        clave_unica = f"{servicio_id}|{f}|{h}"
                        turnos_visibles_hoy.add(clave_unica)

                        if clave_unica not in TURNOS_NOTIFICADOS:
                            turnos_nuevos_detectados.append(clave_unica)

                    lineas_resumen.append(texto_linea)

        except Exception:
            pass

        time.sleep(0.05)

    if not consulta_exitosa:
        return  # Si el ID está inactivo en la API, se ignora en silencio

    # Limpiar memoria de turnos tomados
    turnos_a_remover = [
        t for t in TURNOS_NOTIFICADOS 
        if t.startswith(f"{servicio_id}|") and t not in turnos_visibles_hoy
    ]
    for t in turnos_a_remover:
        TURNOS_NOTIFICADOS.remove(t)

    # Notificar únicamente si hay turnos nuevos
    if turnos_nuevos_detectados:
        resumen_turnos = "\n".join(lineas_resumen)
        mensaje = (
            "🔔 <b>¡NUEVO TURNO DISPONIBLE EN CABA!</b> 🔔\n\n"
            f"📍 <b>Lugar:</b> {NOMBRE_POLIDEPORTIVO}\n"
            f"🎾 <b>Opción:</b> {nombre_cancha}\n\n"
            f"<b>Disponibilidad encontrada:</b>\n{resumen_turnos}\n\n"
            f"🔗 <a href='{url_reserva}'>RESERVAR AHORA EN SIGECI</a>"
        )
        if enviar_mensaje_telegram(mensaje):
            for t in turnos_nuevos_detectados:
                TURNOS_NOTIFICADOS.add(t)
            print(f"✅ ALERTA ENVIADA: {len(turnos_nuevos_detectados)} turnos nuevos en {nombre_cancha}.")
    elif lineas_resumen:
        print(f"ℹ️ {nombre_cancha}: Hay turnos libres pero ya fueron notificados.")
    else:
        print(f"ℹ️ {nombre_cancha}: Sin disponibilidad.")


if __name__ == "__main__":
    print(f"🚀 Iniciando monitoreo ampliado para {NOMBRE_POLIDEPORTIVO}...")

    enviar_mensaje_telegram(
        f"🚀 <b>Bot Activo:</b> Monitoreando catálogo completo de canchas en {NOMBRE_POLIDEPORTIVO}."
    )

    while True:
        try:
            for s_id in SERVICIOS_IDS:
                consultar_cancha(s_id)
                time.sleep(0.5)
        except Exception as main_e:
            print(f"❌ Error en el bucle principal: {main_e}")

        time.sleep(300)
