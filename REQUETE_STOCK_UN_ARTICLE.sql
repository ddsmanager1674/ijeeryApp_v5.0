-- ============================================================================
-- REQUÊTE SIMPLIFIÉE - AFFICHAGE STOCK POUR 1 ARTICLE SPÉCIFIQUE
-- ============================================================================
-- Version simplifiée : remplacer '0070374501' par le code article désiré
-- Action: Copier-coller dans pgAdmin/DBeaver et exécuter pour voir le stock exact
-- ============================================================================

WITH mouvements_bruts AS (
    SELECT
        lf.idarticle,
        lf.idmag,
        COALESCE(u.qtunite, 1) as qtunite_source,
        lf.qtlivrefrs as quantite,
        'reception' as type_mouvement
    FROM tb_livraisonfrs lf
    INNER JOIN tb_unite u ON lf.idarticle = u.idarticle AND lf.idunite = u.idunite
    WHERE lf.deleted = 0 AND u.codearticle = '0070374501'

    UNION ALL

    SELECT
        vd.idarticle,
        v.idmag,
        COALESCE(u.qtunite, 1) as qtunite_source,
        vd.qtvente as quantite,
        'vente' as type_mouvement
    FROM tb_ventedetail vd
    INNER JOIN tb_vente v ON vd.idvente = v.id AND v.deleted = 0 AND v.statut = 'VALIDEE'
    INNER JOIN tb_unite u ON vd.idarticle = u.idarticle AND vd.idunite = u.idunite
    WHERE vd.deleted = 0 AND u.codearticle = '0070374501'

    UNION ALL

    SELECT
        t.idarticle,
        t.idmagentree as idmag,
        COALESCE(u.qtunite, 1) as qtunite_source,
        t.qttransfert as quantite,
        'transfert_in' as type_mouvement
    FROM tb_transfertdetail t
    INNER JOIN tb_unite u ON t.idarticle = u.idarticle AND t.idunite = u.idunite
    WHERE t.deleted = 0 AND u.codearticle = '0070374501'

    UNION ALL

    SELECT
        t.idarticle,
        t.idmagsortie as idmag,
        COALESCE(u.qtunite, 1) as qtunite_source,
        t.qttransfert as quantite,
        'transfert_out' as type_mouvement
    FROM tb_transfertdetail t
    INNER JOIN tb_unite u ON t.idarticle = u.idarticle AND t.idunite = u.idunite
    WHERE t.deleted = 0 AND u.codearticle = '0070374501'

    UNION ALL

    SELECT
        sd.idarticle,
        sd.idmag,
        COALESCE(u.qtunite, 1) as qtunite_source,
        sd.qtsortie as quantite,
        'sortie' as type_mouvement
    FROM tb_sortiedetail sd
    INNER JOIN tb_unite u ON sd.idarticle = u.idarticle AND sd.idunite = u.idunite
    WHERE u.codearticle = '0070374501'

    UNION ALL

    SELECT
        u.idarticle,
        i.idmag,
        COALESCE(u.qtunite, 1) as qtunite_source,
        i.qtinventaire as quantite,
        'inventaire' as type_mouvement
    FROM tb_inventaire i
    INNER JOIN tb_unite u ON i.codearticle = u.codearticle
    WHERE u.idunite IN (
        SELECT DISTINCT ON (idarticle) idunite
        FROM tb_unite
        WHERE deleted = 0 AND codearticle = '0070374501'
        ORDER BY idarticle, qtunite ASC
    )

    UNION ALL

    SELECT
        ad.idarticle,
        ad.idmag,
        COALESCE(u.qtunite, 1) as qtunite_source,
        ad.qtavoir as quantite,
        'avoir' as type_mouvement
    FROM tb_avoir a
    INNER JOIN tb_avoirdetail ad ON a.id = ad.idavoir
    INNER JOIN tb_unite u ON ad.idarticle = u.idarticle AND ad.idunite = u.idunite
    WHERE a.deleted = 0 AND ad.deleted = 0 AND u.codearticle = '0070374501'
),

solde_base_par_mag AS (
    SELECT
        idarticle,
        idmag,
        SUM(
            CASE type_mouvement
                WHEN 'reception'     THEN  quantite * qtunite_source
                WHEN 'transfert_in'  THEN  quantite * qtunite_source
                WHEN 'inventaire'    THEN  quantite * qtunite_source
                WHEN 'avoir'         THEN  quantite * qtunite_source
                WHEN 'vente'         THEN -quantite * qtunite_source
                WHEN 'sortie'        THEN -quantite * qtunite_source
                WHEN 'transfert_out' THEN -quantite * qtunite_source
                ELSE 0
            END
        ) as solde_base
    FROM mouvements_bruts
    GROUP BY idarticle, idmag
),

unite_hierarchie AS (
    SELECT
        u.idarticle,
        u.idunite,
        u.niveau,
        u.qtunite,
        u.designationunite,
        u.codearticle
    FROM tb_unite u
    WHERE u.deleted = 0 AND u.codearticle = '0070374501'
),

unite_coeff AS (
    SELECT
        idarticle,
        idunite,
        niveau,
        qtunite,
        designationunite,
        codearticle,
        exp(sum(ln(NULLIF(CASE WHEN qtunite > 0 THEN qtunite ELSE 1 END, 0))) 
            OVER (PARTITION BY idarticle ORDER BY niveau ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
        ) as coeff_hierarchique
    FROM unite_hierarchie
)

-- ============================================================================
-- RÉSULTAT
-- ============================================================================
SELECT
    u.codearticle,
    a.designation,
    u.designationunite,
    u.idarticle,
    u.idunite,
    m.designationmag,
    m.idmag,
    sb.solde_base as solde_base_brut,
    COALESCE(uc.coeff_hierarchique, 1) as coefficient,
    COALESCE(sb.solde_base, 0) / 
    NULLIF(COALESCE(uc.coeff_hierarchique, 1), 0) as stock_reel
FROM tb_unite u
INNER JOIN tb_article a ON u.idarticle = a.idarticle
CROSS JOIN tb_magasin m
LEFT JOIN solde_base_par_mag sb
    ON sb.idarticle = u.idarticle
    AND sb.idmag = m.idmag
LEFT JOIN unite_coeff uc
    ON uc.idarticle = u.idarticle
    AND uc.idunite = u.idunite
WHERE a.deleted = 0
  AND m.deleted = 0
  AND u.codearticle = '0070374501'
ORDER BY m.idmag ASC, u.designationunite ASC;
