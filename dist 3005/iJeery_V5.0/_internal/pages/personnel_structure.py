# -*- coding: utf-8 -*-
"""
Structure personnel : categories et postes.

Le nouveau rattachement met tb_personnel.idposte au centre. L'ancienne colonne
idfonction reste en base pour compatibilite utilisateurs/autorisations, mais
n'est plus utilisee par l'ajout/modification du personnel.
"""


UNKNOWN_LABEL = "Inconnu"
_STRUCTURE_READY = False


def ensure_personnel_structure(conn):
    """Cree les tables/colonnes necessaires au concept categorie -> poste."""
    global _STRUCTURE_READY
    if not conn:
        return False
    if _STRUCTURE_READY:
        return True
    cur = conn.cursor()
    try:
        # Evite les blocages UI si une autre transaction tient un verrou.
        cur.execute("SET LOCAL lock_timeout = '1500ms'")
        cur.execute("SET LOCAL statement_timeout = '5000ms'")

        cur.execute(
            """
            SELECT
                to_regclass('public.tb_categoriepersonnel') IS NOT NULL,
                to_regclass('public.tb_postepersonnel') IS NOT NULL,
                EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema='public'
                      AND table_name='tb_personnel'
                      AND column_name='idposte'
                ),
                EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname='tb_personnel_idposte_fkey'
                )
            """
        )
        has_cat, has_poste, has_idposte, has_fk = cur.fetchone()
        if has_cat and has_poste and has_idposte and has_fk:
            conn.commit()
            _STRUCTURE_READY = True
            return True

        if not has_cat:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tb_categoriepersonnel (
                    idcategorie SERIAL PRIMARY KEY,
                    titre VARCHAR(120) NOT NULL,
                    description TEXT,
                    dateregistre TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted INTEGER DEFAULT 0
                )
                """
            )
        if not has_poste:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tb_postepersonnel (
                    idposte SERIAL PRIMARY KEY,
                    idcategorie INTEGER REFERENCES tb_categoriepersonnel(idcategorie)
                        ON UPDATE CASCADE ON DELETE SET NULL,
                    titre VARCHAR(120) NOT NULL,
                    description TEXT,
                    dateregistre TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted INTEGER DEFAULT 0
                )
                """
            )
        if not has_idposte:
            cur.execute("ALTER TABLE tb_personnel ADD COLUMN IF NOT EXISTS idposte INTEGER")
        if not has_fk:
            cur.execute(
                """
                ALTER TABLE tb_personnel
                ADD CONSTRAINT tb_personnel_idposte_fkey
                FOREIGN KEY (idposte)
                REFERENCES tb_postepersonnel(idposte)
                ON UPDATE CASCADE
                ON DELETE SET NULL
                NOT VALID
                """
            )
        conn.commit()
        _STRUCTURE_READY = True
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def has_personnel_structure(conn):
    """Verification rapide, sans DDL, pour choisir les requetes de fallback."""
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                to_regclass('public.tb_categoriepersonnel') IS NOT NULL
                AND to_regclass('public.tb_postepersonnel') IS NOT NULL
                AND EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema='public'
                      AND table_name='tb_personnel'
                      AND column_name='idposte'
                )
            """
        )
        ok = bool(cur.fetchone()[0])
        conn.commit()
        return ok
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def personnel_poste_select(extra_where=""):
    """Fragment SELECT standard avec fallback Inconnu."""
    where = f" AND {extra_where}" if extra_where else ""
    return f"""
        SELECT p.id, p.matricule, p.nom, p.prenom, p.adresse,
               p.cin, p.contact, p.sexe,
               COALESCE(cp.titre, '{UNKNOWN_LABEL}') AS categorie,
               COALESCE(pp.titre, '{UNKNOWN_LABEL}') AS poste,
               p.idposte, pp.idcategorie
        FROM tb_personnel p
        LEFT JOIN tb_postepersonnel pp
               ON p.idposte = pp.idposte AND COALESCE(pp.deleted, 0)=0
        LEFT JOIN tb_categoriepersonnel cp
               ON pp.idcategorie = cp.idcategorie AND COALESCE(cp.deleted, 0)=0
        WHERE COALESCE(p.deleted, 0)=0{where}
    """


def personnel_poste_join_columns():
    """Colonnes courtes pour les autres modules."""
    return (
        "COALESCE(cp.titre, 'Inconnu') AS categorie, "
        "COALESCE(pp.titre, 'Inconnu') AS poste"
    )


def personnel_poste_joins(alias="p"):
    return f"""
        LEFT JOIN tb_postepersonnel pp
               ON {alias}.idposte = pp.idposte AND COALESCE(pp.deleted, 0)=0
        LEFT JOIN tb_categoriepersonnel cp
               ON pp.idcategorie = cp.idcategorie AND COALESCE(cp.deleted, 0)=0
    """
