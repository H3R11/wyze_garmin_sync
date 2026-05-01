import requests
import os
import ssl
import sys
import warnings
from datetime import datetime, timedelta
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# 1. Protocolo Heredado: Bypass SSL
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
old_merge_environment_settings = requests.Session.merge_environment_settings
def new_merge_environment_settings(self, url, proxies, stream, verify, cert):
    settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
    settings['verify'] = False
    return settings
requests.Session.merge_environment_settings = new_merge_environment_settings

# 2. Importaciones de SDK y Lógica Local
from wyze_sdk import Client
from fit import FitEncoder_Weight 

# Variables de entorno
WYZE_EMAIL = os.environ.get('WYZE_EMAIL')
WYZE_PASSWORD = os.environ.get('WYZE_PASSWORD')
WYZE_KEY_ID = os.environ.get('WYZE_KEY_ID')
WYZE_API_KEY = os.environ.get('WYZE_API_KEY')

def main():
    try:
        client = Client(email=WYZE_EMAIL, password=WYZE_PASSWORD, key_id=WYZE_KEY_ID, api_key=WYZE_API_KEY)
        
        # 3. Localización de la Scale Ultra
        devices = client.devices_list()
        scale = next((d for d in devices if getattr(d, 'product_model', None) == 'WL_SCU' or 
                      (hasattr(d, 'product') and getattr(d.product, 'model', None) == 'WL_SCU')), None)
        
        if not scale:
            print("Error: No se encontró la báscula WL_SCU.")
            sys.exit(1)

        # 4. Obtener peso (225.1 lbs)
        # Usamos 48 horas de rango para asegurar la captura del último dato
        start_time = datetime.now() - timedelta(hours=48)
        records = client.scales.get_records(device_mac=scale.mac, start_time=start_time, limit=1)
        
        if not records:
            print("No se encontraron registros en el rango de tiempo.")
            return
        
        last_record = records[0]
        print(f"Éxito: Peso identificado -> {last_record.weight} lbs")

        # 5. Generación del archivo FIT compatible con Garmin
        fit_file = "weight_manual.fit"
        encoder = FitEncoder_Weight()

        # Validación dinámica del método de guardado
        if hasattr(encoder, 'write_fit'):
            encoder.write_fit(fit_file, last_record)
        elif hasattr(encoder, 'write_fit_file'):
            encoder.write_fit_file(fit_file, last_record)
        else:
            # Si no encuentra ninguno, listamos los métodos para corregir manualmente
            metodos = [m for m in dir(encoder) if not m.startswith('_')]
            print(f"Error: No se encontró método de escritura. Métodos en fit.py: {metodos}")
            sys.exit(1)

        print(f"--- ARCHIVO GENERADO EXITOSAMENTE: {fit_file} ---")

    except Exception as e:
        print(f"Fallo durante la ejecución: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
