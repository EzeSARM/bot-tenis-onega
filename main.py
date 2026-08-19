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

# IDs de servicios a monitorear
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


def obtener_fechas_disponibles(servicio_id, headers):
    """
    Paso 1: Consulta los días que REALMENTE tienen disponibilidad en la web.
    Evita consultar días sin cupo que devuelven horarios fantasma.
    """
    hoy = datetime.now()
    mes_actual = hoy.strftime("%Y-%m")
    mes_siguiente = (hoy + timedelta(days=30)).strftime("%Y-%m")

    fechas_validas = set()

    for mes in list(dict.fromkeys([mes_actual, mes_siguiente])):
        # Intentar endpoints conocidos de fechas de SIGECI
        for endpoint in ["getFechasDisp", "getDiasDisp"]:
            api_url = f"https://formulario-sigeci.buenosaires.gob.ar/{endpoint}"
            params = {
                "month": mes,
                "sedeId": SEDE_ID,
                "servicioId": servicio_id
            }
            try:
                res = requests.get(api_url, headers=headers, params=params, timeout=8)
                if res.status_code == 200:
                    datos = res.json()
                    if isinstance(datos, list):
                        for item in datos:
                            if isinstance(item, str) and len(item) >= 10:
                                fechas_validas.add(item[:10])
                            elif isinstance(item, dict) and "fecha" in item:
                                fechas_validas.add(str(item["fecha"])[:10])
            except Exception:
                pass

    return sorted(list(fechas_validas))


def extraer_horas_validas(lista_datos):
    """Filtra y valida los bloques de hora recibidos."""
    horas_validas = []
    if not isinstance(lista_datos, list):
        return horas_validas

    for item in lista_datos:
        item_str = str(item).strip()
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


def consultar_cancha(servicio_id):
    global TURNOS_NOTIFICADOS

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    }

    nombre_cancha = f"Cancha (ID {servicio_id})"
    url_reserva = f"https://formulario-sigeci.buenosaires.gob.ar/AgendarTramite?idPrestacion={servicio_id}"

    # Paso 1: Filtrar primero solo las fechas con disponibilidad real reportada por el calendario
    fechas_disponibles = obtener_fechas_disponibles(servicio_id, headers)

    # Si getFechasDisp no devolvió fechas pero queremos fallback controlado por días
    hoy = datetime.now()
    fechas_a_revisar = fechas_disponibles if fechas_disponibles else [
        (hoy + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(DIAS_A_CONSULTAR)
    ]

    lineas_resumen = []
    turnos_nuevos_detectados = []
    turnos_visibles_hoy = set()
    hay_turnos_reales = False

    # Paso 2: Consultar únicamente los horarios para las fechas filtradas
    for fecha_str in fechas_a_revisar:
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
                except Exception:
                    datos = []

                if datos and isinstance(datos, list):
                    horas_limpias = extraer_horas_validas(datos)

                    if horas_limpias:
                        hay_turnos_reales = True
                        try:
                            dt_fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
                            dia_nombre = DIAS_SEMANA.get(dt_fecha.strftime("%A"), dt_fecha.strftime("%A"))
                            fecha_corta = dt_fecha.strftime("%d/%m")
                            texto_linea = f"📅 <b>{dia_nombre} {fecha_corta}:</b> {', '.join(horas_limpias)}"
                        except Exception:
                            texto_linea = f"📅 <b>{fecha_str}:</b> {', '.join(horas_limpias)}"

                        for h in horas_limpias:
                            clave_unica = f"{servicio_id}|{fecha_str}|{h}"
                            turnos_visibles_hoy.add(clave_unica)

                            if clave_unica not in TURNOS_NOTIFICADOS:
                                turnos_nuevos_detectados.append(clave_unica)

                        lineas_resumen.append(texto_linea)
        except Exception:
            pass

        time.sleep(0.05)

    # Limpiar memoria de turnos viejos
    turnos_a_remover = [
        t for t in TURNOS_NOTIFICADOS 
        if t.startswith(f"{servicio_id}|") and t not in turnos_visibles_hoy
    ]
    for t in turnos_a_remover:
        TURNOS_NOTIFICADOS.remove(t)

    # Notificación a Telegram
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
    elif hay_turnos_reales:
        print(f"ℹ️ {nombre_cancha}: Hay turnos libres pero ya fueron notificados.")
    else:
        print(f"ℹ️ {nombre_cancha}: Sin disponibilidad real.")


if __name__ == "__main__":
    print(f"🚀 Iniciando monitoreo en 2 pasos para {NOMBRE_POLIDEPORTIVO}...")

    enviar_mensaje_telegram(
        f"🚀 <b>Bot Activo:</b> Monitoreando disponibilidad verificada en {NOMBRE_POLIDEPORTIVO}."
    )

    while True:
        try:
            for s_id in SERVICIOS_IDS:
                consultar_cancha(s_id)
                time.sleep(0.5)
        except Exception as main_e:
            print(f"❌ Error en el bucle principal: {main_e}")

        time.sleep(300)
