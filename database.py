# database.py
import os
import sqlite3
from contextlib import contextmanager
from datetime import date as _date
from pathlib import Path
from typing import Optional

from app_paths import path as data_path, local_path as exe_path

# =========================
#   Ubicación persistente
# =========================

DB_FILENAME = "cra.sqlite3"
_DB_PATH = Path(data_path(DB_FILENAME))  # %APPDATA%/Sistema_CRA/cra.sqlite3 (Windows)
_LEGACY_CANDIDATES = ("cra.db", "cra.sqlite3")  # posibles nombres viejos junto al exe


def get_db_path() -> str:
    """Ruta absoluta del archivo de base de datos (persistente en AppData)."""
    return str(_DB_PATH)


def _migrate_db_from_exe_dir_if_needed() -> None:
    """
    Si existe una BD junto al .exe/.py (legacy) y no hay BD en AppData,
    mueve la BD legacy a la carpeta de datos del usuario (AppData).
    """
    try:
        if _DB_PATH.exists():
            return
        for name in _LEGACY_CANDIDATES:
            src = Path(exe_path(name))
            if src.exists():
                _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
                src.replace(_DB_PATH)
                break
    except Exception:
        # Si algo falla, seguimos: se creará una BD nueva en AppData.
        pass


@contextmanager
def get_conn():
    """Conexión a la BD en la ruta persistente."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(get_db_path(), check_same_thread=False)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# =========================
#   Inicialización / DDL
# =========================

def init_db():
    """Crea tablas si no existen y aplica migraciones mínimas."""
    _migrate_db_from_exe_dir_if_needed()
    with get_conn() as conn:
        c = conn.cursor()

        # Libros
        c.execute("""
            CREATE TABLE IF NOT EXISTS libros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                autor TEXT NOT NULL,
                editorial TEXT,
                anio INTEGER,
                categoria TEXT,
                stock INTEGER NOT NULL CHECK (stock >= 0),
                ubicacion TEXT NOT NULL
            )
        """)
        # Asegurar columna ubicacion si viene de un esquema viejo
        c.execute("PRAGMA table_info(libros)")
        cols = [x[1] for x in c.fetchall()]
        if "ubicacion" not in cols:
            c.execute("ALTER TABLE libros ADD COLUMN ubicacion TEXT NOT NULL DEFAULT 'Sin ubicación'")

        # Lectores
        c.execute("""
            CREATE TABLE IF NOT EXISTS lectores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                curso TEXT
            )
        """)

        # Préstamos (con observación)
        c.execute("""
            CREATE TABLE IF NOT EXISTS prestamos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                libro_id INTEGER NOT NULL,
                lector_id INTEGER NOT NULL,
                fecha_prestamo TEXT NOT NULL,
                fecha_devolucion_esperada TEXT NOT NULL,
                fecha_devolucion TEXT,
                estado TEXT NOT NULL DEFAULT 'ACTIVO',
                observacion TEXT,
                FOREIGN KEY(libro_id) REFERENCES libros(id),
                FOREIGN KEY(lector_id) REFERENCES lectores(id)
            )
        """)
        # Asegurar columna observacion si viene de esquema viejo
        c.execute("PRAGMA table_info(prestamos)")
        pcols = [x[1] for x in c.fetchall()]
        if "observacion" not in pcols:
            c.execute("ALTER TABLE prestamos ADD COLUMN observacion TEXT")


# =========================
#   Libros
# =========================

def libros_listar(filtro: Optional[str] = None):
    with get_conn() as conn:
        c = conn.cursor()
        if filtro:
            like = f"%{filtro}%"
            c.execute("""
                SELECT id, titulo, autor, editorial, anio, categoria, stock, ubicacion
                FROM libros
                WHERE titulo LIKE ? OR autor LIKE ? OR categoria LIKE ? OR ubicacion LIKE ?
                ORDER BY titulo COLLATE NOCASE
            """, (like, like, like, like))
        else:
            c.execute("""
                SELECT id, titulo, autor, editorial, anio, categoria, stock, ubicacion
                FROM libros
                ORDER BY titulo COLLATE NOCASE
            """)
        return c.fetchall()


def libros_disponibles():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, titulo, stock
            FROM libros
            WHERE stock > 0
            ORDER BY titulo COLLATE NOCASE
        """)
        return c.fetchall()


def libro_get(libro_id: int):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, titulo, autor, editorial, anio, categoria, stock, ubicacion
            FROM libros WHERE id=?
        """, (libro_id,))
        return c.fetchone()


def libros_agregar(titulo, autor, editorial, anio, categoria, stock, ubicacion):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO libros (titulo, autor, editorial, anio, categoria, stock, ubicacion)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (titulo, autor, editorial, anio, categoria, stock, ubicacion))
        return c.lastrowid


def libros_actualizar(libro_id, titulo, autor, editorial, anio, categoria, stock, ubicacion):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            UPDATE libros
            SET titulo=?, autor=?, editorial=?, anio=?, categoria=?, stock=?, ubicacion=?
            WHERE id=?
        """, (titulo, autor, editorial, anio, categoria, stock, ubicacion, libro_id))
        return c.rowcount


def libros_eliminar(libro_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM libros WHERE id=?", (libro_id,))
        return c.rowcount


def libros_buscar(termino: Optional[str]):
    with get_conn() as conn:
        c = conn.cursor()
        if not termino:
            c.execute("""
                SELECT id, titulo, autor, anio, stock, ubicacion
                FROM libros
                ORDER BY id DESC
            """)
        else:
            like = f"%{termino}%"
            c.execute("""
                SELECT id, titulo, autor, anio, stock, ubicacion
                FROM libros
                WHERE titulo LIKE ? OR autor LIKE ? OR ubicacion LIKE ?
                ORDER BY id DESC
            """, (like, like, like))
        return c.fetchall()


# =========================
#   Lectores
# =========================

def lector_get_or_create(nombre: str, curso: Optional[str]):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id FROM lectores WHERE nombre=? AND (curso IS ? OR curso=?)",
            (nombre, curso, curso),
        )
        row = c.fetchone()
        if row:
            return row[0]
        c.execute("INSERT INTO lectores (nombre, curso) VALUES (?, ?)", (nombre, curso))
        return c.lastrowid


# =========================
#   Préstamos
# =========================

MAX_PRESTAMOS_POR_LECTOR = 5

def contar_prestamos_activos_por_lector(lector_id: int) -> int:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT COUNT(*) FROM prestamos WHERE lector_id=? AND estado='ACTIVO'",
            (lector_id,),
        )
        x = c.fetchone()
        return x[0] if x else 0


def prestamos_crear(libro_id, nombre_lector, curso, fecha_prestamo, fecha_esperada):
    with get_conn() as conn:
        c = conn.cursor()
        # stock
        c.execute("SELECT stock FROM libros WHERE id=?", (libro_id,))
        row = c.fetchone()
        if not row:
            raise ValueError("Libro no encontrado")
        if row[0] <= 0:
            raise ValueError("No hay stock disponible de este libro")

        # lector
        lector_id = lector_get_or_create(nombre_lector, curso)
        if contar_prestamos_activos_por_lector(lector_id) >= MAX_PRESTAMOS_POR_LECTOR:
            raise ValueError(
                f"El lector alcanzó el máximo de {MAX_PRESTAMOS_POR_LECTOR} préstamos activos."
            )

        # insertar y descontar stock
        c.execute("""
            INSERT INTO prestamos (libro_id, lector_id, fecha_prestamo, fecha_devolucion_esperada, estado)
            VALUES (?, ?, ?, ?, 'ACTIVO')
        """, (libro_id, lector_id, fecha_prestamo, fecha_esperada))
        c.execute("UPDATE libros SET stock = stock - 1 WHERE id=?", (libro_id,))
        return c.lastrowid


def prestamos_activos():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT p.id, l.titulo, le.nombre, COALESCE(le.curso,''),
                   p.fecha_prestamo, p.fecha_devolucion_esperada
            FROM prestamos p
            JOIN libros l ON p.libro_id = l.id
            JOIN lectores le ON p.lector_id = le.id
            WHERE p.estado='ACTIVO'
            ORDER BY p.fecha_prestamo DESC
        """)
        return c.fetchall()


def prestamos_devolver(prestamo_id, fecha_devolucion, observacion=None):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT libro_id FROM prestamos WHERE id=? AND estado='ACTIVO'", (prestamo_id,))
        row = c.fetchone()
        if not row:
            return 0
        libro_id = row[0]
        c.execute("""
            UPDATE prestamos
            SET fecha_devolucion=?, estado='DEVUELTO', observacion=?
            WHERE id=?
        """, (fecha_devolucion, observacion, prestamo_id))
        c.execute("UPDATE libros SET stock = stock + 1 WHERE id=?", (libro_id,))
        return c.rowcount


def prestamos_get(prestamo_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, libro_id, lector_id, fecha_prestamo, fecha_devolucion_esperada,
                   fecha_devolucion, estado, observacion
            FROM prestamos
            WHERE id=?
        """, (prestamo_id,))
        return c.fetchone()


# =========================
#   Historial / Reportes
# =========================

def _safe_date(s) -> Optional[_date]:
    """Devuelve date o None si no se puede parsear."""
    try:
        return _date.fromisoformat((s or "")[:10])
    except Exception:
        return None


def _in_range(d: Optional[_date], d_from: Optional[_date], d_to: Optional[_date]) -> bool:
    if not d:
        return False
    if d_from and d < d_from:
        return False
    if d_to and d > d_to:
        return False
    return True


def historial_filtrar(estado=None, fecha_desde=None, fecha_hasta=None, termino=None):
    """
    Devuelve tuplas:
    (p.id, l.titulo, le.nombre, COALESCE(le.curso,''), p.fecha_prestamo, p.fecha_devolucion_esperada,
     COALESCE(p.fecha_devolucion,''), p.estado, COALESCE(p.observacion,''))
    Reglas:
      - estado:
          * None / "Todos": no filtra por estado y NO aplica fechas (muestra todo).
          * "ACTIVO":     p.estado='ACTIVO' AND p.fecha_devolucion_esperada >= hoy
                          (rango se aplica sobre p.fecha_devolucion_esperada)
          * "ATRASADO":   p.estado='ACTIVO' AND p.fecha_devolucion_esperada < hoy
                          (rango se aplica sobre p.fecha_devolucion_esperada)
          * "DEVUELTO":   p.estado='DEVUELTO'
                          (rango se aplica sobre p.fecha_devolucion)
      - termino: LIKE en título o nombre del lector.
    """
    where = []
    params = []

    # término de búsqueda
    if termino:
        like = f"%{termino}%"
        where.append("(l.titulo LIKE ? OR le.nombre LIKE ?)")
        params.extend([like, like])

    hoy_iso = _date.today().isoformat()
    date_field = None

    if estado == "ACTIVO":
        where.append("p.estado='ACTIVO'")
        where.append("DATE(p.fecha_devolucion_esperada) >= DATE(?)")
        params.append(hoy_iso)
        date_field = "p.fecha_devolucion_esperada"
    elif estado == "ATRASADO":
        where.append("p.estado='ACTIVO'")
        where.append("DATE(p.fecha_devolucion_esperada) < DATE(?)")
        params.append(hoy_iso)
        date_field = "p.fecha_devolucion_esperada"
    elif estado == "DEVUELTO":
        where.append("p.estado='DEVUELTO'")
        date_field = "p.fecha_devolucion"
    else:
        # Todos: si hay fechas, usar fecha de préstamo
        if fecha_desde or fecha_hasta:
            date_field = "p.fecha_prestamo"

    if date_field:
        if fecha_desde:
            where.append(f"DATE({date_field}) >= DATE(?)")
            params.append(fecha_desde[:10])
        if fecha_hasta:
            where.append(f"DATE({date_field}) <= DATE(?)")
            params.append(fecha_hasta[:10])

    sql = """
        SELECT p.id, l.titulo, le.nombre, COALESCE(le.curso,''),
               p.fecha_prestamo, p.fecha_devolucion_esperada,
               COALESCE(p.fecha_devolucion,''), p.estado,
               COALESCE(p.observacion,'')
        FROM prestamos p
        JOIN libros l ON p.libro_id = l.id
        JOIN lectores le ON p.lector_id = le.id
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY p.id DESC"

    with get_conn() as conn:
        c = conn.cursor()
        c.execute(sql, tuple(params))
        rows = c.fetchall()

        # Filtro adicional por seguridad cuando estado=None y hay fechas
        if estado is None and (fecha_desde or fecha_hasta):
            d_from = _safe_date(fecha_desde)
            d_to   = _safe_date(fecha_hasta)
            if d_from or d_to:
                rows = [r for r in rows if _in_range(_safe_date(r[4]), d_from, d_to)]
        return rows


def reportes_prestamos_activos():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT l.titulo, le.nombre, COALESCE(le.curso,''), p.fecha_prestamo, p.fecha_devolucion_esperada
            FROM prestamos p
            JOIN libros l ON p.libro_id = l.id
            JOIN lectores le ON p.lector_id = le.id
            WHERE p.estado='ACTIVO'
            ORDER BY p.fecha_prestamo DESC
        """)
        return c.fetchall()


def reportes_stock_bajo(threshold=2):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT titulo, stock
            FROM libros
            WHERE stock <= ?
            ORDER BY stock ASC, titulo COLLATE NOCASE
        """, (threshold,))
        return c.fetchall()


def reportes_libros_mas_prestados(limit=10):
    """Devuelve los libros más prestados (título y total de veces)."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT libros.titulo, COUNT(*) as total
            FROM prestamos
            JOIN libros ON prestamos.libro_id = libros.id
            GROUP BY prestamos.libro_id
            ORDER BY total DESC
            LIMIT ?
        """, (limit,))
        return c.fetchall()
