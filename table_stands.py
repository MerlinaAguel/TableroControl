import pandas as pd
from conecta import conexion

# Leer el archivo CSV
file_path = 'datasets/stands.csv'
data = pd.read_csv(file_path, delimiter=';', decimal=',', encoding='utf-8')

# Configurar nombres de columnas para SQL
data.columns = [
    "fecha",
    "origen_base_datos",
    "comprobante",
    "item_cantidad",
    "articulo_codigo",
    "articulo_descripcion",
    "item_monto_sin_impuestos",
    "item_monto_con_impuestos",
    "item_descuento_sin_impuestos",
    "item_descuento_con_impuestos",
    "item_monto_neto_sin_impuestos",
    "item_monto_neto"
]

# Convertir datos de fecha y montos
# Manejar formato ddmmyy para convertirlo a DATE en SQL
data["fecha"] = pd.to_datetime(data["fecha"].astype(str), format='%d/%m/%Y', errors='coerce')

for col in [
    "item_monto_sin_impuestos",
    "item_monto_con_impuestos",
    "item_descuento_sin_impuestos",
    "item_descuento_con_impuestos",
    "item_monto_neto_sin_impuestos",
    "item_monto_neto"
]:
    data[col] = (
        data[col]
        .astype(str)  # Asegurar que todo es texto
        .str.replace('.', '', regex=False)  # Eliminar separadores de miles
        .str.replace(',', '', regex=False)  # Eliminar comas decimales
        .astype(int)  # Convertir a int
    )

# Conectar y cargar datos
try:
    connection = conexion()
    cursor = connection.cursor()

    # Verificar si la tabla existe
    check_table_query = """
    SELECT COUNT(*)
    FROM information_schema.tables
    WHERE table_schema = %s AND table_name = 'stands';
    """
    cursor.execute(check_table_query, (connection.db.decode(),))
    table_exists = cursor.fetchone()[0] > 0

    if table_exists:
        # Vaciar la tabla si ya existe
        truncate_table_query = "TRUNCATE TABLE stands;"
        cursor.execute(truncate_table_query)
    else:
        # Crear la tabla si no existe
        create_table_query = """
        CREATE TABLE stands (
            fecha DATE,
            origen_base_datos VARCHAR(50),
            comprobante VARCHAR(50),
            item_cantidad INT,
            articulo_codigo INT,
            articulo_descripcion VARCHAR(255),
            item_monto_sin_impuestos INT,
            item_monto_con_impuestos INT,
            item_descuento_sin_impuestos INT,
            item_descuento_con_impuestos INT,
            item_monto_neto_sin_impuestos INT,
            item_monto_neto INT
        );
        """
        cursor.execute(create_table_query)

    # Insertar datos fila por fila con manejo de errores
    skipped_rows = []

    for index, row in data.iterrows():
        try:
            insert_query = """
            INSERT INTO stands (
                fecha, origen_base_datos, comprobante, item_cantidad, articulo_codigo,
                articulo_descripcion, item_monto_sin_impuestos, item_monto_con_impuestos,
                item_descuento_sin_impuestos, item_descuento_con_impuestos,
                item_monto_neto_sin_impuestos, item_monto_neto
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
            cursor.execute(insert_query, tuple(row))
        except Exception as e:
            print(f"Error al insertar la fila {index}: {e}")
            skipped_rows.append((index, row, str(e)))  # Guardar fila problemática

    # Confirmar los cambios
    connection.commit()

    # Informar filas omitidas
    print(f"Se omitieron {len(skipped_rows)} filas.")
    for skipped in skipped_rows:
        print(f"Fila {skipped[0]} con error: {skipped[2]}")

    print("Datos cargados exitosamente en la tabla 'stands'.")

except pymysql.MySQLError as e:
    print(f"Error al trabajar con la base de datos: {e}")
finally:
    if 'connection' in locals() and connection.open:
        connection.close()
