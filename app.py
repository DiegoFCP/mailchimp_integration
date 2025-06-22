#!/usr/bin/env python3
import os
import sqlite3
import hashlib
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from mailchimp_marketing import Client
from mailchimp_marketing.api_client import ApiClientError

# 1) Carga de variables de entorno
load_dotenv()
MC_API_KEY = os.getenv("MAILCHIMP_API_KEY")
MC_SERVER  = os.getenv("MAILCHIMP_SERVER")
MC_LIST_ID = os.getenv("MAILCHIMP_LIST_ID")

# 2) Configuración de logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# 3) Inicialización del cliente de Mailchimp
mc = Client()
mc.set_config({
    "api_key": MC_API_KEY,
    "server":  MC_SERVER
})

# 4) Parámetro de la base de datos
DB_FILE = "reservas.db"

def init_db():
    """Crea la tabla subscriptions si no existe."""
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

def upsert_subscription(email, first_name, vehicle, service_date):
    """Inserta o actualiza la suscripción en SQLite."""
    conn = sqlite3.connect(DB_FILE)
    now = datetime.utcnow().isoformat()
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

def unsubscribe_db(email):
    """Marca como dado de baja la suscripción en SQLite."""
    conn = sqlite3.connect(DB_FILE)
    now = datetime.utcnow().isoformat()
    conn.execute("""
        UPDATE subscriptions
        SET subscribed = 0,
            unsubscribed_at = ?
        WHERE email = ?
    """, (now, email))
    conn.commit()
    conn.close()

def subscribe_mailchimp(email, first_name, vehicle, service_date):
    """Añade o actualiza el contacto en Mailchimp como subscribed."""
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
        logging.error(f"Mailchimp subscribe error: {e.text}")
        raise

def unsubscribe_mailchimp(email):
    """Marca el contacto en Mailchimp como unsubscribed."""
    subscriber_hash = hashlib.md5(email.lower().encode()).hexdigest()
    body = { "status": "unsubscribed" }
    try:
        mc.lists.update_list_member(MC_LIST_ID, subscriber_hash, body)
    except ApiClientError as e:
        logging.error(f"Mailchimp unsubscribe error: {e.text}")
        raise

# Inicializamos la base de datos
init_db()

# 5) Creación de la app Flask
app = Flask(__name__)

@app.route("/subscribe", methods=["POST"])
def subscribe():
    data = request.get_json() or {}
    # Validación de campos necesarios
    for field in ("email", "first_name", "vehicle", "service_date"):
        if field not in data:
            return jsonify({
                "success": False,
                "message": f"Falta campo: {field}"
            }), 400

    email        = data["email"]
    first_name   = data["first_name"]
    vehicle      = data["vehicle"]
    service_date = data["service_date"]

    try:
        # 5.1) Upsert local
        upsert_subscription(email, first_name, vehicle, service_date)
        # 5.2) Suscripción en Mailchimp
        subscribe_mailchimp(email, first_name, vehicle, service_date)
        return jsonify({"success": True, "message": "Subscribed"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/unsubscribe", methods=["POST"])
def unsubscribe():
    data = request.get_json() or {}
    if "email" not in data:
        return jsonify({"success": False, "message": "Falta campo: email"}), 400

    email = data["email"]
    try:
        # 5.3) Baja local
        unsubscribe_db(email)
        # 5.4) Baja en Mailchimp
        unsubscribe_mailchimp(email)
        return jsonify({"success": True, "message": "Unsubscribed"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# 6) Ejecutar la aplicación
if __name__ == "__main__":
    app.run(debug=True, port=5000)
