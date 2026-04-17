"""
config/database.py
Konfigurasi koneksi MySQL menggunakan mysql-connector-python
"""
import os
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv

load_dotenv()

# ── Pool konfigurasi ──────────────────────────────────────────
_pool_config = {
    "pool_name":    "skincare_pool",
    "pool_size":    5,
    "host":         os.getenv("DB_HOST", "localhost"),
    "port":         int(os.getenv("DB_PORT", 3306)),
    "database":     os.getenv("DB_NAME", "skincare_overclaim"),
    "user":         os.getenv("DB_USER", "root"),
    "password":     os.getenv("DB_PASSWORD", ""),
    "charset":      "utf8mb4",
    "autocommit":   False,
    "connection_timeout": 10,
}

_connection_pool = None


def _get_pool():
    global _connection_pool
    if _connection_pool is None:
        try:
            _connection_pool = pooling.MySQLConnectionPool(**_pool_config)
        except mysql.connector.Error as e:
            raise ConnectionError(f"Gagal membuat connection pool: {e}")
    return _connection_pool


def get_connection():
    """Ambil koneksi dari pool."""
    return _get_pool().get_connection()


def execute_query(sql: str, params: tuple = None, fetch: bool = False):
    """
    Eksekusi query tunggal.
    - fetch=True  → kembalikan list of dict
    - fetch=False → kembalikan last_insert_id (jika insert) atau rows affected
    """
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        if fetch:
            result = cursor.fetchall()
            return result
        else:
            conn.commit()
            # --- INI KUNCI PERBAIKANNYA ---
            # Jika ada ID yang baru dibuat (auto-increment), kembalikan ID tersebut.
            # Jika tidak, kembalikan jumlah baris yang terpengaruh (rowcount).
            if cursor.lastrowid:
                return cursor.lastrowid
            return cursor.rowcount
            # ------------------------------
    except mysql.connector.Error as e:
        conn.rollback()
        raise RuntimeError(f"Query gagal: {e}")
    finally:
        cursor.close()
        conn.close()


def execute_many(sql: str, data: list):
    """Eksekusi batch insert/update."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.executemany(sql, data)
        conn.commit()
        return cursor.rowcount
    except mysql.connector.Error as e:
        conn.rollback()
        raise RuntimeError(f"Batch query gagal: {e}")
    finally:
        cursor.close()
        conn.close()


def test_connection() -> bool:
    """Cek apakah koneksi berhasil."""
    try:
        conn = get_connection()
        conn.close()
        return True
    except Exception:
        return False
