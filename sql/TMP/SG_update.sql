-- =============================================================================
-- iJeery V5.0 — SG_update.sql
-- =============================================================================
-- But:
--   Aligner une base "ancienne structure" (ex: dumps `sql/TMP/SG0505.sql` et `sql/TMP/AM0505.sql`)
--   sur la référence `sql/Structure database.sql`.
--
-- Référence utilisée:
--   - `sql/Structure database.sql` (pg_dump) : contient la structure attendue par le logiciel
--   - `sql/TMP/SG0505.sql` et `sql/TMP/AM0505.sql` : exemples de structures prod “anciennes”
--
-- Propriétés:
--   - Idempotent: ré-exécutable sans erreur si déjà appliqué.
--   - Additif: crée les objets manquants, ajoute les colonnes manquantes, corrige certains typos.
--   - Ne supprime rien (pas de DROP).
--   - Safe FK: n'ajoute une FK que si la PK/UNIQUE existe côté table référencée.
--
-- Exécution (exemple):
--   psql -v ON_ERROR_STOP=1 -U postgres -d <votre_base> -f sql/TMP/SG_update.sql
-- =============================================================================

SET client_min_messages = warning;

BEGIN;

-- ---------------------------------------------------------------------------
-- 1) Tables/objets absents des dumps anciens (référence -> prod)
-- ---------------------------------------------------------------------------

-- Logs (présents dans la référence)
CREATE TABLE IF NOT EXISTS public.event_logs (
    id_log timestamp with time zone DEFAULT clock_timestamp() NOT NULL,
    description text NOT NULL,
    "user" character varying(150),
    datetime timestamp with time zone DEFAULT now() NOT NULL
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'event_logs_pkey') THEN
        ALTER TABLE IF EXISTS public.event_logs
            ADD CONSTRAINT event_logs_pkey PRIMARY KEY (id_log);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.tb_log_evenements (
    id_log timestamp with time zone DEFAULT clock_timestamp() NOT NULL,
    description text NOT NULL,
    "user" character varying(150),
    datetime timestamp with time zone DEFAULT now() NOT NULL
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tb_log_evenements_pkey') THEN
        ALTER TABLE IF EXISTS public.tb_log_evenements
            ADD CONSTRAINT tb_log_evenements_pkey PRIMARY KEY (id_log);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_tb_log_evenements_datetime
    ON public.tb_log_evenements USING btree (datetime DESC);

CREATE INDEX IF NOT EXISTS idx_tb_log_evenements_user
    ON public.tb_log_evenements USING btree ("user");

-- Personnel: catégories / postes (référence)
CREATE TABLE IF NOT EXISTS public.tb_categoriepersonnel (
    idcategorie integer NOT NULL,
    titre character varying(120) NOT NULL,
    description text,
    dateregistre timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    deleted integer DEFAULT 0
);

CREATE SEQUENCE IF NOT EXISTS public.tb_categoriepersonnel_idcategorie_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.tb_categoriepersonnel_idcategorie_seq OWNED BY public.tb_categoriepersonnel.idcategorie;

ALTER TABLE IF EXISTS public.tb_categoriepersonnel
    ALTER COLUMN idcategorie SET DEFAULT nextval('public.tb_categoriepersonnel_idcategorie_seq'::regclass);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tb_categoriepersonnel_pkey') THEN
        ALTER TABLE IF EXISTS public.tb_categoriepersonnel
            ADD CONSTRAINT tb_categoriepersonnel_pkey PRIMARY KEY (idcategorie);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.tb_postepersonnel (
    idposte integer NOT NULL,
    idcategorie integer,
    titre character varying(120) NOT NULL,
    description text,
    dateregistre timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    deleted integer DEFAULT 0
);

CREATE SEQUENCE IF NOT EXISTS public.tb_postepersonnel_idposte_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.tb_postepersonnel_idposte_seq OWNED BY public.tb_postepersonnel.idposte;

ALTER TABLE IF EXISTS public.tb_postepersonnel
    ALTER COLUMN idposte SET DEFAULT nextval('public.tb_postepersonnel_idposte_seq'::regclass);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tb_postepersonnel_pkey') THEN
        ALTER TABLE IF EXISTS public.tb_postepersonnel
            ADD CONSTRAINT tb_postepersonnel_pkey PRIMARY KEY (idposte);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tb_postepersonnel_idcategorie_fkey') THEN
        ALTER TABLE IF EXISTS public.tb_postepersonnel
            ADD CONSTRAINT tb_postepersonnel_idcategorie_fkey
            FOREIGN KEY (idcategorie) REFERENCES public.tb_categoriepersonnel(idcategorie)
            ON UPDATE CASCADE ON DELETE SET NULL;
    END IF;
END $$;

-- Entrées (présentes dans la référence)
CREATE TABLE IF NOT EXISTS public.tb_entree (
    id integer NOT NULL,
    refentree character varying(50),
    iduser integer,
    dateregistre timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    description character varying(150),
    deleted integer DEFAULT 0
);

CREATE SEQUENCE IF NOT EXISTS public.tb_entree_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.tb_entree_id_seq OWNED BY public.tb_entree.id;

ALTER TABLE IF EXISTS public.tb_entree
    ALTER COLUMN id SET DEFAULT nextval('public.tb_entree_id_seq'::regclass);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tb_entree_pkey') THEN
        ALTER TABLE IF EXISTS public.tb_entree
            ADD CONSTRAINT tb_entree_pkey PRIMARY KEY (id);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.tb_entreedetail (
    id integer NOT NULL,
    idmag integer,
    idarticle integer,
    idunite integer,
    qtentree double precision,
    typemouvement integer DEFAULT 1,
    deleted integer DEFAULT 0,
    identree integer,
    motif character varying(250)
);

CREATE SEQUENCE IF NOT EXISTS public.tb_entreedetail_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.tb_entreedetail_id_seq OWNED BY public.tb_entreedetail.id;

ALTER TABLE IF EXISTS public.tb_entreedetail
    ALTER COLUMN id SET DEFAULT nextval('public.tb_entreedetail_id_seq'::regclass);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tb_entreedetail_pkey') THEN
        ALTER TABLE IF EXISTS public.tb_entreedetail
            ADD CONSTRAINT tb_entreedetail_pkey PRIMARY KEY (id);
    END IF;
END $$;

-- Livraison en attente (présente dans la référence)
CREATE TABLE IF NOT EXISTS public.tb_livraisoncli_attente (
    id integer NOT NULL,
    refvente character varying(50),
    idarticle integer,
    idunite integer,
    idmag integer,
    idclient integer,
    qt_a_livrer double precision,
    qt_bl double precision DEFAULT 0,
    statut character varying(20) DEFAULT 'EN_ATTENTE'::character varying,
    dateregistre timestamp without time zone,
    iduser integer
);

CREATE SEQUENCE IF NOT EXISTS public.tb_livraisoncli_attente_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.tb_livraisoncli_attente_id_seq OWNED BY public.tb_livraisoncli_attente.id;

ALTER TABLE IF EXISTS public.tb_livraisoncli_attente
    ALTER COLUMN id SET DEFAULT nextval('public.tb_livraisoncli_attente_id_seq'::regclass);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tb_livraisoncli_attente_pkey') THEN
        ALTER TABLE IF EXISTS public.tb_livraisoncli_attente
            ADD CONSTRAINT tb_livraisoncli_attente_pkey PRIMARY KEY (id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_livcli_attente_statut
    ON public.tb_livraisoncli_attente USING btree (statut);

CREATE INDEX IF NOT EXISTS idx_livcli_attente_refvente
    ON public.tb_livraisoncli_attente USING btree (refvente);

-- Historique sauvegarde (référence)
CREATE TABLE IF NOT EXISTS public.tb_save_history (
    id integer NOT NULL,
    datetime timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    libelle character varying(255) NOT NULL,
    appareil character varying(200),
    description text,
    taille_mo numeric(14, 2),
    utilisateur character varying(150)
);

CREATE SEQUENCE IF NOT EXISTS public.tb_save_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.tb_save_history_id_seq OWNED BY public.tb_save_history.id;

ALTER TABLE IF EXISTS public.tb_save_history
    ALTER COLUMN id SET DEFAULT nextval('public.tb_save_history_id_seq'::regclass);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tb_save_history_pkey') THEN
        ALTER TABLE IF EXISTS public.tb_save_history
            ADD CONSTRAINT tb_save_history_pkey PRIMARY KEY (id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_tb_save_history_datetime
    ON public.tb_save_history USING btree (datetime DESC);

CREATE INDEX IF NOT EXISTS idx_tb_save_history_utilisateur
    ON public.tb_save_history USING btree (utilisateur);

-- Paramètres (référence)
CREATE TABLE IF NOT EXISTS public.tb_param_livraison_client (
    id smallint NOT NULL DEFAULT 1,
    idtransporteur_defaut integer,
    transporteur_bl_auto smallint NOT NULL DEFAULT 0,
    CONSTRAINT tb_param_livraison_client_pkey PRIMARY KEY (id),
    CONSTRAINT tb_param_livraison_client_singleton CHECK (id = 1)
);

INSERT INTO public.tb_param_livraison_client (id, idtransporteur_defaut, transporteur_bl_auto)
VALUES (1, NULL, 0)
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS public.tb_param_commande_frs (
    id smallint NOT NULL DEFAULT 1,
    idfrs_defaut integer,
    CONSTRAINT tb_param_commande_frs_pkey PRIMARY KEY (id),
    CONSTRAINT tb_param_commande_frs_singleton CHECK (id = 1)
);

INSERT INTO public.tb_param_commande_frs (id, idfrs_defaut)
VALUES (1, NULL)
ON CONFLICT (id) DO NOTHING;

-- Assurer l'unicité côté tables référencées (sinon FK impossible)
DO $$
BEGIN
    -- tb_transporteur(idtransporteur) doit être UNIQUE/PK
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = 'public'
          AND t.relname = 'tb_transporteur'
          AND c.contype IN ('p','u')
          AND pg_get_constraintdef(c.oid) ILIKE '%(idtransporteur)%'
    ) THEN
        BEGIN
            ALTER TABLE IF EXISTS public.tb_transporteur
                ADD CONSTRAINT tb_transporteur_pkey PRIMARY KEY (idtransporteur);
        EXCEPTION WHEN others THEN
            RAISE NOTICE 'Impossible d''ajouter la PK tb_transporteur(idtransporteur) (doublons/NULL ?). FK tb_param_livraison_client sera ignorée si nécessaire.';
        END;
    END IF;

    -- tb_fournisseur(idfrs) doit être UNIQUE/PK
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = 'public'
          AND t.relname = 'tb_fournisseur'
          AND c.contype IN ('p','u')
          AND pg_get_constraintdef(c.oid) ILIKE '%(idfrs)%'
    ) THEN
        BEGIN
            ALTER TABLE IF EXISTS public.tb_fournisseur
                ADD CONSTRAINT tb_fournisseur_pkey PRIMARY KEY (idfrs);
        EXCEPTION WHEN others THEN
            RAISE NOTICE 'Impossible d''ajouter la PK tb_fournisseur(idfrs) (doublons/NULL ?). FK tb_param_commande_frs sera ignorée si nécessaire.';
        END;
    END IF;

    -- Assurer les DEFAULT nextval(...) sur les identifiants si la séquence existe
    -- (certaines bases ont la séquence mais pas le DEFAULT sur la colonne)

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'tb_transporteur'
          AND column_name = 'idtransporteur'
          AND column_default IS NULL
    )
    AND to_regclass('public.tb_transporteur_idtransporteur_seq') IS NOT NULL
    THEN
        BEGIN
            ALTER TABLE IF EXISTS public.tb_transporteur
                ALTER COLUMN idtransporteur SET DEFAULT nextval('public.tb_transporteur_idtransporteur_seq'::regclass);
        EXCEPTION WHEN others THEN
            RAISE NOTICE 'Impossible de définir le DEFAULT de tb_transporteur.idtransporteur.';
        END;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'tb_fournisseur'
          AND column_name = 'idfrs'
          AND column_default IS NULL
    )
    AND to_regclass('public.tb_fournisseur_idfrs_seq') IS NOT NULL
    THEN
        BEGIN
            ALTER TABLE IF EXISTS public.tb_fournisseur
                ALTER COLUMN idfrs SET DEFAULT nextval('public.tb_fournisseur_idfrs_seq'::regclass);
        EXCEPTION WHEN others THEN
            RAISE NOTICE 'Impossible de définir le DEFAULT de tb_fournisseur.idfrs.';
        END;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'tb_param_livraison_client_idtransporteur_fkey'
    ) THEN
        -- FK possible uniquement si idtransporteur est UNIQUE/PK
        IF EXISTS (
            SELECT 1
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE n.nspname = 'public'
              AND t.relname = 'tb_transporteur'
              AND c.contype IN ('p','u')
              AND pg_get_constraintdef(c.oid) ILIKE '%(idtransporteur)%'
        ) THEN
            ALTER TABLE IF EXISTS public.tb_param_livraison_client
                ADD CONSTRAINT tb_param_livraison_client_idtransporteur_fkey
                FOREIGN KEY (idtransporteur_defaut)
                REFERENCES public.tb_transporteur(idtransporteur)
                ON UPDATE CASCADE ON DELETE SET NULL;
        ELSE
            RAISE NOTICE 'FK tb_param_livraison_client_idtransporteur_fkey ignorée: tb_transporteur.idtransporteur n''est pas UNIQUE/PK.';
        END IF;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'tb_param_commande_frs_idfrs_defaut_fkey'
    ) THEN
        -- FK possible uniquement si idfrs est UNIQUE/PK
        IF EXISTS (
            SELECT 1
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE n.nspname = 'public'
              AND t.relname = 'tb_fournisseur'
              AND c.contype IN ('p','u')
              AND pg_get_constraintdef(c.oid) ILIKE '%(idfrs)%'
        ) THEN
            ALTER TABLE IF EXISTS public.tb_param_commande_frs
                ADD CONSTRAINT tb_param_commande_frs_idfrs_defaut_fkey
                FOREIGN KEY (idfrs_defaut)
                REFERENCES public.tb_fournisseur(idfrs)
                ON UPDATE CASCADE ON DELETE SET NULL;
        ELSE
            RAISE NOTICE 'FK tb_param_commande_frs_idfrs_defaut_fkey ignorée: tb_fournisseur.idfrs n''est pas UNIQUE/PK.';
        END IF;
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 2) Colonnes manquantes sur tables existantes (dumps anciens -> référence)
-- ---------------------------------------------------------------------------

ALTER TABLE IF EXISTS public.tb_magasin
    ADD COLUMN IF NOT EXISTS livraison_auto_client smallint NOT NULL DEFAULT 0;

ALTER TABLE IF EXISTS public.tb_fournisseur
    ADD COLUMN IF NOT EXISTS nombanque character varying(50);

ALTER TABLE IF EXISTS public.tb_fournisseur
    ADD COLUMN IF NOT EXISTS comptebancaire character varying(50);

ALTER TABLE IF EXISTS public.tb_fournisseur
    ADD COLUMN IF NOT EXISTS adressebanque character varying(75);

ALTER TABLE IF EXISTS public.tb_personnel
    ADD COLUMN IF NOT EXISTS idposte integer;

ALTER TABLE IF EXISTS public.tb_livraisoncli
    ADD COLUMN IF NOT EXISTS idtransporteur integer;

ALTER TABLE IF EXISTS public.tb_livraisoncli
    ADD COLUMN IF NOT EXISTS description_livraison character varying(250);

-- ---------------------------------------------------------------------------
-- 3) Ajustement de type (référence): tb_avancepers.datepmt date -> timestamp
-- ---------------------------------------------------------------------------

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'tb_avancepers'
          AND column_name = 'datepmt'
          AND data_type = 'date'
    ) THEN
        ALTER TABLE IF EXISTS public.tb_avancepers
            ALTER COLUMN datepmt TYPE timestamp without time zone
            USING (datepmt::timestamp without time zone);
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 4) FK personnel -> poste (si non présente)
-- ---------------------------------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tb_personnel_idposte_fkey') THEN
        ALTER TABLE IF EXISTS public.tb_personnel
            ADD CONSTRAINT tb_personnel_idposte_fkey
            FOREIGN KEY (idposte) REFERENCES public.tb_postepersonnel(idposte)
            ON UPDATE CASCADE ON DELETE SET NULL;
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 5) Corrections de noms (typos historiques) — AM0505 -> référence
-- ---------------------------------------------------------------------------

-- AM0505: tb_transfertdetail.qttranfertsortie  -> référence: qttransfertsortie
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'tb_transfertdetail'
          AND column_name = 'qttranfertsortie'
    )
    AND NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'tb_transfertdetail'
          AND column_name = 'qttransfertsortie'
    ) THEN
        ALTER TABLE IF EXISTS public.tb_transfertdetail
            RENAME COLUMN qttranfertsortie TO qttransfertsortie;
    END IF;
END $$;

COMMIT;

