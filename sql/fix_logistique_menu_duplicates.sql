-- Fusionne les doublons de menus LOGISTIQUE et réaligne tb_autorisation.
-- À exécuter une fois si logistique_module.sql a été rejoué sans garde-fou.

WITH dups AS (
    SELECT designationmenu, MIN(id) AS keep_id, array_agg(id ORDER BY id) AS ids
    FROM tb_menu
    WHERE designationmenu IN (
        'BLOC: LOGISTIQUE',
        'Parc Vehicule', 'Pieces Detachees', 'Carburant',
        'Itineraires', 'Bons Sortie', 'Maintenance', 'Rapport Logistique'
    )
    GROUP BY designationmenu
    HAVING COUNT(*) > 1
),
dup_rows AS (
    SELECT keep_id, unnest(ids[2:array_length(ids, 1)])::int AS dup_id
    FROM dups
)
UPDATE tb_autorisation a
SET idmenu = d.keep_id
FROM dup_rows d
WHERE a.idmenu = d.dup_id
  AND NOT EXISTS (
      SELECT 1 FROM tb_autorisation x
      WHERE x.idfonction = a.idfonction AND x.idmenu = d.keep_id
  );

WITH dups AS (
    SELECT designationmenu, MIN(id) AS keep_id, array_agg(id ORDER BY id) AS ids
    FROM tb_menu
    WHERE designationmenu IN (
        'BLOC: LOGISTIQUE',
        'Parc Vehicule', 'Pieces Detachees', 'Carburant',
        'Itineraires', 'Bons Sortie', 'Maintenance', 'Rapport Logistique'
    )
    GROUP BY designationmenu
    HAVING COUNT(*) > 1
),
dup_rows AS (
    SELECT unnest(ids[2:array_length(ids, 1)])::int AS dup_id
    FROM dups
)
DELETE FROM tb_autorisation a
USING dup_rows d
WHERE a.idmenu = d.dup_id;

WITH dups AS (
    SELECT designationmenu, MIN(id) AS keep_id, array_agg(id ORDER BY id) AS ids
    FROM tb_menu
    WHERE designationmenu IN (
        'BLOC: LOGISTIQUE',
        'Parc Vehicule', 'Pieces Detachees', 'Carburant',
        'Itineraires', 'Bons Sortie', 'Maintenance', 'Rapport Logistique'
    )
    GROUP BY designationmenu
    HAVING COUNT(*) > 1
),
dup_rows AS (
    SELECT unnest(ids[2:array_length(ids, 1)])::int AS dup_id
    FROM dups
)
DELETE FROM tb_menu m
USING dup_rows d
WHERE m.id = d.dup_id;
