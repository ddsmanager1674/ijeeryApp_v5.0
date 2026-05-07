#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour corriger automatiquement tous les chemins relatifs problématiques
dans les fichiers pages/*.py
"""

import os
import re
from pathlib import Path


def add_imports_if_needed(content, needed_imports):
    """Ajoute les imports nécessaires au début du fichier"""
    import_section_pattern = r'^(^import |^from ).*?(?=\n(?!import |from )|\Z)'
    
    # Trouver la position après les imports
    match = re.search(import_section_pattern, content, re.MULTILINE | re.IGNORECASE)
    
    if match:
        end_pos = match.end()
    else:
        # Pas d'imports trouvés, ajouter après le shebang/docstring
        end_pos = 0
        if content.startswith('#!'):
            end_pos = content.find('\n') + 1
        if content[end_pos:].startswith('# -*- coding'):
            end_pos = content.find('\n', end_pos) + 1
        if content[end_pos:].startswith('"""') or content[end_pos:].startswith("'''"):
            end_pos = content.find('"""' if content[end_pos:].startswith('"""') else "'''", end_pos + 3) + 3
            end_pos = content.find('\n', end_pos) + 1
    
    # Vérifier quels imports sont déjà là
    for imp in needed_imports:
        if imp not in content:
            insert_line = f"from resource_utils import {imp}\n"
            # Trouver une bonne place pour insérer
            check_text = content[:end_pos]
            if "from resource_utils import" not in check_text:
                # Ajouter juste avant les classes/fonctions
                content = content[:end_pos] + insert_line + content[end_pos:]
                end_pos += len(insert_line)
    
    return content


def fix_config_json_joins(content):
    """Corrige os.path.join(parent_dir, 'config.json')"""
    # Ajouter import si nécessaire
    if "os.path.join(parent_dir," in content and "get_config_path" not in content:
        content = add_imports_if_needed(content, ["get_config_path"])
    
    # Remplacer les patterns
    content = re.sub(
        r"config_path\s*=\s*os\.path\.join\s*\(\s*parent_dir\s*,\s*['\"]config\.json['\"]\s*\)",
        "config_path = get_config_path('config.json')",
        content
    )
    
    return content


def fix_open_config_json(content):
    """Corrige with open('config.json')"""
    # Ajouter import si nécessaire
    if "open('config.json')" in content and "get_config_path" not in content:
        content = add_imports_if_needed(content, ["get_config_path"])
    
    # Remplacer les patterns
    content = re.sub(
        r"with\s+open\s*\(\s*['\"]config\.json['\"]\s*\)",
        "with open(get_config_path('config.json'))",
        content
    )
    content = re.sub(
        r"open\s*\(\s*['\"]config\.json['\"]\s*\)",
        "open(get_config_path('config.json'))",
        content
    )
    
    return content


def fix_exists_config_json(content):
    """Corrige if not os.path.exists('config.json')"""
    # Ajouter import si nécessaire
    if "os.path.exists('config.json')" in content and "get_config_path" not in content:
        content = add_imports_if_needed(content, ["get_config_path"])
    
    content = re.sub(
        r"os\.path\.exists\s*\(\s*['\"]config\.json['\"]\s*\)",
        "os.path.exists(get_config_path('config.json'))",
        content
    )
    
    return content


def fix_safe_file_read(content):
    """Corrige safe_file_read('config.json')"""
    # Ajouter import si nécessaire
    if "safe_file_read('config.json')" in content and "get_config_path" not in content:
        content = add_imports_if_needed(content, ["get_config_path"])
    
    content = re.sub(
        r"safe_file_read\s*\(\s*['\"]config\.json['\"]\s*\)",
        "safe_file_read(get_config_path('config.json'))",
        content
    )
    
    return content


def fix_file(filepath):
    """Corrige tous les chemins problématiques dans un fichier"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            original_content = f.read()
        
        content = original_content
        
        # Appliquer tous les fixes
        content = fix_config_json_joins(content)
        content = fix_open_config_json(content)
        content = fix_exists_config_json(content)
        content = fix_safe_file_read(content)
        
        # Écrire si modifié
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return False


def main():
    """Corrige tous les fichiers pages/*.py"""
    pages_dir = Path("pages")
    
    if not pages_dir.exists():
        print("❌ Répertoire 'pages' non trouvé!")
        return
    
    print("\n" + "="*80)
    print("CORRECTION AUTOMATIQUE DES CHEMINS RELATIFS")
    print("="*80 + "\n")
    
    all_files = sorted(pages_dir.glob("page_*.py"))
    fixed_count = 0
    skipped_count = 0
    
    for filepath in all_files:
        if fix_file(filepath):
            print(f"✅ {filepath.name}")
            fixed_count += 1
        else:
            skipped_count += 1
    
    # Résumé
    print("\n" + "="*80)
    print(f"📊 RÉSUMÉ:")
    print(f"   • Fichiers traités: {len(all_files)}")
    print(f"   • Fichiers corrigés: {fixed_count}")
    print(f"   • Fichiers inchangés: {skipped_count}")
    print("="*80)
    
    if fixed_count > 0:
        print("\n✅ PROCHAINES ÉTAPES:")
        print("   1. Vérifiez les modifications: git diff pages/")
        print("   2. Testez en Python: python page_login.py")
        print("   3. Si tout fonctionne, régénérez l'EXE")
    else:
        print("\n⚠️  Aucun fichier n'a pu être corrigé!")
    
    print()


if __name__ == "__main__":
    main()
