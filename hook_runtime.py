import sys
import os

# Ajoute le dossier _internal au sys.path pour que les imports de pages fonctionnent
if getattr(sys, 'frozen', False):
    # On est dans un EXE PyInstaller
    base_path = sys._MEIPASS
    if base_path not in sys.path:
        sys.path.insert(0, base_path)
