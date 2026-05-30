#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
  iJeery V5.0 — Script unique de génération EXE (PyInstaller)
================================================================================

Objectif
  Produire un exécutable Windows fiable (--onedir) avec toutes les dépendances
  (customtkinter, tkcalendar, pandas, psycopg2, etc.) et tous les modules pages/
  chargés dynamiquement (importlib) — évite « page introuvable » en production.

Usage (depuis la racine du projet) :
  python build_ijerry_exe.py
  python build_ijerry_exe.py --console          # fenêtre console pour déboguer
  python build_ijerry_exe.py --skip-venv        # utilise le Python actuel
  python build_ijerry_exe.py --clean-only       # supprime build/ dist/ spec
  python build_ijerry_exe.py --dry-run          # affiche le .spec sans compiler

Recommandation Python
  Utiliser Python 3.11 ou 3.12 (64 bits). Le script crée .venv-build si besoin.
  Éviter de mélanger plusieurs versions : compiler TOUJOURS avec le venv du script.

Sortie
  dist/iJeery_V5.0/iJeery_V5.0.exe
  Copie des modèles config.json / config.ini à côté de l'exe (writable).
  NE PAS embarquer settings.json ni session.json (créés au 1er lancement).

Icône application
  - Fichier source : icons/iconeIjeery.ico
  - Embarquée dans l'EXE (barre des tâches / raccourci Windows)
  - Copiée dans dist/.../_internal/icons/ (runtime app_icon_utils.py)

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
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

APP_NAME = "iJeery_V5.0"
ENTRY_SCRIPT = "page_login.py"
ICON_REL = os.path.join("icons", "iconeIjeery.ico")
ICON_FILENAME = "iconeIjeery.ico"
SPEC_FILENAME = f"{APP_NAME}.spec"
VENV_DIRNAME = ".venv-build"

# Versions Python conseillées (tuple majeur, mineur)
PYTHON_OK = {(3, 11), (3, 12)}
PYTHON_WARN = {(3, 13), (3, 14)}

# Dossiers embarqués tels quels (assets + code pages pour ressources statiques)
DATA_DIRS = ("image", "icons", "pages", "fonts")

# Fichiers modèles DB / ini uniquement (données utilisateur = writable à côté de l'exe)
DATA_FILES_ROOT = ("config.json", "config.ini")

# Paquets avec fichiers de données / sous-modules non détectés par l'analyse statique
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

# Modules racine importés par login / app_main / utils (hors pages.*)
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

# Nettoyage après build
CLEAN_PATTERNS = ("build", "dist", SPEC_FILENAME)


# ─────────────────────────────────────────────────────────────────────────────
# Utilitaires
# ─────────────────────────────────────────────────────────────────────────────

def ensure_app_icon(root: Path) -> Path:
    """
    Vérifie la présence de icons/iconeIjeery.ico avant compilation.
    Utilisée pour l'EXE PyInstaller et le runtime (app_icon_utils).
    """
    icon = root / ICON_REL
    if not icon.is_file():
        raise FileNotFoundError(
            f"Icône introuvable : {icon}\n"
            f"Placez {ICON_FILENAME} dans le dossier icons/ à la racine du projet."
        )
    size_kb = icon.stat().st_size / 1024
    print(f"[OK] Icône application : {icon} ({size_kb:.1f} Ko)")
    return icon


def project_root() -> Path:
    return Path(__file__).resolve().parent


def venv_python(root: Path) -> Path:
    if sys.platform == "win32":
        return root / VENV_DIRNAME / "Scripts" / "python.exe"
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


def ensure_venv(root: Path, skip_venv: bool) -> Path:
    if skip_venv:
        check_python_version()
        return Path(sys.executable)

    py = venv_python(root)
    if not py.is_file():
        print(f"[INFO] Création du virtualenv : {root / VENV_DIRNAME}")
        run([sys.executable, "-m", "venv", str(root / VENV_DIRNAME)], cwd=root)
    check_python_version()
    return py


def pip_install(py: Path, root: Path) -> None:
    req = root / "requirements.txt"
    if not req.is_file():
        raise FileNotFoundError(f"requirements.txt introuvable : {req}")
    run([str(py), "-m", "pip", "install", "--upgrade", "pip"], cwd=root)
    run([str(py), "-m", "pip", "install", "-r", str(req)], cwd=root)
    run(
        [str(py), "-m", "pip", "install", "--upgrade", "pyinstaller>=6.0"],
        cwd=root,
    )


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
    """Tous les modules importables sous pages/ (y compris vente/, avoir/)."""
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
    """Extrait pages.xxx référencés dans app_main.py (MENU + navigate)."""
    app_main = root / "app_main.py"
    if not app_main.is_file():
        return set()
    text = app_main.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"pages\.[a-zA-Z0-9_]+", text))


def discover_root_py_modules(root: Path) -> set[str]:
    """Modules .py à la racine du projet (hors build script)."""
    found: set[str] = set()
    skip = {Path(__file__).name, "build_ijerry_exe.py"}
    for py_file in root.glob("*.py"):
        if py_file.name in skip:
            continue
        found.add(py_file.stem)
    return found


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

    print(f"[INFO] Icône EXE PyInstaller : {icon}")
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
# Généré automatiquement par build_ijerry_exe.py — ne pas éditer à la main.

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
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
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
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon={str(icon)!r},
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name={APP_NAME!r},
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
    dist_app = root / "dist" / APP_NAME
    if not dist_app.is_dir():
        raise FileNotFoundError(f"Dossier de sortie introuvable : {dist_app}")
    for filename in DATA_FILES_ROOT:
        src = root / filename
        if src.is_file():
            dest = dist_app / filename
            if not dest.exists():
                shutil.copy2(src, dest)
                print(f"[POST] Modèle copié : {dest.name}")
    exe = dist_app / f"{APP_NAME}.exe"
    if not exe.is_file():
        raise FileNotFoundError(f"EXE introuvable : {exe}")
    internal_icon = dist_app / "_internal" / "icons" / ICON_FILENAME
    if internal_icon.is_file():
        print(f"[POST] Icône runtime embarquée : {internal_icon.relative_to(dist_app)}")
    else:
        print(
            f"[AVERTISSEMENT] {ICON_FILENAME} absent de _internal/icons/ "
            f"(barre de titre en runtime peut échouer)."
        )
    print(f"\n{'=' * 72}")
    print("  BUILD TERMINÉ")
    print(f"{'=' * 72}")
    print(f"  Exécutable : {exe}")
    print(f"  Icône EXE  : {icon.name} (barre des tâches Windows / raccourci)")
    print(f"  Dossier    : {dist_app}")
    print()
    print("  Fichiers créés au 1er lancement (à côté de l'exe, modifiables) :")
    print("    settings.json, session.json, remember.json, ijeery_app.log")
    print()
    print("  NE PAS copier settings.json depuis le PC de dev vers la prod")
    print("  si vous voulez des paramètres vierges sur le poste client.")
    print(f"{'=' * 72}\n")
    return dist_app


def verify_dist(dist_app: Path) -> None:
    """Contrôles rapides sur le bundle (présence des libs critiques + icône)."""
    internal = dist_app / "_internal"
    search_roots = [dist_app, internal] if internal.is_dir() else [dist_app]
    checks = (
        "customtkinter",
        "tkcalendar",
        "pandas",
        "psycopg2",
        "PIL",
        "pages",
        "image",
        "icons",
    )
    missing = []
    for name in checks:
        found = any((root / name).exists() for root in search_roots)
        if not found:
            missing.append(name)
    icon_ok = any(
        (root / "icons" / ICON_FILENAME).is_file()
        for root in search_roots
    )
    if not icon_ok:
        missing.append(f"icons/{ICON_FILENAME}")
    if missing:
        print("[VÉRIFICATION] Éléments non trouvés dans dist (à contrôler) :")
        for m in missing:
            print(f"  - {m}")
    else:
        print(
            "[VÉRIFICATION] Dossiers / paquets critiques présents dans dist "
            f"(icône {ICON_FILENAME} incluse)."
        )


def collect_hidden_imports(root: Path) -> list[str]:
    pages_dir = root / "pages"
    mods = set(ROOT_HIDDEN_IMPORTS)
    mods |= discover_page_modules(pages_dir)
    mods |= modules_from_app_main(root)
    mods |= discover_root_py_modules(root)
    # Normaliser noms de modules (pas de chemins)
    return sorted(m for m in mods if m and not m.endswith(".py"))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Génère l'EXE iJeery V5.0 avec PyInstaller (script tout-en-un).",
    )
    p.add_argument(
        "--skip-venv",
        action="store_true",
        help="Ne pas créer/utiliser .venv-build ; utiliser le Python courant.",
    )
    p.add_argument(
        "--console",
        action="store_true",
        help="Garder une console (utile pour voir les erreurs import lazy_load).",
    )
    p.add_argument(
        "--clean-only",
        action="store_true",
        help="Supprime build/, dist/ et le .spec puis quitte.",
    )
    p.add_argument(
        "--no-clean",
        action="store_true",
        help="Ne pas nettoyer avant le build.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Génère uniquement le fichier .spec sans lancer PyInstaller.",
    )
    p.add_argument(
        "--icon",
        metavar="CHEMIN",
        default=None,
        help=f"Icône .ico pour l'EXE (défaut : {ICON_REL}).",
    )
    p.add_argument(
        "--skip-verify",
        action="store_true",
        help="Ne pas vérifier la présence des libs dans dist/.",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = project_root()
    os.chdir(root)

    print(f"\n{'=' * 72}")
    print("  iJeery V5.0 — Génération EXE")
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
        print(f"[OK] Icône personnalisée : {icon_path} ({icon_path.stat().st_size / 1024:.1f} Ko)")

    py = ensure_venv(root, args.skip_venv)
    if not args.dry_run:
        pip_install(py, root)

    hidden = collect_hidden_imports(root)
    print(f"[INFO] {len(hidden)} hidden-import(s) (pages + racine + menu)")

    datas = build_datas_list(root)
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
