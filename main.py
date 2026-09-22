import os
import time
import requests
from datetime import datetime, timedelta

# ==========================================
# CONFIGURACIÓN Y CREDENCIALES - ONEGA
# ==========================================
NOMBRE_POLIDEPORTIVO = "Polideportivo Onega"
SERVICIO_ID = "3137"

CANCHAS = [
    {"id": "2289", "nombre": "Cancha 1"},
    {"id": "2290", "nombre": "Cancha 2"}
]

DIAS_A_CONSULTAR = 30

# Se leen exclusivamente de las variables de entorno sin valores por defecto expuestos
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

DIAS_SEMANA = {
    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
}

LAST_UPDATE_ID = None
TURNOS_NOTIFICADOS = set()

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
        print(f"❌ Error enviando mensaje por Telegram: {e}")
        return False

def crear_sesion_sigeci():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"https://formulario-sigeci.buenosaires.gob.ar/AgendarTramite?idPrestacion={SERVICIO_ID}&flow=primeros"
    })
    try:
        session.get(f"https://formulario-sigeci.buenosaires.gob.ar/AgendarTramite?idPrestacion={SERVICIO_ID}&flow=primeros", timeout=10)
    except Exception:
        pass
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
                horas_validas.append(f"{int(partes[0]):02d}:{int(partes[1]):02d} hs")
            except ValueError:
                pass
    return sorted(list(set(horas_validas)))

def consultar_turnos_cancha(session, sede_id, fecha_str):
    url = "https://formulario-sigeci.buenosaires.gob.ar/getHorasDisp"
    params = {"day": fecha_str, "sedeId": sede_id, "servicioId": SERVICIO_ID}
    try:
        response = session.get(url, params=params, timeout=8)
        if response.status_code == 200:
            try:
                return extraer_horas_validas(response.json())
            except Exception:
                return []
    except Exception as e:
        print(f"Error consultando cancha {sede_id}: {e}")
    return []

def obtener_estado_turnos():
    global TURNOS_NOTIFICADOS
    session = crear_sesion_sigeci()
    url_reserva = f"https://formulario-sigeci.buenosaires.gob.ar/AgendarTramite?idPrestacion={SERVICIO_ID}&flow=primeros"
    hoy = datetime.now()
    fechas_a_consultar = [(hoy + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(DIAS_A_CONSULTAR)]

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Escaneando turnos en {NOMBRE_POLIDEPORTIVO}...")

    lineas_todas = []
    lineas_nuevas = []
    turnos_visibles_actualmente = set()

    for cancha in CANCHAS:
        for fecha in fechas_a_consultar:
            horas = consultar_turnos_cancha(session, cancha["id"], fecha)
            if horas:
                dt_fecha = datetime.strptime(fecha, "%Y-%m-%d")
                dia_nombre = DIAS_SEMANA.get(dt_fecha.strftime("%A"), dt_fecha.strftime("%A"))
                fecha_corta = dt_fecha.strftime("%d/%m")

                horas_nuevas = []
                for h in horas:
                    clave = f"{cancha['id']}|{fecha}|{h}"
                    turnos_visibles_actualmente.add(clave)
                    if clave not in TURNOS_NOTIFICADOS:
                        horas_nuevas.append(h)

                lineas_todas.append(f"🎾 <b>{cancha['nombre']}</b> - 📅 <b>{dia_nombre} {fecha_corta}:</b> {', '.join(horas)}")
                if horas_nuevas:
                    lineas_nuevas.append(f"🎾 <b>{cancha['nombre']}</b> - 📅 <b>{dia_nombre} {fecha_corta}:</b> {', '.join(horas_nuevas)}")

            time.sleep(0.05)

    TURNOS_NOTIFICADOS = TURNOS_NOTIFICADOS.intersection(turnos_visibles_actualmente)
    return lineas_todas, lineas_nuevas, turnos_visibles_actualmente, url_reserva

def procesar_mensajes_telegram():
    global LAST_UPDATE_ID, TURNOS_NOTIFICADOS
    if not TELEGRAM_TOKEN:
        return

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
                    enviar_notificacion_telegram("🔎 Consultando la disponibilidad en el SIGECI, aguarda un momento...", chat_id=chat_id)
                    lineas_todas, _, turnos_visibles, url_reserva = obtener_estado_turnos()

                    if lineas_todas:
                        TURNOS_NOTIFICADOS.update(turnos_visibles)
                        resumen = "\n".join(lineas_todas)
                        mensaje = (
                            f"🔔 <b>¡TURNOS DISPONIBLES EN {NOMBRE_POLIDEPORTIVO.upper()}!</b> 🔔\n\n"
                            f"{resumen}\n\n"
                            f"🔗 <a href='{url_reserva}'>RESERVAR AHORA EN SIGECI</a>"
                        )
                    else:
                        hora_actual = datetime.now().strftime("%H:%M:%S")
                        mensaje = (
                            f"❌ <b>Sin turnos disponibles en {NOMBRE_POLIDEPORTIVO}</b>\n\n"
                            f"<i>Última verificación: {hora_actual} hs (Próximos {DIAS_A_CONSULTAR} días).</i>"
                        )
                    enviar_notificacion_telegram(mensaje, chat_id=chat_id)
    except Exception as e:
        print(f"⚠️ Error procesando mensajes: {e}")

def bucle_principal():
    global TURNOS_NOTIFICADOS
    print(f"🚀 Bot iniciado en {NOMBRE_POLIDEPORTIVO}.")
    enviar_notificacion_telegram(f"🤖 <b>Bot Activo en {NOMBRE_POLIDEPORTIVO}:</b> Envíame un mensaje para consultar la disponibilidad actual.")

    ULTIMO_ESCANEO = 0
    INTERVALO_ESCANEO = 900  # 15 minutos

    while True:
        procesar_mensajes_telegram()
        tiempo_actual = time.time()
        if tiempo_actual - ULTIMO_ESCANEO >= INTERVALO_ESCANEO:
            _, lineas_nuevas, turnos_visibles, url_reserva = obtener_estado_turnos()
            if lineas_nuevas:
                resumen_nuevos = "\n".join(lineas_nuevas)
                mensaje_alerta = (
                    f"🚨 <b>¡NUEVOS TURNOS DETECTADOS EN {NOMBRE_POLIDEPORTIVO.upper()}!</b> 🚨\n\n"
                    f"{resumen_nuevos}\n\n"
                    f"🔗 <a href='{url_reserva}'>RESERVAR AHORA EN SIGECI</a>"
                )
                enviar_notificacion_telegram(mensaje_alerta)
                TURNOS_NOTIFICADOS.update(turnos_visibles)
            ULTIMO_ESCANEO = tiempo_actual
        time.sleep(2)

if __name__ == "__main__":
    bucle_principal()
