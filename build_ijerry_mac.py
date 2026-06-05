#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
  iJeery V5.0 — Script de génération APP macOS (PyInstaller)
================================================================================

Objectif
  Produire un bundle .app macOS (--onedir) avec toutes les dépendances
  (customtkinter, tkcalendar, pandas, psycopg2, etc.) et tous les modules pages/
  chargés dynamiquement (importlib) — équivalent du build_ijerry_exe.py Windows.

Usage (depuis la racine du projet, dans le Terminal macOS) :
  chmod +x build_mac.sh && ./build_mac.sh     # script shell de lancement
  python3 build_ijerry_mac.py
  python3 build_ijerry_mac.py --console        # garde un terminal (debug)
  python3 build_ijerry_mac.py --skip-venv      # utilise le Python courant
  python3 build_ijerry_mac.py --clean-only     # supprime build/ dist/ spec
  python3 build_ijerry_mac.py --dry-run        # génère le .spec sans compiler

Prérequis macOS
  1. Python 3.11 ou 3.12 depuis https://www.python.org/downloads/macos/
     (installer .pkg « macOS 64-bit universal2 »)
  2. pip3 install pyinstaller customtkinter psycopg2-binary pillow
     (psycopg2-binary embarque libpq — pas besoin de PostgreSQL installé)
  3. Icône au format .icns : icons/iconeIjeery.icns
     Convertir depuis .ico :
       sips -s format icns icons/iconeIjeery.ico --out icons/iconeIjeery.icns
     Ou depuis un PNG 1024x1024 :
       mkdir icone.iconset
       sips -z 512 512 icone_1024.png --out icone.iconset/icon_512x512.png
       iconutil -c icns icone.iconset -o icons/iconeIjeery.icns

Sortie
  dist/iJeery_V5.0/iJeery_V5.0.app
  Copie des modèles config.json / config.ini à côté du .app

Point d'entrée : page_login.py
================================================================================
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

# ─────────────────────────────────────────────────────────────────────────────
# Configuration (identique au build Windows)
# ─────────────────────────────────────────────────────────────────────────────

APP_NAME       = "iJeery_V5.0"
ENTRY_SCRIPT   = "page_login.py"
ICON_REL       = os.path.join("icons", "iconeIjeery.icns")   # .icns pour macOS
ICON_FILENAME  = "iconeIjeery.icns"
SPEC_FILENAME  = f"{APP_NAME}_mac.spec"
VENV_DIRNAME   = ".venv-build-mac"

PYTHON_OK   = {(3, 11), (3, 12)}
PYTHON_WARN = {(3, 13), (3, 14)}

DATA_DIRS       = ("image", "icons", "pages", "fonts")
DATA_FILES_ROOT = ("config.json", "config.ini")

COLLECT_ALL_PACKAGES = (
    "customtkinter",
    "darkdetect",
    "tkcalendar",
    "babel",
    "pandas",
    "PIL",
    "reportlab",
    "openpyxl",
    "num2words",
    "fpdf",
)

COLLECT_SUBMODULES_PACKAGES = ("pages",)

ROOT_HIDDEN_IMPORTS = (
    "app_main",
    "page_login",
    "ijeeryApp_V5.0",
    "db",
    "config_db",
    "configDataBase",
    "resource_utils",
    "app_icon_utils",
    "app_runtime_log",
    "settings_utils",
    "stock_service",
    "stock_snapshot",
    "stock_manager",
    "stock_utils",
    "log_utils",
    "format_utils",
    "export_utils",
    "impression_pdf_utils",
    "EtatsPDF_Mouvements",
    "pdf_print_settings_registry",
    "theme",
    "app_theme",
    "treeview_sort_utils",
    "user_settings_window",
    "action_tracer",
    "ticket_caisse_personnel",
    "pages.db_helper",
    "babel.numbers",
    "tkinter",
    "tkinter.ttk",
    "tkinter.messagebox",
    "tkinter.filedialog",
    "psycopg2",
    "psycopg2.extensions",
    "psycopg2.extras",
    "psycopg2._psycopg",
    "PIL.Image",
    "PIL.ImageTk",
    "PIL._imagingtk",
)

CLEAN_PATTERNS = ("build", "dist", SPEC_FILENAME)


# ─────────────────────────────────────────────────────────────────────────────
# Utilitaires
# ─────────────────────────────────────────────────────────────────────────────

def ensure_app_icon(root: Path) -> Path:
    icon = root / ICON_REL
    if not icon.is_file():
        # Essai fallback : même nom en .ico (conversion automatique par PyInstaller)
        fallback = root / "icons" / "iconeIjeery.ico"
        if fallback.is_file():
            print(
                f"[AVERTISSEMENT] Icône .icns absente. Utilisation de {fallback.name}\n"
                f"  → Pour un vrai .app macOS, convertissez-la :\n"
                f"    sips -s format icns icons/iconeIjeery.ico --out icons/iconeIjeery.icns"
            )
            return fallback
        raise FileNotFoundError(
            f"Icône introuvable : {icon}\n"
            f"Placez {ICON_FILENAME} dans icons/ ou lancez :\n"
            f"  sips -s format icns icons/iconeIjeery.ico --out icons/iconeIjeery.icns"
        )
    size_kb = icon.stat().st_size / 1024
    print(f"[OK] Icône application : {icon} ({size_kb:.1f} Ko)")
    return icon


def project_root() -> Path:
    return Path(__file__).resolve().parent


def venv_python(root: Path) -> Path:
    return root / VENV_DIRNAME / "bin" / "python"


def check_python_version() -> None:
    v = sys.version_info[:2]
    if v in PYTHON_OK:
        print(f"[OK] Python {sys.version.split()[0]}")
        return
    if v in PYTHON_WARN:
        print(
            f"[AVERTISSEMENT] Python {v[0]}.{v[1]} : certaines wheels "
            f"(pandas, psycopg2) peuvent manquer. Préférez 3.11 ou 3.12."
        )
        return
    print(
        f"[AVERTISSEMENT] Python {v[0]}.{v[1]} non testé officiellement. "
        f"Recommandé : 3.11 ou 3.12 (64 bits)."
    )


def run(cmd: list[str], *, cwd: Path, env: dict | None = None) -> None:
    print("\n>>>", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, cwd=str(cwd), env=env, check=True)


def _python_mm(exe: Path, *, cwd: Path) -> tuple[int, int]:
    out = subprocess.run(
        [str(exe), "-c", "import sys; print(sys.version_info.major, sys.version_info.minor)"],
        cwd=str(cwd), capture_output=True, text=True, check=True,
    )
    a, b = out.stdout.strip().split()
    return int(a), int(b)


def ensure_venv(root: Path, skip_venv: bool) -> Path:
    if skip_venv:
        check_python_version()
        return Path(sys.executable)

    venv_dir = root / VENV_DIRNAME
    py = venv_python(root)
    launcher = Path(sys.executable).resolve()

    if py.is_file():
        try:
            if _python_mm(py, cwd=root) != _python_mm(launcher, cwd=root):
                print(f"[INFO] {VENV_DIRNAME} version différente — recréation")
                shutil.rmtree(venv_dir, ignore_errors=True)
                py = venv_python(root)
        except (subprocess.CalledProcessError, ValueError, OSError):
            print(f"[INFO] {VENV_DIRNAME} invalide — recréation")
            shutil.rmtree(venv_dir, ignore_errors=True)
            py = venv_python(root)

    if not py.is_file():
        print(f"[INFO] Création du virtualenv : {venv_dir}")
        run([str(launcher), "-m", "venv", str(venv_dir)], cwd=root)

    check_python_version()
    return py


def pip_install(py: Path, root: Path) -> None:
    req = root / "requirements.txt"
    if not req.is_file():
        raise FileNotFoundError(f"requirements.txt introuvable : {req}")
    run([str(py), "-m", "pip", "install", "--upgrade", "pip"], cwd=root)
    run([str(py), "-m", "pip", "install", "-r", str(req)], cwd=root)
    run([str(py), "-m", "pip", "install", "--upgrade", "pyinstaller>=6.0"], cwd=root)


def clean_artifacts(root: Path) -> None:
    for name in CLEAN_PATTERNS:
        path = root / name
        if path.is_dir():
            print(f"[CLEAN] Dossier {path}")
            shutil.rmtree(path, ignore_errors=True)
        elif path.is_file():
            print(f"[CLEAN] Fichier {path}")
            path.unlink(missing_ok=True)


def discover_page_modules(pages_dir: Path) -> set[str]:
    found: set[str] = set()
    if not pages_dir.is_dir():
        return found
    for py_file in pages_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        rel = py_file.relative_to(pages_dir.parent)
        mod = str(rel.with_suffix("")).replace(os.sep, ".")
        found.add(mod)
    return found


def modules_from_app_main(root: Path) -> set[str]:
    app_main = root / "app_main.py"
    if not app_main.is_file():
        return set()
    text = app_main.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"pages\.[a-zA-Z0-9_]+", text))


def discover_root_py_modules(root: Path) -> set[str]:
    found: set[str] = set()
    skip = {Path(__file__).name, "build_ijerry_exe.py", "build_ijerry_mac.py"}
    for py_file in root.glob("*.py"):
        if py_file.name in skip:
            continue
        found.add(py_file.stem)
    return found


def collect_hidden_imports(root: Path) -> list[str]:
    pages_dir = root / "pages"
    mods = set(ROOT_HIDDEN_IMPORTS)
    mods |= discover_page_modules(pages_dir)
    mods |= modules_from_app_main(root)
    mods |= discover_root_py_modules(root)
    return sorted(m for m in mods if m and not m.endswith(".py"))


def build_datas_list(root: Path) -> list[tuple[str, str]]:
    datas: list[tuple[str, str]] = []
    for folder in DATA_DIRS:
        src = root / folder
        if src.is_dir():
            datas.append((str(src), folder))
        else:
            print(f"[AVERTISSEMENT] Dossier absent, ignoré : {folder}/")
    for filename in DATA_FILES_ROOT:
        src = root / filename
        if src.is_file():
            datas.append((str(src), "."))
        else:
            print(f"[AVERTISSEMENT] Fichier modèle absent : {filename}")
    return datas


def format_spec_datas(datas: list[tuple[str, str]]) -> str:
    lines = []
    for src, dest in datas:
        lines.append(f"    ({src!r}, {dest!r}),")
    return "\n".join(lines) if lines else "    # (aucune donnée)"


def format_spec_list(items: Iterable[str], indent: str = "    ") -> str:
    return "\n".join(f"{indent}{item!r}," for item in sorted(set(items)))


def write_spec_file(
    root: Path,
    *,
    windowed: bool,
    hiddenimports: list[str],
    datas: list[tuple[str, str]],
    icon: Path,
) -> Path:
    entry = root / ENTRY_SCRIPT
    if not entry.is_file():
        raise FileNotFoundError(f"Point d'entrée introuvable : {entry}")

    print(f"[INFO] Icône .app PyInstaller : {icon}")

    collect_all_block = "\n".join(
        f"tmpret = collect_all({pkg!r})\n"
        f"datas += tmpret[0]; binaries += tmpret[1]; hiddenimports += tmpret[2]"
        for pkg in COLLECT_ALL_PACKAGES
    )
    collect_sub_block = "\n".join(
        f"hiddenimports += collect_submodules({pkg!r})"
        for pkg in COLLECT_SUBMODULES_PACKAGES
    )

    console_flag = "False" if windowed else "True"

    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
# Généré automatiquement par build_ijerry_mac.py — ne pas éditer à la main.

import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

datas = [
{format_spec_datas(datas)}
]

binaries = []
hiddenimports = [
{format_spec_list(hiddenimports)}
]

{collect_all_block}

{collect_sub_block}

a = Analysis(
    [{str(entry)!r}],
    pathex=[{str(root)!r}],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "numpy.distutils",
        "pytest",
        "IPython",
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name={APP_NAME!r},
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console={console_flag},
    disable_windowed_traceback=False,
    argv_emulation=True,        # nécessaire pour macOS .app
    target_arch=None,           # None = architecture native (arm64 ou x86_64)
    codesign_identity=None,
    entitlements_file=None,
    icon={str(icon)!r},
)

# BUNDLE macOS : crée le .app
app = BUNDLE(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name={APP_NAME + ".app"!r},
    icon={str(icon)!r},
    bundle_identifier="mg.ijeery.v5",
    info_plist={{
        "NSHighResolutionCapable": True,
        "NSPrincipalClass": "NSApplication",
        "CFBundleShortVersionString": "5.0",
        "CFBundleVersion": "5.0.0",
        "NSAppleEventsUsageDescription": "iJeery V5.0",
    }},
)
'''
    spec_path = root / SPEC_FILENAME
    spec_path.write_text(spec_content, encoding="utf-8")
    print(f"[OK] Fichier spec écrit : {spec_path}")
    return spec_path


def run_pyinstaller(py: Path, root: Path, spec_path: Path) -> None:
    run(
        [str(py), "-m", "PyInstaller", str(spec_path), "--noconfirm", "--clean"],
        cwd=root,
    )


def post_build_copy_templates(root: Path, icon: Path) -> Path:
    # Sur macOS le bundle est dist/iJeery_V5.0.app
    dist_app = root / "dist" / f"{APP_NAME}.app"
    dist_dir = root / "dist" / APP_NAME   # dossier contenant le .app

    # Copie des fichiers modèles à côté du .app (pas à l'intérieur)
    dist_root = root / "dist"
    for filename in DATA_FILES_ROOT:
        src = root / filename
        if src.is_file():
            dest = dist_root / filename
            if not dest.exists():
                shutil.copy2(src, dest)
                print(f"[POST] Modèle copié : {dest}")

    if not dist_app.is_dir():
        raise FileNotFoundError(f"Bundle .app introuvable : {dist_app}")

    print(f"\n{'=' * 72}")
    print("  BUILD macOS TERMINÉ")
    print(f"{'=' * 72}")
    print(f"  Bundle  : {dist_app}")
    print(f"  Icône   : {icon.name}")
    print()
    print("  Premier lancement :")
    print("    Clic droit → Ouvrir → Ouvrir  (contourne Gatekeeper)")
    print("  Ou en Terminal :")
    print(f"    xattr -rd com.apple.quarantine dist/{APP_NAME}.app")
    print()
    print("  Fichiers créés au 1er lancement (dans ~/Library/Application Support/iJeery")
    print("  ou à côté du .app selon votre config) :")
    print("    settings.json, session.json, remember.json, ijeery_app.log")
    print(f"{'=' * 72}\n")
    return dist_app


def verify_dist(dist_app: Path) -> None:
    resources = dist_app / "Contents" / "Resources"
    macos_dir  = dist_app / "Contents" / "MacOS"
    checks = (
        "customtkinter", "tkcalendar", "pandas", "psycopg2",
        "PIL", "pages", "image", "icons",
    )
    search_roots = [resources, macos_dir, dist_app]
    missing = []
    for name in checks:
        found = any((r / name).exists() for r in search_roots)
        if not found:
            missing.append(name)
    if missing:
        print("[VÉRIFICATION] Éléments non trouvés dans le .app (à contrôler) :")
        for m in missing:
            print(f"  - {m}")
    else:
        print("[VÉRIFICATION] Dossiers / paquets critiques présents dans le .app")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Génère le bundle .app iJeery V5.0 pour macOS avec PyInstaller.",
    )
    p.add_argument("--skip-venv",   action="store_true", help="Utiliser le Python courant.")
    p.add_argument("--console",     action="store_true", help="Garder un terminal (debug).")
    p.add_argument("--clean-only",  action="store_true", help="Supprime build/ dist/ et .spec.")
    p.add_argument("--no-clean",    action="store_true", help="Ne pas nettoyer avant le build.")
    p.add_argument("--dry-run",     action="store_true", help="Génère le .spec sans compiler.")
    p.add_argument("--icon",        metavar="CHEMIN", default=None,
                   help=f"Icône .icns personnalisée (défaut : {ICON_REL}).")
    p.add_argument("--skip-verify", action="store_true", help="Ne pas vérifier dist/.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = project_root()
    os.chdir(root)

    print(f"\n{'=' * 72}")
    print("  iJeery V5.0 — Génération bundle macOS (.app)")
    print(f"  Racine projet : {root}")
    print(f"{'=' * 72}\n")

    if args.clean_only:
        clean_artifacts(root)
        print("[OK] Nettoyage terminé.")
        return 0

    if not args.no_clean:
        clean_artifacts(root)

    if args.icon is None:
        icon_path = ensure_app_icon(root)
    else:
        custom = Path(args.icon)
        if not custom.is_file():
            custom = root / args.icon
        if not custom.is_file():
            raise FileNotFoundError(f"Icône personnalisée introuvable : {args.icon}")
        icon_path = custom.resolve()
        print(f"[OK] Icône personnalisée : {icon_path}")

    py = ensure_venv(root, args.skip_venv)
    if not args.dry_run:
        pip_install(py, root)

    hidden = collect_hidden_imports(root)
    print(f"[INFO] {len(hidden)} hidden-import(s) (pages + racine + menu)")

    datas    = build_datas_list(root)
    spec_path = write_spec_file(
        root,
        windowed=not args.console,
        hiddenimports=hidden,
        datas=datas,
        icon=icon_path,
    )

    if args.dry_run:
        print("[DRY-RUN] Spec généré, compilation ignorée.")
        return 0

    run_pyinstaller(py, root, spec_path)
    dist_app = post_build_copy_templates(root, icon_path)
    if not args.skip_verify:
        verify_dist(dist_app)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as e:
        print(f"\n[ERREUR] Commande échouée (code {e.returncode})")
        raise SystemExit(e.returncode)
    except FileNotFoundError as e:
        print(f"\n[ERREUR] {e}")
        raise SystemExit(1)
