import webbrowser
from ttkbootstrap import ttk
import tkinter.font as tkFont

VERSION = "1.5"

class ContactoFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=20)
        self._build_ui()

    def _build_ui(self):
        # Marco elegante
        marco = ttk.Frame(self, padding=20, bootstyle="secondary")
        marco.pack(fill="both", expand=True)

        # Encabezado
        header = ttk.Frame(marco, padding=(0, 0, 0, 10))
        header.pack(fill="x")
        ttk.Label(header, text="📚 Sistema CRA – Gestión de Biblioteca Escolar",
                  font=("-size", 16, "-weight", "bold")).pack(anchor="center")
        ttk.Label(header, text="Versión: "+ VERSION, font=("-size", 11)).pack(anchor="center", pady=(2, 6))
        ttk.Label(header, text="Autor: Kevin Albanez",
                  font=("-size", 11, "-weight", "bold")).pack(anchor="center")

        ttk.Separator(marco, bootstyle="secondary").pack(fill="x", pady=10)

        # Correos
        self._correo(marco, "📧 Correo institucional:", "Kevinalbanez.r.grecia@educacionlascabras.cl")
        self._correo(marco, "📧 Correo alternativo:", "kevinalbanezpalacios616@gmail.com")

        ttk.Separator(marco, bootstyle="secondary").pack(fill="x", pady=10)

        # Mensaje final
        italic_font = tkFont.Font(family="Segoe UI", size=10, slant="italic")
        ttk.Label(marco, text="Gracias por utilizar el Sistema CRA.",
                  font=italic_font, foreground="#555").pack(anchor="center", pady=(10, 0))

    def _correo(self, parent, label, email):
        frame = ttk.Frame(parent, padding=5)
        frame.pack(anchor="center", pady=(4, 0))
        ttk.Label(frame, text=label, font=("-size", 10)).pack(side="left", padx=(0, 5))
        lbl = ttk.Label(frame, text=email, foreground="blue", cursor="hand2", underline=True)
        lbl.pack(side="left")
        lbl.bind("<Button-1>", lambda e: webbrowser.open(f"mailto:{email}"))
