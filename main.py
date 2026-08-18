import time
import requests

# CREDENCIALES CONFIGURADAS
TELEGRAM_TOKEN = "8679048960:AAHNy7YqRGx1Bt-oeKCr9xP29h0L-BnBE1M"
TELEGRAM_CHAT_ID = "8295036704"
ID_PRESTACION = "3137"

URL_BASE = "https://formulario-sigeci.buenosaires.gob.ar/AgendarTramite"


def enviar_mensaje_telegram(mensaje):
    """Envía una notificación a Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error enviando mensaje a Telegram: {e}")


def consultar_turnos_detallados():
    """Consulta las fechas y horarios específicos disponibles en la API interna de SIGECI."""
    session = requests.Session()

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{URL_BASE}?idPrestacion={ID_PRESTACION}",
    }

    try:
        # 1. Petición inicial a la página para obtener las cookies de sesión
        url_inicio = f"{URL_BASE}?idPrestacion={ID_PRESTACION}"
        session.get(url_inicio, headers=headers, timeout=15)

        # 2. Consultar las fechas disponibles
        url_fechas = f"{URL_BASE}/ObtenerFechas"
        params_fechas = {"idPrestacion": ID_PRESTACION}

        resp_fechas = session.get(
            url_fechas, params=params_fechas, headers=headers, timeout=15
        )

        if resp_fechas.status_code == 200:
            try:
                fechas_data = resp_fechas.json()
            except Exception:
                fechas_data = []

            # Si se encuentran fechas disponibles
            if fechas_data and isinstance(fechas_data, list) and len(fechas_data) > 0:
                mensaje = "🎾 <b>¡TURNOS ENCONTRADOS EN ONEGA!</b> 🎾\n\n"
                turnos_encontrados = False

                # 3. Iterar cada fecha para obtener sus horarios correspondientes
                for f in fechas_data:
                    # 'f' suele ser un string con la fecha o un diccionario según la respuesta de la API
                    fecha_str = f.get("fecha") if isinstance(f, dict) else str(f)

                    url_horarios = f"{URL_BASE}/ObtenerHorarios"
                    params_horarios = {
                        "idPrestacion": ID_PRESTACION,
                        "fecha": fecha_str,
                    }

                    resp_horarios = session.get(
                        url_horarios,
                        params=params_horarios,
                        headers=headers,
                        timeout=15,
                    )

                    if resp_horarios.status_code == 200:
                        try:
                            horarios_data = resp_horarios.json()
                        except Exception:
                            horarios_data = []

                        if horarios_data and isinstance(horarios_data, list):
                            horarios_lista = []
                            for h in horarios_data:
                                hora = h.get("hora") if isinstance(h, dict) else str(h)
                                horarios_lista.append(hora)

                            if horarios_lista:
                                turnos_encontrados = True
                                horarios_texto = ", ".join(horarios_lista)
                                mensaje += f"📅 <b>Fecha:</b> {fecha_str}\n⏰ <b>Horarios:</b> {horarios_texto}\n\n"

                if turnos_encontrados:
                    mensaje += f"🔗 <a href='{url_inicio}'>Ingresar para reservar en SIGECI</a>"
                    enviar_mensaje_telegram(mensaje)
                    print("¡Turnos detallados encontrados y mensaje enviado!")
                else:
                    # Había fechas pero sin horarios confirmados
                    mensaje_generico = (
                        "🎾 <b>¡FECHAS DETECTADAS EN ONEGA!</b> 🎾\n\n"
                        f"Se detectaron fechas en el sistema. Revisa la web directamente:\n{url_inicio}"
                    )
                    enviar_mensaje_telegram(mensaje_generico)
                    print("Se detectaron fechas pero no se obtuvieron horarios detallados.")

            else:
                print("No hay fechas ni turnos disponibles en este momento.")

        else:
            print(f"El servidor de SIGECI respondió con código: {resp_fechas.status_code}")

    except Exception as e:
        print(f"Error consultando turnos: {e}")


if __name__ == "__main__":
    print("Iniciando monitoreo detallado de turnos de tenis en Polideportivo Onega...")
    enviar_mensaje_telegram(
        "🚀 Bot actualizado: Ahora verificará fechas y horarios exactos disponibles."
    )

    while True:
        consultar_turnos_detallados()
        time.sleep(300)  # Consulta cada 5 minutos
