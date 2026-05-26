import tkinter as tk
from tkinter import messagebox, filedialog
from ttkbootstrap import ttk
import database as db
import csv, shutil, os, json, re
from datetime import datetime, timedelta
import atexit
from app_paths import path

CONFIG_PATH = path("backup_config.json")

_DAYS = ["Lunes", "Martes", "Miércoles", "Jueves",
         "Viernes", "Sábado", "Domingo"]  # Monday=0 .. Sunday=6


def _day_name_to_index(val) -> int:
    if isinstance(val, int):
        return max(0, min(6, val))
    try:
        return _DAYS.index(str(val))
    except Exception:
        return 0


def _day_index_to_name(idx: int) -> str:
    try:
        return _DAYS[int(idx)]
    except Exception:
        return _DAYS[0]


def _sanitize_prefix(txt: str) -> str:
    txt = (txt or "").strip()
    if not txt:
        return "cra_auto"
    txt = txt.replace(" ", "_")
    txt = re.sub(r"[^A-Za-z0-9_\-]", "", txt)
    return txt or "cra_auto"


class BackupFrame(ttk.Frame):
    def __init__(self, master, on_after_import=None):
        super().__init__(master, padding=10)
        self.on_after_import = on_after_import
        self._weekly_after_id = None
        self._hourly_after_id = None

        self._build_ui()
        self._load_backup_config()

        # auto-backup al salir (sin tocar UI)
        atexit.register(lambda: self._maybe_auto_backup_on_exit())

        # cancelar timers al destruir el frame (evita afters corriendo al cerrar)
        self.bind("<Destroy>", self._on_destroy, add="+")

        # arrancar programaciones si corresponde
        self._maybe_start_periodic_backup()

    # ------------------ UI ------------------
    def _build_ui(self):
        ttk.Label(self, text="Backup / Importación", font=("-size", 14, "-weight", "bold")).pack(anchor="w", pady=(0, 8))

        # Exportación manual
        box = ttk.Labelframe(self, text="Exportar manualmente", padding=10); box.pack(fill="x", pady=(0, 8))
        ttk.Button(box, text="Exportar copia completa de la BD (.db)", command=self.export_db).pack(side="left", padx=6)
        ttk.Button(box, text="Exportar catálogo de libros (.csv)", command=self.export_csv).pack(side="left", padx=6)

        # Importación
        box2 = ttk.Labelframe(self, text="Importar", padding=10); box2.pack(fill="x", pady=(0, 8))
        ttk.Button(box2, text="Importar BD desde archivo (.db)", bootstyle="warning", command=self.import_db).pack(side="left", padx=6)
        ttk.Button(box2, text="Importar catálogo de libros (.csv)", bootstyle="info", command=self.import_csv_catalog).pack(side="left", padx=6)

        # Configuración automática
        box3 = ttk.Labelframe(self, text="Backup automático", padding=10); box3.pack(fill="x", pady=(0, 8))

        self.var_auto = tk.BooleanVar()          # al cerrar
        self.var_auto_hours = tk.BooleanVar()    # cada X horas
        self.var_hours = tk.IntVar(value=6)

        self.var_auto_weekly = tk.BooleanVar()   # semanal
        self.var_weekly_day = tk.StringVar(value=_DAYS[0])
        self.var_weekly_hour = tk.IntVar(value=9)
        self.var_weekly_min = tk.IntVar(value=0)

        self.var_path = tk.StringVar()
        self.var_limit = tk.IntVar(value=5)

        # prefijo de archivo
        self.var_prefix = tk.StringVar(value="cra_auto")

        # Cierre
        ttk.Checkbutton(box3, text="Activar backup automático al cerrar la aplicación", variable=self.var_auto).pack(anchor="w", pady=(0, 6))

        # Cada X horas
        frame_hours = ttk.Frame(box3); frame_hours.pack(fill="x", pady=2)
        ttk.Checkbutton(frame_hours, text="Activar backup automático cada X horas", variable=self.var_auto_hours).pack(side="left")
        ttk.Label(frame_hours, text="Cada").pack(side="left", padx=(6, 2))
        ttk.Spinbox(frame_hours, from_=1, to=24, textvariable=self.var_hours, width=5).pack(side="left")
        ttk.Label(frame_hours, text="hora(s)").pack(side="left")

        # Semanal
        frame_week = ttk.Frame(box3); frame_week.pack(fill="x", pady=6)
        ttk.Checkbutton(frame_week, text="Activar backup semanal", variable=self.var_auto_weekly).pack(side="left")
        ttk.Label(frame_week, text="   Día:").pack(side="left", padx=(8, 4))
        day_cbo = ttk.Combobox(frame_week, state="readonly", width=12, values=_DAYS, textvariable=self.var_weekly_day)
        day_cbo.current(0); day_cbo.pack(side="left")
        ttk.Label(frame_week, text="  Hora:").pack(side="left", padx=(8, 4))
        ttk.Spinbox(frame_week, from_=0, to=23, textvariable=self.var_weekly_hour, width=4).pack(side="left")
        ttk.Label(frame_week, text=":").pack(side="left")
        ttk.Spinbox(frame_week, from_=0, to=59, textvariable=self.var_weekly_min, width=4).pack(side="left")

        # Ruta, nombre base y límite
        path_frame = ttk.Frame(box3); path_frame.pack(fill="x", pady=2)
        ttk.Label(path_frame, text="Ruta destino *:").pack(side="left")
        ttk.Entry(path_frame, textvariable=self.var_path, width=50).pack(side="left", padx=4)
        ttk.Button(path_frame, text="Examinar", command=self._select_backup_path).pack(side="left")

        name_frame = ttk.Frame(box3); name_frame.pack(fill="x", pady=2)
        ttk.Label(name_frame, text="Nombre base del archivo:").pack(side="left")
        ttk.Entry(name_frame, textvariable=self.var_prefix, width=24).pack(side="left", padx=4)
        ttk.Label(name_frame, text="(se usará: nombre_YYYYMMDD_HHMMSS.db)").pack(side="left")

        limit_frame = ttk.Frame(box3); limit_frame.pack(fill="x", pady=2)
        ttk.Label(limit_frame, text="Máximo de copias guardadas:").pack(side="left")
        ttk.Spinbox(limit_frame, from_=1, to=50, textvariable=self.var_limit, width=5).pack(side="left", padx=4)

        ttk.Button(box3, text="Guardar configuración", bootstyle="success", command=self._save_backup_config).pack(pady=(6, 0))

        # Estado/información
        self.status = ttk.Label(self, text="", anchor="w")
        self.status.pack(fill="x", pady=(6, 0))
        ttk.Label(self, text="Sugerencia: guarda la copia en un pendrive o carpeta de red.", anchor="w").pack(fill="x")

    # ------------------ Utilidad segura de estado ------------------
    def _safe_set_status(self, text: str):
        try:
            # Verifica que el widget no haya sido destruido
            if self.winfo_exists() and self.status.winfo_exists():
                self.status.config(text=text)
        except Exception:
            pass

    # ------------------ Exportar / Importar manual ------------------
    def export_db(self):
        src = db.get_db_path()
        default = f"{_sanitize_prefix(self.var_prefix.get())}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        dst = filedialog.asksaveasfilename(defaultextension=".db", initialfile=default, filetypes=[("SQLite DB", "*.db")])
        if not dst:
            return
        try:
            shutil.copyfile(src, dst)
            messagebox.showinfo("Backup OK", f"Copia de seguridad creada en:\n{dst}")
            self._safe_set_status(f"Backup creado en {dst}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar la BD: {e}")

    def export_csv(self):
        rows = db.libros_listar()
        default = f"libros_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        dst = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=default, filetypes=[("CSV", "*.csv")])
        if not dst:
            return
        try:
            with open(dst, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["id", "titulo", "autor", "editorial", "anio", "categoria", "stock", "ubicacion"])
                for r in rows:
                    w.writerow(r)
            messagebox.showinfo("Exportación OK", f"Catálogo exportado a CSV:\n{dst}")
            self._safe_set_status(f"CSV exportado a {dst}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar CSV: {e}")

    def import_db(self):
        src = filedialog.askopenfilename(filetypes=[("SQLite DB", "*.db")])
        if not src:
            return
        if not messagebox.askyesno("Confirmar importación", "Esto reemplazará la base de datos actual. ¿Deseas continuar?"):
            return
        try:
            dst = db.get_db_path()
            shutil.copyfile(src, dst)
            messagebox.showinfo("Importación OK", "Se importó la base de datos correctamente. Reinicia la aplicación para ver los cambios.")
            if self.on_after_import:
                self.on_after_import()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo importar la BD: {e}")

    def import_csv_catalog(self):
        src = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not src:
            return
        try:
            total, agregados, actualizados, errores = 0, 0, 0, 0
            with open(src, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                required = {"titulo", "autor", "editorial", "anio", "categoria", "stock", "ubicacion"}
                if not required.issubset(set([h.lower() for h in reader.fieldnames])):
                    messagebox.showerror(
                        "Formato inválido",
                        "El CSV no tiene los encabezados esperados.\n"
                        "Se requieren: titulo, autor, editorial, anio, categoria, stock, ubicacion"
                    )
                    return
                for row in reader:
                    total += 1
                    try:
                        titulo = (row.get("titulo") or row.get("TITULO") or "").strip()
                        autor = (row.get("autor") or row.get("AUTOR") or "").strip()
                        editorial = (row.get("editorial") or row.get("EDITORIAL") or "").strip() or None
                        anio_txt = (row.get("anio") or row.get("ANIO") or "").strip()
                        categoria = (row.get("categoria") or row.get("CATEGORIA") or "").strip() or None
                        stock_txt = (row.get("stock") or row.get("STOCK") or "").strip()
                        ubicacion = (row.get("ubicacion") or row.get("UBICACION") or "").strip()

                        anio = int(anio_txt) if anio_txt else None
                        stock = int(stock_txt) if stock_txt else 0

                        if not titulo or not autor or not ubicacion:
                            raise ValueError("Campos obligatorios vacíos")

                        libro = db.libro_buscar_por_titulo_autor(titulo, autor) if hasattr(db, "libro_buscar_por_titulo_autor") else None
                        if libro:
                            db.libros_actualizar(libro[0], titulo, autor, editorial, anio, categoria, stock, ubicacion)
                            actualizados += 1
                        else:
                            db.libros_agregar(titulo, autor, editorial, anio, categoria, stock, ubicacion)
                            agregados += 1
                    except Exception:
                        errores += 1

            self._safe_set_status(f"Importación CSV: total {total} | agregados {agregados} | actualizados {actualizados} | errores {errores}")
            messagebox.showinfo(
                "Importación CSV",
                f"Proceso finalizado.\nTotal: {total}\nAgregados: {agregados}\nActualizados: {actualizados}\nErrores: {errores}"
            )
            if self.on_after_import:
                self.on_after_import()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo importar el CSV:\n{e}")

    # ------------------ Config & Schedulers ------------------
    def _select_backup_path(self):
        _path = filedialog.askdirectory()
        if _path:
            self.var_path.set(_path)

    def _save_backup_config(self):
        any_enabled = self.var_auto.get() or self.var_auto_hours.get() or self.var_auto_weekly.get()
        dest_dir = self.var_path.get().strip()
        prefix = _sanitize_prefix(self.var_prefix.get())

        if any_enabled:
            if not dest_dir or not os.path.isdir(dest_dir):
                messagebox.showerror("Configuración", "Debes seleccionar una carpeta de destino válida (obligatoria).")
                return
            parts = []
            if self.var_auto.get():
                parts.append("• Al cerrar la aplicación")
            if self.var_auto_hours.get():
                parts.append(f"• Cada {int(self.var_hours.get())} hora(s)")
            if self.var_auto_weekly.get():
                parts.append(f"• Semanal: {_day_index_to_name(_day_name_to_index(self.var_weekly_day.get()))} "
                             f"{int(self.var_weekly_hour.get()):02d}:{int(self.var_weekly_min.get()):02d}")
            resumen = (
                "¿Guardar la siguiente configuración de backup?\n\n"
                + "\n".join(parts)
                + f"\n\nDestino: {dest_dir}\nNombre base: {prefix}\nMáximo archivos: {int(self.var_limit.get())}"
            )
            if not messagebox.askyesno("Confirmar configuración de backup", resumen):
                return
        else:
            if not messagebox.askyesno(
                "Confirmar",
                "No hay ninguna copia automática activada.\n"
                "Se guardará la configuración sin programar respaldos.\n\n¿Deseas continuar?"
            ):
                return

        day_idx = _day_name_to_index(self.var_weekly_day.get())
        config = {
            "enabled": self.var_auto.get(),
            "enabled_hours": self.var_auto_hours.get(),
            "interval_hours": int(self.var_hours.get()),
            "enabled_weekly": self.var_auto_weekly.get(),
            "weekly_day": int(day_idx),
            "weekly_hour": int(self.var_weekly_hour.get()),
            "weekly_minute": int(self.var_weekly_min.get()),
            "dest": dest_dir,
            "max_backups": int(self.var_limit.get()),
            "name_prefix": prefix,
        }
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            self._safe_set_status("Configuración guardada.")
            self._cancel_schedules()
            self._maybe_start_periodic_backup()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar configuración:\n{e}")

    def _load_backup_config(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.var_auto.set(config.get("enabled", False))
                self.var_auto_hours.set(config.get("enabled_hours", False))
                self.var_hours.set(config.get("interval_hours", 6))
                self.var_auto_weekly.set(config.get("enabled_weekly", False))
                self.var_weekly_day.set(_day_index_to_name(config.get("weekly_day", 0)))
                self.var_weekly_hour.set(config.get("weekly_hour", 9))
                self.var_weekly_min.set(config.get("weekly_minute", 0))
                self.var_path.set(config.get("dest", ""))
                self.var_limit.set(config.get("max_backups", 5))
                self.var_prefix.set(config.get("name_prefix", "cra_auto"))
        except FileNotFoundError:
            pass
        except Exception as e:
            print("Error cargando configuración de backup:", e)

    def _maybe_auto_backup_on_exit(self):
        if self.var_auto.get():
            # No tocar UI durante atexit
            self._run_backup(ui_update=False)

    def _maybe_start_periodic_backup(self):
        if self.var_auto_hours.get():
            self._schedule_next_hourly()
        if self.var_auto_weekly.get():
            self._schedule_next_weekly()

    def _cancel_schedules(self):
        try:
            if self._hourly_after_id is not None:
                self.after_cancel(self._hourly_after_id)
        except Exception:
            pass
        self._hourly_after_id = None
        try:
            if self._weekly_after_id is not None:
                self.after_cancel(self._weekly_after_id)
        except Exception:
            pass
        self._weekly_after_id = None

    def _on_destroy(self, event):
        # Cancelar timers sólo cuando el frame principal (self) se destruye
        if event.widget is self:
            self._cancel_schedules()

    # ---- Cada X horas
    def _schedule_next_hourly(self):
        ms = max(1, int(self.var_hours.get()) * 3600000)
        self._hourly_after_id = self.after(ms, self._auto_backup_and_reschedule_hourly)

    def _auto_backup_and_reschedule_hourly(self):
        if self.var_auto_hours.get():
            self._run_backup()
            self._schedule_next_hourly()

    # ---- Semanal
    def _schedule_next_weekly(self):
        ms = self._ms_until_next_weekly()
        self._weekly_after_id = self.after(ms, self._auto_backup_and_reschedule_weekly)

    def _auto_backup_and_reschedule_weekly(self):
        if self.var_auto_weekly.get():
            self._run_backup()
            self._schedule_next_weekly()

    def _ms_until_next_weekly(self) -> int:
        now = datetime.now()
        target_dow = _day_name_to_index(self.var_weekly_day.get())
        target = now.replace(
            hour=int(self.var_weekly_hour.get()),
            minute=int(self.var_weekly_min.get()),
            second=0, microsecond=0
        )
        days_ahead = (target_dow - now.weekday()) % 7
        target = target + timedelta(days=days_ahead)
        if target <= now:
            target += timedelta(days=7)
        delta_ms = int((target - now).total_seconds() * 1000)
        return max(1000, delta_ms)

    # ------------------ Ejecutar backup ------------------
    def _run_backup(self, ui_update: bool = True):
        dest_dir = self.var_path.get()
        if not dest_dir or not os.path.isdir(dest_dir):
            return
        try:
            prefix = _sanitize_prefix(self.var_prefix.get())
            filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            dest_path = os.path.join(dest_dir, filename)
            shutil.copyfile(db.get_db_path(), dest_path)

            backups = sorted(
                [f for f in os.listdir(dest_dir) if f.startswith(f"{prefix}_") and f.endswith(".db")],
                reverse=True
            )
            for old in backups[self.var_limit.get():]:
                try:
                    os.remove(os.path.join(dest_dir, old))
                except Exception:
                    pass

            if ui_update:
                self._safe_set_status(f"Backup automático creado: {dest_path}")
        except Exception as e:
            # Evitar que errores en cierre rompan el proceso; log simple a consola
            print("Error creando backup automático:", e)
