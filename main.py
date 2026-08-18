import time
import requests
from bs4 import BeautifulSoup

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


def consultar_turnos_exactos():
    """Analiza estrictamente los selectores del calendario para evitar falsos positivos."""
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
            soup = BeautifulSoup(response.text, "html.parser")

            # 1. Buscar si la página muestra explícitamente la alerta de "Sin Turnos"
            alerta_sin_turnos = soup.find(id="divSinTurnos") or soup.find(
                class_="alert-warning"
            )

            # Si el elemento de alerta está visible en pantalla, no hay turnos
            if alerta_sin_turnos and "no hay turnos" in alerta_sin_turnos.text.lower():
                print("Verificación OK: No hay turnos disponibles actualmente.")
                return

            # 2. Buscar días habilitados en el calendario interactivo (días con clase 'day' o 'disponible' que no estén deshabilitados)
            dias_habilitados = soup.find_all(
                "td", class_=lambda c: c and "day" in c and "disabled" not in c
            )

            # 3. Buscar selectores de horas activas en el formulario
            combo_horarios = soup.find("select", id="idHorario")
            opciones_horas = []
            if combo_horarios:
                opciones_horas = [
                    opt.text.strip()
                    for opt in combo_horarios.find_all("option")
                    if opt.get("value") and opt.get("value") != ""
                ]

            # Solo notificar si se detectan días activos en el calendario o lista de horas reales
            if dias_habilitados or opciones_horas:
                fechas = [d.text.strip() for d in dias_habilitados if d.text.strip()]
                
                mensaje = "🎾 <b>¡TURNO DISPONIBLE EN ONEGA!</b> 🎾\n\n"
                
                if fechas:
                    mensaje += f"📅 <b>Días libres en el calendario:</b> {', '.join(fechas)}\n"
                if opciones_horas:
                    mensaje += f"⏰ <b>Horarios a reservar:</b> {', '.join(opciones_horas)}\n"
                
                mensaje += f"\n🔗 <a href='{URL_TRAMITE}'>RESERVAR AHORA EN SIGECI</a>"

                enviar_mensaje_telegram(mensaje)
                print("¡ALERTA REAL ENVIADA! Se encontraron turnos habilitados.")
            else:
                print("Verificación OK: Sin días habilitados en el calendario.")

        else:
            print(f"Error de servidor SIGECI: {response.status_code}")

    except Exception as e:
        print(f"Error procesando la página: {e}")


if __name__ == "__main__":
    print("Iniciando monitoreo estricto de precisión para Polideportivo Onega...")
    enviar_mensaje_telegram(
        "🚀 Bot actualizado con filtro anti-falsos positivos. Listo para monitorear."
    )

    while True:
        consultar_turnos_exactos()
        time.sleep(300)  # Revisa cada 5 minutos
