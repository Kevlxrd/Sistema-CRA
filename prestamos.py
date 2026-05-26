import tkinter as tk
from tkinter import messagebox
from ttkbootstrap import ttk
from ttkbootstrap.widgets import DateEntry
import database as db
from datetime import date, timedelta

# ---------- helpers de fecha ----------
def hoy():
    return date.today()

def en_7_dias():
    return date.today() + timedelta(days=7)


# ---------- Autocomplete combobox con popup propio ----------
class AutoCompleteCombobox(ttk.Entry):
    """
    Entry con lista desplegable (Toplevel+Listbox) que filtra en tiempo real.
    - set_completion_list(labels, ids)  -> define las opciones y su id asociado
    - get_selected_id()                 -> devuelve el id de la opción elegida (si coincide exacto)
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self._all_labels = []        # lista de strings mostrados
        self._label_to_id = {}       # label -> id (para recuperar el id)
        self._popup = None           # Toplevel
        self._listbox = None
        self._yscroll = None
        self._popup_visible = False  # estado del popup

        # bindings de escritura, navegación y visibilidad
        self.bind("<KeyRelease>", self._on_keyrelease, add="+")
        self.bind("<Down>", self._on_down, add="+")
        self.bind("<Up>", self._on_up, add="+")
        self.bind("<Return>", self._on_return, add="+")
        self.bind("<Escape>", lambda e: self._hide_popup(), add="+")
        self.bind("<FocusOut>", lambda e: self.after(100, self._hide_popup), add="+")
        self.bind("<Button-1>", self._on_click, add="+")

    # ---- API pública ----
    def set_completion_list(self, labels, ids=None):
        """labels: lista de textos. ids: lista paralela (mismo largo) o None si se parsea el id del label."""
        self._all_labels = list(labels)
        self._label_to_id = {}

        if ids is not None and len(ids) == len(labels):
            for lab, lid in zip(labels, ids):
                self._label_to_id[lab] = lid
        else:
            # fallback: tratar de leer el id si el label comienza con "ID - ..."
            for lab in labels:
                try:
                    lid = int(str(lab).split(" - ", 1)[0])
                except Exception:
                    lid = None
                self._label_to_id[lab] = lid

        # si hay popup abierto, refrescarlo
        if self._popup and self._popup.winfo_exists():
            self._update_popup_items(self._all_labels)

    def get_selected_id(self):
        """Si el contenido del entry coincide con un label exacto, retorna su id; si no, None."""
        txt = self.get().strip()
        return self._label_to_id.get(txt, None)

    # ---- Interno: popup ----
    def _ensure_popup(self):
        if self._popup and self._popup.winfo_exists():
            return

        self._popup = tk.Toplevel(self)
        self._popup.wm_overrideredirect(True)
        self._popup.transient(self.winfo_toplevel())

        # listbox + scrollbar
        frame = ttk.Frame(self._popup)
        frame.pack(fill="both", expand=True)

        self._listbox = tk.Listbox(frame, activestyle="dotbox")
        self._listbox.pack(side="left", fill="both", expand=True)

        self._yscroll = ttk.Scrollbar(frame, orient="vertical", command=self._listbox.yview)
        self._yscroll.pack(side="right", fill="y")
        self._listbox.configure(yscrollcommand=self._yscroll.set)

        # clicks y teclado/scroll en la lista
        self._listbox.bind("<ButtonRelease-1>", self._on_list_click)
        self._listbox.bind("<Return>", self._on_return)
        self._listbox.bind("<Escape>", lambda e: self._hide_popup())

        # Rueda del mouse (Windows/macOS)
        self._listbox.bind("<MouseWheel>", self._on_mousewheel)
        # Rueda del mouse (Linux X11)
        self._listbox.bind("<Button-4>", self._on_mousewheel)
        self._listbox.bind("<Button-5>", self._on_mousewheel)

    def _place_popup(self):
        if not (self._popup and self._popup.winfo_exists()):
            return
        # coordenadas pantalla
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        w = self.winfo_width()

        # alto fijo a 5 filas visibles (si hay menos, ajusta)
        visible_items = min(max(1, self._listbox.size()), 5)
        item_h = 22
        h = visible_items * item_h

        self._popup.geometry(f"{w}x{h}+{x}+{y}")

    def _show_popup(self, items):
        self._ensure_popup()
        self._update_popup_items(items)
        if self._listbox.size() == 0:
            self._hide_popup()
            return
        self._place_popup()
        self._popup.deiconify()
        self._popup.lift()
        self._popup_visible = True

    def _hide_popup(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.withdraw()
        self._popup_visible = False

    def _update_popup_items(self, items):
        if not (self._popup and self._popup.winfo_exists()):
            return
        self._listbox.delete(0, "end")
        # Importante: cargar **todas** las coincidencias para poder hacer scroll
        for it in items:
            self._listbox.insert("end", it)
        if items:
            self._listbox.selection_clear(0, "end")
            self._listbox.selection_set(0)
            self._listbox.activate(0)

    # ---- Handlers ----
    def _on_click(self, event):
        """Alterna visibilidad del popup al hacer clic en el campo."""
        # Si ya está visible -> ocultar
        if self._popup_visible:
            self._hide_popup()
        else:
            # Mostrar lista completa (5 visibles con scroll)
            if self._all_labels:
                self._show_popup(self._all_labels)

    def _on_keyrelease(self, event):
        # ignorar navegación que ya tienen handlers dedicados
        if event.keysym in ("Up", "Down", "Return", "Escape"):
            return
        txt = self.get().strip().lower()
        if not txt:
            # sin texto: abre lista completa con 5 visibles
            self._show_popup(self._all_labels)
            return
        matches = [lab for lab in self._all_labels if txt in lab.lower()]
        # Mostrar todas las coincidencias (altura del popup seguirá siendo 5)
        self._show_popup(matches)

    def _on_down(self, event):
        if not (self._popup and self._popup.winfo_exists() and self._popup.state() != "withdrawn"):
            # si no hay popup, abrir con todos
            self._show_popup(self._all_labels)
            return "break"
        # mover selección
        cur = self._listbox.curselection()
        if not cur:
            idx = 0
        else:
            idx = min(cur[0] + 1, self._listbox.size() - 1)
        self._listbox.selection_clear(0, "end")
        self._listbox.selection_set(idx)
        self._listbox.activate(idx)
        # asegurar que el ítem seleccionado sea visible al bajar
        self._listbox.see(idx)
        return "break"

    def _on_up(self, event):
        if not (self._popup and self._popup.winfo_exists() and self._popup.state() != "withdrawn"):
            return "break"
        cur = self._listbox.curselection()
        if not cur:
            idx = 0
        else:
            idx = max(cur[0] - 1, 0)
        self._listbox.selection_clear(0, "end")
        self._listbox.selection_set(idx)
        self._listbox.activate(idx)
        self._listbox.see(idx)
        return "break"

    def _on_return(self, event):
        # aplicar selección actual
        if self._popup and self._popup.winfo_exists() and self._popup.state() != "withdrawn":
            cur = self._listbox.curselection()
            if cur:
                value = self._listbox.get(cur[0])
                self.delete(0, "end")
                self.insert(0, value)
        self._hide_popup()
        return "break"

    def _on_list_click(self, event):
        idx = self._listbox.nearest(event.y)
        if idx >= 0:
            value = self._listbox.get(idx)
            self.delete(0, "end")
            self.insert(0, value)
        self._hide_popup()

    def _on_mousewheel(self, event):
        """Soporte de scroll con la rueda (Windows/macOS y Linux X11)."""
        if event.num == 4:      # Linux scroll up
            delta = -1
        elif event.num == 5:    # Linux scroll down
            delta = 1
        else:
            # Windows/macOS: event.delta es múltiplo de 120
            delta = -1 if event.delta > 0 else 1
        self._listbox.yview_scroll(delta, "units")
        return "break"


# ---------- Vista Préstamos ----------
class PrestamosFrame(ttk.Frame):
    def __init__(self, master, on_data_changed=None):
        super().__init__(master, padding=10)
        self.on_data_changed = on_data_changed
        self._build_ui()
        self._libros_cache = []   # [(id, titulo, stock)]
        self._labels = []         # ["id - titulo (stock N)"]
        self.cargar_libros_disponibles()
        self.cargar_prestamos_activos()

        # cuando cambian datos en otras pestañas, refrescar lista de libros
        self.bind_all("<<CRA-DataChanged>>", lambda e: self._reload_libros(), add="+")

    def _notify(self):
        if self.on_data_changed:
            try:
                self.on_data_changed()
            except Exception:
                pass

    # ---------- UI ----------
    def _build_ui(self):
        ttk.Label(self, text="Registrar Préstamo", font=("-size", 14, "-weight", "bold")).pack(anchor="w", pady=(0,8))

        form = ttk.Labelframe(self, text="Datos del préstamo", padding=10)
        form.pack(fill="x", pady=(0,10))

        # --- Libro (AutoComplete) ---
        ttk.Label(form, text="Libro *").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.cmb_libro = AutoCompleteCombobox(form, width=60)
        self.cmb_libro.grid(row=0, column=1, columnspan=3, sticky="ew", padx=4, pady=4)

        # Lector y curso
        self.var_lector = tk.StringVar()
        self.var_curso  = tk.StringVar()
        ttk.Label(form, text="Lector *").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(form, textvariable=self.var_lector, width=30).grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        ttk.Label(form, text="Curso").grid(row=1, column=2, sticky="w", padx=4, pady=4)
        ttk.Entry(form, textvariable=self.var_curso, width=15).grid(row=1, column=3, sticky="ew", padx=4, pady=4)

        # Fechas
        ttk.Label(form, text="Fecha préstamo *").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        self.dt_prestamo = DateEntry(form, width=16, dateformat="%Y-%m-%d"); self.dt_prestamo.set_date(hoy())
        self.dt_prestamo.grid(row=2, column=1, sticky="w", padx=4, pady=4)

        ttk.Label(form, text="Fecha devolución esperada *").grid(row=2, column=2, sticky="w", padx=4, pady=4)
        self.dt_esperada = DateEntry(form, width=16, dateformat="%Y-%m-%d"); self.dt_esperada.set_date(en_7_dias())
        self.dt_esperada.grid(row=2, column=3, sticky="w", padx=4, pady=4)

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        ttk.Button(self, text="Registrar préstamo", bootstyle="success", command=self.registrar).pack(anchor="w", pady=(0,10))

        # Tabla préstamos activos (con scroll)
        ttk.Label(self, text="Préstamos activos", font=("-size", 12, "-weight", "bold")).pack(anchor="w", pady=(6,6))

        table_wrap = ttk.Frame(self)
        table_wrap.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(table_wrap, columns=("id","libro","lector","curso","fecha_p","fecha_e"),
                                 show="headings", height=12)
        self.tree.pack(side="left", fill="both", expand=True)
        headers = {"id":"ID","libro":"Libro","lector":"Lector","curso":"Curso",
                   "fecha_p":"Fecha préstamo","fecha_e":"Fecha devolución esperada"}
        widths  = {"id":60,"libro":320,"lector":180,"curso":100,"fecha_p":130,"fecha_e":170}
        for col in self.tree["columns"]:
            self.tree.heading(col, text=headers[col], anchor="w")
            self.tree.column(col, width=widths[col], anchor="w")

        vscroll = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        vscroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vscroll.set)

    # ---------- Libros disponibles ----------
    def _reload_libros(self):
        # conserva lo que el usuario está escribiendo
        current_text = self.cmb_libro.get().strip()
        self.cargar_libros_disponibles()
        if current_text:
            # rehacer el filtrado con el texto actual
            self.cmb_libro.delete(0, "end")
            self.cmb_libro.insert(0, current_text)
            self.cmb_libro.event_generate("<KeyRelease>")

    def cargar_libros_disponibles(self):
        self._libros_cache = db.libros_disponibles()  # [(id, titulo, stock)]
        labels = []
        ids = []
        for lid, titulo, stock in self._libros_cache:
            labels.append(f"{lid} - {titulo} (stock {stock})")
            ids.append(lid)
        self._labels = labels
        self.cmb_libro.set_completion_list(labels, ids)

    # ---------- Registrar ----------
    def registrar(self):
        # validar libro elegido
        libro_id = self.cmb_libro.get_selected_id()
        if libro_id is None:
            messagebox.showwarning("Libro no válido", "Selecciona un libro de la lista (escribe y elige una opción).")
            return

        lector = self.var_lector.get().strip()
        if not lector:
            messagebox.showwarning("Campos obligatorios", "Escribe el nombre del lector.")
            return

        # fechas
        try:
            f_p = date.fromisoformat(self.dt_prestamo.entry.get())
            f_e = date.fromisoformat(self.dt_esperada.entry.get())
        except Exception:
            messagebox.showerror("Fecha inválida", "Formato de fecha inválido. Use YYYY-MM-DD.")
            return

        if f_e < f_p:
            messagebox.showerror("Fecha inválida", "La fecha de devolución esperada no puede ser anterior a la fecha de préstamo.")
            return

        # registrar
        try:
            db.prestamos_crear(
                libro_id,
                lector,
                (self.var_curso.get().strip() or None),
                f_p.isoformat(),
                f_e.isoformat()
            )
        except ValueError as e:
            messagebox.showerror("No se pudo registrar", str(e))
            return

        # notificaciones/limpieza
        self.event_generate("<<CRA-DataChanged>>", when="tail")
        messagebox.showinfo("Éxito", "Préstamo registrado.")
        self.var_lector.set("")
        self.var_curso.set("")
        self.cargar_libros_disponibles()
        self.cargar_prestamos_activos()
        self._notify()

    # ---------- Tabla activos ----------
    def cargar_prestamos_activos(self):
        self.tree.delete(*self.tree.get_children())
        for row in db.prestamos_activos():
            self.tree.insert("", "end", values=row)
