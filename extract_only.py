import requests
import os
import ssl
import sys  # Corrección 1: Importación necesaria para sys.exit()
import warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# 1. Protocolo Heredado (image_7.png)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Parche de Sesión para ignorar SSL
old_merge_environment_settings = requests.Session.merge_environment_settings
def new_merge_environment_settings(self, url, proxies, stream, verify, cert):
    settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
    settings['verify'] = False
    return settings
requests.Session.merge_environment_settings = new_merge_environment_settings

# 2. Importaciones de SDK y Lógica
from wyze_sdk import Client
from fit import FitEncoder_Weight 

# Variables de entorno desde GitHub Secrets
WYZE_EMAIL = os.environ.get('WYZE_EMAIL')
WYZE_PASSWORD = os.environ.get('WYZE_PASSWORD')
WYZE_KEY_ID = os.environ.get('WYZE_KEY_ID')
WYZE_API_KEY = os.environ.get('WYZE_API_KEY')

def main():
    try:
        client = Client(email=WYZE_EMAIL, password=WYZE_PASSWORD, key_id=WYZE_KEY_ID, api_key=WYZE_API_KEY)
        
        # 3. Obtención de dispositivos
        devices = client.devices_list()
        
        # Corrección 2: Búsqueda robusta para dispositivo "Unknown"
        # Como el SDK no reconoce el objeto WL_SCU, buscamos en el atributo 'product' o 'raw'
        scale = None
        for d in devices:
            # Probamos las dos rutas posibles para identificar el modelo WL_SCU
            model = getattr(d, 'product_model', None)
            if not model and hasattr(d, 'product'):
                model = getattr(d.product, 'model', None)
            
            if model == 'WL_SCU':
                scale = d
                break
        
        if not scale:
            print("Error: No se encontró la báscula Scale Ultra (WL_SCU) en la cuenta.")
            sys.exit(1)

        # 4. Extracción del registro (Peso: 225.1 lb aprox)
        records = client.scales.get_records(device_mac=scale.mac, limit=1)
        if not records:
            print("No se encontraron registros de peso recientes.")
            return
        
        last_record = records[0]
        print(f"Éxito: Registro identificado -> {last_record.weight} lbs")

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
