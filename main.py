import os
import time
import requests

TELEGRAM_TOKEN = "8679048960:AAHNy7YqRGx1Bt-oeKCr9xP29h0L-BnBE1M"
TELEGRAM_CHAT_ID = "8295036704"
ID_PRESTACION = "3137"

URL_TRAMITE = (
    f"https://formulario-sigeci.buenosaires.gob.ar/AgendarTramite?idPrestacion={ID_PRESTACION}"
)


def enviar_mensaje_telegram(mensaje):
    """Envía una notificación a Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: No se han configurado las credenciales de Telegram.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error enviando mensaje a Telegram: {e}")


def consultar_turnos():
    """Analiza la página principal del trámite para detectar disponibilidad."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
    }

    try:
        response = requests.get(URL_TRAMITE, headers=headers, timeout=15)

        if response.status_code == 200:
            contenido = response.text.lower()

            # Frases típicas que indican que NO hay turnos
            sin_turnos_indicadores = [
                "no hay turnos disponibles",
                "no existen turnos disponibles",
                "no se encontraron turnos",
                "en este momento no hay turnos",
            ]

            # Verificamos si alguna de las frases de "sin turnos" está presente
            hay_cartel_sin_turnos = any(
                frase in contenido for frase in sin_turnos_indicadores
            )

            if not hay_cartel_sin_turnos:
                mensaje = (
                    "🎾 <b>¡HAY TURNOS DISPONIBLES EN ONEGA!</b> 🎾\n\n"
                    "El sistema no muestra el aviso de 'sin turnos'.\n"
                    "Ingresa rápido para reservar:\n"
                    f"{URL_TRAMITE}"
                )
                enviar_mensaje_telegram(mensaje)
                print("¡Posibles turnos detectados! Notificación enviada.")
            else:
                print("No hay turnos disponibles por el momento.")

        else:
            print(f"La web de SIGECI respondió con estado: {response.status_code}")

    except Exception as e:
        print(f"Error al conectar con la web de la Ciudad: {e}")


if __name__ == "__main__":
    print("Iniciando monitoreo de turnos de tenis en Polideportivo Onega...")
    enviar_mensaje_telegram("🚀 Bot de tenis reactivado con escaneo directo de la web.")

    while True:
        consultar_turnos()
        time.sleep(300)  # Revisa cada 5 minutos
