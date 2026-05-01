import os
import ssl
import sys
import warnings
import requests
import functools
from wyze_sdk import Client
from fit import FitEncoder_Weight 

# 1. DESHABILITAR WARNINGS Y VERIFICACIÓN SSL TOTAL
# Esto silencia las advertencias de "Insecure Request" en el log
from urllib3.exceptions import InsecureRequestWarning
warnings.simplefilter('ignore', InsecureRequestWarning)

# Esto fuerza a la librería 'requests' a ignorar el SSL en todas sus llamadas
requests.Session.request = functools.partialmethod(requests.Session.request, verify=False)

# Bypass adicional para el contexto global de Python
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Configuración de variables
WYZE_EMAIL = os.environ.get('WYZE_EMAIL')
WYZE_PASSWORD = os.environ.get('WYZE_PASSWORD')
WYZE_KEY_ID = os.environ.get('WYZE_KEY_ID')
WYZE_API_KEY = os.environ.get('WYZE_API_KEY')

def main():
    try:
        # Autenticación con Wyze
        client = Client(email=WYZE_EMAIL, password=WYZE_PASSWORD, key_id=WYZE_KEY_ID, api_key=WYZE_API_KEY)
        
        # Localizar la báscula WL_SCU
        devices = client.devices_list()
        scale = next((d for d in devices if d.product_model == 'WL_SCU'), None)
        
        if not scale:
            print("Error: No se encontró la báscula Scale Ultra.")
            sys.exit(1)

        # Obtener el registro más reciente
        records = client.scales.get_records(device_mac=scale.mac, limit=1)
        if not records:
            print("No hay registros disponibles.")
            return
        
        last_record = records[0]
        print(f"Éxito: Dato obtenido -> {last_record.weight} lbs")

        # Generar archivo .fit
        fit_file = "weight_extraction.fit"
        encoder = FitEncoder_Weight()
        encoder.write_fit_file(fit_file, last_record)
        print(f"--- ARCHIVO GENERADO: {fit_file} ---")

    except Exception as e:
        print(f"Error durante la ejecución: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
