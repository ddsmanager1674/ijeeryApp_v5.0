#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour corriger la syntaxe cassée des imports
Répare: import Xfrom resource_utils → import X + from resource_utils
"""

import os
import re
from pathlib import Path


def fix_broken_imports(content):
    """Corrige les imports fusionnés sur une ligne"""
    
    # Pattern: import_statement + "from resource_utils"
    # Exemple: "import jsonfrom resource_utils import get_config_path"
    
    patterns = [
        # Répare: import Xfrom resource_utils
        (r'import (\w+)from resource_utils', r'import \1\nfrom resource_utils'),
        # Répare: from Xfrom resource_utils
        (r'from ([^\n]+)from resource_utils', r'from \1\nfrom resource_utils'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    # S'assurer que safe_file_read est importé si get_config_path l'est
    if 'get_config_path' in content and 'safe_file_read' not in content:
        content = re.sub(
            r'(from resource_utils import [^)]*get_config_path)',
            r'\1, safe_file_read',
            content
        )
    
    return content


def fix_file(filepath):
    """Corrige les imports dans un fichier"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        content = fix_broken_imports(original_content)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    
    except Exception as e:
        print(f"   ❌ Erreur dans {filepath.name}: {e}")
        return False


def main():
    """Corrige tous les fichiers pages/*.py"""
    pages_dir = Path("pages")
    
    if not pages_dir.exists():
        print("❌ Répertoire 'pages' non trouvé!")
        return
    
    print("\n" + "="*80)
    print("CORRECTION DES IMPORTS CASSÉS (import Xfrom resource_utils)")
    print("="*80 + "\n")
    
    all_files = sorted(pages_dir.glob("page_*.py"))
    fixed_count = 0
    
    for filepath in all_files:
        if fix_file(filepath):
            print(f"✅ {filepath.name}")
            fixed_count += 1
    
    print("\n" + "="*80)
    print(f"📊 RÉSUMÉ:")
    print(f"   • Fichiers traités: {len(all_files)}")
    print(f"   • Fichiers corrigés: {fixed_count}")
    print("="*80)
    
    if fixed_count > 0:
        print("\n✅ PROCHAINES ÉTAPES:")
        print("   1. Testez l'import: python -c 'from pages.page_absence import *'")
        print("   2. Si tout fonctionne, régénérez l'EXE")
    
    print()


if __name__ == "__main__":
    main()
