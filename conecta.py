import pymysql

def conexion():
    return pymysql.connect(
        host='aguel.com.ar',
        user='aguelca_aguelca',
        password='gdaU0908',
        database='aguelca_bdd'
    )