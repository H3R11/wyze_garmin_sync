import requests
import os
import ssl
import sys
import warnings
from datetime import datetime, timedelta
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# 1. Protocolo Heredado (Bypass SSL)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
old_merge_environment_settings = requests.Session.merge_environment_settings
def new_merge_environment_settings(self, url, proxies, stream, verify, cert):
    settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
    settings['verify'] = False
    return settings
requests.Session.merge_environment_settings = new_merge_environment_settings

# 2. Importaciones de SDK y Lógica
from wyze_sdk import Client
from fit import FitEncoder_Weight 

# Credenciales de entorno
WYZE_EMAIL = os.environ.get('WYZE_EMAIL')
WYZE_PASSWORD = os.environ.get('WYZE_PASSWORD')
WYZE_KEY_ID = os.environ.get('WYZE_KEY_ID')
WYZE_API_KEY = os.environ.get('WYZE_API_KEY')

def main():
    try:
        client = Client(email=WYZE_EMAIL, password=WYZE_PASSWORD, key_id=WYZE_KEY_ID, api_key=WYZE_API_KEY)
        
        # 3. Localización del dispositivo (WL_SCU)
        devices = client.devices_list()
        scale = None
        for d in devices:
            model = getattr(d, 'product_model', None)
            if not model and hasattr(d, 'product'):
                model = getattr(d.product, 'model', None)
            if model == 'WL_SCU':
                scale = d
                break
        
        if not scale:
            print("Error: No se encontró la báscula Scale Ultra.")
            sys.exit(1)

        # 4. Extracción de registros con start_time (Obligatorio en SDK)
        # Definimos el inicio de la búsqueda hace 24 horas
        start_time = datetime.now() - timedelta(hours=24)
        
        records = client.scales.get_records(
            device_mac=scale.mac, 
            start_time=start_time, # Argumento corregido
            limit=1
        )
        
        if not records:
            print("No se encontraron registros en las últimas 24 horas.")
            return
        
        last_record = records[0]
        print(f"Éxito: Peso identificado -> {last_record.weight} lbs")

        # 5. Generación del archivo FIT
        fit_file = "weight_manual.fit"
        encoder = FitEncoder_Weight()
        encoder.write_fit_file(fit_file, last_record)
        print(f"--- ARCHIVO GENERADO: {fit_file} ---")

    except Exception as e:
        print(f"Fallo durante la ejecución: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
