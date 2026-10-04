import glob
import json
import os
from astropy.io import fits

ruta_datos = "./raw_data/*.fits"
archivos = glob.glob(ruta_datos)
catalogo_bd = []

print(f"Extrayendo datos de {len(archivos)} archivos FITS...")

for i, archivo in enumerate(archivos):
    if (i + 1) % 300 == 0:
        print(f"Procesando... {i + 1}/{len(archivos)}")
        
    try:
        header = fits.getheader(archivo)
        nombre_archivo = os.path.basename(archivo)
        
        # 1. Extraer variables CORE (con .get() por si algún archivo no tiene el campo)
        documento = {
            "archivo_id": nombre_archivo,
            "telescopio": header.get("TELESCOP", "Desconocido"),
            "instrumento": header.get("INSTRUME", "Desconocido"),
            "objeto_celeste": header.get("OBJECT", "Desconocido"),
            "fecha_observacion": header.get("DATE-OBS", None),
            "tiempo_exposicion": header.get("EXPTIME", 0.0),
            "coordenadas": {
                "ra": header.get("RA", None),
                "dec": header.get("DEC", None)
            },
            "header_raw": {}
        }
        
        # 2. Empaquetar el resto de los metadatos en header_raw
        for key, value in header.items():
            if not key or key in ('COMMENT', 'HISTORY'):
                continue
            # Evitar duplicar los campos que ya pusimos en el CORE
            if key not in ('TELESCOP', 'INSTRUME', 'OBJECT', 'DATE-OBS', 'EXPTIME', 'RA', 'DEC'):
                documento["header_raw"][key] = value
                
        catalogo_bd.append(documento)
        
    except Exception as e:
        print(f"Error procesando {nombre_archivo}: {e}")

# 3. Exportar a formato JSON (listo para la base de datos)
archivo_salida = "catalogo_observaciones.json"
with open(archivo_salida, 'w', encoding='utf-8') as f:
    json.dump(catalogo_bd, f, indent=2, ensure_ascii=False)

print(f"\n¡Catálogo generado con éxito! Se guardaron {len(catalogo_bd)} documentos en '{archivo_salida}'.")