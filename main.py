import re
import time
import requests

TELEGRAM_TOKEN = "8679048960:AAHNy7YqRGx1Bt-oeKCr9xP29h0L-BnBE1M"
TELEGRAM_CHAT_ID = "8295036704"
ID_PRESTACION = "3137"

URL_TRAMITE = f"https://formulario-sigeci.buenosaires.gob.ar/AgendarTramite?idPrestacion={ID_PRESTACION}"


def enviar_mensaje_telegram(mensaje):
    """Envía una notificación a Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error enviando mensaje a Telegram: {e}")


def consultar_turnos_estables():
    """Analiza la página principal buscando fechas y horarios sin consumir endpoints protegidos."""
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
            html = response.text

            # Frases que confirman que la agenda está cerrada o sin cupos
            frases_sin_turnos = [
                "no hay turnos disponibles",
                "no existen turnos disponibles",
                "sin turnos disponibles",
                "no se encontraron turnos",
            ]

            sin_turnos = any(
                frase in html.lower() for frase in frases_sin_turnos
            )

            # Extraer fechas visibles en formato DD/MM/YYYY o YYYY-MM-DD mediante expresión regular
            fechas_encontradas = re.findall(
                r"\b\d{2}/\d{2}/\d{4}\b|\b\d{4}-\d{2}-\d{2}\b", html
            )
            # Eliminar duplicados
            fechas_unicas = list(set(fechas_encontradas))

            # Extraer posibles horarios (formatos HH:MM)
            horarios_encontrados = re.findall(
                r"\b(?:[01]?\d|2[03]):[05]0\b", html
            )
            horarios_unicos = list(set(horarios_encontrados))

            if not sin_turnos or len(fechas_unicas) > 0:
                mensaje = "🎾 <b>¡TURNOS DETECTADOS EN POLIDEPORTIVO ONEGA!</b> 🎾\n\n"

                if fechas_unicas:
                    mensaje += f"📅 <b>Fechas detectadas:</b> {', '.join(fechas_unicas[:5])}\n"
                if horarios_unicos:
                    mensaje += f"⏰ <b>Horarios aproximados:</b> {', '.join(horarios_unicos[:6])}\n"

                mensaje += f"\n🔗 <a href='{URL_TRAMITE}'>Ingresar rápido a reservar en SIGECI</a>"

                enviar_mensaje_telegram(mensaje)
                print(
                    "¡Notificación enviada a Telegram! Se detectó disponibilidad."
                )
            else:
                print("Consulta exitosa (Estado 200): No hay turnos en este momento.")

        else:
            print(f"Respuesta inesperada de SIGECI: Estado {response.status_code}")

    except Exception as e:
        print(f"Error durante la verificación: {e}")


if __name__ == "__main__":
    print("Servidor activo. Monitoreando Polideportivo Onega cada 5 minutos...")
    enviar_mensaje_telegram("🚀 Bot de tenis activo con modo de escaneo estable.")

    while True:
        consultar_turnos_estables()
        time.sleep(300)
