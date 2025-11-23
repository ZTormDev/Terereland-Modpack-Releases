import os
import hashlib
import json
import re

MODPACK_NAME = "Terereland"
MC_VERSION = "1.20.1"
LOADER = "fabric"

# Carpeta donde está tu modpack
MODPACK_ROOT = "./"

# Archivo de salida
OUTPUT_JSON = os.path.join(MODPACK_ROOT, "modpack.json")
VERSION_FILE = os.path.join(MODPACK_ROOT, "version.txt")

# Archivos o carpetas a ignorar
IGNORE = {
    "modpack.json",
    "version.txt",
    ".DS_Store",
    "__pycache__",
    ".git",
    ".gitignore",
    "build_modpack.py"
}


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

    for base, dirs, fs in os.walk(root):
        # Filtrar carpetas ignoradas
        dirs[:] = [d for d in dirs if d not in IGNORE]

        for fname in fs:
            if fname in IGNORE:
                continue

            full_path = os.path.join(base, fname)
            rel_path = os.path.relpath(full_path, root)

            hash_val = sha1_of_file(full_path)

            files.append({
                "path": rel_path.replace("\\", "/"),
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
        "files": files
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)

    write_version(new_version)

    print("✅ modpack.json generado con éxito")
    print("✅ version.txt actualizado")
    print("✓ Archivos hash calculados")


if __name__ == "__main__":
    build_modpack()
