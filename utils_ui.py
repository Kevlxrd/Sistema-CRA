import tkinter as tk

# === Branding ===
BRAND = "#1976d2"        # azul principal
BRAND_DARK = "#1565c0"   # azul más oscuro
HEAD_TEXT = "white"

def center_window(win, w=None, h=None):
    win.update_idletasks()
    if w is None or h is None:
        w = win.winfo_width()
        h = win.winfo_height()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw // 2) - (w // 2)
    y = (sh // 2) - (h // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")

def setup_branding(style):
    """
    Colores de marca para Notebook (tabs) y Treeview (encabezados/filas).
    Llamar al inicio y después de cambiar el tema (claro/oscuro).
    """
    # Tabs activas
    style.configure("TNotebook.Tab", padding=(14, 8), font=("-size", 10, "bold"))
    style.map(
        "TNotebook.Tab",
        background=[("selected", BRAND)],
        foreground=[("selected", HEAD_TEXT)],
    )

    # Treeview filas
    style.configure(
        "Brand.Treeview",
        background="#ffffff",
        fieldbackground="#ffffff",
        foreground="#1e293b",
        rowheight=24,
        borderwidth=0,
    )
    style.map(
        "Brand.Treeview",
        background=[("selected", "#0ea5e9")],
        foreground=[("selected", "white")],
    )

    # Encabezados azules
    style.configure(
        "Brand.Treeview.Heading",
        background=BRAND,
        foreground=HEAD_TEXT,
        relief="flat",
        font=("-size", 10, "bold"),
        padding=(6, 4),
    )
    style.map(
        "Brand.Treeview.Heading",
        background=[("active", BRAND_DARK), ("pressed", BRAND_DARK)],
        foreground=[("active", HEAD_TEXT), ("pressed", HEAD_TEXT)],
    )

def make_scrolled_treeview(parent, columns, height=12, show="headings"):
    """
    Treeview con estilo 'Brand.Treeview' + scrollbar vertical.
    Devuelve el Treeview ya empaquetado.
    """
    wrap = tk.Frame(parent)
    wrap.pack(fill="both", expand=True)
    from ttkbootstrap import ttk
    tree = ttk.Treeview(
        wrap,
        columns=columns,
        show=show,
        height=height,
        style="Brand.Treeview",
    )
    yscroll = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=yscroll.set)
    tree.pack(side="left", fill="both", expand=True)
    yscroll.pack(side="right", fill="y")
    return tree
