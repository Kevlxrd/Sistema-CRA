import tkinter as tk
from tkinter import messagebox
from ttkbootstrap import ttk
from ttkbootstrap.widgets import DateEntry
import database as db
from datetime import date as _date
from utils_ui import make_scrolled_treeview

def hoy(): return _date.today()

class DevolucionesFrame(ttk.Frame):
    def __init__(self, master, on_data_changed=None):
        super().__init__(master, padding=10)
        self.on_data_changed = on_data_changed
        self._build_ui()
        self.cargar_prestamos_activos()

    def _notify(self):
        if self.on_data_changed:
            try: self.on_data_changed()
            except Exception: pass

    def _build_ui(self):
        ttk.Label(self, text="Registrar Devolución", font=("-size", 14, "-weight", "bold")).pack(anchor="w", pady=(0,8))

        # === Datos arriba ===
        action = ttk.Labelframe(self, text="Datos de devolución", padding=8)
        action.pack(fill="x", pady=(0,8))
        ttk.Label(action, text="Fecha de devolución *").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.dt_dev = DateEntry(action, width=16, dateformat="%Y-%m-%d"); self.dt_dev.set_date(hoy())
        self.dt_dev.grid(row=0, column=1, sticky="w", padx=4, pady=4)

        self.var_obs = tk.StringVar()
        ttk.Label(action, text="Observación (opcional):").grid(row=0, column=2, sticky="w", padx=8, pady=4)
        ttk.Entry(action, textvariable=self.var_obs, width=50).grid(row=0, column=3, sticky="ew", padx=4, pady=4)
        action.columnconfigure(3, weight=1)

        btns = ttk.Frame(self, padding=4); btns.pack(fill="x", pady=(0,8))
        ttk.Button(btns, text="Registrar devolución", bootstyle="success", command=self.devolver).pack(side="left", padx=6)

        # === Tabla abajo con scroll ===
        self.tree = make_scrolled_treeview(
            self,
            columns=("id","libro","lector","curso","fecha_p","fecha_e"),
            height=12,
            show="headings"
        )
        headers = {"id":"ID","libro":"Libro","lector":"Lector","curso":"Curso","fecha_p":"Fecha préstamo","fecha_e":"Fecha devolución esperada"}
        widths  = {"id":60,"libro":340,"lector":200,"curso":100,"fecha_p":130,"fecha_e":170}
        for col in self.tree["columns"]:
            self.tree.heading(col, text=headers[col], anchor="w")
            self.tree.column(col, width=widths[col], anchor="w")

    def cargar_prestamos_activos(self):
        self.tree.delete(*self.tree.get_children())
        for row in db.prestamos_activos():
            self.tree.insert("", "end", values=row)

    def devolver(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Sin selección", "Selecciona un préstamo para devolver."); return
        prestamo_id = self.tree.item(sel[0])["values"][0]
        try:
            f_d = hoy().__class__.fromisoformat(self.dt_dev.entry.get())
        except Exception:
            messagebox.showerror("Fecha inválida", "Formato de fecha inválido. Use YYYY-MM-DD."); return
        if f_d < hoy():
            messagebox.showerror("Fecha inválida", "La fecha de devolución no puede ser pasada respecto a hoy."); return

        p = db.prestamos_get(prestamo_id)
        if p:
            f_prestamo = hoy().__class__.fromisoformat(p[3])
            if f_d < f_prestamo:
                messagebox.showerror("Fecha inválida", "La devolución no puede ser anterior a la fecha de préstamo."); return

        ok = db.prestamos_devolver(prestamo_id, f_d.isoformat(), self.var_obs.get().strip() or None)
        if ok:
            self.event_generate("<<CRA-DataChanged>>", when="tail")
            messagebox.showinfo("Éxito", "Devolución registrada.")
            self.cargar_prestamos_activos(); self.var_obs.set(""); self._notify()
        else:
            messagebox.showerror("Error", "No se pudo registrar la devolución (¿ya estaba devuelto?).")
