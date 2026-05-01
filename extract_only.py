import requests
import os
import ssl
import sys
import warnings
from datetime import datetime, timedelta
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# 1. PROTOCOLO DE SEGURIDAD (Bypass SSL para entorno GitHub Actions)
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

# Configuración de variables desde GitHub Secrets
WYZE_EMAIL = os.environ.get('WYZE_EMAIL')
WYZE_PASSWORD = os.environ.get('WYZE_PASSWORD')
WYZE_KEY_ID = os.environ.get('WYZE_KEY_ID')
WYZE_API_KEY = os.environ.get('WYZE_API_KEY')

def main():
    try:
        # Autenticación inicial con Wyze
        client = Client(email=WYZE_EMAIL, password=WYZE_PASSWORD, key_id=WYZE_KEY_ID, api_key=WYZE_API_KEY)
        
        # 3. DETECCIÓN DE LA SCALE ULTRA (WL_SCU)
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

        # 4. EXTRACCIÓN Y CONVERSIÓN DE DATOS
        # Ventana de búsqueda de 48 horas
        search_window = datetime.now() - timedelta(hours=48)
        records = client.scales.get_records(
            device_mac=scale.mac, 
            start_time=search_window, 
            limit=1
        )
        
        if not records:
            print("AVISO: No se encontraron registros recientes en Wyze.")
            return
        
        last_record = records[0]
        
        # CONVERSIÓN CRÍTICA: Wyze (Lbs) -> Garmin (Kg)
        # Garmin requiere el peso en Kg dentro del archivo FIT[span_2](start_span)[span_2](end_span)
        peso_lbs = last_record.weight
        peso_kg = peso_lbs * 0.453592
        
        # Normalización de Timestamp (Milisegundos a Segundos de Garmin)[span_3](start_span)[span_3](end_span)
        raw_ts = getattr(last_record, 'measure_ts', int(datetime.now().timestamp() * 1000))
        ts_seconds = int(raw_ts / 1000) if raw_ts > 9999999999 else int(raw_ts)

        print(f"ÉXITO: Peso identificado -> {peso_lbs} lbs (~{peso_kg:.2f} kg)")

        # 5. GENERACIÓN DEL ARCHIVO FIT (Protocolo Secuencial)
        fit_file = "weight_manual.fit"
        encoder = FitEncoder_Weight()

        # ORDEN CRÍTICO PARA COMPATIBILIDAD CON GARMIN[span_4](start_span)[span_4](end_span)
        # 1. Cabecera del archivo
        encoder.write_header()
        
        # 2. Identificación del tipo de archivo (Weight Scale)
        encoder.write_file_info()
        
        # 3. Información del creador/dispositivo
        encoder.write_file_creator()
        
        # 4. Metadatos del dispositivo (usando el timestamp de la medición)[span_5](start_span)[span_5](end_span)
        encoder.write_device_info(timestamp=ts_seconds)
        
        # 5. Inserción del registro de peso convertido[span_6](start_span)[span_6](end_span)
        encoder.write_weight_scale(weight=peso_kg, timestamp=ts_seconds)
        
        # 6. Finalización (Cálculo de CRC y cierre del buffer)[span_7](start_span)[span_7](end_span)
        encoder.finish()

        # 6. ESCRITURA FÍSICA DEL ARCHIVO BINARIO
        with open(fit_file, "wb") as f:
            f.write(encoder.getvalue())

        print(f"--- ARCHIVO GENERADO EXITOSAMENTE: {fit_file} ---")

    except Exception as e:
        print(f"FALLO CRÍTICO: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
