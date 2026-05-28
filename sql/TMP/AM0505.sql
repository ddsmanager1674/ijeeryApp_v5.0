--
-- PostgreSQL database dump
--

\restrict 4ZrI12a9iOXVNrk2Med9piEANtLTNGDr9KFB54pVfBUUVjllEvAUhYpxGfKm0li

-- Dumped from database version 18.3
-- Dumped by pg_dump version 18.3

-- Started on 2026-05-28 14:54:03

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
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
-- TOC entry 219 (class 1259 OID 18023)
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
-- TOC entry 220 (class 1259 OID 18027)
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
-- TOC entry 5677 (class 0 OID 0)
-- Dependencies: 220
-- Name: tb_absence_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_absence_id_seq OWNED BY public.tb_absence.id;


--
-- TOC entry 221 (class 1259 OID 18028)
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
-- TOC entry 222 (class 1259 OID 18033)
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
-- TOC entry 5678 (class 0 OID 0)
-- Dependencies: 222
-- Name: tb_article_idarticle_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_article_idarticle_seq OWNED BY public.tb_article.idarticle;


--
-- TOC entry 223 (class 1259 OID 18034)
-- Name: tb_autorisation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_autorisation (
    id integer NOT NULL,
    idfonction integer,
    idmenu integer
);


ALTER TABLE public.tb_autorisation OWNER TO postgres;

--
-- TOC entry 224 (class 1259 OID 18038)
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
-- TOC entry 5679 (class 0 OID 0)
-- Dependencies: 224
-- Name: tb_autorisation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_autorisation_id_seq OWNED BY public.tb_autorisation.id;


--
-- TOC entry 225 (class 1259 OID 18039)
-- Name: tb_autre_infos; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_autre_infos (
    id integer NOT NULL,
    intitule character varying(250) DEFAULT ''::character varying,
    valeur character varying(1000) DEFAULT ''::character varying
);


ALTER TABLE public.tb_autre_infos OWNER TO postgres;

--
-- TOC entry 226 (class 1259 OID 18047)
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
-- TOC entry 5680 (class 0 OID 0)
-- Dependencies: 226
-- Name: tb_autre_infos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_autre_infos_id_seq OWNED BY public.tb_autre_infos.id;


--
-- TOC entry 227 (class 1259 OID 18048)
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
-- TOC entry 228 (class 1259 OID 18052)
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
-- TOC entry 5681 (class 0 OID 0)
-- Dependencies: 228
-- Name: tb_autrecreance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_autrecreance_id_seq OWNED BY public.tb_autrecreance.id;


--
-- TOC entry 229 (class 1259 OID 18053)
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
-- TOC entry 230 (class 1259 OID 18058)
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
-- TOC entry 5682 (class 0 OID 0)
-- Dependencies: 230
-- Name: tb_autredette_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_autredette_id_seq OWNED BY public.tb_autredette.id;


--
-- TOC entry 231 (class 1259 OID 18059)
-- Name: tb_avancepers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_avancepers (
    id integer NOT NULL,
    datepmt date,
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
-- TOC entry 232 (class 1259 OID 18063)
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
-- TOC entry 5683 (class 0 OID 0)
-- Dependencies: 232
-- Name: tb_avancepers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_avancepers_id_seq OWNED BY public.tb_avancepers.id;


--
-- TOC entry 233 (class 1259 OID 18064)
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
-- TOC entry 234 (class 1259 OID 18068)
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
-- TOC entry 5684 (class 0 OID 0)
-- Dependencies: 234
-- Name: tb_avanceprof_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_avanceprof_id_seq OWNED BY public.tb_avanceprof.id;


--
-- TOC entry 235 (class 1259 OID 18069)
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
-- TOC entry 236 (class 1259 OID 18073)
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
-- TOC entry 5685 (class 0 OID 0)
-- Dependencies: 236
-- Name: tb_avancespecpers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_avancespecpers_id_seq OWNED BY public.tb_avancespecpers.id;


--
-- TOC entry 237 (class 1259 OID 18074)
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
-- TOC entry 238 (class 1259 OID 18079)
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
-- TOC entry 5686 (class 0 OID 0)
-- Dependencies: 238
-- Name: tb_avoir_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_avoir_id_seq OWNED BY public.tb_avoir.id;


--
-- TOC entry 239 (class 1259 OID 18080)
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
-- TOC entry 240 (class 1259 OID 18085)
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
-- TOC entry 5687 (class 0 OID 0)
-- Dependencies: 240
-- Name: tb_avoirdetail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_avoirdetail_id_seq OWNED BY public.tb_avoirdetail.id;


--
-- TOC entry 241 (class 1259 OID 18086)
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
-- TOC entry 242 (class 1259 OID 18090)
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
-- TOC entry 5688 (class 0 OID 0)
-- Dependencies: 242
-- Name: tb_banque_id_banque_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_banque_id_banque_seq OWNED BY public.tb_banque.id_banque;


--
-- TOC entry 243 (class 1259 OID 18091)
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
-- TOC entry 244 (class 1259 OID 18096)
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
-- TOC entry 5689 (class 0 OID 0)
-- Dependencies: 244
-- Name: tb_baseliste_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_baseliste_id_seq OWNED BY public.tb_baseliste.id;


--
-- TOC entry 245 (class 1259 OID 18097)
-- Name: tb_categoriearticle; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_categoriearticle (
    idca integer NOT NULL,
    designationcat character varying(150),
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_categoriearticle OWNER TO postgres;

--
-- TOC entry 246 (class 1259 OID 18102)
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
-- TOC entry 5690 (class 0 OID 0)
-- Dependencies: 246
-- Name: tb_categoriearticle_idca_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_categoriearticle_idca_seq OWNED BY public.tb_categoriearticle.idca;


--
-- TOC entry 247 (class 1259 OID 18103)
-- Name: tb_categoriecompte; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_categoriecompte (
    idcc integer NOT NULL,
    categoriecompte character varying(100)
);


ALTER TABLE public.tb_categoriecompte OWNER TO postgres;

--
-- TOC entry 248 (class 1259 OID 18107)
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
-- TOC entry 5691 (class 0 OID 0)
-- Dependencies: 248
-- Name: tb_categoriecompte_idcc_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_categoriecompte_idcc_seq OWNED BY public.tb_categoriecompte.idcc;


--
-- TOC entry 249 (class 1259 OID 18108)
-- Name: tb_changement; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_changement (
    idchg integer NOT NULL,
    refchg character varying(20) NOT NULL,
    datechg timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    iduser integer NOT NULL,
    note text
);


ALTER TABLE public.tb_changement OWNER TO postgres;

--
-- TOC entry 250 (class 1259 OID 18118)
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
-- TOC entry 5692 (class 0 OID 0)
-- Dependencies: 250
-- Name: tb_changement_idchg_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_changement_idchg_seq OWNED BY public.tb_changement.idchg;


--
-- TOC entry 251 (class 1259 OID 18119)
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
-- TOC entry 252 (class 1259 OID 18130)
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
-- TOC entry 5693 (class 0 OID 0)
-- Dependencies: 252
-- Name: tb_chat_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_chat_id_seq OWNED BY public.tb_chat.id;


--
-- TOC entry 253 (class 1259 OID 18131)
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
    blocked integer DEFAULT 0,
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_client OWNER TO postgres;

--
-- TOC entry 254 (class 1259 OID 18137)
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
-- TOC entry 5694 (class 0 OID 0)
-- Dependencies: 254
-- Name: tb_client_idclient_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_client_idclient_seq OWNED BY public.tb_client.idclient;


--
-- TOC entry 255 (class 1259 OID 18138)
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
-- TOC entry 256 (class 1259 OID 18143)
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
-- TOC entry 5695 (class 0 OID 0)
-- Dependencies: 256
-- Name: tb_codeautorisation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_codeautorisation_id_seq OWNED BY public.tb_codeautorisation.id;


--
-- TOC entry 257 (class 1259 OID 18144)
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
-- TOC entry 258 (class 1259 OID 18149)
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
-- TOC entry 5696 (class 0 OID 0)
-- Dependencies: 258
-- Name: tb_commande_idcom_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_commande_idcom_seq OWNED BY public.tb_commande.idcom;


--
-- TOC entry 259 (class 1259 OID 18150)
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
-- TOC entry 260 (class 1259 OID 18155)
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
-- TOC entry 5697 (class 0 OID 0)
-- Dependencies: 260
-- Name: tb_commandedetail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_commandedetail_id_seq OWNED BY public.tb_commandedetail.id;


--
-- TOC entry 261 (class 1259 OID 18156)
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
-- TOC entry 262 (class 1259 OID 18160)
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
-- TOC entry 5698 (class 0 OID 0)
-- Dependencies: 262
-- Name: tb_configdb_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_configdb_id_seq OWNED BY public.tb_configdb.id;


--
-- TOC entry 263 (class 1259 OID 18161)
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
-- TOC entry 264 (class 1259 OID 18171)
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
    observation text,
    montant_total numeric(15,2) GENERATED ALWAYS AS ((qtconsomme * prixunit)) STORED
);


ALTER TABLE public.tb_consommationinterne_details OWNER TO postgres;

--
-- TOC entry 265 (class 1259 OID 18184)
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
-- TOC entry 5699 (class 0 OID 0)
-- Dependencies: 265
-- Name: tb_consommationinterne_details_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_consommationinterne_details_id_seq OWNED BY public.tb_consommationinterne_details.id;


--
-- TOC entry 266 (class 1259 OID 18185)
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
-- TOC entry 5700 (class 0 OID 0)
-- Dependencies: 266
-- Name: tb_consommationinterne_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_consommationinterne_id_seq OWNED BY public.tb_consommationinterne.id;


--
-- TOC entry 267 (class 1259 OID 18186)
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
-- TOC entry 268 (class 1259 OID 18191)
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
-- TOC entry 5701 (class 0 OID 0)
-- Dependencies: 268
-- Name: tb_decaissement_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_decaissement_id_seq OWNED BY public.tb_decaissement.id;


--
-- TOC entry 269 (class 1259 OID 18192)
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
-- TOC entry 270 (class 1259 OID 18197)
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
-- TOC entry 5702 (class 0 OID 0)
-- Dependencies: 270
-- Name: tb_decaissementbq_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_decaissementbq_id_seq OWNED BY public.tb_decaissementbq.id;


--
-- TOC entry 271 (class 1259 OID 18198)
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
-- TOC entry 272 (class 1259 OID 18207)
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
-- TOC entry 5703 (class 0 OID 0)
-- Dependencies: 272
-- Name: tb_detailchange_entree_iddetail_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_detailchange_entree_iddetail_seq OWNED BY public.tb_detailchange_entree.iddetail;


--
-- TOC entry 273 (class 1259 OID 18208)
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
-- TOC entry 274 (class 1259 OID 18217)
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
-- TOC entry 5704 (class 0 OID 0)
-- Dependencies: 274
-- Name: tb_detailchange_sortie_iddetail_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_detailchange_sortie_iddetail_seq OWNED BY public.tb_detailchange_sortie.iddetail;


--
-- TOC entry 275 (class 1259 OID 18218)
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
-- TOC entry 276 (class 1259 OID 18223)
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
-- TOC entry 5705 (class 0 OID 0)
-- Dependencies: 276
-- Name: tb_encaissement_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_encaissement_id_seq OWNED BY public.tb_encaissement.id;


--
-- TOC entry 277 (class 1259 OID 18224)
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
-- TOC entry 278 (class 1259 OID 18229)
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
-- TOC entry 5706 (class 0 OID 0)
-- Dependencies: 278
-- Name: tb_encaissementbq_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_encaissementbq_id_seq OWNED BY public.tb_encaissementbq.id;


--
-- TOC entry 279 (class 1259 OID 18230)
-- Name: tb_evenement; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_evenement (
    id integer NOT NULL,
    date timestamp without time zone,
    evenements character varying(200)
);


ALTER TABLE public.tb_evenement OWNER TO postgres;

--
-- TOC entry 280 (class 1259 OID 18234)
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
-- TOC entry 5707 (class 0 OID 0)
-- Dependencies: 280
-- Name: tb_evenement_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_evenement_id_seq OWNED BY public.tb_evenement.id;


--
-- TOC entry 281 (class 1259 OID 18235)
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
-- TOC entry 282 (class 1259 OID 18239)
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
-- TOC entry 5708 (class 0 OID 0)
-- Dependencies: 282
-- Name: tb_facturecli_idfact_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_facturecli_idfact_seq OWNED BY public.tb_facturecli.idfact;


--
-- TOC entry 283 (class 1259 OID 18240)
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
-- TOC entry 284 (class 1259 OID 18245)
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
-- TOC entry 5709 (class 0 OID 0)
-- Dependencies: 284
-- Name: tb_fonction_idfonction_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_fonction_idfonction_seq OWNED BY public.tb_fonction.idfonction;


--
-- TOC entry 285 (class 1259 OID 18246)
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
-- TOC entry 286 (class 1259 OID 18253)
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
-- TOC entry 5710 (class 0 OID 0)
-- Dependencies: 286
-- Name: tb_fournisseur_idfrs_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_fournisseur_idfrs_seq OWNED BY public.tb_fournisseur.idfrs;


--
-- TOC entry 287 (class 1259 OID 18254)
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
-- TOC entry 288 (class 1259 OID 18260)
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
-- TOC entry 5711 (class 0 OID 0)
-- Dependencies: 288
-- Name: tb_infosociete_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_infosociete_id_seq OWNED BY public.tb_infosociete.id;


--
-- TOC entry 289 (class 1259 OID 18261)
-- Name: tb_inventaire; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_inventaire (
    id integer NOT NULL,
    qtinventaire double precision,
    observation character varying(100),
    date timestamp without time zone,
    iduser integer,
    idmag integer,
    codearticle character varying(50),
    prix double precision
);


ALTER TABLE public.tb_inventaire OWNER TO postgres;

--
-- TOC entry 290 (class 1259 OID 18265)
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
-- TOC entry 5712 (class 0 OID 0)
-- Dependencies: 290
-- Name: tb_inventaire_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_inventaire_id_seq OWNED BY public.tb_inventaire.id;


--
-- TOC entry 291 (class 1259 OID 18266)
-- Name: tb_inventaire_temporaire; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_inventaire_temporaire (
    id integer NOT NULL,
    date_creation timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    date_mise_ajour timestamp without time zone,
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
-- TOC entry 292 (class 1259 OID 18278)
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
-- TOC entry 5713 (class 0 OID 0)
-- Dependencies: 292
-- Name: tb_inventaire_temporaire_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_inventaire_temporaire_id_seq OWNED BY public.tb_inventaire_temporaire.id;


--
-- TOC entry 293 (class 1259 OID 18279)
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
-- TOC entry 294 (class 1259 OID 18283)
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
-- TOC entry 5714 (class 0 OID 0)
-- Dependencies: 294
-- Name: tb_livraisoncli_idlivcli_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_livraisoncli_idlivcli_seq OWNED BY public.tb_livraisoncli.idlivcli;


--
-- TOC entry 295 (class 1259 OID 18284)
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
-- TOC entry 296 (class 1259 OID 18290)
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
-- TOC entry 5715 (class 0 OID 0)
-- Dependencies: 296
-- Name: tb_livraisonfrs_idlivfrs_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_livraisonfrs_idlivfrs_seq OWNED BY public.tb_livraisonfrs.idlivfrs;


--
-- TOC entry 297 (class 1259 OID 18291)
-- Name: tb_log_stock; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_log_stock (
    id integer NOT NULL,
    idarticle integer,
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
-- TOC entry 298 (class 1259 OID 18297)
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
-- TOC entry 5716 (class 0 OID 0)
-- Dependencies: 298
-- Name: tb_log_stock_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_log_stock_id_seq OWNED BY public.tb_log_stock.id;


--
-- TOC entry 299 (class 1259 OID 18298)
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
-- TOC entry 300 (class 1259 OID 18306)
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
-- TOC entry 5717 (class 0 OID 0)
-- Dependencies: 300
-- Name: tb_lot_peremption_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_lot_peremption_id_seq OWNED BY public.tb_lot_peremption.id;


--
-- TOC entry 301 (class 1259 OID 18307)
-- Name: tb_magasin; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_magasin (
    idmag integer NOT NULL,
    designationmag character varying(50),
    adressemag character varying(50),
    livraison integer,
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_magasin OWNER TO postgres;

--
-- TOC entry 302 (class 1259 OID 18312)
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
-- TOC entry 5718 (class 0 OID 0)
-- Dependencies: 302
-- Name: tb_magasin_idmag_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_magasin_idmag_seq OWNED BY public.tb_magasin.idmag;


--
-- TOC entry 303 (class 1259 OID 18313)
-- Name: tb_menu; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_menu (
    id integer NOT NULL,
    designationmenu character varying(100),
    page character varying(50)
);


ALTER TABLE public.tb_menu OWNER TO postgres;

--
-- TOC entry 304 (class 1259 OID 18317)
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
-- TOC entry 5719 (class 0 OID 0)
-- Dependencies: 304
-- Name: tb_menu_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_menu_id_seq OWNED BY public.tb_menu.id;


--
-- TOC entry 305 (class 1259 OID 18318)
-- Name: tb_modepaiement; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_modepaiement (
    idmode integer NOT NULL,
    modedepaiement character varying(50)
);


ALTER TABLE public.tb_modepaiement OWNER TO postgres;

--
-- TOC entry 306 (class 1259 OID 18322)
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
-- TOC entry 5720 (class 0 OID 0)
-- Dependencies: 306
-- Name: tb_modepaiement_idmode_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_modepaiement_idmode_seq OWNED BY public.tb_modepaiement.idmode;


--
-- TOC entry 307 (class 1259 OID 18323)
-- Name: tb_paiement; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_paiement (
    idpaiement integer NOT NULL,
    paiement character varying(25)
);


ALTER TABLE public.tb_paiement OWNER TO postgres;

--
-- TOC entry 308 (class 1259 OID 18327)
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
-- TOC entry 5721 (class 0 OID 0)
-- Dependencies: 308
-- Name: tb_paiement_idpaiement_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_paiement_idpaiement_seq OWNED BY public.tb_paiement.idpaiement;


--
-- TOC entry 309 (class 1259 OID 18328)
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
-- TOC entry 310 (class 1259 OID 18333)
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
-- TOC entry 5722 (class 0 OID 0)
-- Dependencies: 310
-- Name: tb_peremption_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_peremption_id_seq OWNED BY public.tb_peremption.id;


--
-- TOC entry 311 (class 1259 OID 18334)
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
    matricule character varying(12),
    sexe character varying(15),
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_personnel OWNER TO postgres;

--
-- TOC entry 312 (class 1259 OID 18339)
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
-- TOC entry 5723 (class 0 OID 0)
-- Dependencies: 312
-- Name: tb_personnel_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_personnel_id_seq OWNED BY public.tb_personnel.id;


--
-- TOC entry 313 (class 1259 OID 18340)
-- Name: tb_pmtavoir; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_pmtavoir (
    id integer NOT NULL,
    datepmt timestamp without time zone,
    mtpaye double precision,
    refvente character varying(50),
    refavoir character varying(50),
    observation character varying(150),
    idtypeoperation integer DEFAULT 1,
    refpmt character varying(100),
    idtypepmt integer DEFAULT 1,
    deleted integer DEFAULT 0,
    id_banque integer,
    iduser integer,
    idmode integer
);


ALTER TABLE public.tb_pmtavoir OWNER TO postgres;

--
-- TOC entry 314 (class 1259 OID 18347)
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
-- TOC entry 5724 (class 0 OID 0)
-- Dependencies: 314
-- Name: tb_pmtavoir_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_pmtavoir_id_seq OWNED BY public.tb_pmtavoir.id;


--
-- TOC entry 315 (class 1259 OID 18348)
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
-- TOC entry 316 (class 1259 OID 18353)
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
-- TOC entry 5725 (class 0 OID 0)
-- Dependencies: 316
-- Name: tb_pmtcom_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_pmtcom_id_seq OWNED BY public.tb_pmtcom.id;


--
-- TOC entry 317 (class 1259 OID 18354)
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
-- TOC entry 318 (class 1259 OID 18359)
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
-- TOC entry 5726 (class 0 OID 0)
-- Dependencies: 318
-- Name: tb_pmtcredit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_pmtcredit_id_seq OWNED BY public.tb_pmtcredit.id;


--
-- TOC entry 319 (class 1259 OID 18360)
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
-- TOC entry 320 (class 1259 OID 18366)
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
-- TOC entry 5727 (class 0 OID 0)
-- Dependencies: 320
-- Name: tb_pmtfacture_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_pmtfacture_id_seq OWNED BY public.tb_pmtfacture.id;


--
-- TOC entry 321 (class 1259 OID 18367)
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
-- TOC entry 322 (class 1259 OID 18373)
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
-- TOC entry 5728 (class 0 OID 0)
-- Dependencies: 322
-- Name: tb_pmtsalaire_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_pmtsalaire_id_seq OWNED BY public.tb_pmtsalaire.id;


--
-- TOC entry 323 (class 1259 OID 18374)
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
-- TOC entry 324 (class 1259 OID 18378)
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
-- TOC entry 5729 (class 0 OID 0)
-- Dependencies: 324
-- Name: tb_presencepers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_presencepers_id_seq OWNED BY public.tb_presencepers.id;


--
-- TOC entry 325 (class 1259 OID 18379)
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
-- TOC entry 326 (class 1259 OID 18384)
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
-- TOC entry 5730 (class 0 OID 0)
-- Dependencies: 326
-- Name: tb_prix_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_prix_id_seq OWNED BY public.tb_prix.id;


--
-- TOC entry 327 (class 1259 OID 18385)
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
    deleted integer DEFAULT 0,
    datemodif timestamp without time zone,
    statut character varying(50),
    datefacturation timestamp without time zone
);


ALTER TABLE public.tb_proforma OWNER TO postgres;

--
-- TOC entry 328 (class 1259 OID 18390)
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
-- TOC entry 5731 (class 0 OID 0)
-- Dependencies: 328
-- Name: tb_proforma_idprof_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_proforma_idprof_seq OWNED BY public.tb_proforma.idprof;


--
-- TOC entry 329 (class 1259 OID 18391)
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
-- TOC entry 330 (class 1259 OID 18395)
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
-- TOC entry 5732 (class 0 OID 0)
-- Dependencies: 330
-- Name: tb_proformadetail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_proformadetail_id_seq OWNED BY public.tb_proformadetail.id;


--
-- TOC entry 331 (class 1259 OID 18396)
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
-- TOC entry 332 (class 1259 OID 18400)
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
-- TOC entry 5733 (class 0 OID 0)
-- Dependencies: 332
-- Name: tb_salairebasepers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_salairebasepers_id_seq OWNED BY public.tb_salairebasepers.id;


--
-- TOC entry 333 (class 1259 OID 18401)
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
-- TOC entry 334 (class 1259 OID 18407)
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
-- TOC entry 5734 (class 0 OID 0)
-- Dependencies: 334
-- Name: tb_sortie_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_sortie_id_seq OWNED BY public.tb_sortie.id;


--
-- TOC entry 335 (class 1259 OID 18408)
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
-- TOC entry 336 (class 1259 OID 18414)
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
-- TOC entry 5735 (class 0 OID 0)
-- Dependencies: 336
-- Name: tb_sortiedetail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_sortiedetail_id_seq OWNED BY public.tb_sortiedetail.id;


--
-- TOC entry 337 (class 1259 OID 18415)
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
-- TOC entry 338 (class 1259 OID 18420)
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
-- TOC entry 5736 (class 0 OID 0)
-- Dependencies: 338
-- Name: tb_stock_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_stock_id_seq OWNED BY public.tb_stock.id;


--
-- TOC entry 339 (class 1259 OID 18421)
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
-- TOC entry 340 (class 1259 OID 18431)
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
-- TOC entry 5737 (class 0 OID 0)
-- Dependencies: 340
-- Name: tb_suivipresence_idpresence_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_suivipresence_idpresence_seq OWNED BY public.tb_suivipresence.idpresence;


--
-- TOC entry 341 (class 1259 OID 18432)
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
-- TOC entry 342 (class 1259 OID 18436)
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
-- TOC entry 5738 (class 0 OID 0)
-- Dependencies: 342
-- Name: tb_tauxhoraire_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_tauxhoraire_id_seq OWNED BY public.tb_tauxhoraire.id;


--
-- TOC entry 343 (class 1259 OID 18437)
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
-- TOC entry 344 (class 1259 OID 18442)
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
-- TOC entry 5739 (class 0 OID 0)
-- Dependencies: 344
-- Name: tb_transfert_idtransfert_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_transfert_idtransfert_seq OWNED BY public.tb_transfert.idtransfert;


--
-- TOC entry 345 (class 1259 OID 18443)
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
-- TOC entry 346 (class 1259 OID 18447)
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
-- TOC entry 5740 (class 0 OID 0)
-- Dependencies: 346
-- Name: tb_transfertbanque_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_transfertbanque_id_seq OWNED BY public.tb_transfertbanque.id;


--
-- TOC entry 347 (class 1259 OID 18448)
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
-- TOC entry 348 (class 1259 OID 18452)
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
-- TOC entry 5741 (class 0 OID 0)
-- Dependencies: 348
-- Name: tb_transfertcaisse_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_transfertcaisse_id_seq OWNED BY public.tb_transfertcaisse.id;


--
-- TOC entry 349 (class 1259 OID 18453)
-- Name: tb_transfertdetail; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_transfertdetail (
    id integer NOT NULL,
    idarticle integer,
    idunite integer,
    qttranfertsortie double precision,
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
-- TOC entry 350 (class 1259 OID 18458)
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
-- TOC entry 5742 (class 0 OID 0)
-- Dependencies: 350
-- Name: tb_transfertdetail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_transfertdetail_id_seq OWNED BY public.tb_transfertdetail.id;


--
-- TOC entry 351 (class 1259 OID 18459)
-- Name: tb_transporteur; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_transporteur (
    idtransporteur integer NOT NULL,
    nom character varying(150),
    contact character varying(100),
    adresse character varying(200),
    montant double precision,
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_transporteur OWNER TO postgres;

--
-- TOC entry 352 (class 1259 OID 18464)
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
-- TOC entry 5743 (class 0 OID 0)
-- Dependencies: 352
-- Name: tb_transporteur_idtransporteur_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_transporteur_idtransporteur_seq OWNED BY public.tb_transporteur.idtransporteur;


--
-- TOC entry 353 (class 1259 OID 18465)
-- Name: tb_typeclient; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_typeclient (
    idtypeclient integer NOT NULL,
    designationtypeclient character varying(25)
);


ALTER TABLE public.tb_typeclient OWNER TO postgres;

--
-- TOC entry 354 (class 1259 OID 18469)
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
-- TOC entry 5744 (class 0 OID 0)
-- Dependencies: 354
-- Name: tb_typeclient_idtypeclient_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_typeclient_idtypeclient_seq OWNED BY public.tb_typeclient.idtypeclient;


--
-- TOC entry 355 (class 1259 OID 18470)
-- Name: tb_typeoperation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_typeoperation (
    idtypeoperation integer NOT NULL,
    typeoperation character varying(3)
);


ALTER TABLE public.tb_typeoperation OWNER TO postgres;

--
-- TOC entry 356 (class 1259 OID 18474)
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
-- TOC entry 5745 (class 0 OID 0)
-- Dependencies: 356
-- Name: tb_typeoperation_idtypeoperation_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_typeoperation_idtypeoperation_seq OWNED BY public.tb_typeoperation.idtypeoperation;


--
-- TOC entry 357 (class 1259 OID 18475)
-- Name: tb_typepmt; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_typepmt (
    idtypepmt integer NOT NULL,
    typepmt character varying(50),
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_typepmt OWNER TO postgres;

--
-- TOC entry 358 (class 1259 OID 18480)
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
-- TOC entry 5746 (class 0 OID 0)
-- Dependencies: 358
-- Name: tb_typepmt_idtypepmt_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_typepmt_idtypepmt_seq OWNED BY public.tb_typepmt.idtypepmt;


--
-- TOC entry 359 (class 1259 OID 18481)
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
-- TOC entry 360 (class 1259 OID 18486)
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
-- TOC entry 5747 (class 0 OID 0)
-- Dependencies: 360
-- Name: tb_unite_idunite_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_unite_idunite_seq OWNED BY public.tb_unite.idunite;


--
-- TOC entry 361 (class 1259 OID 18487)
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
-- TOC entry 362 (class 1259 OID 18492)
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
-- TOC entry 5748 (class 0 OID 0)
-- Dependencies: 362
-- Name: tb_users_iduser_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_users_iduser_seq OWNED BY public.tb_users.iduser;


--
-- TOC entry 363 (class 1259 OID 18493)
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
-- TOC entry 364 (class 1259 OID 18499)
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
-- TOC entry 5749 (class 0 OID 0)
-- Dependencies: 364
-- Name: tb_vente_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_vente_id_seq OWNED BY public.tb_vente.id;


--
-- TOC entry 365 (class 1259 OID 18500)
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
-- TOC entry 366 (class 1259 OID 18507)
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
-- TOC entry 5750 (class 0 OID 0)
-- Dependencies: 366
-- Name: tb_ventedetail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_ventedetail_id_seq OWNED BY public.tb_ventedetail.id;


--
-- TOC entry 5221 (class 2604 OID 18508)
-- Name: tb_absence id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_absence ALTER COLUMN id SET DEFAULT nextval('public.tb_absence_id_seq'::regclass);


--
-- TOC entry 5222 (class 2604 OID 18509)
-- Name: tb_article idarticle; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_article ALTER COLUMN idarticle SET DEFAULT nextval('public.tb_article_idarticle_seq'::regclass);


--
-- TOC entry 5224 (class 2604 OID 18510)
-- Name: tb_autorisation id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autorisation ALTER COLUMN id SET DEFAULT nextval('public.tb_autorisation_id_seq'::regclass);


--
-- TOC entry 5225 (class 2604 OID 18511)
-- Name: tb_autre_infos id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autre_infos ALTER COLUMN id SET DEFAULT nextval('public.tb_autre_infos_id_seq'::regclass);


--
-- TOC entry 5228 (class 2604 OID 18512)
-- Name: tb_autrecreance id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autrecreance ALTER COLUMN id SET DEFAULT nextval('public.tb_autrecreance_id_seq'::regclass);


--
-- TOC entry 5229 (class 2604 OID 18513)
-- Name: tb_autredette id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autredette ALTER COLUMN id SET DEFAULT nextval('public.tb_autredette_id_seq'::regclass);


--
-- TOC entry 5231 (class 2604 OID 18514)
-- Name: tb_avancepers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avancepers ALTER COLUMN id SET DEFAULT nextval('public.tb_avancepers_id_seq'::regclass);


--
-- TOC entry 5232 (class 2604 OID 18515)
-- Name: tb_avanceprof id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avanceprof ALTER COLUMN id SET DEFAULT nextval('public.tb_avanceprof_id_seq'::regclass);


--
-- TOC entry 5233 (class 2604 OID 18516)
-- Name: tb_avancespecpers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avancespecpers ALTER COLUMN id SET DEFAULT nextval('public.tb_avancespecpers_id_seq'::regclass);


--
-- TOC entry 5234 (class 2604 OID 18517)
-- Name: tb_avoir id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avoir ALTER COLUMN id SET DEFAULT nextval('public.tb_avoir_id_seq'::regclass);


--
-- TOC entry 5236 (class 2604 OID 18518)
-- Name: tb_avoirdetail id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avoirdetail ALTER COLUMN id SET DEFAULT nextval('public.tb_avoirdetail_id_seq'::regclass);


--
-- TOC entry 5238 (class 2604 OID 18519)
-- Name: tb_banque id_banque; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_banque ALTER COLUMN id_banque SET DEFAULT nextval('public.tb_banque_id_banque_seq'::regclass);


--
-- TOC entry 5239 (class 2604 OID 18520)
-- Name: tb_baseliste id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_baseliste ALTER COLUMN id SET DEFAULT nextval('public.tb_baseliste_id_seq'::regclass);


--
-- TOC entry 5241 (class 2604 OID 18521)
-- Name: tb_categoriearticle idca; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_categoriearticle ALTER COLUMN idca SET DEFAULT nextval('public.tb_categoriearticle_idca_seq'::regclass);


--
-- TOC entry 5243 (class 2604 OID 18522)
-- Name: tb_categoriecompte idcc; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_categoriecompte ALTER COLUMN idcc SET DEFAULT nextval('public.tb_categoriecompte_idcc_seq'::regclass);


--
-- TOC entry 5244 (class 2604 OID 18523)
-- Name: tb_changement idchg; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_changement ALTER COLUMN idchg SET DEFAULT nextval('public.tb_changement_idchg_seq'::regclass);


--
-- TOC entry 5246 (class 2604 OID 18524)
-- Name: tb_chat id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_chat ALTER COLUMN id SET DEFAULT nextval('public.tb_chat_id_seq'::regclass);


--
-- TOC entry 5249 (class 2604 OID 18525)
-- Name: tb_client idclient; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_client ALTER COLUMN idclient SET DEFAULT nextval('public.tb_client_idclient_seq'::regclass);


--
-- TOC entry 5252 (class 2604 OID 18526)
-- Name: tb_codeautorisation id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_codeautorisation ALTER COLUMN id SET DEFAULT nextval('public.tb_codeautorisation_id_seq'::regclass);


--
-- TOC entry 5254 (class 2604 OID 18527)
-- Name: tb_commande idcom; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_commande ALTER COLUMN idcom SET DEFAULT nextval('public.tb_commande_idcom_seq'::regclass);


--
-- TOC entry 5256 (class 2604 OID 18528)
-- Name: tb_commandedetail id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_commandedetail ALTER COLUMN id SET DEFAULT nextval('public.tb_commandedetail_id_seq'::regclass);


--
-- TOC entry 5258 (class 2604 OID 18529)
-- Name: tb_configdb id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_configdb ALTER COLUMN id SET DEFAULT nextval('public.tb_configdb_id_seq'::regclass);


--
-- TOC entry 5259 (class 2604 OID 18530)
-- Name: tb_consommationinterne id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_consommationinterne ALTER COLUMN id SET DEFAULT nextval('public.tb_consommationinterne_id_seq'::regclass);


--
-- TOC entry 5262 (class 2604 OID 18531)
-- Name: tb_consommationinterne_details id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_consommationinterne_details ALTER COLUMN id SET DEFAULT nextval('public.tb_consommationinterne_details_id_seq'::regclass);


--
-- TOC entry 5264 (class 2604 OID 18532)
-- Name: tb_decaissement id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_decaissement ALTER COLUMN id SET DEFAULT nextval('public.tb_decaissement_id_seq'::regclass);


--
-- TOC entry 5266 (class 2604 OID 18533)
-- Name: tb_decaissementbq id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_decaissementbq ALTER COLUMN id SET DEFAULT nextval('public.tb_decaissementbq_id_seq'::regclass);


--
-- TOC entry 5268 (class 2604 OID 18534)
-- Name: tb_detailchange_entree iddetail; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_detailchange_entree ALTER COLUMN iddetail SET DEFAULT nextval('public.tb_detailchange_entree_iddetail_seq'::regclass);


--
-- TOC entry 5269 (class 2604 OID 18535)
-- Name: tb_detailchange_sortie iddetail; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_detailchange_sortie ALTER COLUMN iddetail SET DEFAULT nextval('public.tb_detailchange_sortie_iddetail_seq'::regclass);


--
-- TOC entry 5270 (class 2604 OID 18536)
-- Name: tb_encaissement id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_encaissement ALTER COLUMN id SET DEFAULT nextval('public.tb_encaissement_id_seq'::regclass);


--
-- TOC entry 5272 (class 2604 OID 18537)
-- Name: tb_encaissementbq id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_encaissementbq ALTER COLUMN id SET DEFAULT nextval('public.tb_encaissementbq_id_seq'::regclass);


--
-- TOC entry 5274 (class 2604 OID 18538)
-- Name: tb_evenement id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_evenement ALTER COLUMN id SET DEFAULT nextval('public.tb_evenement_id_seq'::regclass);


--
-- TOC entry 5275 (class 2604 OID 18539)
-- Name: tb_facturecli idfact; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_facturecli ALTER COLUMN idfact SET DEFAULT nextval('public.tb_facturecli_idfact_seq'::regclass);


--
-- TOC entry 5276 (class 2604 OID 18540)
-- Name: tb_fonction idfonction; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_fonction ALTER COLUMN idfonction SET DEFAULT nextval('public.tb_fonction_idfonction_seq'::regclass);


--
-- TOC entry 5278 (class 2604 OID 18541)
-- Name: tb_fournisseur idfrs; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_fournisseur ALTER COLUMN idfrs SET DEFAULT nextval('public.tb_fournisseur_idfrs_seq'::regclass);


--
-- TOC entry 5280 (class 2604 OID 18542)
-- Name: tb_infosociete id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_infosociete ALTER COLUMN id SET DEFAULT nextval('public.tb_infosociete_id_seq'::regclass);


--
-- TOC entry 5281 (class 2604 OID 18543)
-- Name: tb_inventaire id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_inventaire ALTER COLUMN id SET DEFAULT nextval('public.tb_inventaire_id_seq'::regclass);


--
-- TOC entry 5282 (class 2604 OID 18544)
-- Name: tb_inventaire_temporaire id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_inventaire_temporaire ALTER COLUMN id SET DEFAULT nextval('public.tb_inventaire_temporaire_id_seq'::regclass);


--
-- TOC entry 5286 (class 2604 OID 18545)
-- Name: tb_livraisoncli idlivcli; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_livraisoncli ALTER COLUMN idlivcli SET DEFAULT nextval('public.tb_livraisoncli_idlivcli_seq'::regclass);


--
-- TOC entry 5287 (class 2604 OID 18546)
-- Name: tb_livraisonfrs idlivfrs; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_livraisonfrs ALTER COLUMN idlivfrs SET DEFAULT nextval('public.tb_livraisonfrs_idlivfrs_seq'::regclass);


--
-- TOC entry 5290 (class 2604 OID 18547)
-- Name: tb_log_stock id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_log_stock ALTER COLUMN id SET DEFAULT nextval('public.tb_log_stock_id_seq'::regclass);


--
-- TOC entry 5293 (class 2604 OID 18548)
-- Name: tb_lot_peremption id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_lot_peremption ALTER COLUMN id SET DEFAULT nextval('public.tb_lot_peremption_id_seq'::regclass);


--
-- TOC entry 5296 (class 2604 OID 18549)
-- Name: tb_magasin idmag; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_magasin ALTER COLUMN idmag SET DEFAULT nextval('public.tb_magasin_idmag_seq'::regclass);


--
-- TOC entry 5298 (class 2604 OID 18550)
-- Name: tb_menu id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_menu ALTER COLUMN id SET DEFAULT nextval('public.tb_menu_id_seq'::regclass);


--
-- TOC entry 5299 (class 2604 OID 18551)
-- Name: tb_modepaiement idmode; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_modepaiement ALTER COLUMN idmode SET DEFAULT nextval('public.tb_modepaiement_idmode_seq'::regclass);


--
-- TOC entry 5300 (class 2604 OID 18552)
-- Name: tb_paiement idpaiement; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_paiement ALTER COLUMN idpaiement SET DEFAULT nextval('public.tb_paiement_idpaiement_seq'::regclass);


--
-- TOC entry 5301 (class 2604 OID 18553)
-- Name: tb_peremption id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_peremption ALTER COLUMN id SET DEFAULT nextval('public.tb_peremption_id_seq'::regclass);


--
-- TOC entry 5303 (class 2604 OID 18554)
-- Name: tb_personnel id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_personnel ALTER COLUMN id SET DEFAULT nextval('public.tb_personnel_id_seq'::regclass);


--
-- TOC entry 5305 (class 2604 OID 18555)
-- Name: tb_pmtavoir id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtavoir ALTER COLUMN id SET DEFAULT nextval('public.tb_pmtavoir_id_seq'::regclass);


--
-- TOC entry 5309 (class 2604 OID 18556)
-- Name: tb_pmtcom id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtcom ALTER COLUMN id SET DEFAULT nextval('public.tb_pmtcom_id_seq'::regclass);


--
-- TOC entry 5311 (class 2604 OID 18557)
-- Name: tb_pmtcredit id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtcredit ALTER COLUMN id SET DEFAULT nextval('public.tb_pmtcredit_id_seq'::regclass);


--
-- TOC entry 5313 (class 2604 OID 18558)
-- Name: tb_pmtfacture id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtfacture ALTER COLUMN id SET DEFAULT nextval('public.tb_pmtfacture_id_seq'::regclass);


--
-- TOC entry 5316 (class 2604 OID 18559)
-- Name: tb_pmtsalaire id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtsalaire ALTER COLUMN id SET DEFAULT nextval('public.tb_pmtsalaire_id_seq'::regclass);


--
-- TOC entry 5319 (class 2604 OID 18560)
-- Name: tb_presencepers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_presencepers ALTER COLUMN id SET DEFAULT nextval('public.tb_presencepers_id_seq'::regclass);


--
-- TOC entry 5320 (class 2604 OID 18561)
-- Name: tb_prix id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_prix ALTER COLUMN id SET DEFAULT nextval('public.tb_prix_id_seq'::regclass);


--
-- TOC entry 5322 (class 2604 OID 18562)
-- Name: tb_proforma idprof; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_proforma ALTER COLUMN idprof SET DEFAULT nextval('public.tb_proforma_idprof_seq'::regclass);


--
-- TOC entry 5324 (class 2604 OID 18563)
-- Name: tb_proformadetail id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_proformadetail ALTER COLUMN id SET DEFAULT nextval('public.tb_proformadetail_id_seq'::regclass);


--
-- TOC entry 5325 (class 2604 OID 18564)
-- Name: tb_salairebasepers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_salairebasepers ALTER COLUMN id SET DEFAULT nextval('public.tb_salairebasepers_id_seq'::regclass);


--
-- TOC entry 5326 (class 2604 OID 18565)
-- Name: tb_sortie id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_sortie ALTER COLUMN id SET DEFAULT nextval('public.tb_sortie_id_seq'::regclass);


--
-- TOC entry 5329 (class 2604 OID 18566)
-- Name: tb_sortiedetail id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_sortiedetail ALTER COLUMN id SET DEFAULT nextval('public.tb_sortiedetail_id_seq'::regclass);


--
-- TOC entry 5332 (class 2604 OID 18567)
-- Name: tb_stock id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_stock ALTER COLUMN id SET DEFAULT nextval('public.tb_stock_id_seq'::regclass);


--
-- TOC entry 5334 (class 2604 OID 18568)
-- Name: tb_suivipresence idpresence; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_suivipresence ALTER COLUMN idpresence SET DEFAULT nextval('public.tb_suivipresence_idpresence_seq'::regclass);


--
-- TOC entry 5339 (class 2604 OID 18569)
-- Name: tb_tauxhoraire id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_tauxhoraire ALTER COLUMN id SET DEFAULT nextval('public.tb_tauxhoraire_id_seq'::regclass);


--
-- TOC entry 5340 (class 2604 OID 18570)
-- Name: tb_transfert idtransfert; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfert ALTER COLUMN idtransfert SET DEFAULT nextval('public.tb_transfert_idtransfert_seq'::regclass);


--
-- TOC entry 5342 (class 2604 OID 18571)
-- Name: tb_transfertbanque id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfertbanque ALTER COLUMN id SET DEFAULT nextval('public.tb_transfertbanque_id_seq'::regclass);


--
-- TOC entry 5343 (class 2604 OID 18572)
-- Name: tb_transfertcaisse id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfertcaisse ALTER COLUMN id SET DEFAULT nextval('public.tb_transfertcaisse_id_seq'::regclass);


--
-- TOC entry 5344 (class 2604 OID 18573)
-- Name: tb_transfertdetail id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfertdetail ALTER COLUMN id SET DEFAULT nextval('public.tb_transfertdetail_id_seq'::regclass);


--
-- TOC entry 5346 (class 2604 OID 18574)
-- Name: tb_transporteur idtransporteur; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transporteur ALTER COLUMN idtransporteur SET DEFAULT nextval('public.tb_transporteur_idtransporteur_seq'::regclass);


--
-- TOC entry 5348 (class 2604 OID 18575)
-- Name: tb_typeclient idtypeclient; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_typeclient ALTER COLUMN idtypeclient SET DEFAULT nextval('public.tb_typeclient_idtypeclient_seq'::regclass);


--
-- TOC entry 5349 (class 2604 OID 18576)
-- Name: tb_typeoperation idtypeoperation; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_typeoperation ALTER COLUMN idtypeoperation SET DEFAULT nextval('public.tb_typeoperation_idtypeoperation_seq'::regclass);


--
-- TOC entry 5350 (class 2604 OID 18577)
-- Name: tb_typepmt idtypepmt; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_typepmt ALTER COLUMN idtypepmt SET DEFAULT nextval('public.tb_typepmt_idtypepmt_seq'::regclass);


--
-- TOC entry 5352 (class 2604 OID 18578)
-- Name: tb_unite idunite; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_unite ALTER COLUMN idunite SET DEFAULT nextval('public.tb_unite_idunite_seq'::regclass);


--
-- TOC entry 5354 (class 2604 OID 18579)
-- Name: tb_users iduser; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_users ALTER COLUMN iduser SET DEFAULT nextval('public.tb_users_iduser_seq'::regclass);


--
-- TOC entry 5356 (class 2604 OID 18580)
-- Name: tb_vente id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_vente ALTER COLUMN id SET DEFAULT nextval('public.tb_vente_id_seq'::regclass);


--
-- TOC entry 5359 (class 2604 OID 18581)
-- Name: tb_ventedetail id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_ventedetail ALTER COLUMN id SET DEFAULT nextval('public.tb_ventedetail_id_seq'::regclass);


--
-- TOC entry 5362 (class 2606 OID 18583)
-- Name: tb_absence tb_absence_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_absence
    ADD CONSTRAINT tb_absence_pkey PRIMARY KEY (id);


--
-- TOC entry 5364 (class 2606 OID 18585)
-- Name: tb_article tb_article_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_article
    ADD CONSTRAINT tb_article_pkey PRIMARY KEY (idarticle);


--
-- TOC entry 5366 (class 2606 OID 18587)
-- Name: tb_autorisation tb_autorisation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autorisation
    ADD CONSTRAINT tb_autorisation_pkey PRIMARY KEY (id);


--
-- TOC entry 5368 (class 2606 OID 18589)
-- Name: tb_autre_infos tb_autre_infos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autre_infos
    ADD CONSTRAINT tb_autre_infos_pkey PRIMARY KEY (id);


--
-- TOC entry 5370 (class 2606 OID 18591)
-- Name: tb_autrecreance tb_autrecreance_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autrecreance
    ADD CONSTRAINT tb_autrecreance_pkey PRIMARY KEY (id);


--
-- TOC entry 5372 (class 2606 OID 18593)
-- Name: tb_autredette tb_autredette_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autredette
    ADD CONSTRAINT tb_autredette_pkey PRIMARY KEY (id);


--
-- TOC entry 5374 (class 2606 OID 18595)
-- Name: tb_avancepers tb_avancepers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avancepers
    ADD CONSTRAINT tb_avancepers_pkey PRIMARY KEY (id);


--
-- TOC entry 5376 (class 2606 OID 18597)
-- Name: tb_avanceprof tb_avanceprof_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avanceprof
    ADD CONSTRAINT tb_avanceprof_pkey PRIMARY KEY (id);


--
-- TOC entry 5378 (class 2606 OID 18599)
-- Name: tb_avancespecpers tb_avancespecpers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avancespecpers
    ADD CONSTRAINT tb_avancespecpers_pkey PRIMARY KEY (id);


--
-- TOC entry 5380 (class 2606 OID 18601)
-- Name: tb_avoir tb_avoir_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avoir
    ADD CONSTRAINT tb_avoir_pkey PRIMARY KEY (id);


--
-- TOC entry 5382 (class 2606 OID 18603)
-- Name: tb_avoirdetail tb_avoirdetail_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avoirdetail
    ADD CONSTRAINT tb_avoirdetail_pkey PRIMARY KEY (id);


--
-- TOC entry 5384 (class 2606 OID 18605)
-- Name: tb_banque tb_banque_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_banque
    ADD CONSTRAINT tb_banque_pkey PRIMARY KEY (id_banque);


--
-- TOC entry 5386 (class 2606 OID 18607)
-- Name: tb_baseliste tb_baseliste_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_baseliste
    ADD CONSTRAINT tb_baseliste_pkey PRIMARY KEY (id);


--
-- TOC entry 5388 (class 2606 OID 18609)
-- Name: tb_categoriearticle tb_categoriearticle_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_categoriearticle
    ADD CONSTRAINT tb_categoriearticle_pkey PRIMARY KEY (idca);


--
-- TOC entry 5390 (class 2606 OID 18611)
-- Name: tb_categoriecompte tb_categoriecompte_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_categoriecompte
    ADD CONSTRAINT tb_categoriecompte_pkey PRIMARY KEY (idcc);


--
-- TOC entry 5395 (class 2606 OID 18613)
-- Name: tb_changement tb_changement_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_changement
    ADD CONSTRAINT tb_changement_pkey PRIMARY KEY (idchg);


--
-- TOC entry 5397 (class 2606 OID 18615)
-- Name: tb_changement tb_changement_refchg_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_changement
    ADD CONSTRAINT tb_changement_refchg_key UNIQUE (refchg);


--
-- TOC entry 5399 (class 2606 OID 18617)
-- Name: tb_chat tb_chat_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_chat
    ADD CONSTRAINT tb_chat_pkey PRIMARY KEY (id);


--
-- TOC entry 5401 (class 2606 OID 18619)
-- Name: tb_client tb_client_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_client
    ADD CONSTRAINT tb_client_pkey PRIMARY KEY (idclient);


--
-- TOC entry 5403 (class 2606 OID 18621)
-- Name: tb_codeautorisation tb_codeautorisation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_codeautorisation
    ADD CONSTRAINT tb_codeautorisation_pkey PRIMARY KEY (id);


--
-- TOC entry 5405 (class 2606 OID 18623)
-- Name: tb_commande tb_commande_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_commande
    ADD CONSTRAINT tb_commande_pkey PRIMARY KEY (idcom);


--
-- TOC entry 5407 (class 2606 OID 18625)
-- Name: tb_commandedetail tb_commandedetail_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_commandedetail
    ADD CONSTRAINT tb_commandedetail_pkey PRIMARY KEY (id);


--
-- TOC entry 5409 (class 2606 OID 18627)
-- Name: tb_configdb tb_configdb_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_configdb
    ADD CONSTRAINT tb_configdb_pkey PRIMARY KEY (id);


--
-- TOC entry 5415 (class 2606 OID 18629)
-- Name: tb_consommationinterne_details tb_consommationinterne_details_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_consommationinterne_details
    ADD CONSTRAINT tb_consommationinterne_details_pkey PRIMARY KEY (id);


--
-- TOC entry 5411 (class 2606 OID 18631)
-- Name: tb_consommationinterne tb_consommationinterne_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_consommationinterne
    ADD CONSTRAINT tb_consommationinterne_pkey PRIMARY KEY (id);


--
-- TOC entry 5413 (class 2606 OID 18633)
-- Name: tb_consommationinterne tb_consommationinterne_refconsommation_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_consommationinterne
    ADD CONSTRAINT tb_consommationinterne_refconsommation_key UNIQUE (refconsommation);


--
-- TOC entry 5417 (class 2606 OID 18635)
-- Name: tb_decaissement tb_decaissement_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_decaissement
    ADD CONSTRAINT tb_decaissement_pkey PRIMARY KEY (id);


--
-- TOC entry 5419 (class 2606 OID 18637)
-- Name: tb_decaissementbq tb_decaissementbq_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_decaissementbq
    ADD CONSTRAINT tb_decaissementbq_pkey PRIMARY KEY (id);


--
-- TOC entry 5423 (class 2606 OID 18639)
-- Name: tb_detailchange_entree tb_detailchange_entree_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_detailchange_entree
    ADD CONSTRAINT tb_detailchange_entree_pkey PRIMARY KEY (iddetail);


--
-- TOC entry 5427 (class 2606 OID 18641)
-- Name: tb_detailchange_sortie tb_detailchange_sortie_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_detailchange_sortie
    ADD CONSTRAINT tb_detailchange_sortie_pkey PRIMARY KEY (iddetail);


--
-- TOC entry 5429 (class 2606 OID 18643)
-- Name: tb_encaissement tb_encaissement_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_encaissement
    ADD CONSTRAINT tb_encaissement_pkey PRIMARY KEY (id);


--
-- TOC entry 5431 (class 2606 OID 18645)
-- Name: tb_encaissementbq tb_encaissementbq_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_encaissementbq
    ADD CONSTRAINT tb_encaissementbq_pkey PRIMARY KEY (id);


--
-- TOC entry 5433 (class 2606 OID 18647)
-- Name: tb_evenement tb_evenement_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_evenement
    ADD CONSTRAINT tb_evenement_pkey PRIMARY KEY (id);


--
-- TOC entry 5435 (class 2606 OID 18649)
-- Name: tb_facturecli tb_facturecli_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_facturecli
    ADD CONSTRAINT tb_facturecli_pkey PRIMARY KEY (idfact);


--
-- TOC entry 5437 (class 2606 OID 18651)
-- Name: tb_fonction tb_fonction_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_fonction
    ADD CONSTRAINT tb_fonction_pkey PRIMARY KEY (idfonction);


--
-- TOC entry 5439 (class 2606 OID 18653)
-- Name: tb_fournisseur tb_fournisseur_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_fournisseur
    ADD CONSTRAINT tb_fournisseur_pkey PRIMARY KEY (idfrs);


--
-- TOC entry 5441 (class 2606 OID 18655)
-- Name: tb_infosociete tb_infosociete_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_infosociete
    ADD CONSTRAINT tb_infosociete_pkey PRIMARY KEY (id);


--
-- TOC entry 5443 (class 2606 OID 18657)
-- Name: tb_inventaire tb_inventaire_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_inventaire
    ADD CONSTRAINT tb_inventaire_pkey PRIMARY KEY (id);


--
-- TOC entry 5446 (class 2606 OID 18659)
-- Name: tb_inventaire_temporaire tb_inventaire_temporaire_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_inventaire_temporaire
    ADD CONSTRAINT tb_inventaire_temporaire_pkey PRIMARY KEY (id);


--
-- TOC entry 5448 (class 2606 OID 18661)
-- Name: tb_livraisoncli tb_livraisoncli_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_livraisoncli
    ADD CONSTRAINT tb_livraisoncli_pkey PRIMARY KEY (idlivcli);


--
-- TOC entry 5450 (class 2606 OID 18663)
-- Name: tb_livraisonfrs tb_livraisonfrs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_livraisonfrs
    ADD CONSTRAINT tb_livraisonfrs_pkey PRIMARY KEY (idlivfrs);


--
-- TOC entry 5452 (class 2606 OID 18665)
-- Name: tb_log_stock tb_log_stock_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_log_stock
    ADD CONSTRAINT tb_log_stock_pkey PRIMARY KEY (id);


--
-- TOC entry 5454 (class 2606 OID 18667)
-- Name: tb_lot_peremption tb_lot_peremption_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_lot_peremption
    ADD CONSTRAINT tb_lot_peremption_pkey PRIMARY KEY (id);


--
-- TOC entry 5456 (class 2606 OID 18669)
-- Name: tb_magasin tb_magasin_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_magasin
    ADD CONSTRAINT tb_magasin_pkey PRIMARY KEY (idmag);


--
-- TOC entry 5458 (class 2606 OID 18671)
-- Name: tb_menu tb_menu_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_menu
    ADD CONSTRAINT tb_menu_pkey PRIMARY KEY (id);


--
-- TOC entry 5460 (class 2606 OID 18673)
-- Name: tb_modepaiement tb_modepaiement_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_modepaiement
    ADD CONSTRAINT tb_modepaiement_pkey PRIMARY KEY (idmode);


--
-- TOC entry 5462 (class 2606 OID 18675)
-- Name: tb_paiement tb_paiement_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_paiement
    ADD CONSTRAINT tb_paiement_pkey PRIMARY KEY (idpaiement);


--
-- TOC entry 5464 (class 2606 OID 18677)
-- Name: tb_peremption tb_peremption_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_peremption
    ADD CONSTRAINT tb_peremption_pkey PRIMARY KEY (id);


--
-- TOC entry 5466 (class 2606 OID 18679)
-- Name: tb_personnel tb_personnel_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_personnel
    ADD CONSTRAINT tb_personnel_pkey PRIMARY KEY (id);


--
-- TOC entry 5468 (class 2606 OID 18681)
-- Name: tb_pmtavoir tb_pmtavoir_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtavoir
    ADD CONSTRAINT tb_pmtavoir_pkey PRIMARY KEY (id);


--
-- TOC entry 5470 (class 2606 OID 18683)
-- Name: tb_pmtcom tb_pmtcom_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtcom
    ADD CONSTRAINT tb_pmtcom_pkey PRIMARY KEY (id);


--
-- TOC entry 5472 (class 2606 OID 18685)
-- Name: tb_pmtcredit tb_pmtcredit_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtcredit
    ADD CONSTRAINT tb_pmtcredit_pkey PRIMARY KEY (id);


--
-- TOC entry 5474 (class 2606 OID 18687)
-- Name: tb_pmtfacture tb_pmtfacture_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtfacture
    ADD CONSTRAINT tb_pmtfacture_pkey PRIMARY KEY (id);


--
-- TOC entry 5476 (class 2606 OID 18689)
-- Name: tb_pmtsalaire tb_pmtsalaire_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtsalaire
    ADD CONSTRAINT tb_pmtsalaire_pkey PRIMARY KEY (id);


--
-- TOC entry 5478 (class 2606 OID 18691)
-- Name: tb_presencepers tb_presencepers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_presencepers
    ADD CONSTRAINT tb_presencepers_pkey PRIMARY KEY (id);


--
-- TOC entry 5480 (class 2606 OID 18693)
-- Name: tb_prix tb_prix_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_prix
    ADD CONSTRAINT tb_prix_pkey PRIMARY KEY (id);


--
-- TOC entry 5482 (class 2606 OID 18695)
-- Name: tb_proforma tb_proforma_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_proforma
    ADD CONSTRAINT tb_proforma_pkey PRIMARY KEY (idprof);


--
-- TOC entry 5484 (class 2606 OID 18697)
-- Name: tb_proformadetail tb_proformadetail_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_proformadetail
    ADD CONSTRAINT tb_proformadetail_pkey PRIMARY KEY (id);


--
-- TOC entry 5486 (class 2606 OID 18699)
-- Name: tb_salairebasepers tb_salairebasepers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_salairebasepers
    ADD CONSTRAINT tb_salairebasepers_pkey PRIMARY KEY (id);


--
-- TOC entry 5488 (class 2606 OID 18701)
-- Name: tb_sortie tb_sortie_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_sortie
    ADD CONSTRAINT tb_sortie_pkey PRIMARY KEY (id);


--
-- TOC entry 5490 (class 2606 OID 18703)
-- Name: tb_sortiedetail tb_sortiedetail_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_sortiedetail
    ADD CONSTRAINT tb_sortiedetail_pkey PRIMARY KEY (id);


--
-- TOC entry 5492 (class 2606 OID 18705)
-- Name: tb_stock tb_stock_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_stock
    ADD CONSTRAINT tb_stock_pkey PRIMARY KEY (id);


--
-- TOC entry 5495 (class 2606 OID 18707)
-- Name: tb_suivipresence tb_suivipresence_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_suivipresence
    ADD CONSTRAINT tb_suivipresence_pkey PRIMARY KEY (idpresence);


--
-- TOC entry 5497 (class 2606 OID 18709)
-- Name: tb_tauxhoraire tb_tauxhoraire_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_tauxhoraire
    ADD CONSTRAINT tb_tauxhoraire_pkey PRIMARY KEY (id);


--
-- TOC entry 5499 (class 2606 OID 18711)
-- Name: tb_transfert tb_transfert_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfert
    ADD CONSTRAINT tb_transfert_pkey PRIMARY KEY (idtransfert);


--
-- TOC entry 5501 (class 2606 OID 18713)
-- Name: tb_transfertbanque tb_transfertbanque_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfertbanque
    ADD CONSTRAINT tb_transfertbanque_pkey PRIMARY KEY (id);


--
-- TOC entry 5503 (class 2606 OID 18715)
-- Name: tb_transfertcaisse tb_transfertcaisse_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfertcaisse
    ADD CONSTRAINT tb_transfertcaisse_pkey PRIMARY KEY (id);


--
-- TOC entry 5505 (class 2606 OID 18717)
-- Name: tb_transfertdetail tb_transfertdetail_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfertdetail
    ADD CONSTRAINT tb_transfertdetail_pkey PRIMARY KEY (id);


--
-- TOC entry 5507 (class 2606 OID 18719)
-- Name: tb_transporteur tb_transporteur_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transporteur
    ADD CONSTRAINT tb_transporteur_pkey PRIMARY KEY (idtransporteur);


--
-- TOC entry 5509 (class 2606 OID 18721)
-- Name: tb_typeclient tb_typeclient_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_typeclient
    ADD CONSTRAINT tb_typeclient_pkey PRIMARY KEY (idtypeclient);


--
-- TOC entry 5511 (class 2606 OID 18723)
-- Name: tb_typeoperation tb_typeoperation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_typeoperation
    ADD CONSTRAINT tb_typeoperation_pkey PRIMARY KEY (idtypeoperation);


--
-- TOC entry 5513 (class 2606 OID 18725)
-- Name: tb_typepmt tb_typepmt_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_typepmt
    ADD CONSTRAINT tb_typepmt_pkey PRIMARY KEY (idtypepmt);


--
-- TOC entry 5515 (class 2606 OID 18727)
-- Name: tb_unite tb_unite_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_unite
    ADD CONSTRAINT tb_unite_pkey PRIMARY KEY (idunite);


--
-- TOC entry 5517 (class 2606 OID 18729)
-- Name: tb_users tb_users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_users
    ADD CONSTRAINT tb_users_pkey PRIMARY KEY (iduser);


--
-- TOC entry 5519 (class 2606 OID 18731)
-- Name: tb_vente tb_vente_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_vente
    ADD CONSTRAINT tb_vente_pkey PRIMARY KEY (id);


--
-- TOC entry 5521 (class 2606 OID 18733)
-- Name: tb_ventedetail tb_ventedetail_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_ventedetail
    ADD CONSTRAINT tb_ventedetail_pkey PRIMARY KEY (id);


--
-- TOC entry 5391 (class 1259 OID 18734)
-- Name: idx_changement_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_changement_date ON public.tb_changement USING btree (datechg);


--
-- TOC entry 5392 (class 1259 OID 18735)
-- Name: idx_changement_refchg; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_changement_refchg ON public.tb_changement USING btree (refchg);


--
-- TOC entry 5393 (class 1259 OID 18736)
-- Name: idx_changement_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_changement_user ON public.tb_changement USING btree (iduser);


--
-- TOC entry 5420 (class 1259 OID 18737)
-- Name: idx_detailchange_entree_article; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_detailchange_entree_article ON public.tb_detailchange_entree USING btree (idarticle);


--
-- TOC entry 5421 (class 1259 OID 18738)
-- Name: idx_detailchange_entree_idchg; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_detailchange_entree_idchg ON public.tb_detailchange_entree USING btree (idchg);


--
-- TOC entry 5424 (class 1259 OID 18739)
-- Name: idx_detailchange_sortie_article; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_detailchange_sortie_article ON public.tb_detailchange_sortie USING btree (idarticle);


--
-- TOC entry 5425 (class 1259 OID 18740)
-- Name: idx_detailchange_sortie_idchg; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_detailchange_sortie_idchg ON public.tb_detailchange_sortie USING btree (idchg);


--
-- TOC entry 5444 (class 1259 OID 18741)
-- Name: idx_inv_temp_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_inv_temp_date ON public.tb_inventaire_temporaire USING btree (date_creation);


--
-- TOC entry 5493 (class 1259 OID 18742)
-- Name: idx_suivipresence_date_personnel; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_suivipresence_date_personnel ON public.tb_suivipresence USING btree (datepresence, idpersonnel);


--
-- TOC entry 5523 (class 2606 OID 18743)
-- Name: tb_chat fk_destinataire; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_chat
    ADD CONSTRAINT fk_destinataire FOREIGN KEY (id_destinataire) REFERENCES public.tb_users(iduser);


--
-- TOC entry 5524 (class 2606 OID 18748)
-- Name: tb_chat fk_expediteur; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_chat
    ADD CONSTRAINT fk_expediteur FOREIGN KEY (id_expediteur) REFERENCES public.tb_users(iduser);


--
-- TOC entry 5522 (class 2606 OID 18753)
-- Name: tb_avanceprof tb_avanceprof_idpers_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avanceprof
    ADD CONSTRAINT tb_avanceprof_idpers_fkey FOREIGN KEY (idpers) REFERENCES public.tb_personnel(id);


-- Completed on 2026-05-28 14:54:03

--
-- PostgreSQL database dump complete
--

\unrestrict 4ZrI12a9iOXVNrk2Med9piEANtLTNGDr9KFB54pVfBUUVjllEvAUhYpxGfKm0li

