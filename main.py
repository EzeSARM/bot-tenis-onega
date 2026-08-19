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
SEDE_ID = "2280"  # Sede identificada para Onega

# CONFIGURACIÓN DE CANCHAS DE ONEGA
CANCHAS = [
    {
        "nombre": "Cancha 1",
        "servicio_id": "3151",  # Servicio identificado para la Cancha 1
        "url": "https://formulario-sigeci.buenosaires.gob.ar/AgendarTramite?idPrestacion=3151"
    },
    {
        "nombre": "Cancha 2",
        "servicio_id": "3152",  # Servicio correlativo para la Cancha 2
        "url": "https://formulario-sigeci.buenosaires.gob.ar/AgendarTramite?idPrestacion=3152"
    }
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


def consultar_cancha(cancha):
    global TURNOS_NOTIFICADOS

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    }

    hoy = datetime.now()
    lineas_resumen = []
    turnos_nuevos_detectados = []
    turnos_visibles_hoy = set()

    for i in range(DIAS_A_CONSULTAR):
        fecha_str = (hoy + timedelta(days=i)).strftime("%Y-%m-%d")

        api_url = "https://formulario-sigeci.buenosaires.gob.ar/getHorasDisp"
        params = {
            "day": fecha_str,
            "sedeId": SEDE_ID,
            "servicioId": cancha["servicio_id"]
        }

        try:
            response = requests.get(api_url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                try:
                    datos = response.json()
                except Exception:
                    datos = []

                if datos and isinstance(datos, list) and len(datos) > 0:
                    texto_linea, claves = formatear_horarios(fecha_str, datos)

                    for f, h in claves:
                        clave_unica = f"{cancha['nombre']}|{f}|{h}"
                        turnos_visibles_hoy.add(clave_unica)

                        if clave_unica not in TURNOS_NOTIFICADOS:
                            turnos_nuevos_detectados.append(clave_unica)

                    lineas_resumen.append(texto_linea)

        except Exception as e:
            print(f"Error consultando {cancha['nombre']} ({fecha_str}): {e}")

        time.sleep(0.1)

    # Limpiar de la memoria los turnos que ya fueron tomados
    turnos_a_remover = [
        t for t in TURNOS_NOTIFICADOS 
        if t.startswith(f"{cancha['nombre']}|") and t not in turnos_visibles_hoy
    ]
    for t in turnos_a_remover:
        TURNOS_NOTIFICADOS.remove(t)

    # Enviar alerta únicamente si hay turnos nuevos
    if turnos_nuevos_detectados:
        resumen_turnos = "\n".join(lineas_resumen)
        mensaje = (
            "🔔 <b>¡NUEVO TURNO DISPONIBLE EN CABA!</b> 🔔\n\n"
            f"📍 <b>Lugar:</b> {NOMBRE_POLIDEPORTIVO}\n"
            f"🎾 <b>Cancha:</b> {cancha['nombre']}\n\n"
            f"<b>Disponibilidad encontrada:</b>\n{resumen_turnos}\n\n"
            f"🔗 <a href='{cancha['url']}'>RESERVAR AHORA EN SIGECI</a>"
        )
        if enviar_mensaje_telegram(mensaje):
            for t in turnos_nuevos_detectados:
                TURNOS_NOTIFICADOS.add(t)
            print(f"✅ ALERTA ENVIADA: {len(turnos_nuevos_detectados)} turnos nuevos en {cancha['nombre']}.")
    elif lineas_resumen:
        print(f"ℹ️ {cancha['nombre']} ({NOMBRE_POLIDEPORTIVO}): Hay turnos libres pero ya fueron notificados.")
    else:
        print(f"ℹ️ {cancha['nombre']} ({NOMBRE_POLIDEPORTIVO}): Sin disponibilidad.")


if __name__ == "__main__":
    nombres_canchas = ", ".join([c["nombre"] for c in CANCHAS])
    print(f"🚀 Iniciando monitoreo de {NOMBRE_POLIDEPORTIVO} ({nombres_canchas})...")

    enviar_mensaje_telegram(
        f"🚀 <b>Bot Activo:</b> Monitoreando {NOMBRE_POLIDEPORTIVO} ({nombres_canchas}) sin alertas repetidas cada 5 minutos."
    )

    while True:
        try:
            for cancha in CANCHAS:
                consultar_cancha(cancha)
                time.sleep(1)
        except Exception as main_e:
            print(f"❌ Error en el bucle principal: {main_e}")

        time.sleep(300)  # Chequeo cada 5 minutos
