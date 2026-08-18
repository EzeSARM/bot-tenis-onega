import os
import time
import requests

TELEGRAM_TOKEN = os.environ.get("8679048960:AAHNy7YqRGx1Bt-oeKCr9xP29h0L-BnBE1M")
TELEGRAM_CHAT_ID = os.environ.get("8295036704")
ID_PRESTACION = "3137"

# URL actualizada de la vista de turnos de SIGECI
URL_BASE = "https://formulario-sigeci.buenosaires.gob.ar/AgendarTramite"
URL_OBTENER_FECHAS = f"{URL_BASE}/ObtenerFechas"


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
    """Consulta la disponibilidad de turnos con sesión y encabezados completos."""
    session = requests.Session()

    # Encabezados para simular una navegación real en navegador
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{URL_BASE}?idPrestacion={ID_PRESTACION}",
    }

    try:
        # 1. Petición previa a la página principal para establecer galletas de sesión (Cookies)
        session.get(
            f"{URL_BASE}?idPrestacion={ID_PRESTACION}",
            headers=headers,
            timeout=15,
        )

        # 2. Petición a la API para obtener fechas
        params = {"idPrestacion": ID_PRESTACION}

        response = session.get(
            URL_OBTENER_FECHAS, params=params, headers=headers, timeout=15
        )

        if response.status_code == 200:
            try:
                datos = response.json()
                if datos and len(datos) > 0:
                    mensaje = (
                        "🎾 <b>¡HAY TURNOS DISPONIBLES EN ONEGA!</b> 🎾\n\n"
                        "Se encontraron fechas libres.\n"
                        "Ingresa rápido para reservar:\n"
                        f"{URL_BASE}?idPrestacion={ID_PRESTACION}"
                    )
                    enviar_mensaje_telegram(mensaje)
                    print("¡Turnos encontrados! Notificación enviada.")
                else:
                    print("No hay turnos disponibles por el momento.")
            except Exception:
                # Si responde 200 pero la respuesta es texto HTML plano
                if "No hay turnos" not in response.text:
                    print(
                        "Respuesta con formato inusual. Verificando contenido..."
                    )
                else:
                    print("No hay turnos disponibles por el momento.")

        elif response.status_code == 404:
            print(
                "Error 404: La ruta interna cambió. Revisa los logs de Railway."
            )
        else:
            print(
                f"La web de la ciudad respondió con estado: {response.status_code}"
            )

    except Exception as e:
        print(f"Error al consultar la web: {e}")


if __name__ == "__main__":
    print("Iniciando bot de monitoreo continuo...")
    enviar_mensaje_telegram("🚀 El bot ha actualizado su conexión y está activo.")

    while True:
        consultar_turnos()
        time.sleep(300)
