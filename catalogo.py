import tkinter as tk
from tkinter import messagebox, simpledialog
from ttkbootstrap import ttk
import database as db

HELP_UBICACION = "Ubicación física del libro en la biblioteca. Ejemplos: 'Estante 1', 'Estante 4', 'Sección Infantil'."

class CatalogoFrame(ttk.Frame):
    def __init__(self, master, on_data_changed=None):
        super().__init__(master, padding=10)
        self.on_data_changed = on_data_changed
        self._sort_state = {}  # estado de orden por columna
        self._build_ui()
        # Colores por defecto (tema claro)
        self.apply_tree_colors(is_dark=False)
        self.cargar_tabla()

    def apply_tree_colors(self, is_dark: bool):
        """Configura colores de filas alternas y stock bajo según el tema."""
        if is_dark:
            # Alterna muy sutil en oscuro
            self.tree.tag_configure("altrow",   background="#2b2f33", foreground="#e9e9e9")
            self.tree.tag_configure("lowstock", background="#432e2e", foreground="#ffffff")
        else:
            self.tree.tag_configure("altrow",   background="#f5f5f5", foreground="#000000")
            self.tree.tag_configure("lowstock", background="#ffdfdf", foreground="#000000")

    def _notify(self):
        if self.on_data_changed:
            try:
                self.on_data_changed()
            except Exception:
                pass

    def _build_ui(self):
        ttk.Label(self, text="Catálogo de Libros", font=("-size", 14, "-weight", "bold")).pack(anchor="w", pady=(0,8))

        form = ttk.Labelframe(self, text="Datos del libro", padding=10)
        form.pack(fill="x", pady=(0,10))

        self.var_titulo = tk.StringVar()
        self.var_autor = tk.StringVar()
        self.var_editorial = tk.StringVar()
        self.var_anio = tk.StringVar()
        self.var_categoria = tk.StringVar()
        self.var_stock = tk.StringVar()
        self.var_ubicacion = tk.StringVar()

        ttk.Label(form, text="Título *").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(form, textvariable=self.var_titulo, width=40).grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        ttk.Label(form, text="Autor *").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        ttk.Entry(form, textvariable=self.var_autor, width=30).grid(row=0, column=3, sticky="ew", padx=4, pady=4)

        ttk.Label(form, text="Editorial").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(form, textvariable=self.var_editorial).grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        ttk.Label(form, text="Año").grid(row=1, column=2, sticky="w", padx=4, pady=4)
        ttk.Entry(form, textvariable=self.var_anio).grid(row=1, column=3, sticky="ew", padx=4, pady=4)

        ttk.Label(form, text="Categoría").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(form, textvariable=self.var_categoria).grid(row=2, column=1, sticky="ew", padx=4, pady=4)
        ttk.Label(form, text="Stock *").grid(row=2, column=2, sticky="w", padx=4, pady=4)
        ttk.Entry(form, textvariable=self.var_stock).grid(row=2, column=3, sticky="ew", padx=4, pady=4)

        ttk.Label(form, text="Ubicación *").grid(row=3, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(form, textvariable=self.var_ubicacion).grid(row=3, column=1, sticky="ew", padx=4, pady=4)
        ttk.Label(form, text=HELP_UBICACION).grid(row=3, column=2, columnspan=2, sticky="w", padx=4, pady=4)

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        btns = ttk.Frame(self); btns.pack(fill="x", pady=(0,10))
        ttk.Button(btns, text="Agregar", bootstyle="success",   command=self.agregar).pack(side="left", padx=4)
        ttk.Button(btns, text="Editar",  bootstyle="warning",   command=self.editar).pack(side="left", padx=4)
        ttk.Button(btns, text="Eliminar",bootstyle="danger",    command=self.eliminar).pack(side="left", padx=4)
        ttk.Button(btns, text="Limpiar", bootstyle="secondary", command=self.limpiar).pack(side="left", padx=4)

        buscador = ttk.Frame(self); buscador.pack(fill="x", pady=(0,10))
        ttk.Label(buscador, text="Buscar (título/autor/categoría/ubicación):").pack(side="left", padx=(0,6))
        self.var_buscar = tk.StringVar()
        ent_buscar = ttk.Entry(buscador, textvariable=self.var_buscar, width=40)
        ent_buscar.pack(side="left")
        # Búsqueda en vivo
        self.var_buscar.trace_add("write", lambda *args: self.buscar())
        ttk.Button(buscador, text="Buscar", bootstyle="info", command=self.buscar).pack(side="left", padx=6)

        # Contenedor con scroll vertical
        table_wrap = ttk.Frame(self)
        table_wrap.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(
            table_wrap,
            columns=("id","titulo","autor","editorial","anio","categoria","stock","ubicacion"),
            show="headings",
            height=14,
            selectmode="extended"  # permite selección múltiple
        )
        self.tree.pack(side="left", fill="both", expand=True)

        vscroll = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        vscroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vscroll.set)

        headers = {
            "id":"ID","titulo":"Título","autor":"Autor","editorial":"Editorial","anio":"Año",
            "categoria":"Categoría","stock":"Stock","ubicacion":"Ubicación"
        }
        widths  = {"id":60,"titulo":240,"autor":160,"editorial":140,"anio":80,"categoria":120,"stock":80,"ubicacion":160}
        for col in self.tree["columns"]:
            self.tree.heading(col, text=headers[col], anchor="w", command=lambda c=col: self._ordenar_por(c))
            self.tree.column(col, width=widths[col], anchor="w")

        # Tags: se reconfiguran por tema en apply_tree_colors()
        self.tree.tag_configure("altrow")
        self.tree.tag_configure("lowstock")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.status = ttk.Label(self, text="", anchor="w"); self.status.pack(fill="x", pady=(6,0))

    def limpiar(self):
        self.var_titulo.set(""); self.var_autor.set(""); self.var_editorial.set("")
        self.var_anio.set(""); self.var_categoria.set(""); self.var_stock.set("")
        self.var_ubicacion.set("")
        self.tree.selection_remove(self.tree.selection())

    def cargar_tabla(self):
        self.tree.delete(*self.tree.get_children())
        rows = db.libros_listar()
        total, bajos = 0, 0
        for i, row in enumerate(rows):
            total += 1
            tags = []
            stock = row[6]
            if stock is not None and stock <= 2:
                tags.append("lowstock"); bajos += 1
            if i % 2 == 0:
                tags.append("altrow")
            self.tree.insert("", "end", values=row, tags=tuple(tags))
        self.status.config(text=f"Total libros: {total} | Stock bajo (≤2): {bajos}")

    def buscar(self):
        filtro = self.var_buscar.get().strip()
        self.tree.delete(*self.tree.get_children())
        rows = db.libros_listar(filtro=filtro) if filtro else db.libros_listar()
        for i, row in enumerate(rows):
            tags = ["altrow"] if i % 2 == 0 else []
            stock = row[6]
            if stock is not None and stock <= 2:
                tags.append("lowstock")
            self.tree.insert("", "end", values=row, tags=tuple(tags))

    # ---------- Ordenar columnas ----------
    def _ordenar_por(self, col):
        asc = not self._sort_state.get(col, True)
        self._sort_state[col] = asc
        items = [(self.tree.set(i, col), i) for i in self.tree.get_children("")]
        def _key(v):
            val = v[0]
            try:
                return int(val)
            except (TypeError, ValueError):
                return str(val).lower()
        items.sort(key=_key, reverse=not asc)
        for idx, (_, iid) in enumerate(items):
            self.tree.move(iid, "", idx)

    # ---------- CRUD ----------
    def agregar(self):
        if not self.var_titulo.get().strip() or not self.var_autor.get().strip() or not self.var_stock.get().strip() or not self.var_ubicacion.get().strip():
            messagebox.showwarning("Campos obligatorios", "Título, Autor, Stock y Ubicación son obligatorios.", parent=self)
            return
        try:
            stock = int(self.var_stock.get())
            anio = int(self.var_anio.get()) if self.var_anio.get() else None
        except ValueError:
            messagebox.showerror("Error", "Año y Stock deben ser números enteros.", parent=self); return
        db.libros_agregar(self.var_titulo.get().strip(), self.var_autor.get().strip(),
                          self.var_editorial.get().strip() or None,
                          anio, self.var_categoria.get().strip() or None,
                          stock, self.var_ubicacion.get().strip())
        self.limpiar(); self.cargar_tabla(); self._notify()
        self.event_generate("<<CRA-DataChanged>>", when="tail")
        messagebox.showinfo("Éxito", "Libro agregado correctamente.", parent=self)

    def editar(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Sin selección", "Seleccione un libro para editar.", parent=self)
            return

        # Valores visibles actualmente en la tabla
        libro_id, t0, a0, e0, an0, c0, s0, u0 = self.tree.item(sel[0])["values"]

        # Valores del formulario (posibles cambios)
        titulo     = self.var_titulo.get().strip()
        autor      = self.var_autor.get().strip()
        editorial  = (self.var_editorial.get().strip() or None)
        anio_txt   = self.var_anio.get().strip()
        categoria  = (self.var_categoria.get().strip() or None)
        ubicacion  = self.var_ubicacion.get().strip()
        stock_txt  = self.var_stock.get().strip()

        # Validaciones base
        if not titulo or not autor or not stock_txt or not ubicacion:
            messagebox.showwarning("Campos obligatorios", "Título, Autor, Stock y Ubicación son obligatorios.", parent=self)
            return

        # Normalización segura de enteros
        def to_int_or_none(txt):
            if txt == "" or txt is None:
                return None
            try:
                return int(txt)
            except ValueError:
                return "INVALID"

        stock = to_int_or_none(stock_txt)
        if stock == "INVALID":
            messagebox.showerror("Error", "Stock debe ser un número entero.", parent=self)
            return

        anio = to_int_or_none(anio_txt)
        if anio == "INVALID":
            messagebox.showerror("Error", "Año debe ser un número entero.", parent=self)
            return

        # Función para normalizar valores a string comparables
        def norm(v):
            return "" if v is None else str(v).strip()

        # Construir lista de cambios detectados
        cambios = []
        if norm(t0) != norm(titulo):
            cambios.append(("Título", t0, titulo))
        if norm(a0) != norm(autor):
            cambios.append(("Autor", a0, autor))
        if norm(e0) != norm(editorial):
            cambios.append(("Editorial", e0, editorial))
        if norm(an0) != ("" if anio is None else str(anio)):
            cambios.append(("Año", an0, anio))
        if norm(c0) != norm(categoria):
            cambios.append(("Categoría", c0, categoria))
        if str(s0) != ("" if stock is None else str(stock)):
            cambios.append(("Stock", s0, stock))
        if norm(u0) != norm(ubicacion):
            cambios.append(("Ubicación", u0, ubicacion))

        # Si no hay cambios -> avisar y salir
        if not cambios:
            messagebox.showinfo("Sin cambios", "No se detectaron modificaciones. Realice algún cambio antes de guardar.", parent=self)
            return

        # Confirmación con resumen
        resumen = "\n".join([f"• {campo}: '{orig}' → '{nuevo}'" for campo, orig, nuevo in cambios])
        ok = messagebox.askyesno(
            "Confirmar edición",
            f"Se detectaron los siguientes cambios:\n\n{resumen}\n\n¿Deseas guardar estos cambios?",
            parent=self
        )
        if not ok:
            return

        # Guardar en BD
        db.libros_actualizar(libro_id, titulo, autor, editorial, anio, categoria, stock, ubicacion)

        # Refrescar UI y notificar
        self.limpiar()
        self.cargar_tabla()
        try:
            self.on_data_changed and self.on_data_changed()
        except Exception:
            pass
        self.event_generate("<<CRA-DataChanged>>", when="tail")
        messagebox.showinfo("Actualizado", "Libro editado correctamente.", parent=self)

    def eliminar(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Sin selección", "Seleccione uno o más libros para eliminar.", parent=self)
            return

        confirm = simpledialog.askstring(
            "Confirmar eliminación",
            "Escribe ELIMINAR para confirmar la eliminación de los libros seleccionados:",
            parent=self
        )
        if confirm is None:
            return
        if confirm.strip() != "ELIMINAR":
            messagebox.showerror("Error", "Debe escribir exactamente 'ELIMINAR' (en mayúsculas) para confirmar.", parent=self)
            return

        ids = [self.tree.item(i)["values"][0] for i in sel]
        eliminados, errores = 0, 0
        for libro_id in ids:
            try:
                db.libros_eliminar(libro_id)
                eliminados += 1
            except Exception:
                errores += 1

        self.limpiar(); self.cargar_tabla()
        try:
            self.on_data_changed and self.on_data_changed()
        except Exception:
            pass
        self.event_generate("<<CRA-DataChanged>>", when="tail")

        msg = f"Eliminados: {eliminados}"
        if errores:
            msg += f" | Errores: {errores}"
        messagebox.showinfo("Eliminar", msg, parent=self)

    def _on_select(self, event=None):
        sel = self.tree.selection()
        if not sel: return
        _, titulo, autor, editorial, anio, categoria, stock, ubicacion = self.tree.item(sel[0])["values"]
        self.var_titulo.set(titulo or ""); self.var_autor.set(autor or "")
        self.var_editorial.set(editorial or ""); self.var_anio.set("" if anio in (None, "") else str(anio))
        self.var_categoria.set(categoria or ""); self.var_stock.set("" if stock in (None, "") else str(stock))
        self.var_ubicacion.set(ubicacion or "")
