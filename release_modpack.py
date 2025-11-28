import os
import requests
import json
import zipfile
from datetime import datetime

# Try to import winsound for a native Windows sound play; we'll fall back to
# printing a bell (\a) if it's not available (non-Windows systems).
try:
    import winsound
    HAS_WINSOUND = True
except Exception:
    HAS_WINSOUND = False

REPO = "ZTormDev/Terereland-Modpack-Releases"
TAG_PREFIX = "v"

MODPACK_ROOT = "./modpack"          # Carpeta del modpack
VERSION_FILE = "./modpack/version.txt"
MODPACK_JSON = "./modpack/modpack.json"

ZIP_OUTPUT = "./releases"       # Carpeta temporal para ZIP


# Archivos o carpetas a ignorar
IGNORE = {
    "./modpack/modpack.json",
    "./modpack/version.txt",
    ".DS_Store",
    "__pycache__",
    ".git",
    ".github",
    "./build_modpack.py",
    "./release_modpack.py",
    ".gitignore",
    "./releases"
}



# ============================
#   TOKEN
# ============================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise Exception("❌ No existe la variable de entorno GITHUB_TOKEN.")


# ============================
#   FUNCIONES AUXILIARES
# ============================

def read_version():
    if not os.path.exists(VERSION_FILE):
        raise Exception("❌ version.txt no existe.")
    return open(VERSION_FILE, "r").read().strip()


def zip_modpack(version):
    if not os.path.exists(ZIP_OUTPUT):
        os.makedirs(ZIP_OUTPUT)

    zip_filename = f"modpack_v{version}.zip"
    zip_path = os.path.join(ZIP_OUTPUT, zip_filename)

    print(f"📦 Comprimiendo modpack → {zip_filename}")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(MODPACK_ROOT):
            for file in files:
                if file in IGNORE or any(ig in root for ig in IGNORE):
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, MODPACK_ROOT)

                zipf.write(full_path, rel_path)
                print(f"➕ {rel_path}")

    print("✅ Compresión terminada.")
    return zip_path


def create_release(version):
    url = f"https://api.github.com/repos/{REPO}/releases"

    payload = {
        "tag_name": f"{TAG_PREFIX}{version}",
        "name": f"Terereland Modpack {version}",
        "body": f"Release auto-generado\nFecha: {datetime.now()}",
        "draft": True,
        "prerelease": False
    }

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    r = requests.post(url, json=payload, headers=headers)

    if r.status_code not in (200, 201):
        print("❌ Error creando release:")
        print(r.text)
        raise Exception("No se pudo crear el release.")

    data = r.json()
    print("🎉 Release creado:", data["html_url"])

    upload_url = data["upload_url"].split("{")[0]
    return upload_url


def upload_file(upload_url, file_path):
    file_name = os.path.basename(file_path)

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Content-Type": "application/octet-stream"
    }

    print(f"⬆ Subiendo archivo: {file_name}")

    with open(file_path, "rb") as f:
        r = requests.post(f"{upload_url}?name={file_name}", headers=headers, data=f)

    if r.status_code not in (200, 201):
        print(f"❌ Error subiendo {file_name}:")
        print(r.text)
        raise Exception("Error al subir archivo.")

    print(f"✅ Subido: {file_name}")
    
    
def publish_release(url):
    # Obtener el ID del release
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    r = requests.get(url, headers=headers)
    if r.status_code not in (200, 201):
        print("❌ Error obteniendo release para publicar:")
        print(r.text)
        raise Exception("No se pudo obtener el release.")
    data = r.json()
    release_id = data["id"]
    # Publicar el release (cambiar draft a False)
    patch_url = f"https://api.github.com/repos/{REPO}/releases/{release_id}"
    payload = {
        "draft": False
    }
    r = requests.patch(patch_url, json=payload, headers=headers)
    if r.status_code not in (200, 201):
        print("❌ Error publicando release:")
        print(r.text)
        raise Exception("No se pudo publicar el release.")
    print("🚀 Release publicado correctamente.")

# ============================
#   MAIN
# ============================

def main():
    version = read_version()

    print(f"\n🚀 Generando release v{version}\n")

    zip_path = zip_modpack(version)

    upload_url = create_release(version)

    upload_file(upload_url, VERSION_FILE)
    upload_file(upload_url, MODPACK_JSON)
    upload_file(upload_url, zip_path)
    
    # Publica el release (cambia de draft a publicado)
    publish_release(upload_url)

    print("\n🎯 Release COMPLETO:")
    print("   - version.txt")
    print("   - modpack.json")
    print(f"   - ZIP del modpack → {os.path.basename(zip_path)}")
    print("\n🔥 Todo salió god.\n")

    # Reproduce un sonido al final del script (Windows: winsound; other: BEL)
    def play_finish_sound():
        try:
            if HAS_WINSOUND:
                # Short beep using the Windows MessageBeep with OK icon
                winsound.MessageBeep(winsound.MB_OK)
            else:
                # Fallback: print ASCII bell - may or may not be audible
                print('\a')
        except Exception:
            # Silently ignore any issues playing sound
            pass

    play_finish_sound()


if __name__ == "__main__":
    main()
    input("\nPresiona ENTER para salir...")