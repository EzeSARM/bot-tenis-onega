import threading
import os
import gradio as gr

# Definir la función que ejecuta tu bot principal
def correr_bot():
    print("🚀 Iniciando script del bot de tenis...")
    os.system("python main.py")

# Iniciar el bot en segundo plano para que no bloquee la interfaz
hilo_bot = threading.Thread(target=correr_bot, daemon=True)
hilo_bot.start()

# Interfaz visual mínima para cumplir con Hugging Face
with gr.Blocks() as demo:
    gr.Markdown("# 🎾 Bot de Monitoreo de Tenis CABA")
    gr.Markdown("El bot se encuentra ejecutándose correctamente en segundo plano 24/7.")

if __name__ == "__main__":
    demo.launch()
