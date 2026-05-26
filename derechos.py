import tkinter as tk
from ttkbootstrap import ttk
from utils_ui import center_window

COPYRIGHT_TEXT = "© 2025 Kevin Albanez. Todos los derechos reservados."

EULA_TEXT = """
Acuerdo de Licencia de Usuario Final (EULA)

IMPORTANTE: Lea cuidadosamente este Acuerdo de Licencia de Usuario Final ("EULA") antes de instalar o usar el software Sistema CRA - Gestión de Biblioteca. 
Al instalar, copiar o utilizar este software, usted (el "Licenciatario") acepta estar sujeto a los términos de este EULA. 
Si no acepta los términos, no instale ni utilice el software.

1. TITULARIDAD
Este software es propiedad de Kevin Albanez y está protegido por la Ley N°17.336 sobre Propiedad Intelectual de Chile y tratados internacionales, incluyendo el Convenio de Berna. Todos los derechos no otorgados expresamente se reservan.

2. CONCESIÓN DE LICENCIA
Se concede al Licenciatario una licencia no exclusiva, intransferible y revocable para instalar y utilizar el software exclusivamente en las dependencias de la Escuela República de Grecia con fines de gestión interna del Centro de Recursos para el Aprendizaje (CRA).

3. RESTRICCIONES
El Licenciatario no podrá, sin autorización expresa y por escrito del Licenciante:
- Copiar, distribuir o transmitir el software a terceros.
- Modificar, descompilar, realizar ingeniería inversa o crear trabajos derivados del software.
- Usar el software para prestar servicios a terceros fuera del alcance autorizado.

4. PROPIEDAD INTELECTUAL
Todo el código fuente, interfaz, base de datos, documentación y materiales asociados son propiedad exclusiva de Kevin Albanez. El uso no autorizado podrá dar lugar a acciones legales civiles y penales.

5. SOPORTE Y ACTUALIZACIONES
El soporte técnico y actualizaciones se proveerán conforme al contrato o plan de mantenimiento vigente entre las partes.

6. LIMITACIÓN DE RESPONSABILIDAD
El Licenciante no será responsable por daños directos, indirectos, incidentales o consecuenciales derivados del uso o imposibilidad de uso del software.

7. TERMINACIÓN
Este EULA se considerará terminado automáticamente si el Licenciatario incumple cualquiera de sus términos. En tal caso, el Licenciatario deberá desinstalar y eliminar todas las copias del software.

8. LEY APLICABLE Y JURISDICCIÓN
Este acuerdo se regirá por las leyes de la República de Chile. Cualquier disputa será sometida a los tribunales competentes de la comuna de residencia del Licenciante.
"""

class DerechosAutorFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=15)
        self._build_ui()

    def _build_ui(self):
        marco = ttk.Frame(self, padding=20, bootstyle="secondary")
        marco.pack(fill="both", expand=True)

        ttk.Label(marco, text="Derechos de autor", font=("-size", 14, "-weight", "bold")).pack(anchor="center", pady=(0,8))
        ttk.Label(marco, text="Sistema CRA – Software de Gestión de Biblioteca Escolar", font=("-size", 11)).pack(anchor="center", pady=(0,8))

        ttk.Separator(marco, bootstyle="secondary").pack(fill="x", pady=8)

        body = (
            "Este sistema es una obra protegida por la Ley N°17.336 de Propiedad Intelectual de Chile y por tratados internacionales.\n"
            "El uso del software está sujeto al Contrato de Licencia de Usuario Final (EULA).\n\n"
            "Titular: Kevin Albanez\n"
            f"{COPYRIGHT_TEXT}"
        )
        ttk.Label(marco, text=body, justify="center", wraplength=720).pack(anchor="center", pady=(0,10))

        ttk.Button(marco, text="Ver EULA", bootstyle="outline", command=self._mostrar_eula).pack(anchor="center", pady=(0,5))

    def _mostrar_eula(self):
        top = tk.Toplevel(self)
        top.title("EULA - Sistema CRA")
        top.geometry("820x620")
        top.transient(self.winfo_toplevel())
        top.grab_set()
        center_window(top, 820, 620)

        hdr = ttk.Frame(top, padding=8)
        hdr.pack(fill="x")
        ttk.Label(hdr, text="Acuerdo de Licencia de Usuario Final (EULA)", font=("-size", 13, "-weight", "bold")).pack(anchor="center")

        marco = ttk.Frame(top, padding=10, bootstyle="light")
        marco.pack(fill="both", expand=True, padx=10, pady=10)

        text = tk.Text(marco, wrap="word", font=("Segoe UI", 11), relief="flat")
        yscroll = ttk.Scrollbar(marco, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=yscroll.set)

        text.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")

        text.insert("1.0", EULA_TEXT.strip() + f"\n\n{COPYRIGHT_TEXT}")
        text.config(state="disabled")

        footer = ttk.Frame(top, padding=8)
        footer.pack(fill="x")
        ttk.Button(footer, text="Cerrar", command=top.destroy).pack(side="right")
