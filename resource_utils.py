# -*- coding: utf-8 -*-
"""
Utilitaire global pour gérer les chemins de ressources dans PyInstaller
Résout le problème de chemins relatifs en EXE
"""

import os
import sys

try:
    # Active le badge d'export pour tous les Treeview.
    import export_utils  # noqa: F401
except Exception:
    # Ne bloque pas le chargement des utilitaires en cas d'erreur.
    pass

def get_resource_path(relative_path):
    """
    Retourne le chemin absolu d'une ressource.
    Fonctionne AUSSI bien en Python direct qu'en EXE PyInstaller.
    
    Args:
        relative_path: Chemin relatif du fichier (ex: 'config.json', 'image/logo.png')
    
    Returns:
        Chemin absolu du fichier
    
    Exemple:
        config_path = get_resource_path('config.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
    """
    try:
        # Si l'application est exécutée comme EXE PyInstaller
        base_path = sys._MEIPASS
    except AttributeError:
        # Si c'est du Python direct
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)


def get_config_path(filename='config.json'):
    """
    Retourne le chemin absolu du fichier de configuration.
    
    Args:
        filename: Nom du fichier de config (par défaut: 'config.json')
    
    Returns:
        Chemin absolu
    """
    return get_resource_path(filename)


def get_session_path(filename='session.json'):
    """
    Retourne le chemin absolu du fichier de session.
    
    Args:
        filename: Nom du fichier de session (par défaut: 'session.json')
    
    Returns:
        Chemin absolu
    """
    return get_resource_path(filename)


def safe_file_read(file_path):
    """
    Lit un fichier en essayant plusieurs encodages.
    Résout les problèmes d'encodage avec config.json et autres fichiers.
    
    Args:
        file_path: Chemin du fichier
    
    Returns:
        Tuple (contenu, encoding utilisé)
    
    Raises:
        ValueError: Si le fichier ne peut pas être lu avec aucun encodage
    """
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            print(f"✓ Fichier {os.path.basename(file_path)} lu avec l'encodage: {encoding}")
            return content, encoding
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            raise FileNotFoundError(f"Fichier non trouvé: {file_path}")
    
    raise ValueError(f"Impossible de lire le fichier {file_path} avec les encodages disponibles")


def is_running_as_exe():
    """
    Vérifie si l'application s'exécute comme un EXE PyInstaller.
    
    Returns:
        True si c'est un EXE, False si c'est du Python direct
    """
    return hasattr(sys, '_MEIPASS')


def log_debug_info():
    """
    Affiche des informations de debug sur le contexte d'exécution.
    Utile pour dépanner les problèmes de chemin.
    """
    print("\n" + "="*60)
    print("DEBUG INFO - Contexte d'exécution")
    print("="*60)
    print(f"✓ Running as EXE: {is_running_as_exe()}")
    print(f"✓ Base path: {get_resource_path('')}")
    print(f"✓ Working directory: {os.getcwd()}")
    print(f"✓ Python exec: {sys.executable}")
    print(f"✓ Config path: {get_config_path()}")
    print(f"✓ Session path: {get_session_path()}")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Test quand le fichier est exécuté directement
    log_debug_info()
