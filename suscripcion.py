#!/usr/bin/env python3
import os
import sqlite3
import hashlib
import logging
import re
from datetime import datetime, timezone
from dotenv import load_dotenv
from mailchimp_marketing import Client
from mailchimp_marketing.api_client import ApiClientError

# --- Funciones de validación ---
def validar_email(email):
    if not email or not email.strip():
        return False, "El email no puede estar vacío"
    patron_email = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(patron_email, email):
        return False, "Formato de email inválido"
    return True, "Email válido"

def validar_nombre(nombre):
    if not nombre or not nombre.strip():
        return False, "El nombre no puede estar vacío"
    if len(nombre.strip()) < 2 or len(nombre.strip()) > 50:
        return False, "El nombre debe tener entre 2 y 50 caracteres"
    if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', nombre):
        return False, "El nombre solo puede contener letras y espacios"
    return True, "Nombre válido"

def validar_vehiculo(marca, modelo, anno):
    if not marca.strip() or not modelo.strip() or not anno.strip():
        return False, "Marca, modelo y año no pueden estar vacíos"
    try:
        anno_int = int(anno)
        if anno_int < 1900 or anno_int > 2030:
            return False, "El año debe estar entre 1900 y 2030"
    except ValueError:
        return False, "El año debe ser un número válido"
    return True, "Vehículo válido"

def validar_fecha(fecha_str):
    if not fecha_str.strip():
        return False, "La fecha no puede estar vacía"
    if not re.match(r'^\d{2}-\d{2}-\d{4}$', fecha_str):
        return False, "Formato de fecha inválido. Use DD-MM-YYYY"
    try:
        fecha = datetime.strptime(fecha_str, "%d-%m-%Y")
        ahora = datetime.now()
        if fecha > ahora.replace(year=ahora.year + 1):
            return False, "La fecha no puede ser más de 1 año en el futuro"
        if fecha < ahora.replace(year=ahora.year - 10):
            return False, "La fecha no puede ser más de 10 años en el pasado"
        return True, "Fecha válida"
    except ValueError:
        return False, "Fecha inválida"

def validar_rating(rating_str):
    if not rating_str.strip():
        return False, None  # rating opcional
    if not rating_str.isdigit():
        return False, "La calificación debe ser un número entre 1 y 5"
    val = int(rating_str)
    if val < 1 or val > 5:
        return False, "La calificación debe estar entre 1 y 5"
    return True, val

# --- Flujo de obtención de datos ---
def obtener_datos_con_reintentos():
    datos = {}
    # email
    while True:
        e = input("Correo electrónico del cliente: ").strip()
        ok, msg = validar_email(e)
        if ok:
            datos['email'] = e
            break
        print(f"❌ {msg}\n")
    # nombre
    while True:
        n = input("Nombre y apellido del cliente: ").strip()
        ok, msg = validar_nombre(n)
        if ok:
            datos['nombre'] = n
            break
        print(f"❌ {msg}\n")
    # vehículo
    while True:
        m = input("Marca del vehículo: ").strip()
        mo = input("Modelo del vehículo: ").strip()
        a = input("Año del vehículo: ").strip()
        ok, msg = validar_vehiculo(m, mo, a)
        if ok:
            datos['vehicle'] = f"{m} - {mo} - {a}"
            break
        print(f"❌ {msg}\n")
    # fecha
    while True:
        f = input("Fecha de servicio (DD-MM-YYYY): ").strip()
        ok, msg = validar_fecha(f)
        if ok:
            datos['service_date'] = f
            break
        print(f"❌ {msg}\n")
    return datos

def mostrar_resumen(datos):
    print("\n" + "="*50)
    print(" RESUMEN DE DATOS")
    print("="*50)
    print(f" Email: {datos['email']}")
    print(f" Nombre: {datos['nombre']}")
    print(f" Vehículo: {datos['vehicle']}")
    print(f" Fecha de servicio: {datos['service_date']}")
    print("="*50)

def confirmar_datos():
    while True:
        r = input("¿Los datos son correctos? (S/N): ").strip().upper()
        if r in ("S","SI","SÍ","Y","YES"):
            return True
        if r in ("N","NO"):
            return False

# --- Configuración Mailchimp y DB ---
load_dotenv()
MC_API_KEY = os.getenv("MAILCHIMP_API_KEY")
MC_SERVER  = os.getenv("MAILCHIMP_SERVER")
MC_LIST_ID = os.getenv("MAILCHIMP_LIST_ID")
if not MC_API_KEY or not MC_SERVER or not MC_LIST_ID:
    print("Error: revisa las variables de Mailchimp en tu .env"); exit(1)
if not (MC_SERVER.startswith("us") or MC_SERVER.startswith("eu")):
    print(f"Error: servidor inválido ({MC_SERVER})"); exit(1)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

mc = Client()
mc.set_config({ "api_key": MC_API_KEY, "server": MC_SERVER })

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
            unsubscribed_at  TEXT,
            rating           INTEGER
        )
    """)
    conn.commit()
    conn.close()

# --- Persistencia local ---
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

def update_rating_db(email, rating):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        UPDATE subscriptions
        SET rating = ?
        WHERE email = ?
    """, (rating, email))
    conn.commit()
    conn.close()

# --- Mailchimp API ---
def subscribe_mailchimp(email, first_name, vehicle, service_date):
    h = hashlib.md5(email.lower().encode()).hexdigest()
    body = {
        "email_address": email,
        "status_if_new": "subscribed",
        "status":        "subscribed",
        "merge_fields": {
            "FNAME":        first_name,
            "VEHICLE":      vehicle,
            "SERVICE_DATE": service_date
        },
        "tags": ["2025"]
    }
    try:
        mc.lists.set_list_member(MC_LIST_ID, h, body)
    except ApiClientError as e:
        logging.error(f"Mailchimp error: {e.text}")
        raise

def update_rating_mailchimp(email, rating):
    h = hashlib.md5(email.lower().encode()).hexdigest()
    body = { "merge_fields": { "RATING": rating } }
    try:
        mc.lists.update_list_member(MC_LIST_ID, h, body)
    except ApiClientError as e:
        logging.error(f"Mailchimp rating error: {e.text}")
        raise

# --- CLI principal ---
def main():
    print("\n=== Suscripción de Cliente ===\n")
    datos = obtener_datos_con_reintentos()
    mostrar_resumen(datos)
    if not confirmar_datos():
        print("\nSuscripción cancelada.\n")
        return

    try:
        init_db()
        upsert_subscription(
            datos['email'], datos['nombre'],
            datos['vehicle'], datos['service_date']
        )
        subscribe_mailchimp(
            datos['email'], datos['nombre'],
            datos['vehicle'], datos['service_date']
        )
        # Solicitar rating al cliente
        while True:
            rstr = input("Calificación del servicio (1-5, opcional): ").strip()
            ok, val = validar_rating(rstr)
            if ok:
                if val is not None:
                    update_rating_db(datos['email'], val)
                    update_rating_mailchimp(datos['email'], val)
                    print(f" Calificación {val} registrada.\n")
                break
            print(f" {val}\n")

        print("✅ Cliente suscrito y registrado correctamente.\n")
    except Exception as e:
        print(f"\n Error al suscribir al cliente: {e}\n")

if __name__ == "__main__":
    main()
