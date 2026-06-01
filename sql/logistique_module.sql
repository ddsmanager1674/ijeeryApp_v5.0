-- ============================================================
--  iJeery V5.0 — Module LOGISTIQUE (tables + menus)
--  À exécuter UNE SEULE FOIS dans psql
-- ============================================================

SELECT setval('tb_menu_id_seq', (SELECT MAX(id) FROM tb_menu));

CREATE TABLE IF NOT EXISTS logistique_vehicule (
    id                SERIAL PRIMARY KEY,
    immatriculation   VARCHAR(30) UNIQUE NOT NULL,
    marque            VARCHAR(60) NOT NULL,
    modele            VARCHAR(60),
    type_vehicule     VARCHAR(40)  DEFAULT 'Voiture',
    annee             INTEGER,
    couleur           VARCHAR(30),
    num_chassis       VARCHAR(60),
    num_moteur        VARCHAR(60),
    kilometrage       NUMERIC(10,1) DEFAULT 0,
    carburant         VARCHAR(20)   DEFAULT 'Diesel',
    date_mise_service DATE,
    statut            VARCHAR(30)   DEFAULT 'Actif',
    chauffeur         VARCHAR(80),
    notes             TEXT,
    created_at        TIMESTAMP     DEFAULT NOW(),
    updated_at        TIMESTAMP     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vehicule_immat  ON logistique_vehicule (immatriculation);
CREATE INDEX IF NOT EXISTS idx_vehicule_statut ON logistique_vehicule (statut);

CREATE TABLE IF NOT EXISTS logistique_piece (
    id              SERIAL PRIMARY KEY,
    reference       VARCHAR(40) UNIQUE NOT NULL,
    designation     VARCHAR(120) NOT NULL,
    categorie       VARCHAR(40)  DEFAULT 'Autre',
    marque_vehicule VARCHAR(60),
    fournisseur     VARCHAR(80),
    quantite        INTEGER      DEFAULT 0,
    seuil_alerte    INTEGER      DEFAULT 2,
    prix_unitaire   NUMERIC(12,2),
    emplacement     VARCHAR(80),
    notes           TEXT,
    created_at      TIMESTAMP    DEFAULT NOW(),
    updated_at      TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_piece_reference ON logistique_piece (reference);
CREATE INDEX IF NOT EXISTS idx_piece_quantite  ON logistique_piece (quantite);

CREATE TABLE IF NOT EXISTS logistique_piece_mouvement (
    id              SERIAL PRIMARY KEY,
    piece_id        INTEGER REFERENCES logistique_piece(id) ON DELETE CASCADE,
    type_mouvement  VARCHAR(10)  NOT NULL
                    CHECK (type_mouvement IN ('Entrée','Sortie')),
    quantite        INTEGER      NOT NULL CHECK (quantite > 0),
    ref_document    VARCHAR(60),
    vehicule        VARCHAR(80),
    motif           TEXT,
    date_mouvement  TIMESTAMP    DEFAULT NOW(),
    created_at      TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mvt_piece ON logistique_piece_mouvement (piece_id);

CREATE TABLE IF NOT EXISTS logistique_carburant (
    id              SERIAL PRIMARY KEY,
    vehicule_id     INTEGER REFERENCES logistique_vehicule(id) ON DELETE SET NULL,
    date_plein      DATE         NOT NULL DEFAULT CURRENT_DATE,
    litres          NUMERIC(8,2) NOT NULL,
    prix_litre      NUMERIC(8,2),
    montant_total   NUMERIC(12,2),
    km_au_plein     NUMERIC(10,1),
    type_carburant  VARCHAR(20)  DEFAULT 'Diesel',
    station         VARCHAR(80),
    ref_bon         VARCHAR(60),
    notes           TEXT,
    created_at      TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_carburant_date ON logistique_carburant (date_plein);
CREATE INDEX IF NOT EXISTS idx_carburant_veh  ON logistique_carburant (vehicule_id);

CREATE TABLE IF NOT EXISTS logistique_mission (
    id              SERIAL PRIMARY KEY,
    vehicule_id     INTEGER REFERENCES logistique_vehicule(id) ON DELETE SET NULL,
    chauffeur       VARCHAR(80)  NOT NULL,
    depart          VARCHAR(120) NOT NULL,
    destination     VARCHAR(120) NOT NULL,
    objet           TEXT,
    date_depart     TIMESTAMP,
    date_retour     TIMESTAMP,
    km_depart       NUMERIC(10,1),
    km_retour       NUMERIC(10,1),
    statut          VARCHAR(20)  DEFAULT 'Planifié'
                    CHECK (statut IN ('Planifié','En cours','Terminé','Annulé')),
    passagers       VARCHAR(120),
    notes           TEXT,
    created_at      TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mission_statut   ON logistique_mission (statut);
CREATE INDEX IF NOT EXISTS idx_mission_date     ON logistique_mission (date_depart);
CREATE INDEX IF NOT EXISTS idx_mission_vehicule ON logistique_mission (vehicule_id);

CREATE TABLE IF NOT EXISTS logistique_maintenance (
    id                SERIAL PRIMARY KEY,
    vehicule_id       INTEGER REFERENCES logistique_vehicule(id) ON DELETE SET NULL,
    type_travaux      VARCHAR(80)  NOT NULL,
    description       TEXT,
    garage            VARCHAR(80),
    date_entree       DATE,
    date_sortie       DATE,
    kilometrage       NUMERIC(10,1),
    cout_estime       NUMERIC(12,2),
    cout              NUMERIC(12,2),
    statut            VARCHAR(20)  DEFAULT 'En attente'
                      CHECK (statut IN ('En attente','En cours','Terminé','Annulé')),
    pieces_utilisees  TEXT,
    prochain_km       NUMERIC(10,1),
    notes             TEXT,
    created_at        TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_maintenance_statut   ON logistique_maintenance (statut);
CREATE INDEX IF NOT EXISTS idx_maintenance_vehicule ON logistique_maintenance (vehicule_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_date     ON logistique_maintenance (date_entree);

CREATE TABLE IF NOT EXISTS logistique_bon_sortie (
    id           SERIAL PRIMARY KEY,
    numero_bon   VARCHAR(40) UNIQUE NOT NULL,
    type_bon     VARCHAR(40)  DEFAULT 'Sortie Matériel',
    date_bon     DATE         NOT NULL DEFAULT CURRENT_DATE,
    demandeur    VARCHAR(80)  NOT NULL,
    service      VARCHAR(80),
    responsable  VARCHAR(80),
    destination  VARCHAR(120),
    statut       VARCHAR(20)  DEFAULT 'Brouillon'
                 CHECK (statut IN ('Brouillon','Validé','Clôturé','Annulé')),
    observations TEXT,
    vehicule_id  INTEGER REFERENCES logistique_vehicule(id) ON DELETE SET NULL,
    chauffeur    VARCHAR(80),
    created_at   TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bon_date   ON logistique_bon_sortie (date_bon);
CREATE INDEX IF NOT EXISTS idx_bon_statut ON logistique_bon_sortie (statut);
CREATE INDEX IF NOT EXISTS idx_bon_numero ON logistique_bon_sortie (numero_bon);

CREATE TABLE IF NOT EXISTS logistique_bon_sortie_ligne (
    id           SERIAL PRIMARY KEY,
    bon_id       INTEGER NOT NULL
                 REFERENCES logistique_bon_sortie(id) ON DELETE CASCADE,
    designation  VARCHAR(120) NOT NULL,
    quantite     NUMERIC(10,3) DEFAULT 1,
    unite        VARCHAR(30)   DEFAULT 'Unité',
    observation  TEXT
);

CREATE INDEX IF NOT EXISTS idx_ligne_bon ON logistique_bon_sortie_ligne (bon_id);

INSERT INTO tb_menu (designationmenu, page)
SELECT v.designationmenu, v.page
FROM (VALUES
    ('BLOC: LOGISTIQUE',   ''),
    ('Parc Vehicule',      'pages.page_parcVehicule'),
    ('Pieces Detachees',   'pages.page_piecesDetachees'),
    ('Carburant',          'pages.page_carburant'),
    ('Itineraires',        'pages.page_itineraires'),
    ('Bons Sortie',        'pages.page_bonsSortie'),
    ('Maintenance',        'pages.page_maintenance'),
    ('Rapport Logistique', 'pages.page_rapportLogistique')
) AS v(designationmenu, page)
WHERE NOT EXISTS (
    SELECT 1 FROM tb_menu m WHERE m.designationmenu = v.designationmenu
);

-- Droits admin (fonction 1) : à adapter si votre id admin diffère
INSERT INTO tb_autorisation (idfonction, idmenu)
SELECT 1, m.id FROM tb_menu m
WHERE m.designationmenu IN (
    'BLOC: LOGISTIQUE',
    'Parc Vehicule', 'Pieces Detachees', 'Carburant',
    'Itineraires', 'Bons Sortie', 'Maintenance', 'Rapport Logistique'
)
AND NOT EXISTS (
    SELECT 1 FROM tb_autorisation a
    WHERE a.idfonction = 1 AND a.idmenu = m.id
);
