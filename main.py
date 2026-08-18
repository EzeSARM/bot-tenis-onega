import os
import time
import requests

TELEGRAM_TOKEN = os.environ.get("8679048960:AAHNy7YqRGx1Bt-oeKCr9xP29h0L-BnBE1M")
TELEGRAM_CHAT_ID = os.environ.get("8295036704")

def enviar_telegram(mensaje):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}, timeout=10)

def explorar_ids():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    }

    # Rango de Sedes a probar (Colegiales es 2279, probamos vecinas)
    sedes_a_probar = ["2275", "2276", "2277", "2278", "2279", "2280", "2281", "2282", "2283", "2284", "2285"]
    
    # Rango de Servicios/Canchas a probar (Colegiales es 3149, probamos vecinos)
    servicios_a_probar = [str(i) for i in range(3140, 3165)]

    print("🔎 --- INICIANDO ESCANEO DE IDs EN SIGECI --- 🔎")
    enviar_telegram("🔎 <b>Bot Explorador Activo:</b> Escaneando IDs para encontrar Polideportivo Onega...")

    hallazgos = []

    for sede in sedes_a_probar:
        for servicio in servicios_a_probar:
            api_url = "https://formulario-sigeci.buenosaires.gob.ar/getHorasDisp"
            # Probamos con la fecha de hoy
            params = {"day": "2026-08-18", "sedeId": sede, "servicioId": servicio}

            try:
                res = requests.get(api_url, headers=headers, params=params, timeout=5)
                
                # Si responde status 200, la combinación SEDE + SERVICIO EXISTE en el sistema
                if res.status_code == 200:
                    try:
                        data = res.json()
                        # Si devuelve una lista (aunque esté vacía []), la combinación es VÁLIDA
                        if isinstance(data, list):
                            info = f"✅ COMBINACIÓN VÁLIDA ENCONTRADA -> SedeId: {sede} | ServicioId: {servicio}"
                            print(info)
                            hallazgos.append(f"Sede: <b>{sede}</b> | Servicio: <b>{servicio}</b>")
                    except Exception:
                        pass
            except Exception as e:
                pass
            
            time.sleep(0.05)

    if hallazgos:
        resumen = "\n".join(hallazgos[:15])  # Mostramos los primeros 15
        msg = f"🎯 <b>¡RESULTADOS DEL ESCANEO!</b>\n\nCombinaciones válidas en la API:\n\n{resumen}\n\n<i>Revisa los logs de Railway para ver la lista completa.</i>"
        enviar_telegram(msg)
        print("Fin del escaneo. Resultados enviados a Telegram.")
    else:
        print("No se encontraron combinaciones en este rango.")
        enviar_telegram("⚠️ Escaneo finalizado sin hallazgos en este rango de IDs.")

if __name__ == "__main__":
    explorar_ids()
