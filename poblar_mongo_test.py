import json
import numpy as np
from pymongo import MongoClient

# 1. Conexión a MongoDB local
uri = "mongodb+srv://proyectoBDA:BIGDATA@cluster0.zmecbxl.mongodb.net/?retryWrites=true&w=majority"
cliente = MongoClient(uri)
db = cliente["astronomia_bd"]
coleccion = db["observaciones"]

# Limpiar colección previa para pruebas limpias
coleccion.delete_many({})
print("Colección reiniciada.")

# 2. Leer los datos base que ya tienes
archivo_json = "catalogo_observaciones.json"
try:
    with open(archivo_json, "r", encoding="utf-8") as f:
        datos = json.load(f)
except FileNotFoundError:
    print(f"No se encontró {archivo_json}, generando datos sintéticos...")
    datos = []

print(f"Procesando {len(datos)} registros para MongoDB...")

# Simulamos dimensiones vectoriales para pruebas del motor (ej: 10 términos TF-IDF, 5 componentes LSI)
dim_tfidf = 10
dim_lsi = 5

documentos_mongo = []
for i, d in enumerate(datos):
    coords = d.get("coordenadas", {})
    
    # Simulación de vectores normalizados (esto luego lo reemplazará el script de Spark de tu compañero)
    vec_tfidf = np.random.rand(dim_tfidf)
    vec_tfidf /= np.linalg.norm(vec_tfidf)
    
    vec_lsi = np.random.rand(dim_lsi)
    vec_lsi /= np.linalg.norm(vec_lsi)
    
    doc = {
        "_id": d.get("archivo_id", f"fits_{i}"),
        "archivo_id": d.get("archivo_id"),
        "hdfs_path": f"hdfs://localhost:9000/raw_data/{d.get('archivo_id')}",
        "telescopio": d.get("telescopio"),
        "instrumento": d.get("instrumento"),
        "objeto_celeste": d.get("objeto_celeste"),
        "fecha_observacion": d.get("fecha_observacion"),
        "tiempo_exposicion": d.get("tiempo_exposicion"),
        "coordenadas": {
            "ra": coords.get("ra"),
            "dec": coords.get("dec")
        },
        "tfidf_vector": vec_tfidf.tolist(),
        "lsi_vector": vec_lsi.tolist(),
        "cluster_id": int(i % 3),         # 3 clusters para probar K-Means
        "lsh_bucket": f"bucket_{i % 4}"   # 4 buckets para probar LSH
    }
    documentos_mongo.append(doc)

# 3. Inserción masiva en MongoDB
if documentos_mongo:
    coleccion.insert_many(documentos_mongo)
    print(f"¡Éxito! Se insertaron {len(documentos_mongo)} documentos en MongoDB.")

# 4. Crear índices para los filtros numéricos (Acelera la búsqueda dura)
coleccion.create_index([("coordenadas.ra", 1), ("coordenadas.dec", 1)])
coleccion.create_index([("fecha_observacion", 1)])
print("Índices numéricos creados con éxito.")