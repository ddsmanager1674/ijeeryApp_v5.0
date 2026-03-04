"""
Script de test pour mettre à jour manuellement tb_stock pour BISCUIT 4X4 BE
"""
import psycopg2
import json

def connect_db():
    try:
        with open('config.json') as f:
            config = json.load(f)
            db_config = config['database']
        
        conn = psycopg2.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            port=db_config['port']
        )
        return conn
    except Exception as e:
        print(f"Erreur connexion: {e}")
        return None

def calculer_stock_article(conn, idarticle, idunite_cible, idmag=None):
    """
    Calcul de stock identique à page_stock.py
    """
    try:
        cursor = conn.cursor()
        
        # 1. Récupérer TOUTES les unités liées à cet idarticle
        cursor.execute("""
            SELECT idunite, codearticle, COALESCE(qtunite, 1) 
            FROM tb_unite 
            WHERE idarticle = %s
        """, (idarticle,))
        unites_liees = cursor.fetchall()
        
        # 2. Identifier le qtunite de l'unité cible
        qtunite_affichage = 1
        for idu, code, qt_u in unites_liees:
            if idu == idunite_cible:
                qtunite_affichage = qt_u if qt_u > 0 else 1
                break

        total_stock_global_base = 0

        # 3. Sommer les mouvements de chaque variante
        for idu_boucle, code_boucle, qtunite_boucle in unites_liees:
            print(f"\n  Traitement unité: idunite={idu_boucle}, code={code_boucle}, qtunite={qtunite_boucle}")
            
            # Réceptions
            q_rec = "SELECT COALESCE(SUM(qtlivrefrs), 0) FROM tb_livraisonfrs WHERE idarticle = %s AND idunite = %s AND deleted = 0"
            p_rec = [idarticle, idu_boucle]
            if idmag:
                q_rec += " AND idmag = %s"
                p_rec.append(idmag)
            cursor.execute(q_rec, p_rec)
            receptions = cursor.fetchone()[0] or 0
            print(f"    Réceptions: {receptions}")
    
            # Ventes
            q_ven = "SELECT COALESCE(SUM(qtvente), 0) FROM tb_ventedetail WHERE idarticle = %s AND idunite = %s AND deleted = 0"
            p_ven = [idarticle, idu_boucle]
            if idmag:
                q_ven += " AND idmag = %s"
                p_ven.append(idmag)
            cursor.execute(q_ven, p_ven)
            ventes = cursor.fetchone()[0] or 0
            print(f"    Ventes: {ventes}")
    
            # Sorties
            q_sort = "SELECT COALESCE(SUM(qtsortie), 0) FROM tb_sortiedetail WHERE idarticle = %s AND idunite = %s"
            p_sort = [idarticle, idu_boucle]
            if idmag:
                q_sort += " AND idmag = %s"
                p_sort.append(idmag)
            cursor.execute(q_sort, p_sort)
            sorties = cursor.fetchone()[0] or 0
            print(f"    Sorties: {sorties}")
    
            # Transferts IN
            q_tin = "SELECT COALESCE(SUM(qttransfert), 0) FROM tb_transfertdetail WHERE idarticle = %s AND idunite = %s AND deleted = 0"
            p_tin = [idarticle, idu_boucle]
            if idmag:
                q_tin += " AND idmagentree = %s"
                p_tin.append(idmag)
            cursor.execute(q_tin, p_tin)
            t_in = cursor.fetchone()[0] or 0
            print(f"    Transferts IN: {t_in}")
            
            # Transferts OUT
            q_tout = "SELECT COALESCE(SUM(qttransfert), 0) FROM tb_transfertdetail WHERE idarticle = %s AND idunite = %s AND deleted = 0"
            p_tout = [idarticle, idu_boucle]
            if idmag:
                q_tout += " AND idmagsortie = %s"
                p_tout.append(idmag)
            cursor.execute(q_tout, p_tout)
            t_out = cursor.fetchone()[0] or 0
            print(f"    Transferts OUT: {t_out}")
    
            # Inventaires
            q_inv = "SELECT COALESCE(SUM(qtinventaire), 0) FROM tb_inventaire WHERE codearticle = %s"
            p_inv = [code_boucle]
            if idmag:
                q_inv += " AND idmag = %s"
                p_inv.append(idmag)
            cursor.execute(q_inv, p_inv)
            inv = cursor.fetchone()[0] or 0
            print(f"    Inventaires: {inv}")

            # Avoirs
            q_avoir = """
                SELECT COALESCE(SUM(ad.qtavoir), 0) 
                FROM tb_avoirdetail ad
                INNER JOIN tb_avoir a ON ad.idavoir = a.id
                WHERE ad.idarticle = %s AND ad.idunite = %s 
                AND a.deleted = 0 AND ad.deleted = 0
            """
            p_avoir = [idarticle, idu_boucle]
            if idmag:
                q_avoir += " AND ad.idmag = %s"
                p_avoir.append(idmag)
            cursor.execute(q_avoir, p_avoir)
            avoirs = cursor.fetchone()[0] or 0
            print(f"    Avoirs: {avoirs}")

            # Calcul
            solde_unite = (receptions + t_in + inv + avoirs - ventes - sorties - t_out)
            print(f"    Solde unité: {solde_unite}")
            print(f"    Solde base: {solde_unite} × {qtunite_boucle} = {solde_unite * qtunite_boucle}")
            
            total_stock_global_base += (solde_unite * qtunite_boucle)

        # 4. Conversion finale
        stock_final = total_stock_global_base / qtunite_affichage
        print(f"\n  TOTAL BASE: {total_stock_global_base}")
        print(f"  STOCK FINAL: {total_stock_global_base} ÷ {qtunite_affichage} = {stock_final}")
        
        cursor.close()
        return max(0, stock_final)
    
    except Exception as e:
        print(f"Erreur calcul: {e}")
        import traceback
        traceback.print_exc()
        return 0

def mettre_a_jour_biscuit():
    """Met à jour tb_stock pour BISCUIT 4X4 BE dans tous les magasins"""
    conn = connect_db()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        print("="*80)
        print("MISE À JOUR tb_stock POUR BISCUIT 4X4 BE")
        print("="*80)
        
        # Récupérer les unités du BISCUIT 4X4 BE
        cursor.execute("""
            SELECT u.idarticle, u.idunite, u.codearticle, u.designationunite, a.designation
            FROM tb_unite u
            INNER JOIN tb_article a ON u.idarticle = a.idarticle
            WHERE u.codearticle IN ('0070026600', '0070026701')
            ORDER BY u.codearticle
        """)
        unites = cursor.fetchall()
        
        # Récupérer les magasins
        cursor.execute("""
            SELECT idmag, designationmag
            FROM tb_magasin
            WHERE deleted = 0
            ORDER BY idmag
        """)
        magasins = cursor.fetchall()
        
        print(f"\nUnités trouvées: {len(unites)}")
        print(f"Magasins trouvés: {len(magasins)}")
        
        for idarticle, idunite, codearticle, unite_desig, art_desig in unites:
            print(f"\n{'='*80}")
            print(f"Article: {art_desig} - {unite_desig}")
            print(f"Code: {codearticle}, idarticle: {idarticle}, idunite: {idunite}")
            print(f"{'='*80}")
            
            for idmag, nom_mag in magasins:
                print(f"\n--- Magasin: {nom_mag} (ID: {idmag}) ---")
                
                # Calculer le stock
                stock_calcule = calculer_stock_article(conn, idarticle, idunite, idmag)
                
                print(f"\n✓ Stock calculé: {stock_calcule}")
                
                # Vérifier si existe dans tb_stock
                cursor.execute("""
                    SELECT qtstock FROM tb_stock 
                    WHERE codearticle = %s AND idmag = %s
                """, (codearticle, idmag))
                
                resultat = cursor.fetchone()
                
                if resultat:
                    ancien_stock = resultat[0]
                    print(f"  Ancien stock dans tb_stock: {ancien_stock}")
                    
                    # Mettre à jour
                    cursor.execute("""
                        UPDATE tb_stock 
                        SET qtstock = %s
                        WHERE codearticle = %s AND idmag = %s
                    """, (stock_calcule, codearticle, idmag))
                    print(f"  ✓ Mise à jour : {ancien_stock} → {stock_calcule}")
                else:
                    # Insérer
                    cursor.execute("""
                        INSERT INTO tb_stock (codearticle, idmag, qtstock, qtalert, deleted)
                        VALUES (%s, %s, %s, 0, 0)
                    """, (codearticle, idmag, stock_calcule))
                    print(f"  ✓ Création : stock = {stock_calcule}")
        
        conn.commit()
        print(f"\n{'='*80}")
        print("✅ MISE À JOUR TERMINÉE")
        print(f"{'='*80}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    mettre_a_jour_biscuit()