-- iJeery — Création des tables Bon d'Entrée (BE)
-- Modèle : tb_sortie / tb_sortiedetail (Structure database.sql)
-- Date : 2026-04-21

-- =========================================================
-- Table: tb_entree
-- =========================================================

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
ALTER TABLE ONLY public.tb_entree ALTER COLUMN id SET DEFAULT nextval('public.tb_entree_id_seq'::regclass);
ALTER TABLE ONLY public.tb_entree ADD CONSTRAINT tb_entree_pkey PRIMARY KEY (id);

-- =========================================================
-- Table: tb_entreedetail
-- =========================================================

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
ALTER TABLE ONLY public.tb_entreedetail ALTER COLUMN id SET DEFAULT nextval('public.tb_entreedetail_id_seq'::regclass);
ALTER TABLE ONLY public.tb_entreedetail ADD CONSTRAINT tb_entreedetail_pkey PRIMARY KEY (id);

-- NOTE:
-- - Aucune contrainte FK n'est ajoutée ici car le modèle tb_sortiedetail
--   dans Structure database.sql n'en définit pas non plus.
-- - Si vous voulez des FK, on peut les ajouter ensuite (tb_magasin, tb_article, tb_unite, tb_entree).

