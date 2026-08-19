import os
import time
import requests
from datetime import datetime, timedelta

# ==========================================
# CONFIGURACIÓN Y CREDENCIALES
# ==========================================
TELEGRAM_TOKEN = "8679048960:AAHNy7YqRGx1Bt-oeKCr9xP29h0L-BnBE1M"
TELEGRAM_CHAT_ID = "8295036704"

NOMBRE_POLIDEPORTIVO = "Polideportivo Onega"
SEDE_ID = "2280"

# IDs de servicio activos conocidos y rango de reserva para Onega
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
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN.startswith("COLOCA_AQUI"):
        print("❌ Error: Debes ingresar tu TELEGRAM_TOKEN en el archivo main.py.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
    try:
        res = requests.post(url, json=payload, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"❌ Error enviando a Telegram: {e}")
        return False


def extraer_horas_validas(lista_datos):
    """
    Valida estrictamente que los elementos recibidos sean cadenas de tiempo/ISO reales.
    Filtra objetos estructurados o metadatos falsos.
    """
    horas_validas = []
    
    if not isinstance(lista_datos, list):
        return horas_validas

    for item in lista_datos:
        if not isinstance(item, str):
            continue

        item_str = item.strip()
        
        # Formato ISO tipico de SIGECI: 2026-08-22T08:30:00 o HH:MM:SS
        if "T" in item_str:
            try:
                dt_hora = datetime.strptime(item_str.split(".")[0], "%Y-%m-%dT%H:%M:%S")
                horas_validas.append(dt_hora.strftime("%H:%M hs"))
            except ValueError:
                pass
        elif ":" in item_str and len(item_str) <= 8:
            try:
                partes = item_str.split(":")
                hora_str = f"{int(partes[0]):02d}:{int(partes[1]):02d} hs"
                horas_validas.append(hora_str)
            except ValueError:
                pass

    return horas_validas


def formatear_horarios(fecha_str, lista_iso):
    """Convierte fechas e ISOs validados a texto legible y claves de memoria."""
    horas_limpias = extraer_horas_validas(lista_iso)
    if not horas_limpias:
        return None, []

    claves_turnos = []
    try:
        dt_fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
        dia_nombre = DIAS_SEMANA.get(dt_fecha.strftime("%A"), dt_fecha.strftime("%A"))
        fecha_corta = dt_fecha.strftime("%d/%m")

        for h in horas_limpias:
            claves_turnos.append((fecha_str, h))

        texto = f"📅 <b>{dia_nombre} {fecha_corta}:</b> {', '.join(horas_limpias)}"
        return texto, claves_turnos
    except Exception:
        return None, []


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

                    if texto_linea and claves:
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
        return

    # Limpiar memoria de turnos tomados que ya no existen en la web
    turnos_a_remover = [
        t for t in TURNOS_NOTIFICADOS 
        if t.startswith(f"{servicio_id}|") and t not in turnos_visibles_hoy
    ]
    for t in turnos_a_remover:
        TURNOS_NOTIFICADOS.remove(t)

    # Notificar ÚNICAMENTE si hay turnos reales confirmados
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
            print(f"✅ ALERTA ENVIADA: {len(turnos_nuevos_detectados)} turnos reales en {nombre_cancha}.")
    elif lineas_resumen:
        print(f"ℹ️ {nombre_cancha}: Hay turnos libres pero ya fueron notificados.")
    else:
        print(f"ℹ️ {nombre_cancha}: Sin disponibilidad real.")


if __name__ == "__main__":
    print(f"🚀 Iniciando monitoreo estricto para {NOMBRE_POLIDEPORTIVO}...")

    enviar_mensaje_telegram(
        f"🚀 <b>Bot Activo:</b> Monitoreando disponibilidad en {NOMBRE_POLIDEPORTIVO}."
    )

    while True:
        try:
            for s_id in SERVICIOS_IDS:
                consultar_cancha(s_id)
                time.sleep(0.5)
        except Exception as main_e:
            print(f"❌ Error en el bucle principal: {main_e}")

        time.sleep(300)
