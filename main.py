import os
import time
import requests

TELEGRAM_TOKEN = os.environ.get("8679048960:AAHNy7YqRGx1Bt-oeKCr9xP29h0L-BnBE1M")
TELEGRAM_CHAT_ID = os.environ.get("8295036704")
ID_PRESTACION = "3137"

URL_SIGECI = (
    "https://formulario-sigeci.buenosaires.gob.ar/AgendarTramite/ObtenerFechas"
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
        print(f"Error enviando mensaje: {e}")


def consultar_turnos():
    """Consulta al sistema SIGECI si hay turnos disponibles."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "X-Requested-With": "XMLHttpRequest",
    }
    params = {"idPrestacion": ID_PRESTACION}

    try:
        response = requests.get(
            URL_SIGECI, params=params, headers=headers, timeout=15
        )

        if response.status_code == 200:
            datos = response.json()
            if datos and len(datos) > 0:
                mensaje = (
                    "🎾 ¡HAY TURNOS DISPONIBLES EN ONEGA! 🎾\n\n"
                    "Se encontraron fechas/horarios libres.\n"
                    "Ingresa rápido para reservar:\n"
                    "https://formulario-sigeci.buenosaires.gob.ar/AgendarTramite?idPrestacion=3137"
                )
                enviar_mensaje_telegram(mensaje)
                print("¡Turnos encontrados! Notificación enviada.")
            else:
                print("No hay turnos disponibles por el momento.")
        else:
            print(
                f"La web de la ciudad respondió con estado: {response.status_code}"
            )

    except Exception as e:
        print(f"Error al consultar la web: {e}")


if __name__ == "__main__":
    print("Iniciando bot de monitoreo continuo...")
    enviar_mensaje_telegram("🚀 El bot ha iniciado el monitoreo continuo.")

    # Revisa cada 5 minutos (300 segundos) de forma indefinida
    while True:
        consultar_turnos()
        time.sleep(300)
