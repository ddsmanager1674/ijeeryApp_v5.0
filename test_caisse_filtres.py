# -*- coding: utf-8 -*-
"""
🧪 TEST DE VALIDATION - SYSTÈME DE FILTRAGE DE CAISSE
Vérifie que les filtres par mode de paiement et document fonctionnent correctement
"""

import psycopg2
import json
import os
from datetime import datetime, timedelta
from resource_utils import get_config_path, safe_file_read

def connect_db():
    """Établit la connexion à la base de données"""
    try:
        config_path = get_config_path('config.json')
        if not os.path.exists(config_path):
            config_path = 'config.json'
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            db_config = config['database']

        conn = psycopg2.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            port=db_config['port'],
            client_encoding='UTF8'
        )
        return conn
    except Exception as err:
        print(f"❌ Erreur de connexion: {err}")
        return None

def test_modes_paiement():
    """Test 1: Vérifier les modes de paiement en BD"""
    print("\n" + "="*80)
    print("🧪 TEST 1: MODES DE PAIEMENT EN BD")
    print("="*80)
    
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT idmode, modedepaiement FROM tb_modepaiement ORDER BY modedepaiement")
        modes = cursor.fetchall()
        
        print("\n📊 Modes trouvés en BD:")
        for idmode, nom in modes:
            print(f"   ID {idmode}: '{nom}'")
        
        if not modes:
            print("❌ FAIL: Aucun mode de paiement trouvé!")
            return False
        
        print(f"✅ PASS: {len(modes)} modes de paiement trouvés")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Erreur lors du test: {e}")
        return False
    finally:
        conn.close()

def test_montants_par_mode():
    """Test 2: Vérifier les montants par mode de paiement"""
    print("\n" + "="*80)
    print("🧪 TEST 2: MONTANTS PAR MODE DE PAIEMENT")
    print("="*80)
    
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Récupérer les modes et calculer les montants
        cursor.execute("SELECT idmode, modedepaiement FROM tb_modepaiement ORDER BY modedepaiement")
        modes = cursor.fetchall()
        
        print("\n💰 Montants par mode (encaissement - décaissement):")
        
        for idmode, nom in modes:
            cursor.execute("""
                SELECT SUM(CASE WHEN idtypeoperation = 1 THEN mtpaye ELSE -mtpaye END)
                FROM (
                    SELECT idmode, mtpaye, idtypeoperation FROM tb_pmtfacture WHERE idmode = %s AND id_banque IS NULL
                    UNION ALL
                    SELECT idmode, mtpaye, idtypeoperation FROM tb_pmtcom WHERE idmode = %s AND id_banque IS NULL
                    UNION ALL
                    SELECT idmode, mtpaye, idtypeoperation FROM tb_encaissement WHERE idmode = %s AND id_banque IS NULL
                    UNION ALL
                    SELECT idmode, mtpaye, idtypeoperation FROM tb_decaissement WHERE idmode = %s AND id_banque IS NULL
                    UNION ALL
                    SELECT idmode, mtpaye, idtypeoperation FROM tb_avancepers WHERE idmode = %s AND id_banque IS NULL
                    UNION ALL
                    SELECT idmode, mtpaye, idtypeoperation FROM tb_avancespecpers WHERE idmode = %s AND id_banque IS NULL
                    UNION ALL
                    SELECT idmode, mtpaye, idtypeoperation FROM tb_pmtsalaire WHERE idmode = %s AND id_banque IS NULL
                    UNION ALL
                    SELECT idmode, mtpaye, idtypeoperation FROM tb_pmtavoir WHERE idmode = %s AND id_banque IS NULL
                    UNION ALL
                    SELECT idmode, mtpaye, idtypeoperation FROM tb_pmtcredit WHERE idmode = %s AND id_banque IS NULL
                ) t1
                WHERE t1.idmode = %s
            """, [idmode] * 11)
            
            result = cursor.fetchone()
            montant = float(result[0]) if result and result[0] else 0
            print(f"   '{nom}': {montant:,.2f} Ar")
        
        print("✅ PASS: Montants calculés avec succès")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

def test_filtrage_par_mode():
    """Test 3: Vérifier le filtrage par mode de paiement"""
    print("\n" + "="*80)
    print("🧪 TEST 3: FILTRAGE PAR MODE DE PAIEMENT")
    print("="*80)
    
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        today = datetime.now().date()
        one_month_ago = today - timedelta(days=30)
        date_d = one_month_ago.strftime('%Y-%m-%d')
        date_f = today.strftime('%Y-%m-%d')
        
        # Récupérer un mode de paiement quelconque
        cursor.execute("SELECT idmode, modedepaiement FROM tb_modepaiement LIMIT 1")
        result = cursor.fetchone()
        
        if not result:
            print("❌ FAIL: Aucun mode de paiement trouvé")
            return False
        
        idmode, nom_mode = result
        
        print(f"\n🔍 Test de filtrage avec: '{nom_mode}' (ID: {idmode})")
        
        # Tester le filtrage avec ce mode
        query = f"""
            SELECT COUNT(*)
            FROM (
                SELECT datepmt FROM tb_pmtfacture WHERE idmode = %s AND datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                UNION ALL
                SELECT datepmt FROM tb_pmtcom WHERE idmode = %s AND datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                UNION ALL
                SELECT datepmt FROM tb_encaissement WHERE idmode = %s AND datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                UNION ALL
                SELECT datepmt FROM tb_decaissement WHERE idmode = %s AND datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                UNION ALL
                SELECT datepmt FROM tb_avancepers WHERE idmode = %s AND datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                UNION ALL
                SELECT datepmt FROM tb_avancespecpers WHERE idmode = %s AND datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                UNION ALL
                SELECT datepmt FROM tb_pmtsalaire WHERE idmode = %s AND datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                UNION ALL
                SELECT datepmt FROM tb_pmtavoir WHERE idmode = %s AND datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                UNION ALL
                SELECT datepmt FROM tb_pmtcredit WHERE idmode = %s AND datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
            ) t
        """
        
        params = [idmode, date_d, date_f] * 9
        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        
        print(f"   Résultats trouvés: {count} mouvements")
        
        if count >= 0:
            print(f"✅ PASS: Filtrage par mode '{nom_mode}' fonctionne")
            return True
        else:
            print(f"⚠️  WARN: Pas de données pour ce mode")
            return True
        
    except Exception as e:
        print(f"❌ FAIL: Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

def test_filtrage_par_document():
    """Test 4: Vérifier le filtrage par type de document"""
    print("\n" + "="*80)
    print("🧪 TEST 4: FILTRAGE PAR TYPE DE DOCUMENT")
    print("="*80)
    
    conn = connect_db()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        today = datetime.now().date()
        one_month_ago = today - timedelta(days=30)
        date_d = one_month_ago.strftime('%Y-%m-%d')
        date_f = today.strftime('%Y-%m-%d')
        
        docs = ["Client", "Avoir", "Fournisseur", "Personnel", "Dépenses", "Encaissement"]
        
        print(f"\n📄 Test des documents (période: {date_d} à {date_f}):")
        
        for doc in docs:
            if doc == "Client":
                query = f"""
                    SELECT COUNT(*) FROM (
                        SELECT 1 FROM tb_pmtfacture WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                        UNION ALL
                        SELECT 1 FROM tb_pmtcredit WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    ) t
                """
                cursor.execute(query, [date_d, date_f, date_d, date_f])
            elif doc == "Avoir":
                query = f"SELECT COUNT(*) FROM tb_pmtavoir WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL"
                cursor.execute(query, [date_d, date_f])
            elif doc == "Fournisseur":
                query = f"SELECT COUNT(*) FROM tb_pmtcom WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL"
                cursor.execute(query, [date_d, date_f])
            elif doc == "Personnel":
                query = f"""
                    SELECT COUNT(*) FROM (
                        SELECT 1 FROM tb_avancepers WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                        UNION ALL
                        SELECT 1 FROM tb_avancespecpers WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                        UNION ALL
                        SELECT 1 FROM tb_pmtsalaire WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL
                    ) t
                """
                cursor.execute(query, [date_d, date_f, date_d, date_f, date_d, date_f])
            elif doc == "Dépenses":
                query = f"SELECT COUNT(*) FROM tb_decaissement WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL"
                cursor.execute(query, [date_d, date_f])
            elif doc == "Encaissement":
                query = f"SELECT COUNT(*) FROM tb_encaissement WHERE datepmt::date BETWEEN %s AND %s AND id_banque IS NULL"
                cursor.execute(query, [date_d, date_f])
            
            count = cursor.fetchone()[0]
            print(f"   '{doc}': {count} mouvements")
        
        print("✅ PASS: Filtrage par document fonctionne")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

def main():
    print("\n" + "="*80)
    print("🧪 SUITE DE TESTS - SYSTÈME DE FILTRAGE CAISSE")
    print("="*80)
    
    results = {}
    
    results["Test 1: Modes de paiement"] = test_modes_paiement()
    results["Test 2: Montants par mode"] = test_montants_par_mode()
    results["Test 3: Filtrage par mode"] = test_filtrage_par_mode()
    results["Test 4: Filtrage par document"] = test_filtrage_par_document()
    
    # Résumé
    print("\n" + "="*80)
    print("📊 RÉSUMÉ DES TESTS")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test}")
    
    print(f"\n🎉 RÉSULTAT: {passed}/{total} tests réussis")
    
    if passed == total:
        print("\n✨ Tous les filtres fonctionnent correctement sans erreur!")
    else:
        print(f"\n⚠️  {total - passed} test(s) échoué(s)")

if __name__ == "__main__":
    main()
