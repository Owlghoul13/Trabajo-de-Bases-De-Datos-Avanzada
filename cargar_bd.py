import json
import psycopg2

# 1. Configurar la conexión a PostgreSQL
# IMPORTANTE: Cambia 'tu_contraseña' por la contraseña real de tu base de datos local
# Si tu usuario no es 'postgres', cámbialo también.
try:
    conexion = psycopg2.connect(
        host="localhost",
        database="astronomia_bd",
        user="postgres",
        password="13082005"
    )
    cursor = conexion.cursor()
    print("Conexión exitosa a PostgreSQL.")

    # 2. Cargar los datos del archivo JSON
    archivo_json = "catalogo_observaciones.json"
    with open(archivo_json, 'r', encoding='utf-8') as f:
        datos = json.load(f)
        
    print(f"Preparando para insertar {len(datos)} registros...")

    # 3. Consulta SQL para insertar datos
    # Usamos ON CONFLICT DO NOTHING para evitar errores si ejecutas el script dos veces
    query_insertar = """
        INSERT INTO observaciones 
        (archivo_id, telescopio, instrumento, objeto_celeste, fecha_observacion, tiempo_exposicion, ra, dec, header_raw)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (archivo_id) DO NOTHING;
    """

    # 4. Iterar e insertar
    registros_insertados = 0
    for doc in datos:
        # Extraemos las coordenadas asegurándonos de que existan
        coords = doc.get("coordenadas", {})
        ra = coords.get("ra")
        dec = coords.get("dec")
        
        # Convertimos el diccionario header_raw a un string JSON para que PostgreSQL lo acepte en la columna JSONB
        header_raw_json = json.dumps(doc.get("header_raw", {}))

        # Valores a insertar
        valores = (
            doc.get("archivo_id"),
            doc.get("telescopio"),
            doc.get("instrumento"),
            doc.get("objeto_celeste"),
            doc.get("fecha_observacion"),
            doc.get("tiempo_exposicion"),
            ra,
            dec,
            header_raw_json
        )
        
        cursor.execute(query_insertar, valores)
        registros_insertados += 1
        
        if registros_insertados % 300 == 0:
            print(f"Insertados {registros_insertados} de {len(datos)}...")

    # 5. Confirmar los cambios (Commit)
    conexion.commit()
    print("\n¡Carga finalizada con éxito!")

except Exception as e:
    print(f"Ocurrió un error: {e}")

finally:
    # 6. Cerrar la conexión siempre, pase lo que pase
    if 'conexion' in locals() and conexion:
        cursor.close()
        conexion.close()
        print("Conexión a PostgreSQL cerrada.")