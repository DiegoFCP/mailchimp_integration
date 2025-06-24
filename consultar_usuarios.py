#!/usr/bin/env python3
import sqlite3
import os
from datetime import datetime

def conectar_db():
    """Conecta a la base de datos"""
    db_file = "reservas.db"
    if not os.path.exists(db_file):
        print(f" No se encontró la base de datos: {db_file}")
        return None
    
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Exception as e:
        print(f" Error al conectar a la base de datos: {e}")
        return None

def mostrar_menu():
    """Muestra el menú principal"""
    print("\n" + "="*60)
    print(" CONSULTA DE USUARIOS REGISTRADOS")
    print("="*60)
    print("1) Ver usuarios")
    print("2) Buscar por email")
    print("3) Buscar por nombre")
    print("4) Ver estadísticas")
    print("0) Salir")
    print("="*60)

def formatear_fecha(fecha_str):
    """Formatea una fecha para mejor visualización"""
    if not fecha_str:
        return "N/A"
    try:
        # Convertir de ISO a formato legible
        fecha = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
        return fecha.strftime("%d/%m/%Y %H:%M")
    except:
        return fecha_str

def mostrar_usuario(usuario, numero=None):
    """Muestra un usuario formateado"""
    if numero:
        print(f"\n🔹 Usuario #{numero}")
    else:
        print(f"\n🔹 Usuario")
    
    print(f"   ID: {usuario[0]}")
    print(f"   📧 Email: {usuario[1]}")
    print(f"   👤 Nombre: {usuario[2]}")
    print(f"   🚗 Vehículo: {usuario[3]}")
    print(f"   📅 Fecha servicio: {usuario[4]}")
    print(f"   ✅ Suscrito: {'Sí' if usuario[5] else 'No'}")
    print(f"   📅 Creado: {formatear_fecha(usuario[6])}")
    print(f"   📅 Baja: {formatear_fecha(usuario[7])}")
    print(f"   ⭐ Rating: {usuario[8] or 'N/A'}")
    print("-" * 50)

def consultar_todos_usuarios():
    """Muestra todos los usuarios"""
    conn = conectar_db()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subscriptions ORDER BY created_at DESC")
        usuarios = cursor.fetchall()
        
        if not usuarios:
            print("\n📭 No hay usuarios registrados")
            return
        
        print(f"\n📋 TOTAL DE USUARIOS: {len(usuarios)}")
        print("="*60)
        
        for i, usuario in enumerate(usuarios, 1):
            mostrar_usuario(usuario, i)
        
    except Exception as e:
        print(f"❌ Error al consultar usuarios: {e}")
    finally:
        conn.close()

    """Muestra solo usuarios suscritos"""
    conn = conectar_db()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subscriptions WHERE subscribed = 1 ORDER BY created_at DESC")
        usuarios = cursor.fetchall()
        
        if not usuarios:
            print("\n📭 No hay usuarios suscritos")
            return
        
        print(f"\n✅ USUARIOS SUSCRITOS: {len(usuarios)}")
        print("="*60)
        
        for i, usuario in enumerate(usuarios, 1):
            mostrar_usuario(usuario, i)
        
    except Exception as e:
        print(f"❌ Error al consultar usuarios: {e}")
    finally:
        conn.close()

def buscar_por_email():
    """Busca usuario por email"""
    email = input("\n🔍 Ingrese email a buscar: ").strip()
    if not email:
        print("❌ Email no puede estar vacío")
        return
    
    conn = conectar_db()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subscriptions WHERE email LIKE ?", (f"%{email}%",))
        usuarios = cursor.fetchall()
        
        if not usuarios:
            print(f"\n🔍 No se encontraron usuarios con email que contenga: {email}")
            return
        
        print(f"\n🔍 RESULTADOS PARA '{email}': {len(usuarios)}")
        print("="*60)
        
        for i, usuario in enumerate(usuarios, 1):
            mostrar_usuario(usuario, i)
        
    except Exception as e:
        print(f"❌ Error al buscar usuario: {e}")
    finally:
        conn.close()

def buscar_por_nombre():
    """Busca usuario por nombre"""
    nombre = input("\n🔍 Ingrese nombre a buscar: ").strip()
    if not nombre:
        print("❌ Nombre no puede estar vacío")
        return
    
    conn = conectar_db()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subscriptions WHERE first_name LIKE ?", (f"%{nombre}%",))
        usuarios = cursor.fetchall()
        
        if not usuarios:
            print(f"\n🔍 No se encontraron usuarios con nombre que contenga: {nombre}")
            return
        
        print(f"\n🔍 RESULTADOS PARA '{nombre}': {len(usuarios)}")
        print("="*60)
        
        for i, usuario in enumerate(usuarios, 1):
            mostrar_usuario(usuario, i)
        
    except Exception as e:
        print(f"❌ Error al buscar usuario: {e}")
    finally:
        conn.close()

def mostrar_estadisticas():
    """Muestra estadísticas de la base de datos"""
    conn = conectar_db()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        # Total de usuarios
        cursor.execute("SELECT COUNT(*) FROM subscriptions")
        total = cursor.fetchone()[0]
        
        # Usuarios suscritos
        cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE subscribed = 1")
        suscritos = cursor.fetchone()[0]
        
        # Usuarios dados de baja
        cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE subscribed = 0")
        bajas = cursor.fetchone()[0]
        
        # Usuarios con rating
        cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE rating IS NOT NULL")
        con_rating = cursor.fetchone()[0]
        
        # Promedio de rating
        cursor.execute("SELECT AVG(rating) FROM subscriptions WHERE rating IS NOT NULL")
        avg_rating = cursor.fetchone()[0]
        
        # Último registro
        cursor.execute("SELECT created_at FROM subscriptions ORDER BY created_at DESC LIMIT 1")
        ultimo = cursor.fetchone()
        
        print("\n📊 ESTADÍSTICAS DE LA BASE DE DATOS")
        print("="*50)
        print(f"👥 Total de usuarios: {total}")
        print(f"✅ Usuarios suscritos: {suscritos}")
        print(f"❌ Usuarios dados de baja: {bajas}")
        print(f"⭐ Usuarios con rating: {con_rating}")
        if avg_rating:
            print(f"📈 Promedio de rating: {avg_rating:.1f}/5")
        if ultimo:
            print(f"📅 Último registro: {formatear_fecha(ultimo[0])}")
        print("="*50)
        
    except Exception as e:
        print(f"❌ Error al obtener estadísticas: {e}")
    finally:
        conn.close()

def main():
    """Función principal"""
    while True:
        mostrar_menu()
        opcion = input("\nSeleccione una opción: ").strip()
        
        if opcion == "1":
            consultar_todos_usuarios()
        elif opcion == "2":
            buscar_por_email()
        elif opcion == "3":
            buscar_por_nombre()
        elif opcion == "4":
            mostrar_estadisticas()
            ()
        elif opcion == "0":
            print("\n Hasta luego!")
            break
        else:
            print("\n Opción no válida. Intente nuevamente.")
        
        input("\nPresione Enter para continuar...")

if __name__ == "__main__":
    main() 