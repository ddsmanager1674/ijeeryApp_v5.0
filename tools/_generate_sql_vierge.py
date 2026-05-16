#!/usr/bin/env python3
"""Génère sql/ijeery_schema_vide.sql et sql/ijeery_seed_minimal.sql."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"
STRUCTURE = ROOT / "Structure database.sql"
MENUS_EXPORT = SQL_DIR / "_menus_admin_export.sql"

SCHEMA_OUT = SQL_DIR / "ijeery_schema_vide.sql"
SEED_OUT = SQL_DIR / "ijeery_seed_minimal.sql"

HEADER_SCHEMA = """-- =============================================================================
-- iJeery V5.0 — Base de données VIERGE (structure complète, aucune donnée)
-- =============================================================================
-- Source  : Structure database.sql + base sarah_gros (PostgreSQL 16)
-- Usage   :
--   1) Créer la base : CREATE DATABASE ijeery_vierge OWNER postgres;
--   2) psql -U postgres -d ijeery_vierge -f sql/ijeery_schema_vide.sql
--   3) psql -U postgres -d ijeery_vierge -f sql/ijeery_seed_minimal.sql
--
-- Contenu : tables, séquences, contraintes, index, clés étrangères — 0 ligne métier
-- =============================================================================

BEGIN;

DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;

SET search_path TO public, pg_catalog;

"""

EXTRA_TABLES = """
-- Tables paramètres (présentes sur sarah_gros, absentes du dump Structure initial)
CREATE TABLE public.tb_param_livraison_client (
    id smallint NOT NULL DEFAULT 1,
    idtransporteur_defaut integer,
    transporteur_bl_auto smallint NOT NULL DEFAULT 0,
    CONSTRAINT tb_param_livraison_client_pkey PRIMARY KEY (id),
    CONSTRAINT tb_param_livraison_client_singleton CHECK (id = 1)
);

CREATE TABLE public.tb_param_commande_frs (
    id smallint NOT NULL DEFAULT 1,
    idfrs_defaut integer,
    CONSTRAINT tb_param_commande_frs_pkey PRIMARY KEY (id),
    CONSTRAINT tb_param_commande_frs_singleton CHECK (id = 1)
);

ALTER TABLE ONLY public.tb_param_livraison_client
    ADD CONSTRAINT tb_param_livraison_client_idtransporteur_fkey
    FOREIGN KEY (idtransporteur_defaut) REFERENCES public.tb_transporteur(idtransporteur)
    ON UPDATE CASCADE ON DELETE SET NULL;

ALTER TABLE ONLY public.tb_param_commande_frs
    ADD CONSTRAINT tb_param_commande_frs_idfrs_defaut_fkey
    FOREIGN KEY (idfrs_defaut) REFERENCES public.tb_fournisseur(idfrs)
    ON UPDATE CASCADE ON DELETE SET NULL;
"""

FOOTER_SCHEMA = (
    EXTRA_TABLES
    + """
COMMIT;

-- Fin schéma vide — exécuter ensuite : sql/ijeery_seed_minimal.sql
"""
)

SEED_HEADER = """-- =============================================================================
-- iJeery V5.0 — Données minimales de démarrage
-- =============================================================================
-- À exécuter APRÈS ijeery_schema_vide.sql sur une base vide.
--
-- Compte par défaut :
--   Utilisateur : admin
--   Mot de passe : admin
--
-- Pensez à adapter config.json (database) vers le nom de votre base.
-- =============================================================================

BEGIN;

SET search_path TO public, pg_catalog;

-- Référentiels de base
"""

def main():
    SQL_DIR.mkdir(exist_ok=True)
    body = STRUCTURE.read_text(encoding="utf-8")
    # Retirer l'en-tête pg_dump redondant (on garde le corps CREATE)
    start = body.find("SET statement_timeout")
    if start == -1:
        start = body.find("CREATE TABLE")
    schema_content = HEADER_SCHEMA + body[start:] + FOOTER_SCHEMA
    SCHEMA_OUT.write_text(schema_content, encoding="utf-8")
    print(f"Wrote {SCHEMA_OUT} ({len(schema_content)} chars)")

    menus_raw = MENUS_EXPORT.read_text(encoding="utf-8") if MENUS_EXPORT.is_file() else ""
    if "INSERT INTO tb_autorisation" in menus_raw:
        menus_sql = menus_raw.split("INSERT INTO tb_autorisation")[0].strip()
    else:
        menus_sql = menus_raw
    if menus_sql and not menus_sql.rstrip().endswith(";"):
        menus_sql += ";"
    menus_sql += "\n"

    seed_parts = [
        SEED_HEADER,
        """INSERT INTO tb_fonction (idfonction, designationfonction, dateregistre, idautorisation, deleted) VALUES
  (1, 'Administration', CURRENT_TIMESTAMP, 1, 0);

INSERT INTO tb_magasin (idmag, designationmag, adressemag, livraison, deleted, livraison_auto_client) VALUES
  (1, 'Principal', 'Siège', 0, 0, 0);

INSERT INTO tb_typeoperation (idtypeoperation, typeoperation) VALUES
  (1, 'ENC'),
  (2, 'DEC');

INSERT INTO tb_modepaiement (idmode, modedepaiement) VALUES
  (1, 'Espèces'),
  (2, 'Chèque bancaire'),
  (3, 'Virement bancaire'),
  (4, 'Crédit'),
  (5, 'Autres'),
  (6, 'Orange Money'),
  (7, 'Airtel Money'),
  (8, 'Mvola');

INSERT INTO tb_typepmt (idtypepmt, typepmt, deleted) VALUES
  (1, 'PAYE', 0),
  (2, 'NON PAYE', 0);

INSERT INTO tb_typeclient (idtypeclient, designationtypeclient) VALUES
  (1, 'Au Comptoir'),
  (2, 'A Crédit');

INSERT INTO tb_categoriecompte (idcc, categoriecompte) VALUES
  (1, 'APPRO CAISSE'),
  (2, 'FOURNITURES'),
  (3, 'Frais divers'),
  (4, 'FRAIS BANCAIRE'),
  (5, 'INTERET CREDITEUR');

INSERT INTO tb_categoriearticle (idca, designationcat, deleted) VALUES
  (1, 'DIVERS', 0);

INSERT INTO tb_infosociete (id, nomsociete, adressesociete, contactsociete, villesociete, nifsociete, statsociete, cifsociete, ambleme, autre) VALUES
  (1, 'MON ENTREPRISE', 'Adresse', 'Contact', 'Ville', '', '', NULL, '---', '---');

INSERT INTO tb_configdb (id, dbname, username, password, host, port) VALUES
  (1, 'ijeery_vierge', 'postgres', 'root', 'localhost', 5432);

INSERT INTO tb_transporteur (idtransporteur, nom, contact, adresse, deleted) VALUES
  (1, 'Transport par défaut', '', '', 0);

INSERT INTO tb_codeautorisation (id, code, iduser, deleted, username) VALUES
  (1, '1230', 1, 0, 'admin');

INSERT INTO tb_param_livraison_client (id, idtransporteur_defaut, transporteur_bl_auto) VALUES
  (1, 1, 0);

INSERT INTO tb_param_commande_frs (id, idfrs_defaut) VALUES
  (1, NULL);

""",
        menus_sql,
        "\n-- Droits administrateur : tous les menus\n",
        "INSERT INTO tb_autorisation (idfonction, idmenu)\n",
        "SELECT 1, id FROM tb_menu\n",
        "WHERE NOT EXISTS (\n",
        "  SELECT 1 FROM tb_autorisation a WHERE a.idfonction = 1 AND a.idmenu = tb_menu.id\n",
        ");\n\n",
        """INSERT INTO tb_users (
  iduser, nomuser, prenomuser, adresseuser, contactuser,
  username, password, idfonction, idmag, active, dateregistre, deleted
) VALUES (
  1, 'Administrateur', 'Système', '', '',
  'admin', 'admin', 1, 1, 1, CURRENT_TIMESTAMP, 0
);

""",
        "-- Synchronisation des séquences\n",
        _sequence_resets(),
        "\nCOMMIT;\n",
    ]
    SEED_OUT.write_text("".join(seed_parts), encoding="utf-8")
    print(f"Wrote {SEED_OUT}")


def _sequence_resets() -> str:
    """Aligne les séquences sur les ID insérés explicitement dans ce seed."""
    pairs = [
        ("tb_fonction_idfonction_seq", 1),
        ("tb_magasin_idmag_seq", 1),
        ("tb_typeoperation_idtypeoperation_seq", 2),
        ("tb_modepaiement_idmode_seq", 8),
        ("tb_typepmt_idtypepmt_seq", 2),
        ("tb_typeclient_idtypeclient_seq", 2),
        ("tb_categoriecompte_idcc_seq", 5),
        ("tb_categoriearticle_idca_seq", 1),
        ("tb_infosociete_id_seq", 1),
        ("tb_configdb_id_seq", 1),
        ("tb_transporteur_idtransporteur_seq", 1),
        ("tb_codeautorisation_id_seq", 1),
        ("tb_users_iduser_seq", 1),
        ("tb_menu_id_seq", 87),
    ]
    lines = [
        "SELECT setval('public.tb_autorisation_id_seq', "
        "(SELECT COALESCE(MAX(id), 1) FROM tb_autorisation), true);"
    ]
    for seq, val in pairs:
        lines.append(f"SELECT setval('public.{seq}', {val}, true);")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
