#!/usr/bin/env python3
import os
import sqlite3
import hashlib
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from mailchimp_marketing import Client
from mailchimp_marketing.api_client import ApiClientError

# 1) Carga de configuración
load_dotenv()  # carga MAILCHIMP_API_KEY, MAILCHIMP_SERVER, MAILCHIMP_LIST_ID
MC_API_KEY = os.getenv("MAILCHIMP_API_KEY")
MC_SERVER  = os.getenv("MAILCHIMP_SERVER")
MC_LIST_ID = os.getenv("MAILCHIMP_LIST_ID")

# Validar configuración de Mailchimp
if not MC_API_KEY or not MC_SERVER or not MC_LIST_ID:
    print("❌ Error: Faltan variables de entorno de Mailchimp.")
    print("Asegúrate de tener un archivo .env con:")
    print("MAILCHIMP_API_KEY=tu_api_key")
    print("MAILCHIMP_SERVER=us15 (o tu servidor)")
    print("MAILCHIMP_LIST_ID=tu_list_id")
    exit(1)

# Validar formato del servidor
if not MC_SERVER.startswith('us') and not MC_SERVER.startswith('eu'):
    print(f"❌ Error: Formato de servidor inválido: {MC_SERVER}")
    print("El servidor debe ser algo como 'us15', 'us1', 'eu1', etc.")
    exit(1)

# 2) Logging básico
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# 3) Cliente Mailchimp
mc = Client()
mc.set_config({ "api_key": MC_API_KEY, "server": MC_SERVER })

# 4) Inicialización de la base de datos local
DB_FILE = "reservas.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            email            TEXT    UNIQUE NOT NULL,
            first_name       TEXT,
            vehicle          TEXT,
            service_date     TEXT,
            subscribed       INTEGER DEFAULT 1,
            created_at       TEXT    NOT NULL,
            unsubscribed_at  TEXT
        )
    """)
    conn.commit()
    conn.close()

# 5) Función para insertar o actualizar suscripción local
def upsert_subscription(email, first_name, vehicle, service_date):
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        INSERT INTO subscriptions
          (email, first_name, vehicle, service_date, subscribed, created_at)
        VALUES (?, ?, ?, ?, 1, ?)
        ON CONFLICT(email) DO UPDATE SET
          first_name      = excluded.first_name,
          vehicle         = excluded.vehicle,
          service_date    = excluded.service_date,
          subscribed      = 1,
          unsubscribed_at = NULL
    """, (email, first_name, vehicle, service_date, now))
    conn.commit()
    conn.close()

# 6) Función para suscribir en Mailchimp
def subscribe_mailchimp(email, first_name, vehicle, service_date):
    subscriber_hash = hashlib.md5(email.lower().encode()).hexdigest()
    body = {
        "email_address": email,
        "status_if_new": "subscribed",
        "status":        "subscribed",
        "merge_fields": {
            "FNAME":        first_name,
            "VEHICLE":      vehicle,
            "SERVICE_DATE": service_date
        },
        "tags": ["OFFERS"]
    }
    try:
        mc.lists.set_list_member(MC_LIST_ID, subscriber_hash, body)
    except ApiClientError as e:
        logging.error(f"Mailchimp error: {e.text}")
        raise

# 7) CLI principal
def main():
    print("\n=== Suscripción de Cliente ===\n")
    # Email
    email = input("Correo electrónico del cliente: ").strip()
    # Nombre
    first_name = input("Nombre y apellido del cliente: ").strip()
    # Detalle de vehículo
    marca  = input("Marca del vehículo: ").strip()
    modelo = input("Modelo del vehículo: ").strip()
    anno   = input("Año del vehículo: ").strip()
    vehicle = f"{marca} - {modelo} - {anno}"
    # Fecha de servicio
    service_date = input("Fecha de servicio (DD-MM-YYYY): ").strip()

    try:
        # 1) Guardar localmente
        upsert_subscription(email, first_name, vehicle, service_date)
        # 2) Suscribir en Mailchimp
        subscribe_mailchimp(email, first_name, vehicle, service_date)
        print("\n Cliente suscrito y registrado correctamente.\n")
    except Exception as e:
        print(f"\n Error al suscribir al cliente: {e}\n")

if __name__ == "__main__":
    init_db()
    main()
