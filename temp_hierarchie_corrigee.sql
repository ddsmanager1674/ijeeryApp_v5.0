-- temp_hierarchie_corrigee.sql
-- Requête SQL CORRIGÉE : gère la hiérarchie multi-niveaux des unités
-- Convertit chaque unité via sa chaîne hiérarchique (parent à parent à ... base)

WITH mouvements_bruts AS (
    SELECT
        lf.idarticle,
        lf.idmag,
        COALESCE(u.qtunite, 1) as qtunite_source,
        lf.qtlivrefrs as quantite,
        'reception' as type_mouvement
    FROM tb_livraisonfrs lf
    INNER JOIN tb_unite u ON lf.idarticle = u.idarticle AND lf.idunite = u.idunite
    WHERE lf.deleted = 0

    UNION ALL

    SELECT
        vd.idarticle,
        v.idmag,
        COALESCE(u.qtunite, 1) as qtunite_source,
        vd.qtvente as quantite,
        'vente' as type_mouvement
    FROM tb_ventedetail vd
    INNER JOIN tb_vente v ON vd.idvente = v.id AND v.deleted = 0
    INNER JOIN tb_unite u ON vd.idarticle = u.idarticle AND vd.idunite = u.idunite
    WHERE vd.deleted = 0

    UNION ALL

    SELECT
        t.idarticle,
        t.idmagentree as idmag,
        COALESCE(u.qtunite, 1) as qtunite_source,
        t.qttransfert as quantite,
        'transfert_in' as type_mouvement
    FROM tb_transfertdetail t
    INNER JOIN tb_unite u ON t.idarticle = u.idarticle AND t.idunite = u.idunite
    WHERE t.deleted = 0

    UNION ALL

    SELECT
        t.idarticle,
        t.idmagsortie as idmag,
        COALESCE(u.qtunite, 1) as qtunite_source,
        t.qttransfert as quantite,
        'transfert_out' as type_mouvement
    FROM tb_transfertdetail t
    INNER JOIN tb_unite u ON t.idarticle = u.idarticle AND t.idunite = u.idunite
    WHERE t.deleted = 0

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
        WHERE deleted = 0
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
    WHERE a.deleted = 0 AND ad.deleted = 0
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

-- ✅ NOUVELLE CTE : Calcul de la CHAÎNE HIÉRARCHIQUE
-- Pour chaque unité, calcule le coefficient de conversion à l'unité de base
-- via sa chaîne parent → parent → ... → base
unite_hierarchie AS (
    SELECT
        u.idarticle,
        u.idunite,
        u.niveau,
        u.qtunite,
        u.designationunite,
        -- Coefficient de conversion pour cette unité
        -- = qtunite de cette unité divisé par... (calcul récursif jusqu'à la base)
        ROW_NUMBER() OVER (PARTITION BY u.idarticle ORDER BY u.niveau) as rang_niveau,
        COALESCE(
            -- Si niveau > 1, récupérer le qtunite du niveau précédent
            LAG(u.qtunite) OVER (PARTITION BY u.idarticle ORDER BY u.niveau),
            1  -- Sinon (niveau=1), la base a un ratio de 1
        ) as qtunite_parent
    FROM tb_unite u
    WHERE u.deleted = 0
),

-- Calcul final du coefficient cumulatif pour chaque unité
unite_coeff AS (
    SELECT
        idarticle,
        idunite,
        niveau,
        qtunite,
        designationunite,
        -- Coefficient = produit du qtunite de cette unité et tous ses parents
        exp(sum(ln(NULLIF(CASE WHEN qtunite > 0 THEN qtunite ELSE 1 END, 0))) 
            OVER (PARTITION BY idarticle ORDER BY niveau ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
        ) as coeff_hierarchique
    FROM unite_hierarchie
)

SELECT
    u.codearticle,
    a.designation,
    u.designationunite,
    COALESCE(
        (SELECT cd.punitcmd
         FROM tb_commandedetail cd
         INNER JOIN tb_commande c ON cd.idcom = c.idcom
         WHERE cd.idarticle = u.idarticle
           AND cd.idunite = u.idunite
           AND c.deleted = 0
         ORDER BY c.datecom DESC
         LIMIT 1), 0
    ) as prixachat,
    u.idarticle,
    u.idunite,
    m.idmag,
    -- ✅ DIVISION PAR LE COEFFICIENT HIÉRARCHIQUE (et non par qtunite simplement)
    COALESCE(sb.solde_base, 0) / NULLIF(uc.coeff_hierarchique, 0) as stock
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
ORDER BY u.codearticle, m.idmag;
