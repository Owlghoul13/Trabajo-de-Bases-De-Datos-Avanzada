import math
import re
import numpy as np
from pymongo import MongoClient

class MotorBusquedaAstronomico:
def __init__(self, uri="mongodb+srv://proyectoBDA:BIGDATATU_CLAVE@cluster0.zmecbxl.mongodb.net/?retryWrites=true&w=majority", db_name="astronomia_bd", coleccion_name="observaciones"):
        self.cliente = MongoClient(uri)
        self.db = self.cliente[db_name]
        self.col = self.db[coleccion_name]
        
        # Diccionario auxiliar que cargará el vocabulario e IDF si tu compañero los guarda en otra colección o archivo
        self.vocabulario = {}  
        self.idf = []          
        self.matriz_v_lsi = None 

    # --- REGLA DE LIMPIEZA DE LA QUERY SEGÚN SECCIÓN 3.2 ---
    def preprocesar_query(self, texto_query):
        texto = re.sub(r'\b(unknown|not set)\b', ' ', texto_query, flags=re.IGNORECASE)
        texto = re.sub(r'(\d+)\.(\d+)(x)(\d+)', r'\1_\2\3\4', texto)
        texto = re.sub(r'([a-zA-Z0-9]+)-([a-zA-Z0-9]+)', r'\1_\2', texto)
        texto = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?', ' ', texto)
        texto = re.sub(r'[^\w\s]', ' ', texto)
        tokens = [t.lower() for t in texto.split() if t.strip()]
        return tokens

    # --- SIMILITUD DE COSENO MANUAL (SECCIÓN 3.5) ---
    @staticmethod
    def similitud_coseno(vec_a, vec_b):
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    # --- VECTORIZAR CONSULTA EN TIEMPO DE BÚSQUEDA ---
    def vectorizar_query(self, tokens, modo="TF-IDF"):
        if not self.vocabulario:
            return [1.0] * 10
            
        vec_tf = [0.0] * len(self.vocabulario)
        for t in tokens:
            if t in self.vocabulario:
                vec_tf[self.vocabulario[t]] += 1.0
                
        vec_tfidf = [tf * idf_val for tf, idf_val in zip(vec_tf, self.idf)]
        norm = math.sqrt(sum(x * x for x in vec_tfidf))
        if norm > 0:
            vec_tfidf = [x / norm for x in vec_tfidf]

        if "TF-IDF" in modo:
            return vec_tfidf
        elif "LSI" in modo and self.matriz_v_lsi is not None:
            vec_lsi = np.dot(vec_tfidf, self.matriz_v_lsi).tolist()
            norm_lsi = math.sqrt(sum(x * x for x in vec_lsi))
            return [x / norm_lsi for x in vec_lsi] if norm_lsi > 0 else vec_lsi
        return vec_tfidf

    # --- MOTOR DE BÚSQUEDA HÍBRIDO ---
    def buscar(self, query_texto=None, filtros_num=None, escenario="TF-IDF", k=5):
        mongo_filter = {}
        if filtros_num:
            if "ra_min" in filtros_num and "ra_max" in filtros_num:
                mongo_filter["coordenadas.ra"] = {"$gte": filtros_num["ra_min"], "$lte": filtros_num["ra_max"]}
            if "dec_min" in filtros_num and "dec_max" in filtros_num:
                mongo_filter["coordenadas.dec"] = {"$gte": filtros_num["dec_min"], "$lte": filtros_num["dec_max"]}
            if "fecha_min" in filtros_num and "fecha_max" in filtros_num:
                mongo_filter["fecha_observacion"] = {"$gte": filtros_num["fecha_min"], "$lte": filtros_num["fecha_max"]}

        campo_vector = "tfidf_vector" if "TF-IDF" in escenario else "lsi_vector"
        
        proyeccion = {
            "archivo_id": 1,
            "hdfs_path": 1,
            campo_vector: 1,
            "cluster_id": 1,
            "lsh_bucket": 1
        }

        candidatos = list(self.col.find(mongo_filter, proyeccion))

        # Si no hay texto semántico (ejemplo: Prueba E Espacial)
        if not query_texto or not query_texto.strip():
            return [(d["archivo_id"], d.get("hdfs_path", "hdfs://"), 1.0) for d in candidatos[:k]]

        # 2. PREPROCESAR Y VECTORIZAR QUERY ANASHE
        tokens = self.preprocesar_query(query_texto)
        vec_q = self.vectorizar_query(tokens, modo=escenario)

        # 3. PODA POR ALGORITMO DE OPTIMIZACIÓN LOL
        if "K-MEANS" in escenario:
            pass
        elif "LSH" in escenario:
            pass

        # 4. RANKING POR SIMILITUD DE COSENO MANUAL BOEEEEE
        ranking = []
        for doc in candidatos:
            vec_doc = doc.get(campo_vector, [])
            if vec_doc:
                score = self.similitud_coseno(vec_q, vec_doc)
                ranking.append((doc["archivo_id"], doc.get("hdfs_path", ""), score))

        ranking.sort(key=lambda x: x[2], reverse=True)
        return ranking[:k]