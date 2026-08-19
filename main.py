import os
import time
import requests
from datetime import datetime, timedelta

# Configuración del Polideportivo Onega
SERVICIO_ID = "3137"
CANCHAS = [
    {"id": "2289", "nombre": "Cancha 1"},
    {"id": "2290", "nombre": "Cancha 2"}
]

# Configuración de Telegram (Asegúrate de configurar tus variables de entorno o credenciales)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8679048960:AAHNy7YqRGx1Bt-oeKCr9xP29h0L-BnBE1M")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8295036704")

def enviar_notificacion_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error al enviar mensaje por Telegram: {e}")

def consultar_turnos_cancha(session, sede_id, fecha_str):
    url = f"https://formulario-sigeci.buenosaires.gob.ar/getHorasDisp?day={fecha_str}&sedeId={sede_id}&servicioId={SERVICIO_ID}"
    try:
        response = session.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error al consultar sede {sede_id} para la fecha {fecha_str}: {e}")
    return []

def monitorear_onega():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "X-Requested-With": "XMLHttpRequest"
    })

    # Paso 1: Inicializar la sesión en la página principal de la prestación
    url_inicio = f"https://formulario-sigeci.buenosaires.gob.ar/AgendarTramite?idPrestacion={SERVICIO_ID}&flow=primeros"
    session.get(url_inicio, timeout=10)

    # Rango de días a consultar (próximos 7 días)
    hoy = datetime.now()
    fechas_a_consultar = [(hoy + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Escaneando turnos en Polideportivo Onega...")

    turnos_encontrados = []

    for cancha in CANCHAS:
        for fecha in fechas_a_consultar:
            turnos = consultar_turnos_cancha(session, cancha["id"], fecha)
            if turnos:
                for t in turnos:
                    # Se asume la estructura del objeto devuelto por la API del SIGECI
                    hora = t.get("hora", "Hora N/D") if isinstance(t, dict) else str(t)
                    turnos_encontrados.append({
                        "cancha": cancha["nombre"],
                        "fecha": fecha,
                        "hora": hora
                    })

    if turnos_encontrados:
        mensaje = "🎾 <b>¡Turnos encontrados en Polideportivo Onega!</b>\n\n"
        for t in turnos_encontrados:
            mensaje += f"• <b>{t['cancha']}</b>: {t['fecha']} a las {t['hora']} hs\n"
        mensaje += f"\n👉 <a href='{url_inicio}'>Reservar en SIGECI</a>"
        
        enviar_notificacion_telegram(mensaje)
        print("✅ Notificación enviada por Telegram.")
    else:
        print("Sin turnos disponibles por el momento.")

if __name__ == "__main__":
    monitorear_onega()
