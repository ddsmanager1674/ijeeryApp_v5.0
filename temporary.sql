-- temporary.sql
-- Requête d'extraction des articles + stock (utilisée dans pages/page_venteParMsin.py)

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
                WHEN 'vente'         THEN -quantite * qtunite_source
                WHEN 'transfert_out' THEN -quantite * qtunite_source
                ELSE 0
            END
        ) as solde_base
    FROM mouvements_bruts
    GROUP BY idarticle, idmag
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
    COALESCE(sb.solde_base, 0) / NULLIF(COALESCE(u.qtunite, 1), 0) as stock
FROM tb_unite u
INNER JOIN tb_article a ON u.idarticle = a.idarticle
CROSS JOIN tb_magasin m
LEFT JOIN solde_base_par_mag sb
    ON sb.idarticle = u.idarticle
    AND sb.idmag = m.idmag
WHERE a.deleted = 0
  AND m.deleted = 0
ORDER BY u.codearticle, m.idmag;
