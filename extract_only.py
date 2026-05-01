import os
import ssl
import sys
from wyze_sdk import Client
# Importa tu clase del codificador (asegúrate que el archivo se llame fit.py)
from fit import FitEncoder_Weight 

# BYPASS DE SEGURIDAD SSL (Replicando la lógica de tu flujo de sincronización)
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    # Caso para versiones de Python muy antiguas (no aplica a 3.12, pero es buena práctica)
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Configuración de variables (extraídas de GitHub Secrets)
WYZE_EMAIL = os.environ.get('WYZE_EMAIL')
WYZE_PASSWORD = os.environ.get('WYZE_PASSWORD')
WYZE_KEY_ID = os.environ.get('WYZE_KEY_ID')
WYZE_API_KEY = os.environ.get('WYZE_API_KEY')

def main():
    # 1. Autenticación con Wyze
    client = Client(email=WYZE_EMAIL, password=WYZE_PASSWORD, key_id=WYZE_KEY_ID, api_key=WYZE_API_KEY)
    
    # 2. Localizar la báscula WL_SCU (Ultra)
    devices = client.devices_list()
    scale = next((d for d in devices if d.product_model == 'WL_SCU'), None)
    
    if not scale:
        print("Error: No se encontró la báscula Scale Ultra.")
        sys.exit(1)

    # 3. Obtener el registro más reciente
    records = client.scales.get_records(device_mac=scale.mac, limit=1)
    if not records:
        print("No hay registros disponibles en Wyze.")
        return
    
    last_record = records[0]
    print(f"Dato identificado: {last_record.weight} lbs") 

    # 4. Generar el archivo .fit
    fit_file = f"weight_extraction.fit"
    encoder = FitEncoder_Weight()
    # Asumimos que write_fit_file es el método que genera el archivo
    encoder.write_fit_file(fit_file, last_record) 
    
    print(f"--- ÉXITO: Archivo generado en {fit_file} ---")

if __name__ == "__main__":
    main()
