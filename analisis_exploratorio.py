"""
Análisis exploratorio de headers FITS (X-shooter / VLT, ESO)
Proyecto Semestral Big Data - UDP - 2026-2

Estadísticas pedidas por la guía (sección 2.1):
  1. Cantidad de campos por archivo.
  2. Cantidad de campos sin información por archivo.
  3. Varianza de los campos con información numérica.
  4. Cantidad de elementos distintos por campo con información no numérica.
  5. Cantidad de elementos con baja frecuencia (outliers) por campo no numérico.

Extras para justificar qué campos conservar (2.1) y las reglas de negocio (2.3):
  - Presencia y porcentaje de nulos por campo.
  - Conteo de archivos por tipo (ESO DPR CATG: SCIENCE, CALIB, ...).
  - Rango de fechas y archivos por día.

Todos los resultados completos quedan en CSV dentro de ./resultados_eda/
(sirven como Anexos del informe).
"""

import csv
import glob
import math
import os
import statistics
from collections import defaultdict

from astropy.io import fits
from astropy.io.fits.card import Undefined

# ----------------------------------------------------------------------
# Configuración
# ----------------------------------------------------------------------
RUTA_DATOS = "./raw_data/**/*.fits"   # recursivo: entra a subcarpetas de cada zip
CARPETA_SALIDA = "./resultados_eda"

# Valores que significan "sin información" (además de None, Undefined y NaN/inf).
# Se comparan en mayúsculas.
VALORES_VACIOS = {"", "UNKNOWN", "NOT SET"}

# Un valor es "outlier" si aparece en <= UMBRAL_OUTLIER archivos.
UMBRAL_OUTLIER = 2

# Campos que la guía pide considerar sí o sí + campos extra elegidos por el equipo.
CLAVES_NUM = ["RA", "DEC", "EXPTIME", "MJD-OBS", "UTC"]
CLAVES_TXT = ["DATE-OBS", "TELESCOP", "INSTRUME", "OBJECT", "OBSERVER"]

os.makedirs(CARPETA_SALIDA, exist_ok=True)


def salida(nombre):
    return os.path.join(CARPETA_SALIDA, nombre)


# ----------------------------------------------------------------------
# Funciones auxiliares
# ----------------------------------------------------------------------
def es_nulo(valor):
    """True si el valor del header no aporta información."""
    if valor is None or isinstance(valor, Undefined):  # `KEY =` en blanco en FITS
        return True
    if isinstance(valor, float) and not math.isfinite(valor):  # NaN / inf
        return True
    return str(valor).strip().upper() in VALORES_VACIOS


def categoria_archivo(header):
    """Tipo de archivo (SCIENCE, CALIB, ...) según ESO DPR CATG."""
    for k in ("ESO DPR CATG", "HIERARCH ESO DPR CATG", "DPR CATG"):
        if k in header:
            return str(header[k])
    return "SIN_DPR_CATG"


def pct(parte, total):
    return 100 * parte / total if total else 0.0


# ----------------------------------------------------------------------
# 1) Búsqueda de archivos (se excluyen basura de macOS: __MACOSX y ._*)
# ----------------------------------------------------------------------
todos = glob.glob(RUTA_DATOS, recursive=True)
archivos = sorted(
    a for a in todos
    if "__MACOSX" not in a.split(os.sep) and not os.path.basename(a).startswith("._")
)
print(f"Archivos .fits encontrados: {len(todos)} | válidos tras filtrar basura de macOS: {len(archivos)}")

if not archivos:
    raise SystemExit("No se encontraron archivos. Revisa RUTA_DATOS.")

# ----------------------------------------------------------------------
# 2) Lectura de headers
# ----------------------------------------------------------------------
por_archivo = []                              # (archivo, campos, nulos, categoria)
valores_numericos = defaultdict(list)         # campo -> [valores numéricos]
frecuencia_texto = defaultdict(lambda: defaultdict(int))  # campo -> {valor: conteo}
presencia = defaultdict(int)                  # campo -> en cuántos archivos aparece
nulos_campo = defaultdict(int)                # campo -> cuántas veces es nulo
tipos_campo = defaultdict(set)                # campo -> {"num", "txt", "bool"}
por_categoria = defaultdict(int)
errores = []

for i, archivo in enumerate(archivos):
    if (i + 1) % 300 == 0:
        print(f"Leyendo... {i + 1}/{len(archivos)}")

    try:
        header = fits.getheader(archivo)  # extensión 0, igual que el ejemplo de la guía
    except Exception as e:
        errores.append((archivo, str(e)))
        continue

    campos = 0
    nulos = 0

    for key, value in header.items():
        if not key or key in ("COMMENT", "HISTORY"):
            continue

        campos += 1
        presencia[key] += 1

        if es_nulo(value):
            nulos += 1
            nulos_campo[key] += 1
        elif isinstance(value, bool):
            tipos_campo[key].add("bool")
        elif isinstance(value, (int, float)):
            valores_numericos[key].append(float(value))
            tipos_campo[key].add("num")
        elif isinstance(value, str):
            frecuencia_texto[key][value] += 1
            tipos_campo[key].add("txt")

    cat = categoria_archivo(header)
    por_categoria[cat] += 1
    por_archivo.append((os.path.basename(archivo), campos, nulos, cat))

n = len(por_archivo)
print(f"Archivos leídos correctamente: {n} | con error de lectura: {len(errores)}")

if errores:
    with open(salida("errores_lectura.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["archivo", "error"])
        w.writerows(errores)
    print("Primeros errores (detalle en errores_lectura.csv):")
    for a, e in errores[:5]:
        print(f"  - {a}: {e[:100]}")

if n == 0:
    raise SystemExit("Ningún archivo se pudo leer.")

# ----------------------------------------------------------------------
# ESTADÍSTICAS 1 y 2: campos y campos sin información POR ARCHIVO
# ----------------------------------------------------------------------
with open(salida("campos_nulos_por_archivo.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["archivo", "campos", "campos_sin_info", "pct_sin_info", "dpr_catg"])
    for nombre, c, nl, cat in por_archivo:
        w.writerow([nombre, c, nl, f"{pct(nl, c):.2f}", cat])

lista_campos = [x[1] for x in por_archivo]
lista_nulos = [x[2] for x in por_archivo]


def resumen(nombre, datos):
    print(f"{nombre}: min={min(datos)}, max={max(datos)}, "
          f"promedio={statistics.mean(datos):.2f}, mediana={statistics.median(datos):.1f}")


print("\n 1 y 2: Campos por archivo (detalle en campos_nulos_por_archivo.csv)")
resumen("Campos por archivo", lista_campos)
resumen("Campos sin información por archivo", lista_nulos)

# ----------------------------------------------------------------------
# Dispersión del esquema + nulos por campo (para decidir qué campos conservar)
# ----------------------------------------------------------------------
print("\nDispersión del esquema")
print(f"Campos distintos en todo el lote: {len(presencia)}")
print(f"Presentes en todos los archivos: {sum(1 for c in presencia.values() if c == n)}")
print(f"Presentes en menos de la mitad: {sum(1 for c in presencia.values() if c < n / 2)}")
siempre_nulos = sum(1 for k, c in presencia.items() if nulos_campo[k] == c)
print(f"Campos nulos en el 100% de los archivos donde aparecen: {siempre_nulos}")

with open(salida("presencia_nulos_por_campo.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["campo", "tipo", "archivos_con_campo", "pct_presencia",
                "veces_nulo", "pct_nulo_sobre_presentes"])
    for k, c in sorted(presencia.items(), key=lambda x: -x[1]):
        tipo = "/".join(sorted(tipos_campo[k])) or "solo_nulo"
        w.writerow([k, tipo, c, f"{pct(c, n):.1f}", nulos_campo[k],
                    f"{pct(nulos_campo[k], c):.1f}"])

mixtos = [k for k, t in tipos_campo.items() if len(t) > 1]
if mixtos:
    print(f"Campos con tipos mezclados (p. ej. número y texto): {len(mixtos)} -> {mixtos[:5]}")

# ----------------------------------------------------------------------
# ESTADÍSTICA 3: varianza de TODOS los campos numéricos (varianza muestral, n-1)
# ----------------------------------------------------------------------
varianzas = {k: statistics.variance(v) for k, v in valores_numericos.items() if len(v) > 1}

with open(salida("varianzas_todos.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["campo", "n_valores", "varianza"])
    for k, v in sorted(varianzas.items(), key=lambda x: -x[1]):
        w.writerow([k, len(valores_numericos[k]), v])

constantes = sum(1 for v in varianzas.values() if v == 0)
print("\n3: Varianza de campos numéricos (tabla completa en varianzas_todos.csv)")
print(f"Campos numéricos: {len(varianzas)} | constantes (varianza = 0): {constantes}")
for key in CLAVES_NUM:
    if key in varianzas:
        print(f"- {key}: {varianzas[key]:.6g}  (n={len(valores_numericos[key])})")
    else:
        print(f"- {key}: no disponible como campo numérico")

# ----------------------------------------------------------------------
# ESTADÍSTICAS 4 y 5: distintos y outliers de TODOS los campos de texto
# ----------------------------------------------------------------------
filas = []
for key, dicc in frecuencia_texto.items():
    distintos = len(dicc)
    outliers = sum(1 for c in dicc.values() if c <= UMBRAL_OUTLIER)
    total_valores = sum(dicc.values())
    unico_por_archivo = distintos == total_valores and total_valores > 1
    filas.append((key, distintos, outliers, total_valores, unico_por_archivo))

filas.sort(key=lambda x: -x[1])

with open(salida("texto_distintos_outliers.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["campo", "distintos", f"outliers_frec<={UMBRAL_OUTLIER}",
                "valores_totales", "pct_outliers_sobre_distintos", "unico_por_archivo"])
    for key, d, o, t, u in filas:
        w.writerow([key, d, o, t, f"{pct(o, d):.1f}", u])

n_unicos = sum(1 for x in filas if x[4])
print("\n 4 y 5: Campos de texto (tabla completa en texto_distintos_outliers.csv)")
print(f"Campos de texto analizados: {len(filas)} | con valor único por archivo: {n_unicos} "
      "(en estos los 'outliers' no son significativos: son identificadores/timestamps)")
print(f"{'campo':<12}{'distintos':>10}{'outliers':>10}")
for key in CLAVES_TXT:
    if key in frecuencia_texto:
        d = frecuencia_texto[key]
        o = sum(1 for c in d.values() if c <= UMBRAL_OUTLIER)
        print(f"{key:<12}{len(d):>10}{o:>10}")
    else:
        print(f"{key:<12}{'no disponible como campo de texto':>20}")


# ----------------------------------------------------------------------
# Cruces adicionales: TELESCOP y archivos con RA/DEC según OBJECT
# ----------------------------------------------------------------------
print("\nValores de TELESCOP")
for val, c in sorted(frecuencia_texto.get("TELESCOP", {}).items(), key=lambda x: -x[1]):
    print(f"- {val}: {c}")

radec_por_object = defaultdict(lambda: [0, 0])  # object -> [con RA y DEC, total]
for archivo in archivos:
    try:
        h = fits.getheader(archivo)
    except Exception:
        continue
    obj = str(h.get("OBJECT", "SIN_OBJECT")).strip()
    tiene_radec = all(
        k in h and isinstance(h[k], (int, float)) and not isinstance(h[k], bool) and not es_nulo(h[k])
        for k in ("RA", "DEC")
    )
    radec_por_object[obj][1] += 1
    if tiene_radec:
        radec_por_object[obj][0] += 1

total_radec = sum(v[0] for v in radec_por_object.values())
total_obj = sum(v[1] for v in radec_por_object.values())
print(f"\n Archivos con RA y DEC válidos: {total_radec} de {total_obj}")
print(f"{'OBJECT':<28}{'con RA/DEC':>12}{'total':>8}")
with open(salida("radec_por_object.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["object", "con_radec", "total", "pct_con_radec"])
    for obj, (con, tot) in sorted(radec_por_object.items(), key=lambda x: -x[1][1]):
        print(f"{obj:<28}{con:>12}{tot:>8}")
        w.writerow([obj, con, tot, f"{pct(con, tot):.1f}"])

# ----------------------------------------------------------------------
# Evidencia para las reglas de negocio (2.3)
# ----------------------------------------------------------------------

print("\nArchivos por tipo (ESO DPR CATG)")
for cat, c in sorted(por_categoria.items(), key=lambda x: -x[1]):
    print(f"- {cat}: {c} ({pct(c, n):.1f}%)")

if "OBJECT" in frecuencia_texto:
    objs = sorted(frecuencia_texto["OBJECT"].items(), key=lambda x: -x[1])
    with open(salida("archivos_por_object.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["object", "archivos"])
        w.writerows(objs)
    print(f"\nArchivos por OBJECT (top 15 de {len(objs)}; completo en archivos_por_object.csv)")
    for val, c in objs[:15]:
        print(f"- {val}: {c}")

fechas = frecuencia_texto.get("DATE-OBS")
if fechas:
    por_dia = defaultdict(int)
    for fecha, c in fechas.items():
        por_dia[fecha[:10]] += c
    print(f"\nDATE-OBS: del {min(fechas)} al {max(fechas)}")
    print("Archivos por día:")
    for dia in sorted(por_dia):
        print(f"- {dia}: {por_dia[dia]}")
else:
    print("\nDATE-OBS no disponible como campo de texto.")

print(f"\nListo. CSV generados en {CARPETA_SALIDA}/")