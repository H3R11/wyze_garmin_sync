import requests
import os
import ssl
import sys
import warnings
from datetime import datetime, timedelta
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# 1. PROTOCOLO DE SEGURIDAD HEREDADO (Bypass SSL)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
old_merge_environment_settings = requests.Session.merge_environment_settings

def new_merge_environment_settings(self, url, proxies, stream, verify, cert):
    settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
    settings['verify'] = False
    return settings

requests.Session.merge_environment_settings = new_merge_environment_settings

# 2. IMPORTACIONES TÉCNICAS
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
        
        # 3. LOCALIZACIÓN DE LA BÁSCULA ULTRA (WL_SCU)
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
            print("ERROR: Dispositivo WL_SCU no localizado.")
            sys.exit(1)

        # 4. EXTRACCIÓN DEL DATO (Identificado: 225.1 lbs)
        search_window = datetime.now() - timedelta(hours=48)
        records = client.scales.get_records(
            device_mac=scale.mac, 
            start_time=search_window, 
            limit=1
        )
        
        if not records:
            print("AVISO: No hay registros recientes.")
            return
        
        last_record = records[0]
        peso_valor = last_record.weight # 225.1
        print(f"ÉXITO: Peso identificado -> {peso_valor} lbs")

        # 5. GENERACIÓN DEL ARCHIVO FIT (Protocolo Secuencial Garmin)
        fit_file = "weight_manual.fit"
        encoder = FitEncoder_Weight()

        # Normalización de Timestamp (Segundos para Garmin)
        raw_ts = getattr(last_record, 'measure_ts', int(datetime.now().timestamp() * 1000))
        ts_seconds = int(raw_ts / 1000) if raw_ts > 9999999999 else int(raw_ts)

        # ORDEN CRÍTICO SECUENCIAL
        encoder.write_header()
        encoder.write_file_info()
        encoder.write_file_creator()
        encoder.write_device_info(timestamp=ts_seconds)
        
        # CORRECCIÓN FINAL: Pasamos el peso y el timestamp como argumentos requeridos
        encoder.write_weight_scale(weight=peso_valor, timestamp=ts_seconds)
        
        encoder.finish()

        # 6. ESCRITURA FÍSICA DEL BINARIO
        with open(fit_file, "wb") as f:
            f.write(encoder.getvalue())

        print(f"--- ARCHIVO GENERADO EXITOSAMENTE: {fit_file} ---")

    except Exception as e:
        print(f"FALLO CRÍTICO: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
