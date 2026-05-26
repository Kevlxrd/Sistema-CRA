import tkinter as tk
from ttkbootstrap import ttk
from ttkbootstrap.widgets import DateEntry
import database as db
from datetime import date as _date, datetime
from tkinter import filedialog, messagebox
import csv

ESTADOS = ["Todos", "ACTIVO", "DEVUELTO", "ATRASADO"]

def _parse_iso(dtxt):
    if not dtxt:
        return None
    try:
        return _date.fromisoformat(dtxt[:10])
    except Exception:
        return None

def _in_range(d, d_from, d_to):
    if d is None:
        return False
    if d_from and d < d_from:
        return False
    if d_to and d > d_to:
        return False
    return True


class HistorialReportesFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self._build_ui()
        self.apply_tree_colors(is_dark=False)
        self.cargar_historial()
        # refrescar automáticamente si hay cambios en otras pestañas
        self.bind_all("<<CRA-DataChanged>>", lambda e: self.aplicar_filtros())

    # Colores para filas según tema
    def apply_tree_colors(self, is_dark: bool):
        if is_dark:
            self.tree_h.tag_configure("overdue", background="#4a2e2e", foreground="#ffffff")
            self.tree_h.tag_configure("ontime",  background="#2f3c2f", foreground="#e3ffe3")
        else:
            self.tree_h.tag_configure("overdue", background="#ffe6e6", foreground="#000000")
            self.tree_h.tag_configure("ontime",  background="#e8f5e9", foreground="#000000")

    # ---------------- UI ----------------
    def _build_ui(self):
        ttk.Label(self, text="Historial y Reportes", font=("-size", 14, "-weight", "bold")).pack(anchor="w", pady=(0,8))

        # Filtros
        filt = ttk.Labelframe(self, text="Filtros", padding=8)
        filt.pack(fill="x", pady=(0,8))

        ttk.Label(filt, text="Buscar (título o lector):").grid(row=0, column=0, sticky="w")
        self.var_buscar = tk.StringVar()
        ent = ttk.Entry(filt, textvariable=self.var_buscar, width=32)
        ent.grid(row=0, column=1, sticky="w", padx=(6,12))
        self.var_buscar.trace_add("write", lambda *_: self.aplicar_filtros())

        ttk.Label(filt, text="Estado:").grid(row=0, column=2, sticky="w")
        self.var_estado = tk.StringVar(value="Todos")
        cbo = ttk.Combobox(filt, textvariable=self.var_estado, state="readonly", width=12, values=ESTADOS)
        cbo.grid(row=0, column=3, sticky="w", padx=(6,12))
        self.var_estado.trace_add("write", lambda *_: self.aplicar_filtros())

        ttk.Label(filt, text="Desde:").grid(row=0, column=4, sticky="w")
        self.dt_desde = DateEntry(filt, width=12, dateformat="%Y-%m-%d")
        self.dt_desde.grid(row=0, column=5, sticky="w", padx=(6,12))

        ttk.Label(filt, text="Hasta:").grid(row=0, column=6, sticky="w")
        self.dt_hasta = DateEntry(filt, width=12, dateformat="%Y-%m-%d")
        self.dt_hasta.grid(row=0, column=7, sticky="w", padx=(6,12))

        # limpiar fechas por defecto (sin filtro hasta que el usuario elija)
        self.dt_desde.entry.delete(0, "end")
        self.dt_hasta.entry.delete(0, "end")

        # filtros en vivo al escribir/cambiar fechas
        for w in (self.dt_desde.entry, self.dt_hasta.entry):
            w.bind("<KeyRelease>", lambda e: self.aplicar_filtros())
            w.bind("<FocusOut>",  lambda e: self.aplicar_filtros())
        for w in (self.dt_desde, self.dt_hasta):
            for ev in ("<<DateEntrySelected>>", "<<DateEntryChanged>>"):
                try:
                    w.bind(ev, lambda e: self.aplicar_filtros())
                except Exception:
                    pass

        filt.columnconfigure(1, weight=1)

        # --------- Tabla HISTORIAL (scroll vertical + horizontal, sin descuadres) ----------
        wrap = ttk.Frame(self)
        wrap.pack(fill="both", expand=True, pady=(6,10))

        self.tree_h = ttk.Treeview(
            wrap,
            columns=("id","libro","lector","curso","f_p","f_e","f_d","estado","obs"),
            show="headings",
            height=12
        )

        # Scrollbars
        yscroll_h = ttk.Scrollbar(wrap, orient="vertical",   command=self.tree_h.yview)
        xscroll_h = ttk.Scrollbar(wrap, orient="horizontal", command=self.tree_h.xview)

        # Grid para que nada se desplace ni se superponga
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)

        self.tree_h.grid(row=0, column=0, sticky="nsew")
        yscroll_h.grid(row=0, column=1, sticky="ns")
        xscroll_h.grid(row=1, column=0, sticky="ew")

        self.tree_h.configure(yscrollcommand=yscroll_h.set, xscrollcommand=xscroll_h.set)

        headers = {
            "id":"ID","libro":"Libro","lector":"Lector","curso":"Curso",
            "f_p":"F. préstamo","f_e":"F. devolución esperada","f_d":"F. devolución",
            "estado":"Estado","obs":"Observación"
        }
        # Deja "obs" ancho y usa el scroll horizontal para ver todo
        widths = {"id":60,"libro":260,"lector":160,"curso":90,"f_p":120,"f_e":180,"f_d":140,"estado":110,"obs":700}
        for col in self.tree_h["columns"]:
            self.tree_h.heading(col, text=headers[col], anchor="w")
            self.tree_h.column(col, width=widths[col], anchor="w")

        # Tags (colores se fijan en apply_tree_colors)
        self.tree_h.tag_configure("overdue")
        self.tree_h.tag_configure("ontime")

        # --------- Reportes + Exportación ----------
        box = ttk.Labelframe(self, text="Reportes", padding=10)
        box.pack(fill="x")

        top_frame = ttk.Frame(box)
        top_frame.pack(fill="x", pady=4)
        ttk.Label(top_frame, text="Top libros más prestados:").pack(side="left")
        self.var_topn = tk.IntVar(value=10)
        ttk.Spinbox(top_frame, from_=5, to=50, textvariable=self.var_topn, width=6).pack(side="left", padx=6)
        ttk.Button(top_frame, text="Generar", command=self.rep_top).pack(side="left", padx=(0,8))
        ttk.Button(top_frame, text="Exportar CSV (vista arriba)",
                   command=self.exportar_csv_historial, bootstyle="outline").pack(side="left")

        low_frame = ttk.Frame(box)
        low_frame.pack(fill="x", pady=4)
        ttk.Label(low_frame, text="Stock bajo (umbral):").pack(side="left")
        self.var_thresh = tk.IntVar(value=2)
        ttk.Spinbox(low_frame, from_=1, to=20, textvariable=self.var_thresh, width=6).pack(side="left", padx=6)
        ttk.Button(low_frame, text="Ver libros con stock bajo", command=self.rep_low).pack(side="left")

        # --------- Tabla REPORTES (solo scroll vertical) ----------
        rep_wrap = ttk.Frame(self)
        rep_wrap.pack(fill="both", expand=True, pady=(8,0))

        self.tree_r = ttk.Treeview(rep_wrap, columns=("c1","c2","c3","c4","c5"), show="headings", height=8)
        self.tree_r.pack(side="left", fill="both", expand=True)

        yscroll_r = ttk.Scrollbar(rep_wrap, orient="vertical", command=self.tree_r.yview)
        yscroll_r.pack(side="right", fill="y")
        self.tree_r.configure(yscrollcommand=yscroll_r.set)

    # ---------------- Carga / Filtros ----------------
    def cargar_historial(self):
        self._load_historial_rows(db.historial_filtrar())

    def refresh(self):
        self.aplicar_filtros()

    def aplicar_filtros(self):
        term = (self.var_buscar.get() or "").strip() or None
        estado_sel = self.var_estado.get()
        estado = None if estado_sel == "Todos" else estado_sel

        desde_txt = self.dt_desde.entry.get().strip() or None
        hasta_txt = self.dt_hasta.entry.get().strip() or None

        if estado is None:
            rows = db.historial_filtrar(termino=term)
            if desde_txt or hasta_txt:
                d_from = _parse_iso(desde_txt)
                d_to   = _parse_iso(hasta_txt)
                rows = [r for r in rows if _in_range(_parse_iso(r[4]), d_from, d_to)]
        else:
            rows = db.historial_filtrar(
                estado=estado,
                fecha_desde=desde_txt,
                fecha_hasta=hasta_txt,
                termino=term
            )
        self._load_historial_rows(rows)

    def _load_historial_rows(self, rows):
        """Rellena tabla y marca: atrasado (rojo), activo en plazo (verde)."""
        self.tree_h.delete(*self.tree_h.get_children())
        hoy = _date.today()
        for row in rows:
            tags = []
            f_e = _parse_iso(row[5])  # fecha devolución esperada
            estado = (row[7] or "").upper()
            if estado == "ACTIVO" and f_e:
                tags.append("overdue" if f_e < hoy else "ontime")
            self.tree_h.insert("", "end", values=row, tags=tuple(tags))

    # ---------------- Exportar CSV ----------------
    def exportar_csv_historial(self):
        if not self.tree_h.get_children():
            messagebox.showinfo("Exportar CSV", "No hay datos para exportar.")
            return
        fpath = filedialog.asksaveasfilename(
            title="Guardar como",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"historial_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        )
        if not fpath:
            return
        try:
            with open(fpath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["ID","Libro","Lector","Curso","F. préstamo","F. devolución esperada","F. devolución","Estado","Observación"])
                for iid in self.tree_h.get_children():
                    writer.writerow(self.tree_h.item(iid)["values"])
            messagebox.showinfo("Exportar CSV", "Archivo exportado correctamente.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar el CSV:\n{e}")

    # ---------------- Reportes ----------------
    def _load_report(self, headers, rows):
        self.tree_r["columns"] = tuple([f"c{i+1}" for i in range(len(headers))])
        self.tree_r.delete(*self.tree_r.get_children())
        for i, h in enumerate(headers):
            self.tree_r.heading(f"c{i+1}", text=h, anchor="w")
            self.tree_r.column(f"c{i+1}", width=180, anchor="w")
        for r in rows:
            self.tree_r.insert("", "end", values=r)

    def rep_top(self):
        n = self.var_topn.get()
        rows = db.reportes_libros_mas_prestados(limit=n)
        self._load_report(["Título", "Veces prestado"], rows)

    def rep_low(self):
        th = self.var_thresh.get()
        rows = db.reportes_stock_bajo(threshold=th)
        self._load_report(["Título", "Stock"], rows)
