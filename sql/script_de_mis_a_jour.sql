-- =============================================================================
-- Migration : base production (schéma type temp/structure--sg.sql)
--             -> alignement sur Structure database.sql (référence projet)
--
-- Caractères : idempotent (réexécution sans erreur si déjà appliqué).
-- Exécution  : psql -v ON_ERROR_STOP=1 -f sql/migration_prod_sg_align_structure.sql
-- =============================================================================

SET client_min_messages = warning;

BEGIN;

-- ---------------------------------------------------------------------------
-- 1) Tables absentes en prod (CREATE IF NOT EXISTS + séquences + PK)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.event_logs (
    id_log timestamp with time zone DEFAULT clock_timestamp() NOT NULL,
    description text NOT NULL,
    "user" character varying(150),
    datetime timestamp with time zone DEFAULT now() NOT NULL
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'event_logs_pkey'
    ) THEN
        ALTER TABLE ONLY public.event_logs
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
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'tb_log_evenements_pkey'
    ) THEN
        ALTER TABLE ONLY public.tb_log_evenements
            ADD CONSTRAINT tb_log_evenements_pkey PRIMARY KEY (id_log);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_tb_log_evenements_datetime
    ON public.tb_log_evenements USING btree (datetime DESC);

CREATE INDEX IF NOT EXISTS idx_tb_log_evenements_user
    ON public.tb_log_evenements USING btree ("user");


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

ALTER TABLE ONLY public.tb_categoriepersonnel
    ALTER COLUMN idcategorie SET DEFAULT nextval('public.tb_categoriepersonnel_idcategorie_seq'::regclass);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'tb_categoriepersonnel_pkey'
    ) THEN
        ALTER TABLE ONLY public.tb_categoriepersonnel
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

ALTER TABLE ONLY public.tb_postepersonnel
    ALTER COLUMN idposte SET DEFAULT nextval('public.tb_postepersonnel_idposte_seq'::regclass);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'tb_postepersonnel_pkey'
    ) THEN
        ALTER TABLE ONLY public.tb_postepersonnel
            ADD CONSTRAINT tb_postepersonnel_pkey PRIMARY KEY (idposte);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'tb_postepersonnel_idcategorie_fkey'
    ) THEN
        ALTER TABLE ONLY public.tb_postepersonnel
            ADD CONSTRAINT tb_postepersonnel_idcategorie_fkey
            FOREIGN KEY (idcategorie) REFERENCES public.tb_categoriepersonnel(idcategorie)
            ON UPDATE CASCADE ON DELETE SET NULL;
    END IF;
END $$;


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

ALTER TABLE ONLY public.tb_entree
    ALTER COLUMN id SET DEFAULT nextval('public.tb_entree_id_seq'::regclass);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'tb_entree_pkey'
    ) THEN
        ALTER TABLE ONLY public.tb_entree
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

ALTER TABLE ONLY public.tb_entreedetail
    ALTER COLUMN id SET DEFAULT nextval('public.tb_entreedetail_id_seq'::regclass);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'tb_entreedetail_pkey'
    ) THEN
        ALTER TABLE ONLY public.tb_entreedetail
            ADD CONSTRAINT tb_entreedetail_pkey PRIMARY KEY (id);
    END IF;
END $$;


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

ALTER TABLE ONLY public.tb_livraisoncli_attente
    ALTER COLUMN id SET DEFAULT nextval('public.tb_livraisoncli_attente_id_seq'::regclass);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'tb_livraisoncli_attente_pkey'
    ) THEN
        ALTER TABLE ONLY public.tb_livraisoncli_attente
            ADD CONSTRAINT tb_livraisoncli_attente_pkey PRIMARY KEY (id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_livcli_attente_statut
    ON public.tb_livraisoncli_attente USING btree (statut);

CREATE INDEX IF NOT EXISTS idx_livcli_attente_refvente
    ON public.tb_livraisoncli_attente USING btree (refvente);


-- ---------------------------------------------------------------------------
-- 2) Colonnes à ajouter sur tables existantes (prod SG)
-- ---------------------------------------------------------------------------

ALTER TABLE public.tb_magasin
    ADD COLUMN IF NOT EXISTS livraison_auto_client smallint NOT NULL DEFAULT 0;

COMMENT ON COLUMN public.tb_magasin.livraison_auto_client IS
    '1 = BL auto (tb_livraisoncli) à la validation facture pour ce magasin ; 0 = manuel.';

ALTER TABLE public.tb_fournisseur
    ADD COLUMN IF NOT EXISTS nombanque character varying(50);

ALTER TABLE public.tb_fournisseur
    ADD COLUMN IF NOT EXISTS comptebancaire character varying(50);

ALTER TABLE public.tb_fournisseur
    ADD COLUMN IF NOT EXISTS adressebanque character varying(75);

ALTER TABLE public.tb_personnel
    ADD COLUMN IF NOT EXISTS idposte integer;

COMMENT ON COLUMN public.tb_personnel.idposte IS
    'Lien optionnel vers tb_postepersonnel (nullable, affichage).';


-- ---------------------------------------------------------------------------
-- 3) Type tb_avancepers.datepmt : date -> timestamp (référence)
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
        ALTER TABLE public.tb_avancepers
            ALTER COLUMN datepmt TYPE timestamp without time zone
            USING (datepmt::timestamp without time zone);
    END IF;
END $$;


-- ---------------------------------------------------------------------------
-- 4) FK personnel -> poste (après colonne + table poste)
-- ---------------------------------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'tb_personnel_idposte_fkey'
    ) THEN
        ALTER TABLE ONLY public.tb_personnel
            ADD CONSTRAINT tb_personnel_idposte_fkey
            FOREIGN KEY (idposte) REFERENCES public.tb_postepersonnel(idposte)
            ON UPDATE CASCADE ON DELETE SET NULL;
    END IF;
END $$;


-- ---------------------------------------------------------------------------
-- 5) Historique des sauvegardes (page Sauvegarde)
-- ---------------------------------------------------------------------------

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

ALTER TABLE ONLY public.tb_save_history
    ALTER COLUMN id SET DEFAULT nextval('public.tb_save_history_id_seq'::regclass);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'tb_save_history_pkey'
    ) THEN
        ALTER TABLE ONLY public.tb_save_history
            ADD CONSTRAINT tb_save_history_pkey PRIMARY KEY (id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_tb_save_history_datetime
    ON public.tb_save_history USING btree (datetime DESC);

CREATE INDEX IF NOT EXISTS idx_tb_save_history_utilisateur
    ON public.tb_save_history USING btree (utilisateur);

COMMENT ON TABLE public.tb_save_history IS
    'Historique des sauvegardes PostgreSQL effectuées depuis la page Sauvegarde.';

COMMENT ON COLUMN public.tb_save_history.libelle IS
    'Nom du fichier de sauvegarde.';

COMMENT ON COLUMN public.tb_save_history.appareil IS
    'Nom du poste / IP (format host/ip).';

COMMENT ON COLUMN public.tb_save_history.description IS
    'Chemin complet d''enregistrement du fichier.';

COMMENT ON COLUMN public.tb_save_history.taille_mo IS
    'Taille du fichier en mégaoctets.';

COMMENT ON COLUMN public.tb_save_history.utilisateur IS
    'Utilisateur ayant lancé la sauvegarde.';

-- ── Livraisons client : transporteur + description sur BL ───────────────────
ALTER TABLE public.tb_livraisoncli
    ADD COLUMN IF NOT EXISTS idtransporteur integer;

ALTER TABLE public.tb_livraisoncli
    ADD COLUMN IF NOT EXISTS description_livraison character varying(250);

COMMENT ON COLUMN public.tb_livraisoncli.idtransporteur IS
    'Transporteur optionnel (tb_transporteur). Même valeur pour toutes les lignes d''un reflivcli.';

COMMENT ON COLUMN public.tb_livraisoncli.description_livraison IS
    'Note libre BL (n° voiture, tournée, etc.).';

-- ── Paramètres globaux livraison client (Bon de livraison) ─────────────────
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

COMMENT ON TABLE public.tb_param_livraison_client IS
    'Paramètres globaux Bon de livraison (ligne unique id=1).';

COMMENT ON COLUMN public.tb_param_livraison_client.idtransporteur_defaut IS
    'Transporteur pré-sélectionné pour les BL manuels (tb_transporteur).';

COMMENT ON COLUMN public.tb_param_livraison_client.transporteur_bl_auto IS
    '1 = reporter idtransporteur_defaut sur les BL-AUTO ; 0 = BL-AUTO sans transporteur.';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'tb_param_livraison_client_idtransporteur_fkey'
    ) THEN
        ALTER TABLE ONLY public.tb_param_livraison_client
            ADD CONSTRAINT tb_param_livraison_client_idtransporteur_fkey
            FOREIGN KEY (idtransporteur_defaut)
            REFERENCES public.tb_transporteur(idtransporteur)
            ON UPDATE CASCADE ON DELETE SET NULL;
    END IF;
END $$;

-- ── Paramètres Bon de commande fournisseur ─────────────────────────────────
CREATE TABLE IF NOT EXISTS public.tb_param_commande_frs (
    id smallint NOT NULL DEFAULT 1,
    idfrs_defaut integer,
    CONSTRAINT tb_param_commande_frs_pkey PRIMARY KEY (id),
    CONSTRAINT tb_param_commande_frs_singleton CHECK (id = 1)
);

INSERT INTO public.tb_param_commande_frs (id, idfrs_defaut)
VALUES (1, NULL)
ON CONFLICT (id) DO NOTHING;

COMMENT ON TABLE public.tb_param_commande_frs IS
    'Paramètres globaux Bon de commande fournisseur (ligne unique id=1).';

COMMENT ON COLUMN public.tb_param_commande_frs.idfrs_defaut IS
    'Fournisseur pré-affiché à l''ouverture d''un nouveau bon de commande.';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'tb_param_commande_frs_idfrs_defaut_fkey'
    ) THEN
        ALTER TABLE ONLY public.tb_param_commande_frs
            ADD CONSTRAINT tb_param_commande_frs_idfrs_defaut_fkey
            FOREIGN KEY (idfrs_defaut)
            REFERENCES public.tb_fournisseur(idfrs)
            ON UPDATE CASCADE ON DELETE SET NULL;
    END IF;
END $$;

COMMIT;
