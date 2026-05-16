-- =============================================================================
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

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 366 (class 1259 OID 246576)
-- Name: event_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.event_logs (
    id_log timestamp with time zone DEFAULT clock_timestamp() NOT NULL,
    description text NOT NULL,
    "user" character varying(150),
    datetime timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.event_logs OWNER TO postgres;

--
-- TOC entry 215 (class 1259 OID 213797)
-- Name: tb_absence; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_absence (
    id integer NOT NULL,
    idpers integer,
    date timestamp without time zone,
    observation character varying(120),
    nbreheureabs double precision
);


ALTER TABLE public.tb_absence OWNER TO postgres;

--
-- TOC entry 216 (class 1259 OID 213800)
-- Name: tb_absence_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_absence_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_absence_id_seq OWNER TO postgres;

--
-- TOC entry 5498 (class 0 OID 0)
-- Dependencies: 216
-- Name: tb_absence_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_absence_id_seq OWNED BY public.tb_absence.id;


--
-- TOC entry 217 (class 1259 OID 213801)
-- Name: tb_article; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_article (
    idarticle integer NOT NULL,
    designation character varying(150),
    idca integer,
    alert integer,
    deleted integer DEFAULT 0,
    idmag integer,
    alertdepot double precision
);


ALTER TABLE public.tb_article OWNER TO postgres;

--
-- TOC entry 218 (class 1259 OID 213805)
-- Name: tb_article_idarticle_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_article_idarticle_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_article_idarticle_seq OWNER TO postgres;

--
-- TOC entry 5499 (class 0 OID 0)
-- Dependencies: 218
-- Name: tb_article_idarticle_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_article_idarticle_seq OWNED BY public.tb_article.idarticle;


--
-- TOC entry 219 (class 1259 OID 213806)
-- Name: tb_autorisation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_autorisation (
    id integer NOT NULL,
    idfonction integer,
    idmenu integer
);


ALTER TABLE public.tb_autorisation OWNER TO postgres;

--
-- TOC entry 220 (class 1259 OID 213809)
-- Name: tb_autorisation_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_autorisation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_autorisation_id_seq OWNER TO postgres;

--
-- TOC entry 5500 (class 0 OID 0)
-- Dependencies: 220
-- Name: tb_autorisation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_autorisation_id_seq OWNED BY public.tb_autorisation.id;


--
-- TOC entry 221 (class 1259 OID 213810)
-- Name: tb_autre_infos; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_autre_infos (
    id integer NOT NULL,
    intitule character varying(250) DEFAULT ''::character varying,
    valeur character varying(1000) DEFAULT ''::character varying
);


ALTER TABLE public.tb_autre_infos OWNER TO postgres;

--
-- TOC entry 222 (class 1259 OID 213817)
-- Name: tb_autre_infos_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_autre_infos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_autre_infos_id_seq OWNER TO postgres;

--
-- TOC entry 5501 (class 0 OID 0)
-- Dependencies: 222
-- Name: tb_autre_infos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_autre_infos_id_seq OWNED BY public.tb_autre_infos.id;


--
-- TOC entry 223 (class 1259 OID 213818)
-- Name: tb_autrecreance; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_autrecreance (
    id integer NOT NULL,
    idclient integer,
    dateregistre timestamp without time zone,
    numfact character varying(50),
    montant double precision,
    dateecheance date
);


ALTER TABLE public.tb_autrecreance OWNER TO postgres;

--
-- TOC entry 224 (class 1259 OID 213821)
-- Name: tb_autrecreance_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_autrecreance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_autrecreance_id_seq OWNER TO postgres;

--
-- TOC entry 5502 (class 0 OID 0)
-- Dependencies: 224
-- Name: tb_autrecreance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_autrecreance_id_seq OWNED BY public.tb_autrecreance.id;


--
-- TOC entry 225 (class 1259 OID 213822)
-- Name: tb_autredette; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_autredette (
    id integer NOT NULL,
    idfrs integer,
    dateregistre timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    numfact character varying(50),
    montant double precision,
    dateecheance date
);


ALTER TABLE public.tb_autredette OWNER TO postgres;

--
-- TOC entry 226 (class 1259 OID 213826)
-- Name: tb_autredette_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_autredette_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_autredette_id_seq OWNER TO postgres;

--
-- TOC entry 5503 (class 0 OID 0)
-- Dependencies: 226
-- Name: tb_autredette_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_autredette_id_seq OWNED BY public.tb_autredette.id;


--
-- TOC entry 227 (class 1259 OID 213827)
-- Name: tb_avancepers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_avancepers (
    id integer NOT NULL,
    datepmt timestamp without time zone,
    refpmt character varying(50),
    mtpaye double precision,
    idtypeoperation integer,
    idpers integer,
    observation character varying(100),
    id_banque integer,
    iduser integer,
    idmode integer
);


ALTER TABLE public.tb_avancepers OWNER TO postgres;

--
-- TOC entry 228 (class 1259 OID 213830)
-- Name: tb_avancepers_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_avancepers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_avancepers_id_seq OWNER TO postgres;

--
-- TOC entry 5504 (class 0 OID 0)
-- Dependencies: 228
-- Name: tb_avancepers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_avancepers_id_seq OWNED BY public.tb_avancepers.id;


--
-- TOC entry 229 (class 1259 OID 213831)
-- Name: tb_avanceprof; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_avanceprof (
    id integer NOT NULL,
    refpmt character varying(50),
    idpers integer,
    mtpaye double precision,
    observation character varying(120),
    datepmt timestamp without time zone,
    etat integer,
    idtypeoperation integer,
    iduser integer
);


ALTER TABLE public.tb_avanceprof OWNER TO postgres;

--
-- TOC entry 230 (class 1259 OID 213834)
-- Name: tb_avanceprof_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_avanceprof_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_avanceprof_id_seq OWNER TO postgres;

--
-- TOC entry 5505 (class 0 OID 0)
-- Dependencies: 230
-- Name: tb_avanceprof_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_avanceprof_id_seq OWNED BY public.tb_avanceprof.id;


--
-- TOC entry 231 (class 1259 OID 213835)
-- Name: tb_avancespecpers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_avancespecpers (
    id integer NOT NULL,
    idpers integer,
    refpmt character varying(50),
    mtpaye double precision,
    idtypeoperation integer,
    nbremboursement double precision,
    observation character varying(120),
    datepmt timestamp without time zone,
    id_banque integer,
    idmode integer,
    iduser integer
);


ALTER TABLE public.tb_avancespecpers OWNER TO postgres;

--
-- TOC entry 232 (class 1259 OID 213838)
-- Name: tb_avancespecpers_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_avancespecpers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_avancespecpers_id_seq OWNER TO postgres;

--
-- TOC entry 5506 (class 0 OID 0)
-- Dependencies: 232
-- Name: tb_avancespecpers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_avancespecpers_id_seq OWNED BY public.tb_avancespecpers.id;


--
-- TOC entry 233 (class 1259 OID 213839)
-- Name: tb_avoir; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_avoir (
    id integer NOT NULL,
    refavoir character varying(50),
    idclient integer,
    iduser integer,
    mtavoir double precision,
    idmode integer,
    observation character varying(150),
    dateregistre timestamp without time zone,
    deleted integer DEFAULT 0,
    dateavoir timestamp without time zone
);


ALTER TABLE public.tb_avoir OWNER TO postgres;

--
-- TOC entry 234 (class 1259 OID 213843)
-- Name: tb_avoir_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_avoir_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_avoir_id_seq OWNER TO postgres;

--
-- TOC entry 5507 (class 0 OID 0)
-- Dependencies: 234
-- Name: tb_avoir_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_avoir_id_seq OWNED BY public.tb_avoir.id;


--
-- TOC entry 235 (class 1259 OID 213844)
-- Name: tb_avoirdetail; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_avoirdetail (
    id integer NOT NULL,
    idmag integer,
    idarticle integer,
    idunite integer,
    qtavoir double precision,
    prixunit double precision,
    deleted integer DEFAULT 0,
    idavoir integer
);


ALTER TABLE public.tb_avoirdetail OWNER TO postgres;

--
-- TOC entry 236 (class 1259 OID 213848)
-- Name: tb_avoirdetail_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_avoirdetail_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_avoirdetail_id_seq OWNER TO postgres;

--
-- TOC entry 5508 (class 0 OID 0)
-- Dependencies: 236
-- Name: tb_avoirdetail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_avoirdetail_id_seq OWNED BY public.tb_avoirdetail.id;


--
-- TOC entry 237 (class 1259 OID 213849)
-- Name: tb_banque; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_banque (
    id_banque integer NOT NULL,
    nombanque character varying(75),
    adresse character varying(120),
    numcompte integer,
    iduser integer
);


ALTER TABLE public.tb_banque OWNER TO postgres;

--
-- TOC entry 238 (class 1259 OID 213852)
-- Name: tb_banque_id_banque_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_banque_id_banque_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_banque_id_banque_seq OWNER TO postgres;

--
-- TOC entry 5509 (class 0 OID 0)
-- Dependencies: 238
-- Name: tb_banque_id_banque_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_banque_id_banque_seq OWNED BY public.tb_banque.id_banque;


--
-- TOC entry 239 (class 1259 OID 213853)
-- Name: tb_baseliste; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_baseliste (
    id integer NOT NULL,
    nombase character varying(75),
    designationbase character varying(75),
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_baseliste OWNER TO postgres;

--
-- TOC entry 240 (class 1259 OID 213857)
-- Name: tb_baseliste_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_baseliste_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_baseliste_id_seq OWNER TO postgres;

--
-- TOC entry 5510 (class 0 OID 0)
-- Dependencies: 240
-- Name: tb_baseliste_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_baseliste_id_seq OWNED BY public.tb_baseliste.id;


--
-- TOC entry 241 (class 1259 OID 213858)
-- Name: tb_categoriearticle; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_categoriearticle (
    idca integer NOT NULL,
    designationcat character varying(150),
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_categoriearticle OWNER TO postgres;

--
-- TOC entry 242 (class 1259 OID 213862)
-- Name: tb_categoriearticle_idca_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_categoriearticle_idca_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_categoriearticle_idca_seq OWNER TO postgres;

--
-- TOC entry 5511 (class 0 OID 0)
-- Dependencies: 242
-- Name: tb_categoriearticle_idca_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_categoriearticle_idca_seq OWNED BY public.tb_categoriearticle.idca;


--
-- TOC entry 243 (class 1259 OID 213863)
-- Name: tb_categoriecompte; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_categoriecompte (
    idcc integer NOT NULL,
    categoriecompte character varying(100)
);


ALTER TABLE public.tb_categoriecompte OWNER TO postgres;

--
-- TOC entry 244 (class 1259 OID 213866)
-- Name: tb_categoriecompte_idcc_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_categoriecompte_idcc_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_categoriecompte_idcc_seq OWNER TO postgres;

--
-- TOC entry 5512 (class 0 OID 0)
-- Dependencies: 244
-- Name: tb_categoriecompte_idcc_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_categoriecompte_idcc_seq OWNED BY public.tb_categoriecompte.idcc;


--
-- TOC entry 245 (class 1259 OID 213867)
-- Name: tb_categoriepersonnel; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_categoriepersonnel (
    idcategorie integer NOT NULL,
    titre character varying(120) NOT NULL,
    description text,
    dateregistre timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_categoriepersonnel OWNER TO postgres;

--
-- TOC entry 246 (class 1259 OID 213868)
-- Name: tb_categoriepersonnel_idcategorie_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_categoriepersonnel_idcategorie_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_categoriepersonnel_idcategorie_seq OWNER TO postgres;

--
-- TOC entry 5512b (class 0 OID 0)
-- Dependencies: 246
-- Name: tb_categoriepersonnel_idcategorie_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_categoriepersonnel_idcategorie_seq OWNED BY public.tb_categoriepersonnel.idcategorie;


--
-- TOC entry 247 (class 1259 OID 213869)
-- Name: tb_postepersonnel; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_postepersonnel (
    idposte integer NOT NULL,
    idcategorie integer,
    titre character varying(120) NOT NULL,
    description text,
    dateregistre timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_postepersonnel OWNER TO postgres;

--
-- TOC entry 248 (class 1259 OID 213870)
-- Name: tb_postepersonnel_idposte_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_postepersonnel_idposte_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_postepersonnel_idposte_seq OWNER TO postgres;

--
-- TOC entry 5512c (class 0 OID 0)
-- Dependencies: 248
-- Name: tb_postepersonnel_idposte_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_postepersonnel_idposte_seq OWNED BY public.tb_postepersonnel.idposte;


--
-- TOC entry 245 (class 1259 OID 213867)
-- Name: tb_changement; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_changement (
    idchg integer NOT NULL,
    refchg character varying(20) NOT NULL,
    datechg timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    iduser integer NOT NULL,
    note text
);


ALTER TABLE public.tb_changement OWNER TO postgres;

--
-- TOC entry 246 (class 1259 OID 213873)
-- Name: tb_changement_idchg_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_changement_idchg_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_changement_idchg_seq OWNER TO postgres;

--
-- TOC entry 5513 (class 0 OID 0)
-- Dependencies: 246
-- Name: tb_changement_idchg_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_changement_idchg_seq OWNED BY public.tb_changement.idchg;


--
-- TOC entry 247 (class 1259 OID 213874)
-- Name: tb_chat; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_chat (
    id integer NOT NULL,
    id_expediteur integer NOT NULL,
    id_destinataire integer NOT NULL,
    message text NOT NULL,
    date_envoi timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    lu integer DEFAULT 0
);


ALTER TABLE public.tb_chat OWNER TO postgres;

--
-- TOC entry 248 (class 1259 OID 213881)
-- Name: tb_chat_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_chat_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_chat_id_seq OWNER TO postgres;

--
-- TOC entry 5514 (class 0 OID 0)
-- Dependencies: 248
-- Name: tb_chat_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_chat_id_seq OWNED BY public.tb_chat.id;


--
-- TOC entry 249 (class 1259 OID 213882)
-- Name: tb_client; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_client (
    idclient integer NOT NULL,
    nomcli character varying(100),
    contactcli character varying(50),
    adressecli character varying(150),
    nifcli character varying(20),
    statcli character varying(20),
    cifcli character varying(20),
    credit double precision,
    idtypeclient integer,
    dateregistre timestamp without time zone,
    blocked integer,
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_client OWNER TO postgres;

--
-- TOC entry 250 (class 1259 OID 213886)
-- Name: tb_client_idclient_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_client_idclient_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_client_idclient_seq OWNER TO postgres;

--
-- TOC entry 5515 (class 0 OID 0)
-- Dependencies: 250
-- Name: tb_client_idclient_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_client_idclient_seq OWNED BY public.tb_client.idclient;


--
-- TOC entry 251 (class 1259 OID 213887)
-- Name: tb_codeautorisation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_codeautorisation (
    id integer NOT NULL,
    code character varying(10),
    iduser integer,
    deleted integer DEFAULT 0,
    username character varying(50)
);


ALTER TABLE public.tb_codeautorisation OWNER TO postgres;

--
-- TOC entry 252 (class 1259 OID 213891)
-- Name: tb_codeautorisation_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_codeautorisation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_codeautorisation_id_seq OWNER TO postgres;

--
-- TOC entry 5516 (class 0 OID 0)
-- Dependencies: 252
-- Name: tb_codeautorisation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_codeautorisation_id_seq OWNED BY public.tb_codeautorisation.id;


--
-- TOC entry 253 (class 1259 OID 213892)
-- Name: tb_commande; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_commande (
    idcom integer NOT NULL,
    refcom character varying(50),
    datecom timestamp without time zone,
    iduser integer,
    idfrs integer,
    descriptioncom character varying(150),
    deleted integer DEFAULT 0,
    datemodif timestamp without time zone,
    totcmd double precision,
    idtransportuer integer
);


ALTER TABLE public.tb_commande OWNER TO postgres;

--
-- TOC entry 254 (class 1259 OID 213896)
-- Name: tb_commande_idcom_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_commande_idcom_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_commande_idcom_seq OWNER TO postgres;

--
-- TOC entry 5517 (class 0 OID 0)
-- Dependencies: 254
-- Name: tb_commande_idcom_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_commande_idcom_seq OWNED BY public.tb_commande.idcom;


--
-- TOC entry 255 (class 1259 OID 213897)
-- Name: tb_commandedetail; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_commandedetail (
    id integer NOT NULL,
    idcom integer,
    idarticle integer,
    idunite integer,
    qtcmd double precision,
    qtlivre double precision,
    punitcmd double precision,
    typemouvement integer,
    total double precision,
    dateperemption date,
    idfrs integer,
    montant_charge double precision DEFAULT 0
);


ALTER TABLE public.tb_commandedetail OWNER TO postgres;

--
-- TOC entry 256 (class 1259 OID 213901)
-- Name: tb_commandedetail_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_commandedetail_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_commandedetail_id_seq OWNER TO postgres;

--
-- TOC entry 5518 (class 0 OID 0)
-- Dependencies: 256
-- Name: tb_commandedetail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_commandedetail_id_seq OWNED BY public.tb_commandedetail.id;


--
-- TOC entry 257 (class 1259 OID 213902)
-- Name: tb_configdb; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_configdb (
    id integer NOT NULL,
    dbname character varying(50),
    username character varying(50),
    password character varying(100),
    host character varying(100),
    port integer
);


ALTER TABLE public.tb_configdb OWNER TO postgres;

--
-- TOC entry 258 (class 1259 OID 213905)
-- Name: tb_configdb_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_configdb_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_configdb_id_seq OWNER TO postgres;

--
-- TOC entry 5519 (class 0 OID 0)
-- Dependencies: 258
-- Name: tb_configdb_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_configdb_id_seq OWNED BY public.tb_configdb.id;


--
-- TOC entry 259 (class 1259 OID 213906)
-- Name: tb_consommationinterne; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_consommationinterne (
    id integer NOT NULL,
    refconsommation character varying(50) NOT NULL,
    dateregistre timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    observation text,
    iduser integer NOT NULL,
    valeur_totale numeric(15,2) DEFAULT 0
);


ALTER TABLE public.tb_consommationinterne OWNER TO postgres;

--
-- TOC entry 260 (class 1259 OID 213913)
-- Name: tb_consommationinterne_details; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_consommationinterne_details (
    id integer NOT NULL,
    idconsommation integer NOT NULL,
    idarticle integer NOT NULL,
    idunite integer NOT NULL,
    idmag integer NOT NULL,
    qtconsomme numeric(10,2) NOT NULL,
    prixunit numeric(12,2) NOT NULL,
    montant_total numeric(15,2) GENERATED ALWAYS AS ((qtconsomme * prixunit)) STORED,
    observation text
);


ALTER TABLE public.tb_consommationinterne_details OWNER TO postgres;

--
-- TOC entry 261 (class 1259 OID 213919)
-- Name: tb_consommationinterne_details_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_consommationinterne_details_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_consommationinterne_details_id_seq OWNER TO postgres;

--
-- TOC entry 5520 (class 0 OID 0)
-- Dependencies: 261
-- Name: tb_consommationinterne_details_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_consommationinterne_details_id_seq OWNED BY public.tb_consommationinterne_details.id;


--
-- TOC entry 262 (class 1259 OID 213920)
-- Name: tb_consommationinterne_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_consommationinterne_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_consommationinterne_id_seq OWNER TO postgres;

--
-- TOC entry 5521 (class 0 OID 0)
-- Dependencies: 262
-- Name: tb_consommationinterne_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_consommationinterne_id_seq OWNED BY public.tb_consommationinterne.id;


--
-- TOC entry 263 (class 1259 OID 213921)
-- Name: tb_decaissement; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_decaissement (
    id integer NOT NULL,
    refpmt character varying(50),
    idcc integer,
    mtpaye double precision,
    observation character varying(150),
    idtypeoperation integer DEFAULT 2,
    datepmt timestamp without time zone,
    idpaiment integer,
    id_banque integer,
    iduser integer,
    idmode integer
);


ALTER TABLE public.tb_decaissement OWNER TO postgres;

--
-- TOC entry 264 (class 1259 OID 213925)
-- Name: tb_decaissement_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_decaissement_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_decaissement_id_seq OWNER TO postgres;

--
-- TOC entry 5522 (class 0 OID 0)
-- Dependencies: 264
-- Name: tb_decaissement_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_decaissement_id_seq OWNED BY public.tb_decaissement.id;


--
-- TOC entry 265 (class 1259 OID 213926)
-- Name: tb_decaissementbq; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_decaissementbq (
    id integer NOT NULL,
    refpmt character varying(50),
    idcc integer,
    mtpaye double precision,
    observation character varying(150),
    idtypeoperation integer DEFAULT 2,
    datepmt timestamp without time zone,
    idpaiment integer,
    id_banque integer,
    iduser integer,
    idmode integer
);


ALTER TABLE public.tb_decaissementbq OWNER TO postgres;

--
-- TOC entry 266 (class 1259 OID 213930)
-- Name: tb_decaissementbq_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_decaissementbq_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_decaissementbq_id_seq OWNER TO postgres;

--
-- TOC entry 5523 (class 0 OID 0)
-- Dependencies: 266
-- Name: tb_decaissementbq_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_decaissementbq_id_seq OWNED BY public.tb_decaissementbq.id;


--
-- TOC entry 267 (class 1259 OID 213931)
-- Name: tb_detailchange_entree; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_detailchange_entree (
    iddetail integer NOT NULL,
    idchg integer NOT NULL,
    idarticle integer NOT NULL,
    idunite integer NOT NULL,
    idmagasin integer NOT NULL,
    quantite_entree numeric(10,2) NOT NULL
);


ALTER TABLE public.tb_detailchange_entree OWNER TO postgres;

--
-- TOC entry 268 (class 1259 OID 213934)
-- Name: tb_detailchange_entree_iddetail_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_detailchange_entree_iddetail_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_detailchange_entree_iddetail_seq OWNER TO postgres;

--
-- TOC entry 5524 (class 0 OID 0)
-- Dependencies: 268
-- Name: tb_detailchange_entree_iddetail_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_detailchange_entree_iddetail_seq OWNED BY public.tb_detailchange_entree.iddetail;


--
-- TOC entry 269 (class 1259 OID 213935)
-- Name: tb_detailchange_sortie; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_detailchange_sortie (
    iddetail integer NOT NULL,
    idchg integer NOT NULL,
    idarticle integer NOT NULL,
    idunite integer NOT NULL,
    idmagasin integer NOT NULL,
    quantite_sortie numeric(10,2) NOT NULL
);


ALTER TABLE public.tb_detailchange_sortie OWNER TO postgres;

--
-- TOC entry 270 (class 1259 OID 213938)
-- Name: tb_detailchange_sortie_iddetail_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_detailchange_sortie_iddetail_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_detailchange_sortie_iddetail_seq OWNER TO postgres;

--
-- TOC entry 5525 (class 0 OID 0)
-- Dependencies: 270
-- Name: tb_detailchange_sortie_iddetail_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_detailchange_sortie_iddetail_seq OWNED BY public.tb_detailchange_sortie.iddetail;


--
-- TOC entry 271 (class 1259 OID 213939)
-- Name: tb_encaissement; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_encaissement (
    id integer NOT NULL,
    refpmt character varying(50),
    idcc integer,
    mtpaye double precision,
    observation character varying(150),
    idtypeoperation integer DEFAULT 1,
    datepmt timestamp without time zone,
    idpaiment integer,
    id_banque integer,
    iduser integer,
    idmode integer
);


ALTER TABLE public.tb_encaissement OWNER TO postgres;

--
-- TOC entry 272 (class 1259 OID 213943)
-- Name: tb_encaissement_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_encaissement_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_encaissement_id_seq OWNER TO postgres;

--
-- TOC entry 5526 (class 0 OID 0)
-- Dependencies: 272
-- Name: tb_encaissement_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_encaissement_id_seq OWNED BY public.tb_encaissement.id;


--
-- TOC entry 273 (class 1259 OID 213944)
-- Name: tb_encaissementbq; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_encaissementbq (
    id integer NOT NULL,
    refpmt character varying(50),
    idcc integer,
    mtpaye double precision,
    observation character varying(150),
    idtypeoperation integer DEFAULT 1,
    datepmt timestamp without time zone,
    idpaiment integer,
    id_banque integer,
    iduser integer,
    idmode integer
);


ALTER TABLE public.tb_encaissementbq OWNER TO postgres;

--
-- TOC entry 274 (class 1259 OID 213948)
-- Name: tb_encaissementbq_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_encaissementbq_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_encaissementbq_id_seq OWNER TO postgres;

--
-- TOC entry 5527 (class 0 OID 0)
-- Dependencies: 274
-- Name: tb_encaissementbq_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_encaissementbq_id_seq OWNED BY public.tb_encaissementbq.id;


--
-- TOC entry 367 (class 1259 OID 262951)
-- Name: tb_entree; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_entree (
    id integer NOT NULL,
    refentree character varying(50),
    iduser integer,
    dateregistre timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    description character varying(150),
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_entree OWNER TO postgres;

--
-- TOC entry 368 (class 1259 OID 262956)
-- Name: tb_entree_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_entree_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_entree_id_seq OWNER TO postgres;

--
-- TOC entry 5528 (class 0 OID 0)
-- Dependencies: 368
-- Name: tb_entree_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_entree_id_seq OWNED BY public.tb_entree.id;


--
-- TOC entry 369 (class 1259 OID 262960)
-- Name: tb_entreedetail; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_entreedetail (
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


ALTER TABLE public.tb_entreedetail OWNER TO postgres;

--
-- TOC entry 370 (class 1259 OID 262965)
-- Name: tb_entreedetail_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_entreedetail_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_entreedetail_id_seq OWNER TO postgres;

--
-- TOC entry 5529 (class 0 OID 0)
-- Dependencies: 370
-- Name: tb_entreedetail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_entreedetail_id_seq OWNED BY public.tb_entreedetail.id;


--
-- TOC entry 275 (class 1259 OID 213949)
-- Name: tb_evenement; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_evenement (
    id integer NOT NULL,
    date timestamp without time zone,
    evenements character varying(200)
);


ALTER TABLE public.tb_evenement OWNER TO postgres;

--
-- TOC entry 276 (class 1259 OID 213952)
-- Name: tb_evenement_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_evenement_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_evenement_id_seq OWNER TO postgres;

--
-- TOC entry 5530 (class 0 OID 0)
-- Dependencies: 276
-- Name: tb_evenement_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_evenement_id_seq OWNED BY public.tb_evenement.id;


--
-- TOC entry 277 (class 1259 OID 213953)
-- Name: tb_facturecli; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_facturecli (
    idfact integer NOT NULL,
    reffact character varying(50),
    refvente character varying(50),
    idmod integer,
    idclient integer,
    iduser integer,
    mtpaye double precision,
    dateregistre timestamp without time zone
);


ALTER TABLE public.tb_facturecli OWNER TO postgres;

--
-- TOC entry 278 (class 1259 OID 213956)
-- Name: tb_facturecli_idfact_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_facturecli_idfact_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_facturecli_idfact_seq OWNER TO postgres;

--
-- TOC entry 5531 (class 0 OID 0)
-- Dependencies: 278
-- Name: tb_facturecli_idfact_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_facturecli_idfact_seq OWNED BY public.tb_facturecli.idfact;


--
-- TOC entry 279 (class 1259 OID 213957)
-- Name: tb_fonction; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_fonction (
    idfonction integer NOT NULL,
    designationfonction character varying(50),
    dateregistre timestamp without time zone,
    idautorisation integer,
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_fonction OWNER TO postgres;

--
-- TOC entry 280 (class 1259 OID 213961)
-- Name: tb_fonction_idfonction_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_fonction_idfonction_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_fonction_idfonction_seq OWNER TO postgres;

--
-- TOC entry 5532 (class 0 OID 0)
-- Dependencies: 280
-- Name: tb_fonction_idfonction_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_fonction_idfonction_seq OWNED BY public.tb_fonction.idfonction;


--
-- TOC entry 281 (class 1259 OID 213962)
-- Name: tb_fournisseur; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_fournisseur (
    idfrs integer NOT NULL,
    nomfrs character varying(150),
    contactfrs character varying(50),
    adressefrs character varying(150),
    niffrs character varying(20),
    statfrs character varying(20),
    ciffrs character varying(20),
    dateregistre timestamp without time zone,
    deleted integer DEFAULT 0,
    nombanque character varying(50),
    comptebancaire character varying(50),
    adressebanque character varying(75)
);


ALTER TABLE public.tb_fournisseur OWNER TO postgres;

--
-- TOC entry 282 (class 1259 OID 213966)
-- Name: tb_fournisseur_idfrs_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_fournisseur_idfrs_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_fournisseur_idfrs_seq OWNER TO postgres;

--
-- TOC entry 5533 (class 0 OID 0)
-- Dependencies: 282
-- Name: tb_fournisseur_idfrs_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_fournisseur_idfrs_seq OWNED BY public.tb_fournisseur.idfrs;


--
-- TOC entry 283 (class 1259 OID 213967)
-- Name: tb_infosociete; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_infosociete (
    id integer NOT NULL,
    nomsociete character varying(100),
    adressesociete character varying(150),
    contactsociete character varying(50),
    villesociete character varying(100),
    nifsociete character varying(50),
    statsociete character varying(50),
    cifsociete character varying(50),
    ambleme character varying(200),
    autre character varying(100)
);


ALTER TABLE public.tb_infosociete OWNER TO postgres;

--
-- TOC entry 284 (class 1259 OID 213972)
-- Name: tb_infosociete_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_infosociete_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_infosociete_id_seq OWNER TO postgres;

--
-- TOC entry 5534 (class 0 OID 0)
-- Dependencies: 284
-- Name: tb_infosociete_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_infosociete_id_seq OWNED BY public.tb_infosociete.id;


--
-- TOC entry 285 (class 1259 OID 213973)
-- Name: tb_inventaire; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_inventaire (
    id integer NOT NULL,
    qtinventaire double precision,
    observation character varying(100),
    date timestamp without time zone,
    iduser integer,
    idmag integer,
    codearticle character varying(50)
);


ALTER TABLE public.tb_inventaire OWNER TO postgres;

--
-- TOC entry 286 (class 1259 OID 213976)
-- Name: tb_inventaire_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_inventaire_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_inventaire_id_seq OWNER TO postgres;

--
-- TOC entry 5535 (class 0 OID 0)
-- Dependencies: 286
-- Name: tb_inventaire_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_inventaire_id_seq OWNED BY public.tb_inventaire.id;


--
-- TOC entry 287 (class 1259 OID 213977)
-- Name: tb_inventaire_temporaire; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_inventaire_temporaire (
    id integer NOT NULL,
    date_creation timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    date_mise_ajour timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    idarticle integer NOT NULL,
    idunite integer NOT NULL,
    idmagasin integer NOT NULL,
    qte_corrige numeric(12,3) NOT NULL,
    iduser integer NOT NULL,
    iduserverificateur integer,
    statut character varying(20) DEFAULT 'Non vérifié'::character varying,
    deleted integer DEFAULT 0,
    observation character varying(255),
    qt_stock double precision
);


ALTER TABLE public.tb_inventaire_temporaire OWNER TO postgres;

--
-- TOC entry 288 (class 1259 OID 213984)
-- Name: tb_inventaire_temporaire_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_inventaire_temporaire_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_inventaire_temporaire_id_seq OWNER TO postgres;

--
-- TOC entry 5536 (class 0 OID 0)
-- Dependencies: 288
-- Name: tb_inventaire_temporaire_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_inventaire_temporaire_id_seq OWNED BY public.tb_inventaire_temporaire.id;


--
-- TOC entry 289 (class 1259 OID 213985)
-- Name: tb_livraisoncli; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_livraisoncli (
    idlivcli integer NOT NULL,
    reflivcli character varying(50),
    refvente character varying(50),
    idmag integer,
    idarticle integer,
    idunite integer,
    qtlivrecli double precision,
    dateregistre timestamp without time zone,
    iduser integer,
    qtvente double precision,
    idclient integer
);


ALTER TABLE public.tb_livraisoncli OWNER TO postgres;

--
-- TOC entry 364 (class 1259 OID 238374)
-- Name: tb_livraisoncli_attente; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_livraisoncli_attente (
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


ALTER TABLE public.tb_livraisoncli_attente OWNER TO postgres;

--
-- TOC entry 363 (class 1259 OID 238373)
-- Name: tb_livraisoncli_attente_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_livraisoncli_attente_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_livraisoncli_attente_id_seq OWNER TO postgres;

--
-- TOC entry 5537 (class 0 OID 0)
-- Dependencies: 363
-- Name: tb_livraisoncli_attente_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_livraisoncli_attente_id_seq OWNED BY public.tb_livraisoncli_attente.id;


--
-- TOC entry 290 (class 1259 OID 213988)
-- Name: tb_livraisoncli_idlivcli_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_livraisoncli_idlivcli_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_livraisoncli_idlivcli_seq OWNER TO postgres;

--
-- TOC entry 5538 (class 0 OID 0)
-- Dependencies: 290
-- Name: tb_livraisoncli_idlivcli_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_livraisoncli_idlivcli_seq OWNED BY public.tb_livraisoncli.idlivcli;


--
-- TOC entry 291 (class 1259 OID 213989)
-- Name: tb_livraisonfrs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_livraisonfrs (
    idlivfrs integer NOT NULL,
    reflivfrs character varying(50),
    idcom integer,
    idarticle integer,
    idunite integer,
    qtlivrefrs double precision,
    dateregistre timestamp without time zone,
    typemouvement integer,
    idmag integer,
    iduser integer,
    factfrs character varying(50),
    datepaiement date,
    dateperemption date,
    deleted integer DEFAULT 0,
    a_payer integer DEFAULT 0
);


ALTER TABLE public.tb_livraisonfrs OWNER TO postgres;

--
-- TOC entry 292 (class 1259 OID 213994)
-- Name: tb_livraisonfrs_idlivfrs_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_livraisonfrs_idlivfrs_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_livraisonfrs_idlivfrs_seq OWNER TO postgres;

--
-- TOC entry 5539 (class 0 OID 0)
-- Dependencies: 292
-- Name: tb_livraisonfrs_idlivfrs_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_livraisonfrs_idlivfrs_seq OWNED BY public.tb_livraisonfrs.idlivfrs;


--
-- TOC entry 365 (class 1259 OID 246564)
-- Name: tb_log_evenements; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_log_evenements (
    id_log timestamp with time zone DEFAULT clock_timestamp() NOT NULL,
    description text NOT NULL,
    "user" character varying(150),
    datetime timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.tb_log_evenements OWNER TO postgres;

--
-- TOC entry 293 (class 1259 OID 213995)
-- Name: tb_log_stock; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_log_stock (
    id integer NOT NULL,
    idmag integer,
    ancien_stock double precision,
    nouveau_stock double precision,
    date_action timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    iduser integer,
    type_action character varying(50) DEFAULT 'INVENTAIRE'::character varying,
    codearticle character varying(50)
);


ALTER TABLE public.tb_log_stock OWNER TO postgres;

--
-- TOC entry 294 (class 1259 OID 214000)
-- Name: tb_log_stock_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_log_stock_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_log_stock_id_seq OWNER TO postgres;

--
-- TOC entry 5540 (class 0 OID 0)
-- Dependencies: 294
-- Name: tb_log_stock_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_log_stock_id_seq OWNED BY public.tb_log_stock.id;


--
-- TOC entry 295 (class 1259 OID 214001)
-- Name: tb_lot_peremption; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_lot_peremption (
    id integer NOT NULL,
    id_article integer,
    id_unite integer,
    quantite numeric,
    date_peremption date,
    priorite integer,
    date_entree date,
    type_source character varying(20),
    id_source integer,
    id_split integer,
    date_creation timestamp without time zone DEFAULT now(),
    note text,
    deleted integer DEFAULT 0,
    idmag integer
);


ALTER TABLE public.tb_lot_peremption OWNER TO postgres;

--
-- TOC entry 296 (class 1259 OID 214008)
-- Name: tb_lot_peremption_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_lot_peremption_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_lot_peremption_id_seq OWNER TO postgres;

--
-- TOC entry 5541 (class 0 OID 0)
-- Dependencies: 296
-- Name: tb_lot_peremption_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_lot_peremption_id_seq OWNED BY public.tb_lot_peremption.id;


--
-- TOC entry 297 (class 1259 OID 214009)
-- Name: tb_magasin; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_magasin (
    idmag integer NOT NULL,
    designationmag character varying(50),
    adressemag character varying(50),
    livraison integer,
    livraison_auto_client smallint DEFAULT 0 NOT NULL,
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_magasin OWNER TO postgres;

--
-- TOC entry 298 (class 1259 OID 214013)
-- Name: tb_magasin_idmag_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_magasin_idmag_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_magasin_idmag_seq OWNER TO postgres;

--
-- TOC entry 5542 (class 0 OID 0)
-- Dependencies: 298
-- Name: tb_magasin_idmag_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_magasin_idmag_seq OWNED BY public.tb_magasin.idmag;


--
-- TOC entry 299 (class 1259 OID 214014)
-- Name: tb_menu; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_menu (
    id integer NOT NULL,
    designationmenu character varying(100),
    page character varying(50)
);


ALTER TABLE public.tb_menu OWNER TO postgres;

--
-- TOC entry 300 (class 1259 OID 214017)
-- Name: tb_menu_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_menu_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_menu_id_seq OWNER TO postgres;

--
-- TOC entry 5543 (class 0 OID 0)
-- Dependencies: 300
-- Name: tb_menu_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_menu_id_seq OWNED BY public.tb_menu.id;


--
-- TOC entry 301 (class 1259 OID 214018)
-- Name: tb_modepaiement; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_modepaiement (
    idmode integer NOT NULL,
    modedepaiement character varying(50)
);


ALTER TABLE public.tb_modepaiement OWNER TO postgres;

--
-- TOC entry 302 (class 1259 OID 214021)
-- Name: tb_modepaiement_idmode_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_modepaiement_idmode_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_modepaiement_idmode_seq OWNER TO postgres;

--
-- TOC entry 5544 (class 0 OID 0)
-- Dependencies: 302
-- Name: tb_modepaiement_idmode_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_modepaiement_idmode_seq OWNED BY public.tb_modepaiement.idmode;


--
-- TOC entry 303 (class 1259 OID 214022)
-- Name: tb_paiement; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_paiement (
    idpaiement integer NOT NULL,
    paiement character varying(25)
);


ALTER TABLE public.tb_paiement OWNER TO postgres;

--
-- TOC entry 304 (class 1259 OID 214025)
-- Name: tb_paiement_idpaiement_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_paiement_idpaiement_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_paiement_idpaiement_seq OWNER TO postgres;

--
-- TOC entry 5545 (class 0 OID 0)
-- Dependencies: 304
-- Name: tb_paiement_idpaiement_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_paiement_idpaiement_seq OWNED BY public.tb_paiement.idpaiement;


--
-- TOC entry 305 (class 1259 OID 214026)
-- Name: tb_peremption; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_peremption (
    id integer NOT NULL,
    idcom integer,
    idarticle integer,
    idmag integer,
    dateper timestamp without time zone,
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_peremption OWNER TO postgres;

--
-- TOC entry 306 (class 1259 OID 214030)
-- Name: tb_peremption_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_peremption_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_peremption_id_seq OWNER TO postgres;

--
-- TOC entry 5546 (class 0 OID 0)
-- Dependencies: 306
-- Name: tb_peremption_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_peremption_id_seq OWNED BY public.tb_peremption.id;


--
-- TOC entry 307 (class 1259 OID 214031)
-- Name: tb_personnel; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_personnel (
    id integer NOT NULL,
    nom character varying(50),
    prenom character varying(50),
    datenaissance date,
    adresse character varying(100),
    cin character varying(20),
    contact character varying(50),
    idfonction integer,
    idposte integer,
    matricule character varying(12),
    sexe character varying(15),
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_personnel OWNER TO postgres;

--
-- TOC entry 308 (class 1259 OID 214035)
-- Name: tb_personnel_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_personnel_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_personnel_id_seq OWNER TO postgres;

--
-- TOC entry 5547 (class 0 OID 0)
-- Dependencies: 308
-- Name: tb_personnel_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_personnel_id_seq OWNED BY public.tb_personnel.id;


--
-- TOC entry 309 (class 1259 OID 214036)
-- Name: tb_pmtavoir; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_pmtavoir (
    id integer NOT NULL,
    datepmt timestamp without time zone,
    mtpaye double precision,
    observation character varying(150),
    idtypeoperation integer DEFAULT 1,
    deleted integer,
    refvente character varying(50),
    refavoir character varying(50),
    id_banque integer,
    iduser integer,
    idmode integer
);


ALTER TABLE public.tb_pmtavoir OWNER TO postgres;

--
-- TOC entry 310 (class 1259 OID 214040)
-- Name: tb_pmtavoir_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_pmtavoir_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_pmtavoir_id_seq OWNER TO postgres;

--
-- TOC entry 5548 (class 0 OID 0)
-- Dependencies: 310
-- Name: tb_pmtavoir_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_pmtavoir_id_seq OWNED BY public.tb_pmtavoir.id;


--
-- TOC entry 311 (class 1259 OID 214041)
-- Name: tb_pmtcom; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_pmtcom (
    id integer NOT NULL,
    datepmt timestamp without time zone,
    mtpaye double precision,
    observation character varying(150),
    idtypeoperation integer DEFAULT 2,
    idfrs integer,
    refcom character varying(50),
    idmode integer,
    idpaiment integer,
    factfrs character varying(50),
    refpmt character varying(100),
    id_banque integer,
    iduser integer
);


ALTER TABLE public.tb_pmtcom OWNER TO postgres;

--
-- TOC entry 312 (class 1259 OID 214045)
-- Name: tb_pmtcom_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_pmtcom_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_pmtcom_id_seq OWNER TO postgres;

--
-- TOC entry 5549 (class 0 OID 0)
-- Dependencies: 312
-- Name: tb_pmtcom_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_pmtcom_id_seq OWNED BY public.tb_pmtcom.id;


--
-- TOC entry 313 (class 1259 OID 214046)
-- Name: tb_pmtcredit; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_pmtcredit (
    id integer NOT NULL,
    datepmt timestamp without time zone,
    mtpaye double precision,
    observation character varying(150),
    idtypeoperation integer DEFAULT 1,
    idclient integer,
    refvente character varying(50),
    idmode integer,
    idpaiment integer,
    refpmt character varying(50),
    id_banque integer,
    iduser integer
);


ALTER TABLE public.tb_pmtcredit OWNER TO postgres;

--
-- TOC entry 314 (class 1259 OID 214050)
-- Name: tb_pmtcredit_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_pmtcredit_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_pmtcredit_id_seq OWNER TO postgres;

--
-- TOC entry 5550 (class 0 OID 0)
-- Dependencies: 314
-- Name: tb_pmtcredit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_pmtcredit_id_seq OWNED BY public.tb_pmtcredit.id;


--
-- TOC entry 315 (class 1259 OID 214051)
-- Name: tb_pmtfacture; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_pmtfacture (
    id integer NOT NULL,
    datepmt timestamp without time zone,
    mtpaye double precision,
    observation character varying(150),
    idtypeoperation integer DEFAULT 1,
    refpmt character varying(100),
    deleted integer DEFAULT 0,
    refvente character varying(50),
    idclient integer,
    idmode integer,
    id_banque integer,
    iduser integer,
    dateecheance date
);


ALTER TABLE public.tb_pmtfacture OWNER TO postgres;

--
-- TOC entry 316 (class 1259 OID 214056)
-- Name: tb_pmtfacture_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_pmtfacture_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_pmtfacture_id_seq OWNER TO postgres;

--
-- TOC entry 5551 (class 0 OID 0)
-- Dependencies: 316
-- Name: tb_pmtfacture_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_pmtfacture_id_seq OWNED BY public.tb_pmtfacture.id;


--
-- TOC entry 317 (class 1259 OID 214057)
-- Name: tb_pmtsalaire; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_pmtsalaire (
    id integer NOT NULL,
    datepmt date,
    refpmt character varying(50),
    mtpaye double precision,
    idtypeoperation integer DEFAULT 2,
    idpers integer,
    observation character varying(100),
    id_banque integer,
    idmode integer DEFAULT 1,
    iduser integer
);


ALTER TABLE public.tb_pmtsalaire OWNER TO postgres;

--
-- TOC entry 318 (class 1259 OID 214062)
-- Name: tb_pmtsalaire_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_pmtsalaire_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_pmtsalaire_id_seq OWNER TO postgres;

--
-- TOC entry 5552 (class 0 OID 0)
-- Dependencies: 318
-- Name: tb_pmtsalaire_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_pmtsalaire_id_seq OWNED BY public.tb_pmtsalaire.id;


--
-- TOC entry 319 (class 1259 OID 214063)
-- Name: tb_presencepers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_presencepers (
    id integer NOT NULL,
    idpers integer,
    nbheure double precision,
    date timestamp without time zone
);


ALTER TABLE public.tb_presencepers OWNER TO postgres;

--
-- TOC entry 320 (class 1259 OID 214066)
-- Name: tb_presencepers_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_presencepers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_presencepers_id_seq OWNER TO postgres;

--
-- TOC entry 5553 (class 0 OID 0)
-- Dependencies: 320
-- Name: tb_presencepers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_presencepers_id_seq OWNED BY public.tb_presencepers.id;


--
-- TOC entry 321 (class 1259 OID 214067)
-- Name: tb_prix; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_prix (
    id integer NOT NULL,
    idarticle integer,
    idunite integer,
    prix double precision,
    dateregistre timestamp without time zone,
    iduser integer,
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_prix OWNER TO postgres;

--
-- TOC entry 322 (class 1259 OID 214071)
-- Name: tb_prix_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_prix_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_prix_id_seq OWNER TO postgres;

--
-- TOC entry 5554 (class 0 OID 0)
-- Dependencies: 322
-- Name: tb_prix_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_prix_id_seq OWNED BY public.tb_prix.id;


--
-- TOC entry 323 (class 1259 OID 214072)
-- Name: tb_proforma; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_proforma (
    idprof integer NOT NULL,
    refprof character varying(50),
    idclient integer,
    iduser integer,
    mtprof double precision,
    observation character varying(150),
    dateprof timestamp without time zone,
    deleted integer,
    datemodif timestamp without time zone,
    statut character varying(50),
    datefacturation timestamp without time zone
);


ALTER TABLE public.tb_proforma OWNER TO postgres;

--
-- TOC entry 324 (class 1259 OID 214075)
-- Name: tb_proforma_idprof_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_proforma_idprof_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_proforma_idprof_seq OWNER TO postgres;

--
-- TOC entry 5555 (class 0 OID 0)
-- Dependencies: 324
-- Name: tb_proforma_idprof_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_proforma_idprof_seq OWNED BY public.tb_proforma.idprof;


--
-- TOC entry 325 (class 1259 OID 214076)
-- Name: tb_proformadetail; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_proformadetail (
    id integer NOT NULL,
    idprof integer,
    idmag integer,
    idarticle integer,
    idunite integer,
    qtprof double precision,
    prixunit double precision,
    qtlivprof double precision,
    total double precision
);


ALTER TABLE public.tb_proformadetail OWNER TO postgres;

--
-- TOC entry 326 (class 1259 OID 214079)
-- Name: tb_proformadetail_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_proformadetail_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_proformadetail_id_seq OWNER TO postgres;

--
-- TOC entry 5556 (class 0 OID 0)
-- Dependencies: 326
-- Name: tb_proformadetail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_proformadetail_id_seq OWNED BY public.tb_proformadetail.id;


--
-- TOC entry 327 (class 1259 OID 214080)
-- Name: tb_salairebasepers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_salairebasepers (
    id integer NOT NULL,
    idpers integer,
    montant double precision,
    date timestamp without time zone
);


ALTER TABLE public.tb_salairebasepers OWNER TO postgres;

--
-- TOC entry 328 (class 1259 OID 214083)
-- Name: tb_salairebasepers_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_salairebasepers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_salairebasepers_id_seq OWNER TO postgres;

--
-- TOC entry 5557 (class 0 OID 0)
-- Dependencies: 328
-- Name: tb_salairebasepers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_salairebasepers_id_seq OWNED BY public.tb_salairebasepers.id;


--
-- TOC entry 329 (class 1259 OID 214084)
-- Name: tb_sortie; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_sortie (
    id integer NOT NULL,
    refsortie character varying(50),
    iduser integer,
    dateregistre timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    description character varying(150),
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_sortie OWNER TO postgres;

--
-- TOC entry 330 (class 1259 OID 214089)
-- Name: tb_sortie_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_sortie_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_sortie_id_seq OWNER TO postgres;

--
-- TOC entry 5558 (class 0 OID 0)
-- Dependencies: 330
-- Name: tb_sortie_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_sortie_id_seq OWNED BY public.tb_sortie.id;


--
-- TOC entry 331 (class 1259 OID 214090)
-- Name: tb_sortiedetail; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_sortiedetail (
    id integer NOT NULL,
    idmag integer,
    idarticle integer,
    idunite integer,
    qtsortie double precision,
    typemouvement integer DEFAULT 2,
    deleted integer DEFAULT 0,
    idsortie integer,
    motif character varying(250)
);


ALTER TABLE public.tb_sortiedetail OWNER TO postgres;

--
-- TOC entry 332 (class 1259 OID 214095)
-- Name: tb_sortiedetail_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_sortiedetail_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_sortiedetail_id_seq OWNER TO postgres;

--
-- TOC entry 5559 (class 0 OID 0)
-- Dependencies: 332
-- Name: tb_sortiedetail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_sortiedetail_id_seq OWNED BY public.tb_sortiedetail.id;


--
-- TOC entry 333 (class 1259 OID 214096)
-- Name: tb_stock; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_stock (
    id integer NOT NULL,
    idmag integer,
    qtstock double precision,
    qtalert double precision,
    deleted integer DEFAULT 0,
    codearticle character varying(50)
);


ALTER TABLE public.tb_stock OWNER TO postgres;

--
-- TOC entry 334 (class 1259 OID 214100)
-- Name: tb_stock_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_stock_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_stock_id_seq OWNER TO postgres;

--
-- TOC entry 5560 (class 0 OID 0)
-- Dependencies: 334
-- Name: tb_stock_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_stock_id_seq OWNED BY public.tb_stock.id;


--
-- TOC entry 335 (class 1259 OID 214101)
-- Name: tb_suivipresence; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_suivipresence (
    idpresence integer NOT NULL,
    datepresence date NOT NULL,
    idpersonnel integer NOT NULL,
    matin character varying(15) DEFAULT 'en_attente'::character varying,
    apresmidi character varying(15) DEFAULT 'en_attente'::character varying,
    observation character varying(255),
    deleted integer DEFAULT 0,
    dateregistre timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.tb_suivipresence OWNER TO postgres;

--
-- TOC entry 336 (class 1259 OID 214108)
-- Name: tb_suivipresence_idpresence_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_suivipresence_idpresence_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_suivipresence_idpresence_seq OWNER TO postgres;

--
-- TOC entry 5561 (class 0 OID 0)
-- Dependencies: 336
-- Name: tb_suivipresence_idpresence_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_suivipresence_idpresence_seq OWNED BY public.tb_suivipresence.idpresence;


--
-- TOC entry 337 (class 1259 OID 214109)
-- Name: tb_tauxhoraire; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_tauxhoraire (
    id integer NOT NULL,
    tauxhoraire double precision,
    idpers integer,
    dateregistre timestamp without time zone
);


ALTER TABLE public.tb_tauxhoraire OWNER TO postgres;

--
-- TOC entry 338 (class 1259 OID 214112)
-- Name: tb_tauxhoraire_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_tauxhoraire_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_tauxhoraire_id_seq OWNER TO postgres;

--
-- TOC entry 5562 (class 0 OID 0)
-- Dependencies: 338
-- Name: tb_tauxhoraire_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_tauxhoraire_id_seq OWNED BY public.tb_tauxhoraire.id;


--
-- TOC entry 339 (class 1259 OID 214113)
-- Name: tb_transfert; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_transfert (
    idtransfert integer NOT NULL,
    reftransfert character varying(50),
    iduser integer,
    idmagsortie integer,
    idmagentree integer,
    dateregistre timestamp without time zone,
    description character varying(150),
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_transfert OWNER TO postgres;

--
-- TOC entry 340 (class 1259 OID 214117)
-- Name: tb_transfert_idtransfert_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_transfert_idtransfert_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_transfert_idtransfert_seq OWNER TO postgres;

--
-- TOC entry 5563 (class 0 OID 0)
-- Dependencies: 340
-- Name: tb_transfert_idtransfert_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_transfert_idtransfert_seq OWNED BY public.tb_transfert.idtransfert;


--
-- TOC entry 341 (class 1259 OID 214118)
-- Name: tb_transfertbanque; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_transfertbanque (
    id integer NOT NULL,
    datepmt date,
    refpmt character varying(50),
    mtpaye double precision,
    idtypeoperation integer,
    observation character varying(100),
    id_banque integer,
    idmode integer,
    iduser integer
);


ALTER TABLE public.tb_transfertbanque OWNER TO postgres;

--
-- TOC entry 342 (class 1259 OID 214121)
-- Name: tb_transfertbanque_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_transfertbanque_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_transfertbanque_id_seq OWNER TO postgres;

--
-- TOC entry 5564 (class 0 OID 0)
-- Dependencies: 342
-- Name: tb_transfertbanque_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_transfertbanque_id_seq OWNED BY public.tb_transfertbanque.id;


--
-- TOC entry 343 (class 1259 OID 214122)
-- Name: tb_transfertcaisse; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_transfertcaisse (
    id integer NOT NULL,
    datepmt date,
    refpmt character varying(50),
    mtpaye double precision,
    idtypeoperation integer,
    observation character varying(100),
    id_banque integer,
    iduser integer,
    idmode integer
);


ALTER TABLE public.tb_transfertcaisse OWNER TO postgres;

--
-- TOC entry 344 (class 1259 OID 214125)
-- Name: tb_transfertcaisse_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_transfertcaisse_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_transfertcaisse_id_seq OWNER TO postgres;

--
-- TOC entry 5565 (class 0 OID 0)
-- Dependencies: 344
-- Name: tb_transfertcaisse_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_transfertcaisse_id_seq OWNED BY public.tb_transfertcaisse.id;


--
-- TOC entry 345 (class 1259 OID 214126)
-- Name: tb_transfertdetail; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_transfertdetail (
    id integer NOT NULL,
    idarticle integer,
    idunite integer,
    qttransfertsortie double precision,
    qttransfertentree double precision,
    deleted integer DEFAULT 0,
    idtransfert integer,
    idmagsortie integer,
    idmagentree integer,
    qttransfert double precision,
    description character varying(250)
);


ALTER TABLE public.tb_transfertdetail OWNER TO postgres;

--
-- TOC entry 346 (class 1259 OID 214130)
-- Name: tb_transfertdetail_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_transfertdetail_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_transfertdetail_id_seq OWNER TO postgres;

--
-- TOC entry 5566 (class 0 OID 0)
-- Dependencies: 346
-- Name: tb_transfertdetail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_transfertdetail_id_seq OWNED BY public.tb_transfertdetail.id;


--
-- TOC entry 347 (class 1259 OID 214131)
-- Name: tb_transporteur_idtransporteur_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_transporteur_idtransporteur_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_transporteur_idtransporteur_seq OWNER TO postgres;

--
-- TOC entry 348 (class 1259 OID 214132)
-- Name: tb_transporteur; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_transporteur (
    idtransporteur integer DEFAULT nextval('public.tb_transporteur_idtransporteur_seq'::regclass) NOT NULL,
    nom character varying(150) NOT NULL,
    contact character varying(100),
    adresse character varying(200),
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_transporteur OWNER TO postgres;

--
-- TOC entry 349 (class 1259 OID 214137)
-- Name: tb_typeclient; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_typeclient (
    idtypeclient integer NOT NULL,
    designationtypeclient character varying(25)
);


ALTER TABLE public.tb_typeclient OWNER TO postgres;

--
-- TOC entry 350 (class 1259 OID 214140)
-- Name: tb_typeclient_idtypeclient_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_typeclient_idtypeclient_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_typeclient_idtypeclient_seq OWNER TO postgres;

--
-- TOC entry 5567 (class 0 OID 0)
-- Dependencies: 350
-- Name: tb_typeclient_idtypeclient_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_typeclient_idtypeclient_seq OWNED BY public.tb_typeclient.idtypeclient;


--
-- TOC entry 351 (class 1259 OID 214141)
-- Name: tb_typeoperation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_typeoperation (
    idtypeoperation integer NOT NULL,
    typeoperation character varying(3)
);


ALTER TABLE public.tb_typeoperation OWNER TO postgres;

--
-- TOC entry 352 (class 1259 OID 214144)
-- Name: tb_typeoperation_idtypeoperation_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_typeoperation_idtypeoperation_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_typeoperation_idtypeoperation_seq OWNER TO postgres;

--
-- TOC entry 5568 (class 0 OID 0)
-- Dependencies: 352
-- Name: tb_typeoperation_idtypeoperation_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_typeoperation_idtypeoperation_seq OWNED BY public.tb_typeoperation.idtypeoperation;


--
-- TOC entry 353 (class 1259 OID 214145)
-- Name: tb_typepmt; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_typepmt (
    idtypepmt integer NOT NULL,
    typepmt character varying(50),
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_typepmt OWNER TO postgres;

--
-- TOC entry 354 (class 1259 OID 214149)
-- Name: tb_typepmt_idtypepmt_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_typepmt_idtypepmt_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_typepmt_idtypepmt_seq OWNER TO postgres;

--
-- TOC entry 5569 (class 0 OID 0)
-- Dependencies: 354
-- Name: tb_typepmt_idtypepmt_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_typepmt_idtypepmt_seq OWNED BY public.tb_typepmt.idtypepmt;


--
-- TOC entry 355 (class 1259 OID 214150)
-- Name: tb_unite; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_unite (
    idunite integer NOT NULL,
    codearticle character varying(20),
    idarticle integer,
    designationunite character varying(50),
    niveau integer,
    qtunite double precision,
    poids double precision,
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_unite OWNER TO postgres;

--
-- TOC entry 356 (class 1259 OID 214154)
-- Name: tb_unite_idunite_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_unite_idunite_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_unite_idunite_seq OWNER TO postgres;

--
-- TOC entry 5570 (class 0 OID 0)
-- Dependencies: 356
-- Name: tb_unite_idunite_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_unite_idunite_seq OWNED BY public.tb_unite.idunite;


--
-- TOC entry 357 (class 1259 OID 214155)
-- Name: tb_users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_users (
    iduser integer NOT NULL,
    nomuser character varying(50),
    prenomuser character varying(50),
    adresseuser character varying(100),
    contactuser character varying(50),
    username character varying(50),
    password character varying(50),
    idfonction integer,
    idmag integer,
    active integer,
    dateregistre timestamp without time zone,
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_users OWNER TO postgres;

--
-- TOC entry 358 (class 1259 OID 214159)
-- Name: tb_users_iduser_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_users_iduser_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_users_iduser_seq OWNER TO postgres;

--
-- TOC entry 5571 (class 0 OID 0)
-- Dependencies: 358
-- Name: tb_users_iduser_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_users_iduser_seq OWNED BY public.tb_users.iduser;


--
-- TOC entry 359 (class 1259 OID 214160)
-- Name: tb_vente; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_vente (
    id integer NOT NULL,
    refvente character varying(50),
    idclient integer,
    iduser integer,
    totmtvente double precision,
    dateregistre timestamp without time zone,
    deleted integer DEFAULT 0,
    description character varying(150),
    dateupdate timestamp without time zone,
    idmag integer,
    idmode integer,
    statut character varying(20) DEFAULT 'EN_ATTENTE'::character varying
);


ALTER TABLE public.tb_vente OWNER TO postgres;

--
-- TOC entry 360 (class 1259 OID 214165)
-- Name: tb_vente_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_vente_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_vente_id_seq OWNER TO postgres;

--
-- TOC entry 5572 (class 0 OID 0)
-- Dependencies: 360
-- Name: tb_vente_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_vente_id_seq OWNED BY public.tb_vente.id;


--
-- TOC entry 361 (class 1259 OID 214166)
-- Name: tb_ventedetail; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_ventedetail (
    id integer NOT NULL,
    idmag integer,
    idarticle integer,
    idunite integer,
    qtvente double precision,
    prixunit double precision,
    deleted integer DEFAULT 0,
    idvente integer,
    remise numeric
);


ALTER TABLE public.tb_ventedetail OWNER TO postgres;

--
-- TOC entry 362 (class 1259 OID 214172)
-- Name: tb_ventedetail_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tb_ventedetail_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tb_ventedetail_id_seq OWNER TO postgres;

--
-- TOC entry 5573 (class 0 OID 0)
-- Dependencies: 362
-- Name: tb_ventedetail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_ventedetail_id_seq OWNED BY public.tb_ventedetail.id;


--
-- TOC entry 5022 (class 2604 OID 214173)
-- Name: tb_absence id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_absence ALTER COLUMN id SET DEFAULT nextval('public.tb_absence_id_seq'::regclass);


--
-- TOC entry 5023 (class 2604 OID 214174)
-- Name: tb_article idarticle; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_article ALTER COLUMN idarticle SET DEFAULT nextval('public.tb_article_idarticle_seq'::regclass);


--
-- TOC entry 5025 (class 2604 OID 214175)
-- Name: tb_autorisation id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autorisation ALTER COLUMN id SET DEFAULT nextval('public.tb_autorisation_id_seq'::regclass);


--
-- TOC entry 5026 (class 2604 OID 214176)
-- Name: tb_autre_infos id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autre_infos ALTER COLUMN id SET DEFAULT nextval('public.tb_autre_infos_id_seq'::regclass);


--
-- TOC entry 5029 (class 2604 OID 214177)
-- Name: tb_autrecreance id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autrecreance ALTER COLUMN id SET DEFAULT nextval('public.tb_autrecreance_id_seq'::regclass);


--
-- TOC entry 5030 (class 2604 OID 214178)
-- Name: tb_autredette id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autredette ALTER COLUMN id SET DEFAULT nextval('public.tb_autredette_id_seq'::regclass);


--
-- TOC entry 5032 (class 2604 OID 214179)
-- Name: tb_avancepers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avancepers ALTER COLUMN id SET DEFAULT nextval('public.tb_avancepers_id_seq'::regclass);


--
-- TOC entry 5033 (class 2604 OID 214180)
-- Name: tb_avanceprof id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avanceprof ALTER COLUMN id SET DEFAULT nextval('public.tb_avanceprof_id_seq'::regclass);


--
-- TOC entry 5034 (class 2604 OID 214181)
-- Name: tb_avancespecpers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avancespecpers ALTER COLUMN id SET DEFAULT nextval('public.tb_avancespecpers_id_seq'::regclass);


--
-- TOC entry 5035 (class 2604 OID 214182)
-- Name: tb_avoir id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avoir ALTER COLUMN id SET DEFAULT nextval('public.tb_avoir_id_seq'::regclass);


--
-- TOC entry 5037 (class 2604 OID 214183)
-- Name: tb_avoirdetail id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avoirdetail ALTER COLUMN id SET DEFAULT nextval('public.tb_avoirdetail_id_seq'::regclass);


--
-- TOC entry 5039 (class 2604 OID 214184)
-- Name: tb_banque id_banque; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_banque ALTER COLUMN id_banque SET DEFAULT nextval('public.tb_banque_id_banque_seq'::regclass);


--
-- TOC entry 5040 (class 2604 OID 214185)
-- Name: tb_baseliste id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_baseliste ALTER COLUMN id SET DEFAULT nextval('public.tb_baseliste_id_seq'::regclass);


--
-- TOC entry 5042 (class 2604 OID 214186)
-- Name: tb_categoriearticle idca; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_categoriearticle ALTER COLUMN idca SET DEFAULT nextval('public.tb_categoriearticle_idca_seq'::regclass);


--
-- TOC entry 5044 (class 2604 OID 214187)
-- Name: tb_categoriecompte idcc; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_categoriecompte ALTER COLUMN idcc SET DEFAULT nextval('public.tb_categoriecompte_idcc_seq'::regclass);


--
-- TOC entry 5044b (class 2604 OID 214187)
-- Name: tb_categoriepersonnel idcategorie; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_categoriepersonnel ALTER COLUMN idcategorie SET DEFAULT nextval('public.tb_categoriepersonnel_idcategorie_seq'::regclass);


--
-- TOC entry 5044c (class 2604 OID 214187)
-- Name: tb_postepersonnel idposte; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_postepersonnel ALTER COLUMN idposte SET DEFAULT nextval('public.tb_postepersonnel_idposte_seq'::regclass);


--
-- TOC entry 5045 (class 2604 OID 214188)
-- Name: tb_changement idchg; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_changement ALTER COLUMN idchg SET DEFAULT nextval('public.tb_changement_idchg_seq'::regclass);


--
-- TOC entry 5047 (class 2604 OID 214189)
-- Name: tb_chat id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_chat ALTER COLUMN id SET DEFAULT nextval('public.tb_chat_id_seq'::regclass);


--
-- TOC entry 5050 (class 2604 OID 214190)
-- Name: tb_client idclient; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_client ALTER COLUMN idclient SET DEFAULT nextval('public.tb_client_idclient_seq'::regclass);


--
-- TOC entry 5052 (class 2604 OID 214191)
-- Name: tb_codeautorisation id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_codeautorisation ALTER COLUMN id SET DEFAULT nextval('public.tb_codeautorisation_id_seq'::regclass);


--
-- TOC entry 5054 (class 2604 OID 214192)
-- Name: tb_commande idcom; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_commande ALTER COLUMN idcom SET DEFAULT nextval('public.tb_commande_idcom_seq'::regclass);


--
-- TOC entry 5056 (class 2604 OID 214193)
-- Name: tb_commandedetail id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_commandedetail ALTER COLUMN id SET DEFAULT nextval('public.tb_commandedetail_id_seq'::regclass);


--
-- TOC entry 5058 (class 2604 OID 214194)
-- Name: tb_configdb id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_configdb ALTER COLUMN id SET DEFAULT nextval('public.tb_configdb_id_seq'::regclass);


--
-- TOC entry 5059 (class 2604 OID 214195)
-- Name: tb_consommationinterne id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_consommationinterne ALTER COLUMN id SET DEFAULT nextval('public.tb_consommationinterne_id_seq'::regclass);


--
-- TOC entry 5062 (class 2604 OID 214196)
-- Name: tb_consommationinterne_details id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_consommationinterne_details ALTER COLUMN id SET DEFAULT nextval('public.tb_consommationinterne_details_id_seq'::regclass);


--
-- TOC entry 5064 (class 2604 OID 214197)
-- Name: tb_decaissement id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_decaissement ALTER COLUMN id SET DEFAULT nextval('public.tb_decaissement_id_seq'::regclass);


--
-- TOC entry 5066 (class 2604 OID 214198)
-- Name: tb_decaissementbq id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_decaissementbq ALTER COLUMN id SET DEFAULT nextval('public.tb_decaissementbq_id_seq'::regclass);


--
-- TOC entry 5068 (class 2604 OID 214199)
-- Name: tb_detailchange_entree iddetail; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_detailchange_entree ALTER COLUMN iddetail SET DEFAULT nextval('public.tb_detailchange_entree_iddetail_seq'::regclass);


--
-- TOC entry 5069 (class 2604 OID 214200)
-- Name: tb_detailchange_sortie iddetail; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_detailchange_sortie ALTER COLUMN iddetail SET DEFAULT nextval('public.tb_detailchange_sortie_iddetail_seq'::regclass);


--
-- TOC entry 5070 (class 2604 OID 214201)
-- Name: tb_encaissement id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_encaissement ALTER COLUMN id SET DEFAULT nextval('public.tb_encaissement_id_seq'::regclass);


--
-- TOC entry 5072 (class 2604 OID 214202)
-- Name: tb_encaissementbq id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_encaissementbq ALTER COLUMN id SET DEFAULT nextval('public.tb_encaissementbq_id_seq'::regclass);


--
-- TOC entry 5166 (class 2604 OID 262957)
-- Name: tb_entree id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_entree ALTER COLUMN id SET DEFAULT nextval('public.tb_entree_id_seq'::regclass);


--
-- TOC entry 5169 (class 2604 OID 262966)
-- Name: tb_entreedetail id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_entreedetail ALTER COLUMN id SET DEFAULT nextval('public.tb_entreedetail_id_seq'::regclass);


--
-- TOC entry 5074 (class 2604 OID 214203)
-- Name: tb_evenement id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_evenement ALTER COLUMN id SET DEFAULT nextval('public.tb_evenement_id_seq'::regclass);


--
-- TOC entry 5075 (class 2604 OID 214204)
-- Name: tb_facturecli idfact; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_facturecli ALTER COLUMN idfact SET DEFAULT nextval('public.tb_facturecli_idfact_seq'::regclass);


--
-- TOC entry 5076 (class 2604 OID 214205)
-- Name: tb_fonction idfonction; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_fonction ALTER COLUMN idfonction SET DEFAULT nextval('public.tb_fonction_idfonction_seq'::regclass);


--
-- TOC entry 5078 (class 2604 OID 214206)
-- Name: tb_fournisseur idfrs; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_fournisseur ALTER COLUMN idfrs SET DEFAULT nextval('public.tb_fournisseur_idfrs_seq'::regclass);


--
-- TOC entry 5080 (class 2604 OID 214207)
-- Name: tb_infosociete id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_infosociete ALTER COLUMN id SET DEFAULT nextval('public.tb_infosociete_id_seq'::regclass);


--
-- TOC entry 5081 (class 2604 OID 214208)
-- Name: tb_inventaire id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_inventaire ALTER COLUMN id SET DEFAULT nextval('public.tb_inventaire_id_seq'::regclass);


--
-- TOC entry 5082 (class 2604 OID 214209)
-- Name: tb_inventaire_temporaire id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_inventaire_temporaire ALTER COLUMN id SET DEFAULT nextval('public.tb_inventaire_temporaire_id_seq'::regclass);


--
-- TOC entry 5087 (class 2604 OID 214210)
-- Name: tb_livraisoncli idlivcli; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_livraisoncli ALTER COLUMN idlivcli SET DEFAULT nextval('public.tb_livraisoncli_idlivcli_seq'::regclass);


--
-- TOC entry 5159 (class 2604 OID 238377)
-- Name: tb_livraisoncli_attente id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_livraisoncli_attente ALTER COLUMN id SET DEFAULT nextval('public.tb_livraisoncli_attente_id_seq'::regclass);


--
-- TOC entry 5088 (class 2604 OID 214211)
-- Name: tb_livraisonfrs idlivfrs; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_livraisonfrs ALTER COLUMN idlivfrs SET DEFAULT nextval('public.tb_livraisonfrs_idlivfrs_seq'::regclass);


--
-- TOC entry 5091 (class 2604 OID 214212)
-- Name: tb_log_stock id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_log_stock ALTER COLUMN id SET DEFAULT nextval('public.tb_log_stock_id_seq'::regclass);


--
-- TOC entry 5094 (class 2604 OID 214213)
-- Name: tb_lot_peremption id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_lot_peremption ALTER COLUMN id SET DEFAULT nextval('public.tb_lot_peremption_id_seq'::regclass);


--
-- TOC entry 5097 (class 2604 OID 214214)
-- Name: tb_magasin idmag; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_magasin ALTER COLUMN idmag SET DEFAULT nextval('public.tb_magasin_idmag_seq'::regclass);


--
-- TOC entry 5099 (class 2604 OID 214215)
-- Name: tb_menu id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_menu ALTER COLUMN id SET DEFAULT nextval('public.tb_menu_id_seq'::regclass);


--
-- TOC entry 5100 (class 2604 OID 214216)
-- Name: tb_modepaiement idmode; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_modepaiement ALTER COLUMN idmode SET DEFAULT nextval('public.tb_modepaiement_idmode_seq'::regclass);


--
-- TOC entry 5101 (class 2604 OID 214217)
-- Name: tb_paiement idpaiement; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_paiement ALTER COLUMN idpaiement SET DEFAULT nextval('public.tb_paiement_idpaiement_seq'::regclass);


--
-- TOC entry 5102 (class 2604 OID 214218)
-- Name: tb_peremption id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_peremption ALTER COLUMN id SET DEFAULT nextval('public.tb_peremption_id_seq'::regclass);


--
-- TOC entry 5104 (class 2604 OID 214219)
-- Name: tb_personnel id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_personnel ALTER COLUMN id SET DEFAULT nextval('public.tb_personnel_id_seq'::regclass);


--
-- TOC entry 5106 (class 2604 OID 214220)
-- Name: tb_pmtavoir id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtavoir ALTER COLUMN id SET DEFAULT nextval('public.tb_pmtavoir_id_seq'::regclass);


--
-- TOC entry 5108 (class 2604 OID 214221)
-- Name: tb_pmtcom id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtcom ALTER COLUMN id SET DEFAULT nextval('public.tb_pmtcom_id_seq'::regclass);


--
-- TOC entry 5110 (class 2604 OID 214222)
-- Name: tb_pmtcredit id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtcredit ALTER COLUMN id SET DEFAULT nextval('public.tb_pmtcredit_id_seq'::regclass);


--
-- TOC entry 5112 (class 2604 OID 214223)
-- Name: tb_pmtfacture id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtfacture ALTER COLUMN id SET DEFAULT nextval('public.tb_pmtfacture_id_seq'::regclass);


--
-- TOC entry 5115 (class 2604 OID 214224)
-- Name: tb_pmtsalaire id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtsalaire ALTER COLUMN id SET DEFAULT nextval('public.tb_pmtsalaire_id_seq'::regclass);


--
-- TOC entry 5118 (class 2604 OID 214225)
-- Name: tb_presencepers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_presencepers ALTER COLUMN id SET DEFAULT nextval('public.tb_presencepers_id_seq'::regclass);


--
-- TOC entry 5119 (class 2604 OID 214226)
-- Name: tb_prix id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_prix ALTER COLUMN id SET DEFAULT nextval('public.tb_prix_id_seq'::regclass);


--
-- TOC entry 5121 (class 2604 OID 214227)
-- Name: tb_proforma idprof; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_proforma ALTER COLUMN idprof SET DEFAULT nextval('public.tb_proforma_idprof_seq'::regclass);


--
-- TOC entry 5122 (class 2604 OID 214228)
-- Name: tb_proformadetail id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_proformadetail ALTER COLUMN id SET DEFAULT nextval('public.tb_proformadetail_id_seq'::regclass);


--
-- TOC entry 5123 (class 2604 OID 214229)
-- Name: tb_salairebasepers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_salairebasepers ALTER COLUMN id SET DEFAULT nextval('public.tb_salairebasepers_id_seq'::regclass);


--
-- TOC entry 5124 (class 2604 OID 214230)
-- Name: tb_sortie id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_sortie ALTER COLUMN id SET DEFAULT nextval('public.tb_sortie_id_seq'::regclass);


--
-- TOC entry 5127 (class 2604 OID 214231)
-- Name: tb_sortiedetail id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_sortiedetail ALTER COLUMN id SET DEFAULT nextval('public.tb_sortiedetail_id_seq'::regclass);


--
-- TOC entry 5130 (class 2604 OID 214232)
-- Name: tb_stock id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_stock ALTER COLUMN id SET DEFAULT nextval('public.tb_stock_id_seq'::regclass);


--
-- TOC entry 5132 (class 2604 OID 214233)
-- Name: tb_suivipresence idpresence; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_suivipresence ALTER COLUMN idpresence SET DEFAULT nextval('public.tb_suivipresence_idpresence_seq'::regclass);


--
-- TOC entry 5137 (class 2604 OID 214234)
-- Name: tb_tauxhoraire id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_tauxhoraire ALTER COLUMN id SET DEFAULT nextval('public.tb_tauxhoraire_id_seq'::regclass);


--
-- TOC entry 5138 (class 2604 OID 214235)
-- Name: tb_transfert idtransfert; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfert ALTER COLUMN idtransfert SET DEFAULT nextval('public.tb_transfert_idtransfert_seq'::regclass);


--
-- TOC entry 5140 (class 2604 OID 214236)
-- Name: tb_transfertbanque id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfertbanque ALTER COLUMN id SET DEFAULT nextval('public.tb_transfertbanque_id_seq'::regclass);


--
-- TOC entry 5141 (class 2604 OID 214237)
-- Name: tb_transfertcaisse id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfertcaisse ALTER COLUMN id SET DEFAULT nextval('public.tb_transfertcaisse_id_seq'::regclass);


--
-- TOC entry 5142 (class 2604 OID 214238)
-- Name: tb_transfertdetail id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfertdetail ALTER COLUMN id SET DEFAULT nextval('public.tb_transfertdetail_id_seq'::regclass);


--
-- TOC entry 5146 (class 2604 OID 214239)
-- Name: tb_typeclient idtypeclient; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_typeclient ALTER COLUMN idtypeclient SET DEFAULT nextval('public.tb_typeclient_idtypeclient_seq'::regclass);


--
-- TOC entry 5147 (class 2604 OID 214240)
-- Name: tb_typeoperation idtypeoperation; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_typeoperation ALTER COLUMN idtypeoperation SET DEFAULT nextval('public.tb_typeoperation_idtypeoperation_seq'::regclass);


--
-- TOC entry 5148 (class 2604 OID 214241)
-- Name: tb_typepmt idtypepmt; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_typepmt ALTER COLUMN idtypepmt SET DEFAULT nextval('public.tb_typepmt_idtypepmt_seq'::regclass);


--
-- TOC entry 5150 (class 2604 OID 214242)
-- Name: tb_unite idunite; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_unite ALTER COLUMN idunite SET DEFAULT nextval('public.tb_unite_idunite_seq'::regclass);


--
-- TOC entry 5152 (class 2604 OID 214243)
-- Name: tb_users iduser; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_users ALTER COLUMN iduser SET DEFAULT nextval('public.tb_users_iduser_seq'::regclass);


--
-- TOC entry 5154 (class 2604 OID 214244)
-- Name: tb_vente id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_vente ALTER COLUMN id SET DEFAULT nextval('public.tb_vente_id_seq'::regclass);


--
-- TOC entry 5157 (class 2604 OID 214245)
-- Name: tb_ventedetail id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_ventedetail ALTER COLUMN id SET DEFAULT nextval('public.tb_ventedetail_id_seq'::regclass);


--
-- TOC entry 5342 (class 2606 OID 246584)
-- Name: event_logs event_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.event_logs
    ADD CONSTRAINT event_logs_pkey PRIMARY KEY (id_log);


--
-- TOC entry 5173 (class 2606 OID 214247)
-- Name: tb_absence tb_absence_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_absence
    ADD CONSTRAINT tb_absence_pkey PRIMARY KEY (id);


--
-- TOC entry 5175 (class 2606 OID 214249)
-- Name: tb_article tb_article_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_article
    ADD CONSTRAINT tb_article_pkey PRIMARY KEY (idarticle);


--
-- TOC entry 5177 (class 2606 OID 214251)
-- Name: tb_autorisation tb_autorisation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autorisation
    ADD CONSTRAINT tb_autorisation_pkey PRIMARY KEY (id);


--
-- TOC entry 5179 (class 2606 OID 214253)
-- Name: tb_autre_infos tb_autre_infos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autre_infos
    ADD CONSTRAINT tb_autre_infos_pkey PRIMARY KEY (id);


--
-- TOC entry 5181 (class 2606 OID 214255)
-- Name: tb_autrecreance tb_autrecreance_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autrecreance
    ADD CONSTRAINT tb_autrecreance_pkey PRIMARY KEY (id);


--
-- TOC entry 5183 (class 2606 OID 214257)
-- Name: tb_autredette tb_autredette_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autredette
    ADD CONSTRAINT tb_autredette_pkey PRIMARY KEY (id);


--
-- TOC entry 5185 (class 2606 OID 214259)
-- Name: tb_avancepers tb_avancepers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avancepers
    ADD CONSTRAINT tb_avancepers_pkey PRIMARY KEY (id);


--
-- TOC entry 5187 (class 2606 OID 214261)
-- Name: tb_avanceprof tb_avanceprof_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avanceprof
    ADD CONSTRAINT tb_avanceprof_pkey PRIMARY KEY (id);


--
-- TOC entry 5189 (class 2606 OID 214263)
-- Name: tb_avancespecpers tb_avancespecpers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avancespecpers
    ADD CONSTRAINT tb_avancespecpers_pkey PRIMARY KEY (id);


--
-- TOC entry 5191 (class 2606 OID 214265)
-- Name: tb_avoir tb_avoir_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avoir
    ADD CONSTRAINT tb_avoir_pkey PRIMARY KEY (id);


--
-- TOC entry 5193 (class 2606 OID 214267)
-- Name: tb_avoirdetail tb_avoirdetail_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avoirdetail
    ADD CONSTRAINT tb_avoirdetail_pkey PRIMARY KEY (id);


--
-- TOC entry 5195 (class 2606 OID 214269)
-- Name: tb_banque tb_banque_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_banque
    ADD CONSTRAINT tb_banque_pkey PRIMARY KEY (id_banque);


--
-- TOC entry 5197 (class 2606 OID 214271)
-- Name: tb_baseliste tb_baseliste_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_baseliste
    ADD CONSTRAINT tb_baseliste_pkey PRIMARY KEY (id);


--
-- TOC entry 5199 (class 2606 OID 214273)
-- Name: tb_categoriearticle tb_categoriearticle_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_categoriearticle
    ADD CONSTRAINT tb_categoriearticle_pkey PRIMARY KEY (idca);


--
-- TOC entry 5201 (class 2606 OID 214275)
-- Name: tb_categoriecompte tb_categoriecompte_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_categoriecompte
    ADD CONSTRAINT tb_categoriecompte_pkey PRIMARY KEY (idcc);


--
-- TOC entry 5201b (class 2606 OID 214275)
-- Name: tb_categoriepersonnel tb_categoriepersonnel_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_categoriepersonnel
    ADD CONSTRAINT tb_categoriepersonnel_pkey PRIMARY KEY (idcategorie);


--
-- TOC entry 5201c (class 2606 OID 214276)
-- Name: tb_postepersonnel tb_postepersonnel_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_postepersonnel
    ADD CONSTRAINT tb_postepersonnel_pkey PRIMARY KEY (idposte);


--
-- TOC entry 5206 (class 2606 OID 214277)
-- Name: tb_changement tb_changement_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_changement
    ADD CONSTRAINT tb_changement_pkey PRIMARY KEY (idchg);


--
-- TOC entry 5208 (class 2606 OID 214279)
-- Name: tb_changement tb_changement_refchg_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_changement
    ADD CONSTRAINT tb_changement_refchg_key UNIQUE (refchg);


--
-- TOC entry 5210 (class 2606 OID 214281)
-- Name: tb_chat tb_chat_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_chat
    ADD CONSTRAINT tb_chat_pkey PRIMARY KEY (id);


--
-- TOC entry 5212 (class 2606 OID 214283)
-- Name: tb_client tb_client_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_client
    ADD CONSTRAINT tb_client_pkey PRIMARY KEY (idclient);


--
-- TOC entry 5214 (class 2606 OID 214285)
-- Name: tb_codeautorisation tb_codeautorisation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_codeautorisation
    ADD CONSTRAINT tb_codeautorisation_pkey PRIMARY KEY (id);


--
-- TOC entry 5216 (class 2606 OID 214287)
-- Name: tb_commande tb_commande_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_commande
    ADD CONSTRAINT tb_commande_pkey PRIMARY KEY (idcom);


--
-- TOC entry 5218 (class 2606 OID 214289)
-- Name: tb_commandedetail tb_commandedetail_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_commandedetail
    ADD CONSTRAINT tb_commandedetail_pkey PRIMARY KEY (id);


--
-- TOC entry 5220 (class 2606 OID 214291)
-- Name: tb_configdb tb_configdb_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_configdb
    ADD CONSTRAINT tb_configdb_pkey PRIMARY KEY (id);


--
-- TOC entry 5226 (class 2606 OID 214293)
-- Name: tb_consommationinterne_details tb_consommationinterne_details_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_consommationinterne_details
    ADD CONSTRAINT tb_consommationinterne_details_pkey PRIMARY KEY (id);


--
-- TOC entry 5222 (class 2606 OID 214295)
-- Name: tb_consommationinterne tb_consommationinterne_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_consommationinterne
    ADD CONSTRAINT tb_consommationinterne_pkey PRIMARY KEY (id);


--
-- TOC entry 5224 (class 2606 OID 214297)
-- Name: tb_consommationinterne tb_consommationinterne_refconsommation_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_consommationinterne
    ADD CONSTRAINT tb_consommationinterne_refconsommation_key UNIQUE (refconsommation);


--
-- TOC entry 5228 (class 2606 OID 214299)
-- Name: tb_decaissement tb_decaissement_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_decaissement
    ADD CONSTRAINT tb_decaissement_pkey PRIMARY KEY (id);


--
-- TOC entry 5230 (class 2606 OID 214301)
-- Name: tb_decaissementbq tb_decaissementbq_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_decaissementbq
    ADD CONSTRAINT tb_decaissementbq_pkey PRIMARY KEY (id);


--
-- TOC entry 5234 (class 2606 OID 214303)
-- Name: tb_detailchange_entree tb_detailchange_entree_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_detailchange_entree
    ADD CONSTRAINT tb_detailchange_entree_pkey PRIMARY KEY (iddetail);


--
-- TOC entry 5238 (class 2606 OID 214305)
-- Name: tb_detailchange_sortie tb_detailchange_sortie_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_detailchange_sortie
    ADD CONSTRAINT tb_detailchange_sortie_pkey PRIMARY KEY (iddetail);


--
-- TOC entry 5240 (class 2606 OID 214307)
-- Name: tb_encaissement tb_encaissement_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_encaissement
    ADD CONSTRAINT tb_encaissement_pkey PRIMARY KEY (id);


--
-- TOC entry 5242 (class 2606 OID 214309)
-- Name: tb_encaissementbq tb_encaissementbq_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_encaissementbq
    ADD CONSTRAINT tb_encaissementbq_pkey PRIMARY KEY (id);


--
-- TOC entry 5344 (class 2606 OID 262959)
-- Name: tb_entree tb_entree_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_entree
    ADD CONSTRAINT tb_entree_pkey PRIMARY KEY (id);


--
-- TOC entry 5346 (class 2606 OID 262968)
-- Name: tb_entreedetail tb_entreedetail_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_entreedetail
    ADD CONSTRAINT tb_entreedetail_pkey PRIMARY KEY (id);


--
-- TOC entry 5244 (class 2606 OID 214311)
-- Name: tb_evenement tb_evenement_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_evenement
    ADD CONSTRAINT tb_evenement_pkey PRIMARY KEY (id);


--
-- TOC entry 5246 (class 2606 OID 214313)
-- Name: tb_facturecli tb_facturecli_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_facturecli
    ADD CONSTRAINT tb_facturecli_pkey PRIMARY KEY (idfact);


--
-- TOC entry 5248 (class 2606 OID 214315)
-- Name: tb_fonction tb_fonction_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_fonction
    ADD CONSTRAINT tb_fonction_pkey PRIMARY KEY (idfonction);


--
-- TOC entry 5250 (class 2606 OID 214317)
-- Name: tb_fournisseur tb_fournisseur_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_fournisseur
    ADD CONSTRAINT tb_fournisseur_pkey PRIMARY KEY (idfrs);


--
-- TOC entry 5252 (class 2606 OID 214319)
-- Name: tb_infosociete tb_infosociete_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_infosociete
    ADD CONSTRAINT tb_infosociete_pkey PRIMARY KEY (id);


--
-- TOC entry 5254 (class 2606 OID 214321)
-- Name: tb_inventaire tb_inventaire_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_inventaire
    ADD CONSTRAINT tb_inventaire_pkey PRIMARY KEY (id);


--
-- TOC entry 5257 (class 2606 OID 214323)
-- Name: tb_inventaire_temporaire tb_inventaire_temporaire_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_inventaire_temporaire
    ADD CONSTRAINT tb_inventaire_temporaire_pkey PRIMARY KEY (id);


--
-- TOC entry 5336 (class 2606 OID 238381)
-- Name: tb_livraisoncli_attente tb_livraisoncli_attente_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_livraisoncli_attente
    ADD CONSTRAINT tb_livraisoncli_attente_pkey PRIMARY KEY (id);


--
-- TOC entry 5259 (class 2606 OID 214325)
-- Name: tb_livraisoncli tb_livraisoncli_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_livraisoncli
    ADD CONSTRAINT tb_livraisoncli_pkey PRIMARY KEY (idlivcli);


--
-- TOC entry 5261 (class 2606 OID 214327)
-- Name: tb_livraisonfrs tb_livraisonfrs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_livraisonfrs
    ADD CONSTRAINT tb_livraisonfrs_pkey PRIMARY KEY (idlivfrs);


--
-- TOC entry 5340 (class 2606 OID 246572)
-- Name: tb_log_evenements tb_log_evenements_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_log_evenements
    ADD CONSTRAINT tb_log_evenements_pkey PRIMARY KEY (id_log);


--
-- TOC entry 5263 (class 2606 OID 214329)
-- Name: tb_log_stock tb_log_stock_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_log_stock
    ADD CONSTRAINT tb_log_stock_pkey PRIMARY KEY (id);


--
-- TOC entry 5265 (class 2606 OID 214331)
-- Name: tb_lot_peremption tb_lot_peremption_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_lot_peremption
    ADD CONSTRAINT tb_lot_peremption_pkey PRIMARY KEY (id);


--
-- TOC entry 5267 (class 2606 OID 214333)
-- Name: tb_magasin tb_magasin_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_magasin
    ADD CONSTRAINT tb_magasin_pkey PRIMARY KEY (idmag);


--
-- TOC entry 5269 (class 2606 OID 214335)
-- Name: tb_menu tb_menu_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_menu
    ADD CONSTRAINT tb_menu_pkey PRIMARY KEY (id);


--
-- TOC entry 5271 (class 2606 OID 214337)
-- Name: tb_modepaiement tb_modepaiement_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_modepaiement
    ADD CONSTRAINT tb_modepaiement_pkey PRIMARY KEY (idmode);


--
-- TOC entry 5273 (class 2606 OID 214339)
-- Name: tb_paiement tb_paiement_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_paiement
    ADD CONSTRAINT tb_paiement_pkey PRIMARY KEY (idpaiement);


--
-- TOC entry 5275 (class 2606 OID 214341)
-- Name: tb_peremption tb_peremption_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_peremption
    ADD CONSTRAINT tb_peremption_pkey PRIMARY KEY (id);


--
-- TOC entry 5277 (class 2606 OID 214343)
-- Name: tb_personnel tb_personnel_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_personnel
    ADD CONSTRAINT tb_personnel_pkey PRIMARY KEY (id);


--
-- TOC entry 5279 (class 2606 OID 214345)
-- Name: tb_pmtavoir tb_pmtavoir_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtavoir
    ADD CONSTRAINT tb_pmtavoir_pkey PRIMARY KEY (id);


--
-- TOC entry 5281 (class 2606 OID 214347)
-- Name: tb_pmtcom tb_pmtcom_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtcom
    ADD CONSTRAINT tb_pmtcom_pkey PRIMARY KEY (id);


--
-- TOC entry 5283 (class 2606 OID 214349)
-- Name: tb_pmtcredit tb_pmtcredit_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtcredit
    ADD CONSTRAINT tb_pmtcredit_pkey PRIMARY KEY (id);


--
-- TOC entry 5285 (class 2606 OID 214351)
-- Name: tb_pmtfacture tb_pmtfacture_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtfacture
    ADD CONSTRAINT tb_pmtfacture_pkey PRIMARY KEY (id);


--
-- TOC entry 5287 (class 2606 OID 214353)
-- Name: tb_pmtsalaire tb_pmtsalaire_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtsalaire
    ADD CONSTRAINT tb_pmtsalaire_pkey PRIMARY KEY (id);


--
-- TOC entry 5289 (class 2606 OID 214355)
-- Name: tb_presencepers tb_presencepers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_presencepers
    ADD CONSTRAINT tb_presencepers_pkey PRIMARY KEY (id);


--
-- TOC entry 5291 (class 2606 OID 214357)
-- Name: tb_prix tb_prix_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_prix
    ADD CONSTRAINT tb_prix_pkey PRIMARY KEY (id);


--
-- TOC entry 5293 (class 2606 OID 214359)
-- Name: tb_proforma tb_proforma_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_proforma
    ADD CONSTRAINT tb_proforma_pkey PRIMARY KEY (idprof);


--
-- TOC entry 5295 (class 2606 OID 214361)
-- Name: tb_proformadetail tb_proformadetail_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_proformadetail
    ADD CONSTRAINT tb_proformadetail_pkey PRIMARY KEY (id);


--
-- TOC entry 5297 (class 2606 OID 214363)
-- Name: tb_salairebasepers tb_salairebasepers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_salairebasepers
    ADD CONSTRAINT tb_salairebasepers_pkey PRIMARY KEY (id);


--
-- TOC entry 5299 (class 2606 OID 214365)
-- Name: tb_sortie tb_sortie_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_sortie
    ADD CONSTRAINT tb_sortie_pkey PRIMARY KEY (id);


--
-- TOC entry 5301 (class 2606 OID 214367)
-- Name: tb_sortiedetail tb_sortiedetail_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_sortiedetail
    ADD CONSTRAINT tb_sortiedetail_pkey PRIMARY KEY (id);


--
-- TOC entry 5303 (class 2606 OID 214369)
-- Name: tb_stock tb_stock_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_stock
    ADD CONSTRAINT tb_stock_pkey PRIMARY KEY (id);


--
-- TOC entry 5306 (class 2606 OID 214371)
-- Name: tb_suivipresence tb_suivipresence_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_suivipresence
    ADD CONSTRAINT tb_suivipresence_pkey PRIMARY KEY (idpresence);


--
-- TOC entry 5308 (class 2606 OID 214373)
-- Name: tb_tauxhoraire tb_tauxhoraire_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_tauxhoraire
    ADD CONSTRAINT tb_tauxhoraire_pkey PRIMARY KEY (id);


--
-- TOC entry 5310 (class 2606 OID 214375)
-- Name: tb_transfert tb_transfert_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfert
    ADD CONSTRAINT tb_transfert_pkey PRIMARY KEY (idtransfert);


--
-- TOC entry 5312 (class 2606 OID 214377)
-- Name: tb_transfertbanque tb_transfertbanque_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfertbanque
    ADD CONSTRAINT tb_transfertbanque_pkey PRIMARY KEY (id);


--
-- TOC entry 5314 (class 2606 OID 214379)
-- Name: tb_transfertcaisse tb_transfertcaisse_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfertcaisse
    ADD CONSTRAINT tb_transfertcaisse_pkey PRIMARY KEY (id);


--
-- TOC entry 5316 (class 2606 OID 214381)
-- Name: tb_transfertdetail tb_transfertdetail_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfertdetail
    ADD CONSTRAINT tb_transfertdetail_pkey PRIMARY KEY (id);


--
-- TOC entry 5318 (class 2606 OID 214383)
-- Name: tb_transporteur tb_transporteur_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transporteur
    ADD CONSTRAINT tb_transporteur_pkey PRIMARY KEY (idtransporteur);


--
-- TOC entry 5320 (class 2606 OID 214385)
-- Name: tb_typeclient tb_typeclient_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_typeclient
    ADD CONSTRAINT tb_typeclient_pkey PRIMARY KEY (idtypeclient);


--
-- TOC entry 5322 (class 2606 OID 214387)
-- Name: tb_typeoperation tb_typeoperation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_typeoperation
    ADD CONSTRAINT tb_typeoperation_pkey PRIMARY KEY (idtypeoperation);


--
-- TOC entry 5324 (class 2606 OID 214389)
-- Name: tb_typepmt tb_typepmt_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_typepmt
    ADD CONSTRAINT tb_typepmt_pkey PRIMARY KEY (idtypepmt);


--
-- TOC entry 5326 (class 2606 OID 214391)
-- Name: tb_unite tb_unite_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_unite
    ADD CONSTRAINT tb_unite_pkey PRIMARY KEY (idunite);


--
-- TOC entry 5328 (class 2606 OID 214393)
-- Name: tb_users tb_users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_users
    ADD CONSTRAINT tb_users_pkey PRIMARY KEY (iduser);


--
-- TOC entry 5330 (class 2606 OID 214395)
-- Name: tb_vente tb_vente_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_vente
    ADD CONSTRAINT tb_vente_pkey PRIMARY KEY (id);


--
-- TOC entry 5332 (class 2606 OID 214397)
-- Name: tb_ventedetail tb_ventedetail_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_ventedetail
    ADD CONSTRAINT tb_ventedetail_pkey PRIMARY KEY (id);


--
-- TOC entry 5202 (class 1259 OID 214398)
-- Name: idx_changement_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_changement_date ON public.tb_changement USING btree (datechg);


--
-- TOC entry 5203 (class 1259 OID 214399)
-- Name: idx_changement_refchg; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_changement_refchg ON public.tb_changement USING btree (refchg);


--
-- TOC entry 5204 (class 1259 OID 214400)
-- Name: idx_changement_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_changement_user ON public.tb_changement USING btree (iduser);


--
-- TOC entry 5231 (class 1259 OID 214401)
-- Name: idx_detailchange_entree_article; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_detailchange_entree_article ON public.tb_detailchange_entree USING btree (idarticle);


--
-- TOC entry 5232 (class 1259 OID 214402)
-- Name: idx_detailchange_entree_idchg; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_detailchange_entree_idchg ON public.tb_detailchange_entree USING btree (idchg);


--
-- TOC entry 5235 (class 1259 OID 214403)
-- Name: idx_detailchange_sortie_article; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_detailchange_sortie_article ON public.tb_detailchange_sortie USING btree (idarticle);


--
-- TOC entry 5236 (class 1259 OID 214404)
-- Name: idx_detailchange_sortie_idchg; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_detailchange_sortie_idchg ON public.tb_detailchange_sortie USING btree (idchg);


--
-- TOC entry 5255 (class 1259 OID 214405)
-- Name: idx_inv_temp_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_inv_temp_date ON public.tb_inventaire_temporaire USING btree (date_creation);


--
-- TOC entry 5333 (class 1259 OID 238383)
-- Name: idx_livcli_attente_refvente; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_livcli_attente_refvente ON public.tb_livraisoncli_attente USING btree (refvente);


--
-- TOC entry 5334 (class 1259 OID 238382)
-- Name: idx_livcli_attente_statut; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_livcli_attente_statut ON public.tb_livraisoncli_attente USING btree (statut);


--
-- TOC entry 5304 (class 1259 OID 214406)
-- Name: idx_suivipresence_date_personnel; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_suivipresence_date_personnel ON public.tb_suivipresence USING btree (datepresence, idpersonnel);


--
-- TOC entry 5337 (class 1259 OID 246573)
-- Name: idx_tb_log_evenements_datetime; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tb_log_evenements_datetime ON public.tb_log_evenements USING btree (datetime DESC);


--
-- TOC entry 5338 (class 1259 OID 246574)
-- Name: idx_tb_log_evenements_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tb_log_evenements_user ON public.tb_log_evenements USING btree ("user");


--
-- TOC entry 5348 (class 2606 OID 214407)
-- Name: tb_chat fk_destinataire; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_chat
    ADD CONSTRAINT fk_destinataire FOREIGN KEY (id_destinataire) REFERENCES public.tb_users(iduser);


--
-- TOC entry 5349 (class 2606 OID 214412)
-- Name: tb_chat fk_expediteur; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_chat
    ADD CONSTRAINT fk_expediteur FOREIGN KEY (id_expediteur) REFERENCES public.tb_users(iduser);


--
-- TOC entry 5347 (class 2606 OID 214417)
-- Name: tb_avanceprof tb_avanceprof_idpers_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avanceprof
    ADD CONSTRAINT tb_avanceprof_idpers_fkey FOREIGN KEY (idpers) REFERENCES public.tb_personnel(id);


--
-- TOC entry 5349b (class 2606 OID 214418)
-- Name: tb_postepersonnel tb_postepersonnel_idcategorie_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_postepersonnel
    ADD CONSTRAINT tb_postepersonnel_idcategorie_fkey FOREIGN KEY (idcategorie) REFERENCES public.tb_categoriepersonnel(idcategorie) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- TOC entry 5349c (class 2606 OID 214419)
-- Name: tb_personnel tb_personnel_idposte_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_personnel
    ADD CONSTRAINT tb_personnel_idposte_fkey FOREIGN KEY (idposte) REFERENCES public.tb_postepersonnel(idposte) ON UPDATE CASCADE ON DELETE SET NULL;


COMMENT ON COLUMN public.tb_magasin.livraison_auto_client IS '1 = BL auto (tb_livraisoncli) à la validation facture pour ce magasin ; 0 = manuel.';

COMMENT ON COLUMN public.tb_personnel.idposte IS 'Lien optionnel vers tb_postepersonnel (nullable, affichage).';

-- Completed on 2026-04-24 08:27:58

--
-- PostgreSQL database dump complete
--


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

COMMIT;

-- Fin schéma vide — exécuter ensuite : sql/ijeery_seed_minimal.sql
