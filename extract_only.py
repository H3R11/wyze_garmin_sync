import os
from wyze_sdk import Client
from fit import FitEncoder_Weight # Asegúrate de que el nombre del archivo/clase coincida

# Configuración de variables (Wyze)
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
        return

    # 3. Obtener el registro más reciente
    records = client.scales.get_records(device_mac=scale.mac, limit=1)
    if not records:
        print("No hay registros disponibles.")
        return
    
    last_record = records[0]
    print(f"Dato extraído: {last_record.weight} lbs del {last_record.measure_ts}") #

    # 4. Generar el archivo .fit
    # Nota: Ajusta los parámetros según tu clase FitEncoder_Weight
    fit_file = f"weight_{last_record.measure_ts}.fit"
    encoder = FitEncoder_Weight()
    encoder.write_fit_file(fit_file, last_record) 
    
    print(f"--- ARCHIVO GENERADO: {fit_file} ---")

if __name__ == "__main__":
    main()
