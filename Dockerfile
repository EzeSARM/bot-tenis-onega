FROM python:3.10-slim

WORKDIR /app

# Copiar e instalar librerías de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código del bot
COPY . .

# Puerto expuesto por defecto en Hugging Face
EXPOSE 7860

# Ejecutar el script principal del bot
CMD ["python", "main.py"]
