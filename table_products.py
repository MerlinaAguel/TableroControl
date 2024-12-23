import pandas as pd
from conecta import conexion

# Leer el archivo CSV
file_path = 'datasets/products.csv'
data = pd.read_csv(file_path, delimiter=',', decimal='.', encoding='utf-8')

# Configurar nombres de columnas para SQL
data.columns = [
    "product_id",
    "variant_id",
    "product_title",
    "product_status",
    "variant_price",
    "variant_stock",
    "variant_sku",
    "variant_weight"
]

# Limpiar y convertir columnas
data["product_title"] = data["product_title"].str.replace(r"[^\x00-\x7F]+", "", regex=True)  # Eliminar caracteres no ASCII

for col in [
    "product_id",
    "variant_id",
    "variant_price",
    "variant_sku",
    "variant_weight"
]:
    data[col] = (
        data[col]
        .astype(str)  # Asegurar que todo es texto
        .str.replace(',', '', regex=False)  # Eliminar comas decimales
        .replace('--', '0')  # Manejar valores inválidos
        .astype(float if col in ["variant_price", "variant_weight"] else int)  # Convertir según el tipo
    )

# Conectar y cargar datos
try:
    connection = conexion()
    cursor = connection.cursor()

    # Verificar si la tabla existe
    check_table_query = """
    SELECT COUNT(*)
    FROM information_schema.tables
    WHERE table_schema = %s AND table_name = 'products';
    """
    cursor.execute(check_table_query, (connection.db,))
    table_exists = cursor.fetchone()[0] > 0

    if table_exists:
        print("La tabla 'products' ya existe. Procediendo a vaciarla.")
        truncate_table_query = "TRUNCATE TABLE products;"
        cursor.execute(truncate_table_query)
    else:
        print("Creando la tabla 'products'.")
        create_table_query = """
        CREATE TABLE products (
            product_id INT,
            variant_id INT,
            product_title VARCHAR(255),
            product_status VARCHAR(50),
            variant_price FLOAT,
            variant_stock VARCHAR(50),
            variant_sku INT,
            variant_weight FLOAT
        );
        """
        cursor.execute(create_table_query)

    # Insertar datos fila por fila con manejo de errores
    skipped_rows = []

    for index, row in data.iterrows():
        try:
            insert_query = """
            INSERT INTO products (
                product_id, variant_id, product_title, product_status, variant_price,
                variant_stock, variant_sku, variant_weight
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
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

    print("Datos cargados exitosamente en la tabla 'products'.")

except pymysql.MySQLError as e:
    print(f"Error al trabajar con la base de datos: {e}")
finally:
    if 'connection' in locals() and connection.open:
        connection.close()
