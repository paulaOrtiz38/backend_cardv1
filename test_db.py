# Crea un script test_db.py
import psycopg2

try:
    conn = psycopg2.connect(
        dbname="cards_db",
        user="mydjango",
        password="mydjango123",
        host="localhost",
        port="5432"
    )
    print("✅ Conexión exitosa!")
    conn.close()
except Exception as e:
    print(f"❌ Error: {e}")