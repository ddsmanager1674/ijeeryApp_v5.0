#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Diagnostic - Problèmes de Filtrage par Statut
=========================================================

Ce script aide à identifier les problèmes de filtrage et d'affichage des boutons.
"""

import sys
import os
import json
import psycopg2

# Ajouter le répertoire actuel au chemin Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from resource_utils import get_config_path

def diagnostic():
    """Diagnostic complet du système de statut"""
    print("\n" + "="*80)
    print("🔍 DIAGNOSTIC - SYSTÈME DE STATUT DES FACTURES")
    print("="*80 + "\n")
    
    try:
        # 1. Connexion à la base de données
        print("✓ Étape 1: Connexion à la base de données...")
        with open(get_config_path('config.json')) as f:
            config = json.load(f)
        
        conn = psycopg2.connect(**config['database'])
        cursor = conn.cursor()
        print("  ✅ Connexion établie")
        
        # 2. Vérifier les statuts uniques dans la table tb_vente
        print("\n✓ Étape 2: Vérification des statuts uniques dans tb_vente...")
        cursor.execute("""
            SELECT DISTINCT statut, COUNT(*) as count
            FROM tb_vente
            GROUP BY statut
            ORDER BY statut
        """)
        
        statuts_bd = cursor.fetchall()
        print(f"\n  Statuts trouvés dans la base ({len(statuts_bd)} unique(s)):")
        for statut, count in statuts_bd:
            if statut is None:
                print(f"    - [NULL] : {count} factures")
            else:
                print(f"    - '{statut}' (len={len(statut)}, bytes={repr(statut.encode('utf-8'))}) : {count} factures")
        
        # 3. Comparer avec les valeurs du filtre
        print("\n✓ Étape 3: Comparaison avec les valeurs du filtre UI...")
        filter_values = ["Validé", "En attente", "Annulé"]
        
        print(f"\n  Valeurs attendues du filtre:")
        for val in filter_values:
            print(f"    - '{val}' (len={len(val)}, bytes={repr(val.encode('utf-8'))})")
        
        # 4. Test des requêtes SQL
        print("\n✓ Étape 4: Test des requêtes de filtrage...")
        
        for filter_val in ["Tout"] + filter_values:
            if filter_val == "Tout":
                sql = """
                    SELECT COUNT(*) FROM tb_vente
                    WHERE 1=1
                """
                params = []
            else:
                sql = """
                    SELECT COUNT(*) FROM tb_vente
                    WHERE statut = %s
                """
                params = [filter_val]
            
            cursor.execute(sql, params)
            count = cursor.fetchone()[0]
            print(f"  - Filtre '{filter_val}': {count} factures")
        
        # 5. Vérifier un exemple de facture
        print("\n✓ Étape 5: Exemple de facture complète...")
        cursor.execute("""
            SELECT v.id, v.refvente, v.statut, v.dateregistre, v.totmtvente
            FROM tb_vente v
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        if result:
            print(f"\n  ID: {result[0]}")
            print(f"  Ref: {result[1]}")
            print(f"  Statut: '{result[2]}' (type: {type(result[2])}, repr: {repr(result[2])})")
            print(f"  Date: {result[3]}")
            print(f"  Montant: {result[4]}")
        else:
            print("  ⚠️  Aucune facture trouvée dans la base!")
        
        # 6. Vérifier les colonnes de tb_vente
        print("\n✓ Étape 6: Schéma de tb_vente...")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'tb_vente'
            AND column_name IN ('id', 'refvente', 'statut', 'dateregistre', 'totmtvente')
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        for col in columns:
            print(f"  - {col[0]}: {col[1]} (nullable: {col[2]})")
        
        # 7. Requête complète comme dans le code
        print("\n✓ Étape 7: Test de la requête SQL complète...")
        sql_test = """
            SELECT v.dateregistre, v.refvente, COALESCE(c.nomcli, 'Client Divers'), 
                   v.totmtvente, v.statut, u.username, v.id
            FROM tb_vente v
            LEFT JOIN tb_client c ON v.idclient = c.idclient
            LEFT JOIN tb_users u ON v.iduser = u.iduser
            WHERE v.statut = %s
            LIMIT 5
        """
        
        for test_statut in filter_values:
            cursor.execute(sql_test, (test_statut,))
            rows = cursor.fetchall()
            print(f"\n  Requête avec statut='{test_statut}': {len(rows)} résultats")
            if rows:
                for row in rows:
                    print(f"    - {row[1]} | {row[2]} | {row[4]}")
        
        conn.close()
        
        # 8. Résumé et recommandations
        print("\n" + "="*80)
        print("📋 RÉSUMÉ ET RECOMMANDATIONS")
        print("="*80)
        
        if len(statuts_bd) == 0:
            print("❌ PROBLÈME: Aucun statut trouvé dans tb_vente!")
            print("   → La colonne 'statut' est-elle vide ou NULL?")
            print("   → Vérifiez que la colonne 'statut' existe et contient des données")
        else:
            print("✅ Statuts trouvés dans la base de données")
            
            # Vérifier si les valeurs correspondent
            bd_statuts_set = {s[0] for s in statuts_bd if s[0] is not None}
            filter_statuts_set = set(filter_values)
            
            if bd_statuts_set == filter_statuts_set:
                print("✅ Les valeurs BP correspondent exactement avec le filtre")
            else:
                print("❌ PROBLÈME: Les valeurs ne correspondent PAS!")
                print(f"   Statuts BD: {bd_statuts_set}")
                print(f"   Statuts attendus: {filter_statuts_set}")
                print(f"   Manquants: {filter_statuts_set - bd_statuts_set}")
                print(f"   Extras (non attendus): {bd_statuts_set - filter_statuts_set}")
        
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnostic()
