import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
old_merge_environment_settings = requests.Session.merge_environment_settings

def new_merge_environment_settings(self, url, proxies, stream, verify, cert):
    settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
    settings['verify'] = False
    return settings

requests.Session.merge_environment_settings = new_merge_environment_settings

import os
import math
import datetime
import hashlib
import certifi
import garth
from wyze_sdk import Client
from wyze_sdk.errors import WyzeApiError
from fit import FitEncoder_Weight

os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

WYZE_EMAIL      = os.environ.get('WYZE_EMAIL')
WYZE_PASSWORD   = os.environ.get('WYZE_PASSWORD')
WYZE_KEY_ID     = os.environ.get('WYZE_KEY_ID')
WYZE_API_KEY    = os.environ.get('WYZE_API_KEY')
GARMIN_EMAIL    = os.environ.get('GARMIN_EMAIL')
GARMIN_PASSWORD = os.environ.get('GARMIN_PASSWORD')
GARMIN_TOKENS   = os.environ.get('GARMIN_TOKENS')  # Secret con tokens serializados


def login_to_wyze():
    try:
        response = Client().login(
            email=WYZE_EMAIL,
            password=WYZE_PASSWORD,
            key_id=WYZE_KEY_ID,
            api_key=WYZE_API_KEY
        )
        return response.get('access_token')
    except WyzeApiError as e:
        print(f"Wyze API Error: {e}")
        return None


def upload_to_garmin(file_path):
    try:
        if GARMIN_TOKENS:
            # FIX: Reutiliza tokens desde Secret — sin hacer login, evita 429
            garth.client.loads(GARMIN_TOKENS)
            print("Tokens de Garmin cargados desde secret.")
        else:
            # Solo si no hay tokens guardados
            garth.login(GARMIN_EMAIL, GARMIN_PASSWORD)
            print("Login exitoso. Guarda estos tokens como secret GARMIN_TOKENS:")
            print(garth.client.dumps())

        # FIX: Método correcto para subir archivos con garth
        with open(file_path, "rb") as f:
            garth.connectapi(
                "/upload-service/upload",
                method="POST",
                files={"file": (file_path, f, "application/octet-stream")}
            )
        return True
    except Exception as e:
        print(f"Garmin upload error: {e}")
        return False


def generate_fit_file(scale):
    fit = FitEncoder_Weight()

    raw_ts = scale.latest_records[0].measure_ts
    ts_seconds = math.trunc(raw_ts / 1000) if raw_ts > 9999999999 else int(raw_ts)
    # FIX: Convertir a datetime para que el encoder aplique el epoch de Garmin correctamente
    dt_medicion = datetime.datetime.fromtimestamp(ts_seconds)

    weight_in_kg = scale.latest_records[0].weight * 0.45359237

    rec = scale.latest_records[0]
    basal = float(rec.bmr) if rec.bmr is not None else None
    active = int(basal * 1.25) if basal is not None else None

    data = {
        'percent_fat':       float(rec.body_fat)       if rec.body_fat       is not None else None,
        'percent_hydration': float(rec.body_water)     if rec.body_water     is not None else None,
        'visceral_fat_mass': float(rec.body_vfr)       if rec.body_vfr       is not None else None,
        'bone_mass':         float(rec.bone_mineral)   if rec.bone_mineral   is not None else None,
        'muscle_mass':       float(rec.muscle)         if rec.muscle         is not None else None,
        'basal_met':         basal,
        'active_met':        active,
        'physique_rating':   float(rec.body_type or 5),
        'metabolic_age':     float(rec.metabolic_age)  if rec.metabolic_age  is not None else None,
        'visceral_fat_rating': float(rec.body_vfr)     if rec.body_vfr       is not None else None,
        'bmi':               float(rec.bmi)            if rec.bmi            is not None else None,
    }

    # FIX: Pasar dt_medicion (datetime) en todas las llamadas
    fit.write_file_info(time_created=dt_medicion)
    fit.write_file_creator()
    fit.write_device_info(timestamp=dt_medicion)
    fit.write_weight_scale(timestamp=dt_medicion, weight=weight_in_kg, **data)
    fit.finish()

    with open("wyze_scale.fit", "wb") as fitfile:
        fitfile.write(fit.getvalue())


def main():
    access_token = login_to_wyze()
    if not access_token:
        return

    client = Client(token=access_token)

    for device in client.devices_list():
        if device.type == "WyzeScale" or getattr(device.product, 'model', None) == "WL_SCU":

            scale = client.scales.info(device_mac=device.mac)

            if scale is None:
                print(f"Buscando registros profundos para {device.nickname}...")
                try:
                    desde = datetime.datetime.now() - datetime.timedelta(days=2)
                    records = client.scales.get_records(device_mac=device.mac, start_time=desde)
                    if records:
                        class ScaleData: pass
                        scale = ScaleData()
                        scale.latest_records = records
                        scale.mac = device.mac
                    else:
                        print(f"No hay mediciones recientes para {device.nickname}.")
                        continue
                except Exception as e:
                    print(f"Error en búsqueda profunda: {e}")
                    continue

            if not hasattr(scale, 'latest_records') or not scale.latest_records:
                print(f"Saltando {device.nickname}: Sin datos disponibles.")
                continue

            print(f"Scale found with MAC {device.mac}. Latest record is:")
            print(scale.latest_records)
            print(f"Body Type: {scale.latest_records[0].body_type or 5}")

            print("Generating fit data...")
            generate_fit_file(scale)
            print("Fit data generated...")

            fitfile_path  = "wyze_scale.fit"
            cksum_file_path = "cksum.txt"

            with open(fitfile_path, "rb") as fitfile:
                cksum = hashlib.md5(fitfile.read()).hexdigest()

            if os.path.exists(cksum_file_path):
                with open(cksum_file_path, "r") as cksum_file:
                    stored_cksum = cksum_file.read().strip()

                if cksum == stored_cksum:
                    print("No new measurement.")
                else:
                    print("New measurement detected. Uploading file...")
                    if upload_to_garmin(fitfile_path):
                        print("File uploaded successfully.")
                        with open(cksum_file_path, "w") as cksum_file:
                            cksum_file.write(cksum)
                    else:
                        print("File upload failed.")
            else:
                print("No chksum detected. Uploading fit file and creating chksum...")
                if upload_to_garmin(fitfile_path):
                    print("File uploaded successfully.")
                    with open(cksum_file_path, "w") as cksum_file:
                        cksum_file.write(cksum)
                    print("cksum.txt created.")
                else:
                    print("File upload failed.")


if __name__ == "__main__":
    main()
