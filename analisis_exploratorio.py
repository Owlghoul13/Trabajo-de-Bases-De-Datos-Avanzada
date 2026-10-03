import os
import glob
import statistics
from collections import defaultdict
from astropy.io import fits

ruta_datos = "./raw_data/*.fits"
archivos = glob.glob(ruta_datos)

total_campos_lista = []
nulos_lista = []
valores_numericos = defaultdict(list)
frecuencia_no_numericos = defaultdict(lambda: defaultdict(int))

print(f"Procesando {len(archivos)} archivos FITS...")

for i, archivo in enumerate(archivos):
    if (i + 1) % 300 == 0:
        print(f"Leyendo... {i + 1}/{len(archivos)}")
        
    try:
        header = fits.getheader(archivo)
        total_campos_lista.append(len(header))
        nulos = 0
        
        for key, value in header.items():
            if not key or key in ('COMMENT', 'HISTORY'):
                continue
            
            if value is None or str(value).strip() == '':
                nulos += 1
            else:
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    valores_numericos[key].append(value)
                elif isinstance(value, str):
                    frecuencia_no_numericos[key][value] += 1
                    
        nulos_lista.append(nulos)
    except:
        pass

# --- SALIDA DE DATOS ---
print("\nResumen Análisis Exploratorio:")
print(f"Promedio campos por archivo: {sum(total_campos_lista)/len(total_campos_lista):.0f}")
print(f"Promedio nulos por archivo: {sum(nulos_lista)/len(nulos_lista):.2f}")

print("\nVarianza (Campos numéricos):")
for key in ['RA', 'DEC', 'EXPTIME', 'MJD-OBS', 'UTC']:
    if key in valores_numericos and len(valores_numericos[key]) > 1:
        print(f"- {key}: {statistics.variance(valores_numericos[key]):.4f}")

print("\nDistintos y Outliers (Campos texto):")
for key in ['DATE-OBS', 'TELESCOP', 'INSTRUME', 'OBJECT', 'OBSERVER']:
    if key in frecuencia_no_numericos:
        dicc = frecuencia_no_numericos[key]
        outliers = sum(1 for val, count in dicc.items() if count == 1)
        print(f"- {key}: {len(dicc)} distintos, {outliers} outliers")
print("\n")