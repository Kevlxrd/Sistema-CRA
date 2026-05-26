# security.py
import os, json, sys, platform, uuid, hashlib
from datetime import datetime, timedelta, date as _date
from tkinter import messagebox
from pathlib import Path
import atexit

from cryptography.fernet import Fernet, InvalidToken

from app_paths import path as data_path, local_path as exe_path

# ================== Config ==================
TRIAL_DAYS = 3  # días de prueba al no existir licencia
FERNET_KEY = b'Q4mBKk2v3oMCa8m6hO3yZ3yH6sS5mo2nWbPz2QqzEwE='  # 32 bytes base64 url-safe

def _fernet() -> Fernet:
    return Fernet(FERNET_KEY)

def _license_path() -> Path:
    return Path(data_path("licencia.enc"))

def _trial_state_path() -> Path:
    return Path(data_path("trial_state.enc"))

def _trial_marker_path() -> Path:
    # marcador de “trial inicializado” (para SO que no usan registro)
    return Path(data_path("trial_marker.enc"))

def license_path() -> str:
    return str(_license_path())

def trial_state_path() -> str:
    return str(_trial_state_path())

def _read_bytes(p: Path) -> bytes | None:
    try:
        return p.read_bytes()
    except Exception:
        return None

def _write_bytes(dst: Path, data: bytes) -> bool:
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        return True
    except Exception:
        return False

# Archivos posibles legados junto al exe/py (migración automática)
_LEGACY_FILES = ("licencia.enc", "trial_state.enc")

# ============== Utilidades de cifrado ==============
def _encrypt_to_file(obj: dict, file_path: str) -> None:
    data = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    token = _fernet().encrypt(data)
    with open(file_path, "wb") as f:
        f.write(token)

def _decrypt_file(file_path: str) -> dict:
    with open(file_path, "rb") as f:
        token = f.read()
    data = _fernet().decrypt(token)
    return json.loads(data.decode("utf-8"))

# ============== Huella de máquina ==============
def get_machine_fingerprint() -> str:
    try:
        host = platform.node()
        sysinfo = f"{platform.system()}-{platform.machine()}"
        mac = uuid.getnode()
        base = f"{host}|{sysinfo}|{mac}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:32]
    except Exception:
        return "unknown"

# ============== Marcador de trial único por equipo ==============
def _win_reg_available() -> bool:
    return platform.system() == "Windows"

def _trial_marker_exists() -> bool:
    """True si ya se creó trial alguna vez en este EQUIPO."""
    if _win_reg_available():
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Sistema_CRA", 0, winreg.KEY_READ) as k:
                val, _ = winreg.QueryValueEx(k, "TrialInitialized")
                return str(val) == "1"
        except Exception:
            pass
    # fallback fichero en AppData
    return _trial_marker_path().exists()

def _set_trial_marker() -> None:
    """Marca que este EQUIPO ya inicializó el trial una vez."""
    if _win_reg_available():
        try:
            import winreg
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Sistema_CRA") as k:
                winreg.SetValueEx(k, "TrialInitialized", 0, winreg.REG_SZ, "1")
                # también guardo el fingerprint para auditoría básica
                winreg.SetValueEx(k, "Fingerprint", 0, winreg.REG_SZ, get_machine_fingerprint())
        except Exception:
            # si falla el registro, cae al archivo
            pass
    # marcador fichero (idempotente)
    try:
        _write_bytes(_trial_marker_path(), get_machine_fingerprint().encode("utf-8"))
    except Exception:
        pass

# ============== Migración a AppData ==============
def _migrate_security_files_from_exe_dir_if_needed() -> None:
    try:
        for fname in _LEGACY_FILES:
            src = Path(exe_path(fname))
            if src.exists():
                dst = Path(data_path(fname))
                if not dst.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    src.replace(dst)
    except Exception:
        pass

# ============== Carga / Guardado ==============
def load_license() -> dict | None:
    try:
        return _decrypt_file(license_path())
    except FileNotFoundError:
        return None
    except Exception:
        return None

def _load_trial_state() -> dict | None:
    try:
        return _decrypt_file(trial_state_path())
    except Exception:
        return None

def _save_trial_state(state: dict) -> None:
    _encrypt_to_file(state, trial_state_path())

# ============== Trial (primera ejecución) ==============
def _make_trial_license(days: int = TRIAL_DAYS) -> dict:
    today = _date.today()
    return {
        "customer": "Trial",
        "issued_at": datetime.combine(today, datetime.min.time()).isoformat(),
        "vence":     datetime.combine(today + timedelta(days=days), datetime.min.time()).isoformat(),
        "plan_meses": 0,
        "fingerprint": get_machine_fingerprint(),
        "activo": True,
        "tipo": "trial",
    }

def ensure_trial_license_if_absent() -> None:
    """
    - Migra archivos legados.
    - Si NO existe licencia.enc:
        * Si NO existe el marcador -> crea trial de 3 días y marca el equipo.
        * Si YA existe el marcador -> NO crea otro trial (evita “trial infinito”).
    - Inicializa trial_state (anchor y last_seen) si no existe.
    """
    _migrate_security_files_from_exe_dir_if_needed()

    lic_p = _license_path()
    if not lic_p.exists():
        if _trial_marker_exists():
            # Ya tuvo trial; no volver a crear.
            return
        try:
            lic = _make_trial_license(TRIAL_DAYS)
            lic_p.parent.mkdir(parents=True, exist_ok=True)
            _encrypt_to_file(lic, str(lic_p))
            _set_trial_marker()  # ← marca que este equipo ya tuvo trial
        except Exception:
            pass

    # asegurar estado anti-retroceso
    st_p = _trial_state_path()
    if not st_p.exists():
        today = _date.today().isoformat()
        _save_trial_state({"anchor": today, "last_seen": today})

# ============== Anti-retroceso y cálculo de días ==============
def _effective_today() -> _date:
    today = _date.today()
    st = _load_trial_state()
    if not st:
        _save_trial_state({"anchor": today.isoformat(), "last_seen": today.isoformat()})
        return today
    try:
        last_seen = _date.fromisoformat(st.get("last_seen", ""))
    except Exception:
        last_seen = today
    eff = today if today >= last_seen else last_seen
    if eff != last_seen:
        st["last_seen"] = eff.isoformat()
        _save_trial_state(st)
    return eff

def license_days_left(lic: dict) -> int | None:
    try:
        vence = datetime.fromisoformat(lic["vence"]).date()
    except Exception:
        return None
    return (vence - _effective_today()).days

# ============== Validación e importación ==============
def validate_license(lic: dict | None) -> tuple[bool, str | None]:
    if not lic:
        return False, "No hay licencia."
    try:
        if not bool(lic.get("activo", False)):
            return False, "Licencia desactivada."
        fp = str(lic.get("fingerprint") or "")
        if fp and fp != get_machine_fingerprint():
            return False, "Licencia no corresponde a este equipo."
        days = license_days_left(lic)
        if days is None:
            return False, "Campo 'vence' inválido."
        if days < 0:
            return False, "Licencia vencida."
        return True, None
    except Exception as e:
        return False, f"Error validando licencia: {e}"

def import_license_file(src_path: str) -> tuple[bool, str]:
    src = Path(src_path)
    if not src.is_file():
        return False, "Archivo no encontrado."
    try:
        _ = _decrypt_file(str(src))  # valida que descifre
    except InvalidToken:
        return False, "Archivo inválido o no encriptado."
    except Exception as e:
        return False, f"Error leyendo la licencia: {e}"

    try:
        data = src.read_bytes()
        dst = _license_path()
        _write_bytes(dst, data)
        return True, str(dst)
    except Exception as e:
        return False, str(e)

# ============== Enforzar en arranque ==============
def check_license_or_exit(root) -> None:
    """
    Valida al iniciar; si no hay licencia válida, avisa y cierra la app.
    Caso especial: si falta licencia y YA hubo trial, también bloquea (no recrea).
    """
    lic = load_license()
    ok, err = validate_license(lic)

    if not ok:
        # si no hay licencia y ya hubo trial alguna vez, muestra mensaje específico
        if (lic is None) and _trial_marker_exists():
            err = "No hay licencia. El período de prueba ya fue utilizado en este equipo."

        try:
            messagebox.showerror(
                "Licencia",
                f"No se puede iniciar: {err or 'Licencia inválida.'}\n\n"
                f"Importa una licencia válida o contacta al administrador.",
                parent=root
            )
        except Exception:
            pass
        try:
            root.destroy()
        finally:
            raise SystemExit(1)

# ===== Persistencia de licencia junto al EXE (opcional) =====
def _mirror_exe_license_to_appdata_if_newer() -> None:
    try:
        exe_lic = Path(exe_path("licencia.enc"))
        app_lic = _license_path()
        if not exe_lic.exists():
            return
        src_bytes = _read_bytes(exe_lic)
        dst_bytes = _read_bytes(app_lic)
        if not src_bytes or dst_bytes == src_bytes:
            return
        _write_bytes(app_lic, src_bytes)
    except Exception:
        pass

def register_license_persistence_on_exit() -> None:
    try:
        atexit.register(_mirror_exe_license_to_appdata_if_newer)
    except Exception:
        pass

def enforce_monotonic_clock_or_exit(root=None) -> None:
    st = _load_trial_state()
    today = _date.today()
    if not st:
        _save_trial_state({"anchor": today.isoformat(), "last_seen": today.isoformat()})
        return
    try:
        last_seen = _date.fromisoformat(st.get("last_seen", ""))
    except Exception:
        last_seen = today
    if today < last_seen:
        msg = (
            "La fecha del sistema es anterior a la última vez que se usó el programa.\n\n"
            "Ajusta el reloj del equipo a la fecha actual y vuelve a abrir el sistema."
        )
        try:
            messagebox.showerror("Fecha del sistema", msg, parent=root)
        except Exception:
            pass
        raise SystemExit(1)
    if today > last_seen:
        st["last_seen"] = today.isoformat()
        _save_trial_state(st)
