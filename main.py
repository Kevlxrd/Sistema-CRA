import os, json
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import database as db
from catalogo import CatalogoFrame
from prestamos import PrestamosFrame
from devoluciones import DevolucionesFrame
from historial_reportes import HistorialReportesFrame
from backup import BackupFrame
from derechos import DerechosAutorFrame, COPYRIGHT_TEXT
from contacto import ContactoFrame
from utils_ui import center_window
# from license_view import LicenciaFrame  # opcional si quieres la pestaña
from security import (
    ensure_trial_license_if_absent,
    enforce_monotonic_clock_or_exit,
    check_license_or_exit,
    register_license_persistence_on_exit,   # <--- NUEVO
)
from app_paths import path
from license_view import LicenciaFrame

APP_TITLE = "Sistema CRA - Gestión de Biblioteca"
THEME_LIGHT = "flatly"
THEME_DARK  = "darkly"
UI_CONFIG_PATH = path("ui_config.json")
VERSION = "1.5"

def _load_ui_config():
    try:
        if os.path.exists(UI_CONFIG_PATH):
            with open(UI_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("theme") or THEME_LIGHT
    except Exception:
        pass
    return THEME_LIGHT

def _save_ui_config(theme_name: str):
    try:
        with open(UI_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"theme": theme_name}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _is_dark(theme_name: str) -> bool:
    return theme_name.lower() == THEME_DARK.lower()

def main():
    db.init_db()

    # ===== Trial de 3 días si no hay licencia ====
    ensure_trial_license_if_absent()
   # si tu main crea app después, pásala luego; no es obligatorio aquí

    # Registrar persistencia al salir (copia licencia cercana al exe -> AppData)
    register_license_persistence_on_exit()

    current_theme = _load_ui_config()
    app = tb.Window(themename=current_theme)
    app.title(APP_TITLE)
    app.geometry("1280x760")
    app.minsize(1100, 680)
    center_window(app)

    # ===== Enforzar licencia al ARRANQUE =====
        
    
    enforce_monotonic_clock_or_exit(app)
    check_license_or_exit(app)


    # ---- Barra superior + toggle oscuro ----
    topbar = tb.Frame(app)
    tb.Label(topbar, text=APP_TITLE, font=("-size", 16, "-weight", "bold")).pack(side=LEFT, anchor="w")
    topbar.pack(fill=X, side=TOP)

    # Toggle oscuro a la derecha
    dark_var = tb.BooleanVar(value=_is_dark(current_theme))
    dark_btn = tb.Checkbutton(
        topbar, text="  Modo oscuro",
        variable=dark_var, bootstyle="success-round-toggle", width=13
    )
    dark_btn.pack(side=RIGHT, padx=10, pady=6)

    def on_toggle_theme():
        nonlocal current_theme
        new_theme = THEME_DARK if dark_var.get() else THEME_LIGHT
        app.style.theme_use(new_theme)
        current_theme = new_theme
        _save_ui_config(new_theme)
        # Notificar colores de tablas
        try: tab_catalogo.apply_tree_colors(_is_dark(new_theme))
        except Exception: pass
        try: tab_historial.apply_tree_colors(_is_dark(new_theme))
        except Exception: pass

    dark_btn.configure(command=on_toggle_theme)

    # Notebook principal
    notebook = tb.Notebook(app); notebook.pack(fill=BOTH, expand=YES)

    # Pestañas
    def refresh_all():
        try: tab_catalogo.cargar_tabla()
        except Exception: pass
        try:
            tab_prestamos.cargar_libros_disponibles()
            tab_prestamos.cargar_prestamos_activos()
        except Exception: pass
        try: tab_devoluciones.cargar_prestamos_activos()
        except Exception: pass
        try: tab_historial.refresh()
        except Exception: pass

    tab_catalogo     = CatalogoFrame(notebook, on_data_changed=refresh_all)
    tab_prestamos    = PrestamosFrame(notebook, on_data_changed=refresh_all)
    tab_devoluciones = DevolucionesFrame(notebook, on_data_changed=refresh_all)
    tab_historial    = HistorialReportesFrame(notebook)
    tab_backup       = BackupFrame(notebook, on_after_import=refresh_all)
    tab_derechos     = DerechosAutorFrame(notebook)
    tab_contacto     = ContactoFrame(notebook)
    tab_licencia   = LicenciaFrame(notebook)  # si quieres mostrar la pestaña al usuario

    notebook.add(tab_catalogo,     text="Catálogo")
    notebook.add(tab_prestamos,    text="Préstamos")
    notebook.add(tab_devoluciones, text="Devoluciones")
    notebook.add(tab_historial,    text="Historial / Reportes")
    notebook.add(tab_backup,       text="Backup / Importación")
    notebook.add(tab_derechos,     text="Derechos de autor")
    notebook.add(tab_contacto,     text="Contacto")
    notebook.add(tab_licencia,    text="Licencia")  # opcional

    try: tab_catalogo.apply_tree_colors(_is_dark(current_theme))
    except Exception: pass
    try: tab_historial.apply_tree_colors(_is_dark(current_theme))
    except Exception: pass

    # Status
    status = tb.Label(app, text=COPYRIGHT_TEXT, anchor="e"); status.pack(fill=X, side=BOTTOM)
    app.mainloop()

if __name__ == "__main__":
    main()
