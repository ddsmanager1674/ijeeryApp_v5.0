#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour analyser et trovuver tous les chemins relatifs problématiques
dans les fichiers pages/*.py
"""

import os
import re
from pathlib import Path


def analyze_file(filepath):
    """Analyse un fichier pour les patterns problématiques"""
    issues = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        return [(0, f"Erreur de lecture: {e}")]
    
    patterns = [
        (r"open\s*\(\s*['\"]config\.json['\"]", "config.json avec chemin relatif"),
        (r"open\s*\(\s*['\"]session\.json['\"]", "session.json avec chemin relatif"),
        (r"open\s*\(\s*['\"]settings\.json['\"]", "settings.json avec chemin relatif"),
        (r"safe_file_read\s*\(\s*['\"]config\.json['\"]", "safe_file_read('config.json') - chemin relatif"),
        (r"os\.path\.join\s*\(\s*parent_dir\s*,\s*['\"]config\.json['\"]", "config.json avec parent_dir"),
        (r"os\.path\.exists\s*\(\s*['\"]config\.json['\"]", "config.json avec os.path.exists"),
    ]
    
    for line_num, line in enumerate(lines, 1):
        for pattern, description in patterns:
            if re.search(pattern, line):
                issues.append((line_num, f"{description} -> {line.strip()}"))
    
    return issues


def main():
    """Analyse tous les fichiers pages/*.py"""
    pages_dir = Path("pages")
    
    if not pages_dir.exists():
        print("❌ Répertoire 'pages' non trouvé!")
        return
    
    print("\n" + "="*80)
    print("ANALYSE DES CHEMINS RELATIFS PROBLÉMATIQUES")
    print("="*80 + "\n")
    
    all_files = sorted(pages_dir.glob("page_*.py"))
    files_with_issues = 0
    total_issues = 0
    
    for filepath in all_files:
        issues = analyze_file(filepath)
        
        if issues:
            files_with_issues += 1
            total_issues += len(issues)
            
            print(f"⚠️  {filepath.name}")
            for line_num, issue in issues:
                print(f"   {line_num:4d}: {issue}")
            print()
    
    # Résumé
    print("="*80)
    print(f"📊 RÉSUMÉ:")
    print(f"   • Fichiers analysés: {len(all_files)}")
    print(f"   • Fichiers avec problèmes: {files_with_issues}")
    print(f"   • Total d'issues détectées: {total_issues}")
    print("="*80)
    
    if files_with_issues > 0:
        print("\n✅ ÉTAPES SUIVANTES:")
        print("   1. Correction manuelle ou avec Find & Replace (voir GUIDE-CORRIGER-CHEMINS-PYINSTALLER.txt)")
        print("   2. Testez en Python: python page_login.py")
        print("   3. Régénérez l'EXE avec le PROMPT #3")
    else:
        print("\n✅ TOUS LES FICHIERS SONT CORRECTS!")
    
    print()


if __name__ == "__main__":
    main()
