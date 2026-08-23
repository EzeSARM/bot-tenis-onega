import os
import time
import requests
from datetime import datetime, timedelta

# ==========================================
# CONFIGURACIÓN DEL POLIDEPORTIVO ONEGA
# ==========================================
NOMBRE_POLIDEPORTIVO = "Polideportivo Onega"
SERVICIO_ID = "3137"

CANCHAS = [
    {"id": "2289", "nombre": "Cancha 1"},
    {"id": "2290", "nombre": "Cancha 2"}
]

DIAS_A_CONSULTAR = 30

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8679048960:AAHNy7YqRGx1Bt-oeKCr9xP29h0L-BnBE1M")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8295036704")

DIAS_SEMANA = {
    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
}

LAST_UPDATE_ID = None

def enviar_notificacion_telegram(mensaje, chat_id=None):
    target_chat_id = chat_id or TELEGRAM_CHAT_ID
    if not TELEGRAM_TOKEN or not target_chat_id:
        print("❌ Error: Faltan credenciales de Telegram.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": target_chat_id,
        "text": mensaje,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"❌ Error al enviar mensaje por Telegram: {e}")
        return False

def crear_sesion_sigeci():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"https://formulario-sigeci.buenosaires.gob.ar/AgendarTramite?idPrestacion={SERVICIO_ID}&flow=primeros"
    })
    
    url_inicio = f"https://formulario-sigeci.buenosaires.gob.ar/AgendarTramite?idPrestacion={SERVICIO_ID}&flow=primeros"
    try:
        session.get(url_inicio, timeout=10)
    except Exception as e:
        print(f"⚠️ Aviso al inicializar sesión: {e}")
        
    return session

def extraer_horas_validas(lista_datos):
    horas_validas = []
    if not isinstance(lista_datos, list):
        return horas_validas

    for item in lista_datos:
        if not isinstance(item, str):
            continue

        item_str = item.strip()

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

    return sorted(list(set(horas_validas)))

def consultar_turnos_cancha(session, sede_id, fecha_str):
    url = "https://formulario-sigeci.buenosaires.gob.ar/getHorasDisp"
    params = {
        "day": fecha_str,
        "sedeId": sede_id,
        "servicioId": SERVICIO_ID
    }
    try:
        response = session.get(url, params=params, timeout=8)
        if response.status_code == 200:
            try:
                datos = response.json()
                return extraer_horas_validas(datos)
            except Exception:
                return []
    except Exception as e:
        print(f"Error al consultar sede {sede_id} para la fecha {fecha_str}: {e}")
    return []

def escanear_disponibilidad():
    """Realiza la consulta completa de turnos en SIGECI y devuelve el resultado formateado."""
    session = crear_sesion_sigeci()
    url_reserva = f"https://formulario-sigeci.buenosaires.gob.ar/AgendarTramite?idPrestacion={SERVICIO_ID}&flow=primeros"

    hoy = datetime.now()
    fechas_a_consultar = [(hoy + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(DIAS_A_CONSULTAR)]

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Escaneando turnos en {NOMBRE_POLIDEPORTIVO}...")

    lineas_notificacion = []

    for cancha in CANCHAS:
        for fecha in fechas_a_consultar:
            horas = consultar_turnos_cancha(session, cancha["id"], fecha)
            if horas:
                try:
                    dt_fecha = datetime.strptime(fecha, "%Y-%m-%d")
                    dia_nombre = DIAS_SEMANA.get(dt_fecha.strftime("%A"), dt_fecha.strftime("%A"))
                    fecha_corta = dt_fecha.strftime("%d/%m")
                    lineas_notificacion.append(
                        f"🎾 <b>{cancha['nombre']}</b> - 📅 <b>{dia_nombre} {fecha_corta}:</b> {', '.join(horas)}"
                    )
                except Exception:
                    lineas_notificacion.append(
                        f"🎾 <b>{cancha['nombre']}</b> - 📅 <b>{fecha}:</b> {', '.join(horas)}"
                    )

            time.sleep(0.05)

    if lineas_notificacion:
        resumen = "\n".join(lineas_notificacion)
        return (
            f"🔔 <b>¡TURNOS DISPONIBLES EN {NOMBRE_POLIDEPORTIVO.upper()}!</b> 🔔\n\n"
            f"{resumen}\n\n"
            f"🔗 <a href='{url_reserva}'>RESERVAR AHORA EN SIGECI</a>"
        )
    else:
        hora_actual = datetime.now().strftime("%H:%M:%S")
        return (
            f"❌ <b>Sin turnos disponibles en {NOMBRE_POLIDEPORTIVO}</b>\n\n"
            f"<i>Última verificación: {hora_actual} hs (Próximos {DIAS_A_CONSULTAR} días).</i>"
        )

def procesar_mensajes_telegram():
    """Escucha mensajes entrantes en el bot de Telegram."""
    global LAST_UPDATE_ID

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"timeout": 5, "offset": LAST_UPDATE_ID}

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for update in data.get("result", []):
                LAST_UPDATE_ID = update["update_id"] + 1
                message = update.get("message", {})
                chat_id = str(message.get("chat", {}).get("id"))
                texto = message.get("text", "").strip().lower()

                if texto:
                    print(f"📩 Mensaje recibido de Chat ID {chat_id}: '{texto}'")
                    # Enviar mensaje de espera temporal mientras escanea
                    enviar_notificacion_telegram("🔎 Consultando la disponibilidad en el SIGECI, aguarda un momento...", chat_id=chat_id)
                    
                    # Escanear y enviar respuesta
                    respuesta = escanear_disponibilidad()
                    enviar_notificacion_telegram(respuesta, chat_id=chat_id)
    except Exception as e:
        print(f"⚠️ Error al verificar mensajes de Telegram: {e}")

def bucle_principal():
    print(f"🚀 Bot iniciado en {NOMBRE_POLIDEPORTIVO}. Escuchando mensajes...")
    enviar_notificacion_telegram(f"🤖 <b>Bot Activo en {NOMBRE_POLIDEPORTIVO}:</b> Envíame cualquier mensaje o el comando /turnos para consultar la disponibilidad actual.")

    # Timer para escaneo automático programado (cada 15 minutos)
    ULTIMO_ESCANEO = 0
    INTERVALO_ESCANEO = 900  # 15 minutos en segundos

    while True:
        # 1. Escuchar si el usuario escribió un mensaje
        procesar_mensajes_telegram()

        # 2. Escaneo automático programado
        tiempo_actual = time.time()
        if tiempo_actual - ULTIMO_ESCANEO >= INTERVALO_ESCANEO:
            print("⏰ Ejecutando escaneo automático programado...")
            resultado = escanear_disponibilidad()
            # Solo notificar automáticamente si se encontraron turnos
            if "¡TURNOS DISPONIBLES" in resultado:
                enviar_notificacion_telegram(resultado)
            ULTIMO_ESCANEO = tiempo_actual

        time.sleep(2)

if __name__ == "__main__":
    bucle_principal()
