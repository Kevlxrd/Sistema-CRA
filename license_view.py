# license_view.py
import tkinter as tk
from tkinter import filedialog, messagebox
from ttkbootstrap import ttk
from datetime import date as _date, datetime

from security import (
    load_license,
    validate_license,
    import_license_file,
    license_days_left,
)

class LicenciaFrame(ttk.Frame):
    """
    Pestaña para consultar el estado de la licencia e importarla manualmente.
    - Muestra: Cliente, vence, días restantes, estado (válida/inválida) y motivo si aplica.
    - Botón para importar licencia (.lic/.enc) desde cualquier ruta y persistirla en AppData.
    """
    def __init__(self, master, on_status_change=None):
        super().__init__(master, padding=10)
        self.on_status_change = on_status_change  # callback para que main actualice banners si quieres
        self._build_ui()
        self._refresh_status()

    # ---------------- UI ----------------
    def _build_ui(self):
        ttk.Label(self, text="Gestión de Licencia", font=("-size", 14, "-weight", "bold"))\
           .pack(anchor="w", pady=(0, 10))

        box = ttk.Labelframe(self, text="Estado actual", padding=10)
        box.pack(fill="x", pady=(0, 10))

        # Campos visibles
        grid = ttk.Frame(box); grid.pack(fill="x")
        r = 0

        ttk.Label(grid, text="Cliente:").grid(row=r, column=0, sticky="w", padx=(0, 6), pady=4)
        self.lbl_cliente = ttk.Label(grid, text="-")
        self.lbl_cliente.grid(row=r, column=1, sticky="w", pady=4)
        r += 1

        ttk.Label(grid, text="Vence:").grid(row=r, column=0, sticky="w", padx=(0, 6), pady=4)
        self.lbl_vence = ttk.Label(grid, text="-")
        self.lbl_vence.grid(row=r, column=1, sticky="w", pady=4)
        r += 1

        ttk.Label(grid, text="Días restantes:").grid(row=r, column=0, sticky="w", padx=(0, 6), pady=4)
        self.lbl_dias = ttk.Label(grid, text="-")
        self.lbl_dias.grid(row=r, column=1, sticky="w", pady=4)
        r += 1

        ttk.Label(grid, text="Estado:").grid(row=r, column=0, sticky="w", padx=(0, 6), pady=4)
        self.lbl_estado = ttk.Label(grid, text="-")
        self.lbl_estado.grid(row=r, column=1, sticky="w", pady=4)
        r += 1

        ttk.Label(grid, text="Detalle:").grid(row=r, column=0, sticky="nw", padx=(0, 6), pady=4)
        self.txt_detalle = ttk.Label(grid, text="-", wraplength=680, justify="left")
        self.txt_detalle.grid(row=r, column=1, sticky="w", pady=4)
        r += 1

        for c in (0, 1):
            grid.columnconfigure(c, weight=0)
        grid.columnconfigure(1, weight=1)

        # Botones
        btns = ttk.Frame(self); btns.pack(fill="x")
        ttk.Button(btns, text="Importar licencia (.lic / .enc)", bootstyle="primary", command=self._importar)\
           .pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="Revalidar", command=self._refresh_status)\
           .pack(side="left")

        # Ayuda
        ttk.Label(self,
                  text="Solo se aceptan licencias encriptadas (.lic / .enc).",
                  bootstyle="secondary").pack(anchor="w", pady=(10, 0))

    # --------------- Lógica ---------------
    def _refresh_status(self):
        lic = load_license()
        ok, err = validate_license(lic)

        # Valores por defecto
        cliente = "-"
        vence_txt = "-"
        dias_restantes_txt = "-"
        estado_txt = "VÁLIDA" if ok else "INVÁLIDA"
        detalle_txt = "OK" if ok else (err or "-")

        # Calcular campos si hay licencia
        if lic:
            cliente = str(lic.get("customer") or "-")
            vence_val = lic.get("vence")
            if vence_val:
                try:
                    d_vence = datetime.fromisoformat(vence_val).date()
                    vence_txt = d_vence.isoformat()
                    dias = license_days_left(lic)
                    if dias is not None:
                        dias_restantes_txt = str(dias)
                except Exception:
                    vence_txt = str(vence_val)
                    dias_restantes_txt = "-"

        # Pintar en UI
        self.lbl_cliente.config(text=cliente)
        self.lbl_vence.config(text=vence_txt)
        self.lbl_dias.config(text=dias_restantes_txt)

        # Colorear estado y días
        if ok:
            self.lbl_estado.config(text=estado_txt, bootstyle="success")
            # días: verde si >3, rojo si <=3
            try:
                dias_int = int(dias_restantes_txt)
                if dias_int <= 3:
                    self.lbl_dias.config(bootstyle="danger")
                    self.txt_detalle.config(text="⚠️ La licencia está por vencer. Renueva lo antes posible.", bootstyle="danger")
                else:
                    self.lbl_dias.config(bootstyle="success")
                    self.txt_detalle.config(text="OK", bootstyle="success")
            except Exception:
                self.lbl_dias.config(bootstyle="")
                self.txt_detalle.config(text="OK", bootstyle="success")
        else:
            self.lbl_estado.config(text=estado_txt, bootstyle="danger")
            self.txt_detalle.config(text=detalle_txt, bootstyle="danger")

        # Avisar a main si fuera necesario
        if self.on_status_change:
            try:
                self.on_status_change(ok, detalle_txt)
            except Exception:
                pass

    def _importar(self):
        path = filedialog.askopenfilename(
            title="Seleccionar licencia encriptada",
            filetypes=[("Licencia CRA", "*.lic *.enc"), ("Todos los archivos", "*.*")]
        )
        if not path:
            return
        ok, msg = import_license_file(path)
        if not ok:
            messagebox.showerror("Licencia", f"No se pudo importar: {msg}", parent=self)
            return
        # Revalidar y actualizar UI
        self._refresh_status()
        messagebox.showinfo("Licencia", "Licencia importada correctamente.", parent=self)
