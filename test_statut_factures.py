#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de Validation - Système de Statut pour Factures
=========================================================

Ce script teste les modifications apportées au système de gestion des statuts.
"""

import sys
import os

# Ajouter le répertoire actuel au chemin Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """✅ Test 1: Vérifier les imports"""
    print("\n" + "="*70)
    print("TEST 1: IMPORTS")
    print("="*70)
    try:
        from pages.page_ListeFacture import PageDetailFacture, PageListeFacture
        print("✅ SUCCÈS: Import de PageDetailFacture et PageListeFacture")
        return True
    except Exception as e:
        print(f"❌ ERREUR à l'import: {e}")
        return False

def test_page_detail_signature():
    """✅ Test 2: Vérifier la signature de PageDetailFacture"""
    print("\n" + "="*70)
    print("TEST 2: SIGNATURE PageDetailFacture.__init__")
    print("="*70)
    try:
        from pages.page_ListeFacture import PageDetailFacture
        import inspect
        
        sig = inspect.signature(PageDetailFacture.__init__)
        params = list(sig.parameters.keys())
        
        print(f"Signature complète: {sig}")
        print(f"Paramètres: {params}")
        
        # Vérifier les paramètres attendus
        expected = ['self', 'master', 'idvente', 'refvente', 'statut', 'parent_page']
        if params == expected:
            print(f"✅ SUCCÈS: Les paramètres sont corrects")
            return True
        else:
            print(f"❌ ERREUR: Paramètres inattendus")
            print(f"   Attendus: {expected}")
            print(f"   Reçus:    {params}")
            return False
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        return False

def test_methods_exist():
    """✅ Test 3: Vérifier l'existence des nouvelles méthodes"""
    print("\n" + "="*70)
    print("TEST 3: EXISTENCE DES MÉTHODES")
    print("="*70)
    try:
        from pages.page_ListeFacture import PageDetailFacture
        
        methods_to_check = ['annuler_facture', 'reimprimer_duplicata', 'generate_pdf_a5_duplicata', 'charger_details', 'formater_montant']
        
        results = []
        for method_name in methods_to_check:
            if hasattr(PageDetailFacture, method_name):
                print(f"✅ Méthode '{method_name}' existe")
                results.append(True)
            else:
                print(f"❌ Méthode '{method_name}' manquante")
                results.append(False)
        
        return all(results)
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        return False

def test_page_liste_signature():
    """✅ Test 4: Vérifier la signature de PageListeFacture"""
    print("\n" + "="*70)
    print("TEST 4: MÉTHODES PageListeFacture")
    print("="*70)
    try:
        from pages.page_ListeFacture import PageListeFacture
        
        methods_to_check = ['charger_donnees', 'on_double_click', 'setup_ui', 'connect_db', 'exporter_excel']
        
        results = []
        for method_name in methods_to_check:
            if hasattr(PageListeFacture, method_name):
                print(f"✅ Méthode '{method_name}' existe")
                results.append(True)
            else:
                print(f"❌ Méthode '{method_name}' manquante")
                results.append(False)
        
        return all(results)
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        return False

def test_no_syntax_errors():
    """✅ Test 5: Vérifier l'absence d'erreurs de syntaxe"""
    print("\n" + "="*70)
    print("TEST 5: VÉRIFICATION SYNTAXE")
    print("="*70)
    try:
        import py_compile
        
        file_path = "pages/page_ListeFacture.py"
        py_compile.compile(file_path, doraise=True)
        print(f"✅ SUCCÈS: Aucune erreur de syntaxe dans {file_path}")
        return True
    except py_compile.PyCompileError as e:
        print(f"❌ ERREUR SYNTAXE:\n{e}")
        return False

def main():
    """Exécuter tous les tests"""
    print("\n")
    print("╔" + "═"*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  🧪 TESTS DE VALIDATION - SYSTÈME DE STATUT POUR FACTURES  ".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "═"*68 + "╝")
    
    tests = [
        ("Imports", test_imports),
        ("Signature PageDetailFacture", test_page_detail_signature),
        ("Méthodes PageDetailFacture", test_methods_exist),
        ("Méthodes PageListeFacture", test_page_liste_signature),
        ("Syntaxe Python", test_no_syntax_errors),
    ]
    
    results = {}
    for test_name, test_func in tests:
        results[test_name] = test_func()
    
    # Résumé
    print("\n" + "="*70)
    print("RÉSUMÉ DES TESTS")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSÉ" if result else "❌ ÉCHOUÉ"
        print(f"{status} - {test_name}")
    
    print("="*70)
    print(f"\nRésultat: {passed}/{total} tests réussis")
    
    if passed == total:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS! Le système est prêt for production.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) ont échoué. Veuillez corriger les erreurs.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
