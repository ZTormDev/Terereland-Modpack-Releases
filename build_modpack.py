import os
import hashlib
import json
import re
import sys

# Try to import winsound for a Windows-native beep; fallback to the ASCII bell
# if winsound is unavailable (non-Windows systems).
try:
    import winsound
    HAS_WINSOUND = True
except Exception:
    HAS_WINSOUND = False


# Attempt to load TOML parser: prefer stdlib tomllib (Python 3.11+), else toml package.
try:
    import tomllib as _toml
    def _load_toml_file(path):
        with open(path, 'rb') as f:
            return _toml.load(f)
except Exception:
    try:
        import toml as _toml
        def _load_toml_file(path):
            with open(path, 'r', encoding='utf-8') as f:
                return _toml.loads(f.read())
    except Exception:
        _toml = None
        def _load_toml_file(path):
            raise RuntimeError("No toml parser available. Install the 'toml' package or run on Python 3.11+")

def sha1_of_file(path):
    sha1 = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            data = f.read(8192)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()


def scan_folder(root):
    files = []

    def should_ignore_rel(rel_path):
        """Return True if rel_path (relative to root, forward-slash) is in ignore list.

        This compares both the exact entry, basename, and simple prefix matches (for directories with a trailing '/').
        """
        rp = rel_path.replace("\\", "/").lstrip("./")
        # Exact match
        if rp in IGNORE or rp + '/' in IGNORE:
            return True
        # Basename match (file or dir name)
        if os.path.basename(rp) in IGNORE:
            return True
        # Prefix matches for entries that act as dirs (e.g., 'releases/') or for entries that include a path
        for ign in IGNORE:
            ign_norm = ign.replace("\\", "/").lstrip("./")
            if ign_norm.endswith('/'):
                if rp.startswith(ign_norm.rstrip('/')):
                    return True
            else:
                # if ignore is a path prefix like 'modpack/modpack.json', check suffix/prefix
                if rp == ign_norm or rp.endswith('/' + ign_norm) or rp.startswith(ign_norm + '/'):
                    return True
        return False

    for base, dirs, fs in os.walk(root):
        # Filtrar carpetas ignoradas (por ruta relativa y por nombre)
        # Build relative paths for each dir and decide whether to keep it
        new_dirs = []
        for d in dirs:
            full_dir = os.path.join(base, d)
            rel_dir = os.path.relpath(full_dir, root).replace("\\", "/")
            if not should_ignore_rel(rel_dir):
                new_dirs.append(d)
        dirs[:] = new_dirs

        for fname in fs:
            full_path = os.path.join(base, fname)
            rel_path = os.path.relpath(full_path, root).replace("\\", "/")
            if should_ignore_rel(rel_path) or fname in IGNORE:
                continue

            hash_val = sha1_of_file(full_path)

            files.append({
                "path": rel_path,
                "sha1": hash_val
            })

    return files


def read_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r") as f:
            v = f.read().strip()

            # Validar formato X.Y.Z
            if re.match(r"^\d+\.\d+\.\d+$", v):
                return v

            print("⚠️  version.txt no tiene formato válido. Usando 1.0.0")
            return "1.0.0"

    return "1.0.0"


def write_version(new_version):
    with open(VERSION_FILE, "w") as f:
        f.write(new_version)


def next_version(version):
    major, minor, patch = version.split(".")
    return f"{major}.{minor}.{int(patch) + 1}"


def build_modpack():
    print("🔍 Escaneando archivos...")

    files = scan_folder(MODPACK_ROOT)

    current_version = read_version()
    new_version = next_version(current_version)

    print(f"📦 Versión vieja: {current_version}")
    print(f"🚀 Nueva versión: {new_version}")

    manifest = {
        "modpack_name": MODPACK_NAME,
        "version": new_version,
        "mc_version": MC_VERSION,
        "loader": LOADER,
        "loader_version": LOADER_VERSION,
        "java_version": JAVA_VERSION,
        "files": files
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)

    write_version(new_version)

    print("✅ modpack.json generado con éxito")
    print("✅ version.txt actualizado")
    print("✓ Archivos hash calculados")


if __name__ == "__main__":
    # Load configuration from settings.toml if present and apply it
    SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.toml")

    # Defaults (will be overwritten by settings if present)
    MODPACK_NAME = "Terereland"
    MC_VERSION = "1.21.1"
    LOADER = "neoforge"
    LOADER_VERSION = "21.1.215"
    JAVA_VERSION = 21
    MODPACK_ROOT = os.path.join(os.path.dirname(__file__), "modpack")
    IGNORE = [
        "modpack/modpack.json",
        "modpack/version.txt",
        ".DS_Store",
        "__pycache__",
        ".git",
        ".github",
        "build_modpack.py",
        "release_modpack.py",
        ".gitignore",
        "releases/",
        "settings.toml",
    ]

    # Load custom settings if available
    if os.path.exists(SETTINGS_FILE):
        try:
            cfg = _load_toml_file(SETTINGS_FILE)
            # Settings.toml contains tables named "Main params" and "Modpack params"
            main_params = cfg.get("Main params", {})
            modpack_params = cfg.get("Modpack params", {})

            MODPACK_NAME = main_params.get("MODPACK_NAME", MODPACK_NAME)
            MC_VERSION = main_params.get("MC_VERSION", MC_VERSION)
            LOADER = main_params.get("LOADER", LOADER)
            LOADER_VERSION = main_params.get("LOADER_VERSION", LOADER_VERSION)
            JAVA_VERSION = main_params.get("JAVA_VERSION", JAVA_VERSION)

            MODPACK_ROOT = modpack_params.get("MODPACK_ROOT", MODPACK_ROOT)
            IGNORE = modpack_params.get("IGNORE", IGNORE)
        except Exception as e:
            print(f"⚠️  No se pudo leer settings.toml: {e}")
            print("Usando valores por defecto.")

    # Normalize MODPACK_ROOT and ensure it is an absolute path
    MODPACK_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), MODPACK_ROOT))

    VERSION_FILE = os.path.join(MODPACK_ROOT, "version.txt")
    OUTPUT_JSON = os.path.join(MODPACK_ROOT, "modpack.json")

    # Normalize IGNORE entries so they work when MODPACK_ROOT is scanned.
    # Users may include entries like 'modpack/version.txt'; translate those
    # to the relative form used by this script when scanning MODPACK_ROOT.
    normalized_ignore = set()
    root_name = os.path.basename(MODPACK_ROOT).replace('\\', '/')
    for ign in IGNORE:
        if not isinstance(ign, str):
            continue
        ign_norm = ign.replace('\\', '/').lstrip('./')
        normalized_ignore.add(ign_norm)
        # Add basename (e.g., 'modpack/version.txt' -> 'version.txt')
        normalized_ignore.add(os.path.basename(ign_norm))
        # If user included a leading 'modpack/' prefix, remove it
        if ign_norm.startswith(root_name + '/'):
            normalized_ignore.add(ign_norm[len(root_name) + 1:])
        # If trailing slash (dir), add prefix and without slash
        if ign_norm.endswith('/'):
            normalized_ignore.add(ign_norm.rstrip('/'))

    IGNORE = list(normalized_ignore)

    # Verify that MODPACK_ROOT exists
    if not os.path.isdir(MODPACK_ROOT):
        print(f"⚠️  La carpeta de modpack no existe: {MODPACK_ROOT}")
        # Create it to avoid failures if needed
        try:
            os.makedirs(MODPACK_ROOT, exist_ok=True)
            print(f"📁 Carpeta creada: {MODPACK_ROOT}")
        except Exception as e:
            print(f"❌ No se pudo crear la carpeta: {e}")
            sys.exit(1)

    build_modpack()
    # Reproduce un sonido al final del build (Windows: winsound; other: BEL)
    def play_finish_sound():
        try:
            if HAS_WINSOUND:
                winsound.MessageBeep(winsound.MB_OK)
            else:
                print('\a')
        except Exception:
            pass

    play_finish_sound()
    input("\nPresiona ENTER para salir...")
