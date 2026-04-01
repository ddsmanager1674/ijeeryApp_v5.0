--
-- PostgreSQL database dump
--

\restrict fIKjh6jTqcXSYczaU0QDHlm3DraUqWVzyE5JBseFu7fB9g4iqT7fIhPe6SqJQSr

-- Dumped from database version 16.11
-- Dumped by pg_dump version 16.11

-- Started on 2026-04-01 11:10:04

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
-- TOC entry 215 (class 1259 OID 16400)
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
-- TOC entry 216 (class 1259 OID 16403)
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
-- TOC entry 5549 (class 0 OID 0)
-- Dependencies: 216
-- Name: tb_absence_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_absence_id_seq OWNED BY public.tb_absence.id;


--
-- TOC entry 217 (class 1259 OID 16404)
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
-- TOC entry 218 (class 1259 OID 16408)
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
-- TOC entry 5550 (class 0 OID 0)
-- Dependencies: 218
-- Name: tb_article_idarticle_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_article_idarticle_seq OWNED BY public.tb_article.idarticle;


--
-- TOC entry 219 (class 1259 OID 16409)
-- Name: tb_autorisation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_autorisation (
    id integer NOT NULL,
    idfonction integer,
    idmenu integer
);


ALTER TABLE public.tb_autorisation OWNER TO postgres;

--
-- TOC entry 220 (class 1259 OID 16412)
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
-- TOC entry 5551 (class 0 OID 0)
-- Dependencies: 220
-- Name: tb_autorisation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_autorisation_id_seq OWNED BY public.tb_autorisation.id;


--
-- TOC entry 221 (class 1259 OID 16413)
-- Name: tb_autre_infos; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_autre_infos (
    id integer NOT NULL,
    intitule character varying(250) DEFAULT ''::character varying,
    valeur character varying(1000) DEFAULT ''::character varying
);


ALTER TABLE public.tb_autre_infos OWNER TO postgres;

--
-- TOC entry 222 (class 1259 OID 16420)
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
-- TOC entry 5552 (class 0 OID 0)
-- Dependencies: 222
-- Name: tb_autre_infos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_autre_infos_id_seq OWNED BY public.tb_autre_infos.id;


--
-- TOC entry 223 (class 1259 OID 16421)
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
-- TOC entry 224 (class 1259 OID 16424)
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
-- TOC entry 5553 (class 0 OID 0)
-- Dependencies: 224
-- Name: tb_autrecreance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_autrecreance_id_seq OWNED BY public.tb_autrecreance.id;


--
-- TOC entry 225 (class 1259 OID 16425)
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
-- TOC entry 226 (class 1259 OID 16429)
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
-- TOC entry 5554 (class 0 OID 0)
-- Dependencies: 226
-- Name: tb_autredette_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_autredette_id_seq OWNED BY public.tb_autredette.id;


--
-- TOC entry 227 (class 1259 OID 16430)
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
-- TOC entry 228 (class 1259 OID 16433)
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
-- TOC entry 5555 (class 0 OID 0)
-- Dependencies: 228
-- Name: tb_avancepers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_avancepers_id_seq OWNED BY public.tb_avancepers.id;


--
-- TOC entry 229 (class 1259 OID 16434)
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
-- TOC entry 230 (class 1259 OID 16437)
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
-- TOC entry 5556 (class 0 OID 0)
-- Dependencies: 230
-- Name: tb_avanceprof_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_avanceprof_id_seq OWNED BY public.tb_avanceprof.id;


--
-- TOC entry 231 (class 1259 OID 16438)
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
-- TOC entry 232 (class 1259 OID 16441)
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
-- TOC entry 5557 (class 0 OID 0)
-- Dependencies: 232
-- Name: tb_avancespecpers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_avancespecpers_id_seq OWNED BY public.tb_avancespecpers.id;


--
-- TOC entry 233 (class 1259 OID 16442)
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
-- TOC entry 234 (class 1259 OID 16446)
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
-- TOC entry 5558 (class 0 OID 0)
-- Dependencies: 234
-- Name: tb_avoir_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_avoir_id_seq OWNED BY public.tb_avoir.id;


--
-- TOC entry 235 (class 1259 OID 16447)
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
-- TOC entry 236 (class 1259 OID 16451)
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
-- TOC entry 5559 (class 0 OID 0)
-- Dependencies: 236
-- Name: tb_avoirdetail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_avoirdetail_id_seq OWNED BY public.tb_avoirdetail.id;


--
-- TOC entry 237 (class 1259 OID 16452)
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
-- TOC entry 238 (class 1259 OID 16455)
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
-- TOC entry 5560 (class 0 OID 0)
-- Dependencies: 238
-- Name: tb_banque_id_banque_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_banque_id_banque_seq OWNED BY public.tb_banque.id_banque;


--
-- TOC entry 239 (class 1259 OID 16456)
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
-- TOC entry 240 (class 1259 OID 16460)
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
-- TOC entry 5561 (class 0 OID 0)
-- Dependencies: 240
-- Name: tb_baseliste_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_baseliste_id_seq OWNED BY public.tb_baseliste.id;


--
-- TOC entry 241 (class 1259 OID 16461)
-- Name: tb_categoriearticle; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_categoriearticle (
    idca integer NOT NULL,
    designationcat character varying(150),
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_categoriearticle OWNER TO postgres;

--
-- TOC entry 242 (class 1259 OID 16465)
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
-- TOC entry 5562 (class 0 OID 0)
-- Dependencies: 242
-- Name: tb_categoriearticle_idca_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_categoriearticle_idca_seq OWNED BY public.tb_categoriearticle.idca;


--
-- TOC entry 243 (class 1259 OID 16466)
-- Name: tb_categoriecompte; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_categoriecompte (
    idcc integer NOT NULL,
    categoriecompte character varying(100)
);


ALTER TABLE public.tb_categoriecompte OWNER TO postgres;

--
-- TOC entry 244 (class 1259 OID 16469)
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
-- TOC entry 5563 (class 0 OID 0)
-- Dependencies: 244
-- Name: tb_categoriecompte_idcc_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_categoriecompte_idcc_seq OWNED BY public.tb_categoriecompte.idcc;


--
-- TOC entry 245 (class 1259 OID 16470)
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
-- TOC entry 246 (class 1259 OID 16476)
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
-- TOC entry 5564 (class 0 OID 0)
-- Dependencies: 246
-- Name: tb_changement_idchg_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_changement_idchg_seq OWNED BY public.tb_changement.idchg;


--
-- TOC entry 247 (class 1259 OID 16477)
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
-- TOC entry 248 (class 1259 OID 16484)
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
-- TOC entry 5565 (class 0 OID 0)
-- Dependencies: 248
-- Name: tb_chat_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_chat_id_seq OWNED BY public.tb_chat.id;


--
-- TOC entry 249 (class 1259 OID 16485)
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
-- TOC entry 250 (class 1259 OID 16489)
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
-- TOC entry 5566 (class 0 OID 0)
-- Dependencies: 250
-- Name: tb_client_idclient_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_client_idclient_seq OWNED BY public.tb_client.idclient;


--
-- TOC entry 251 (class 1259 OID 16490)
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
-- TOC entry 252 (class 1259 OID 16494)
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
-- TOC entry 5567 (class 0 OID 0)
-- Dependencies: 252
-- Name: tb_codeautorisation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_codeautorisation_id_seq OWNED BY public.tb_codeautorisation.id;


--
-- TOC entry 253 (class 1259 OID 16495)
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
-- TOC entry 254 (class 1259 OID 16499)
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
-- TOC entry 5568 (class 0 OID 0)
-- Dependencies: 254
-- Name: tb_commande_idcom_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_commande_idcom_seq OWNED BY public.tb_commande.idcom;


--
-- TOC entry 255 (class 1259 OID 16500)
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
-- TOC entry 256 (class 1259 OID 16504)
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
-- TOC entry 5569 (class 0 OID 0)
-- Dependencies: 256
-- Name: tb_commandedetail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_commandedetail_id_seq OWNED BY public.tb_commandedetail.id;


--
-- TOC entry 257 (class 1259 OID 16505)
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
-- TOC entry 258 (class 1259 OID 16508)
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
-- TOC entry 5570 (class 0 OID 0)
-- Dependencies: 258
-- Name: tb_configdb_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_configdb_id_seq OWNED BY public.tb_configdb.id;


--
-- TOC entry 259 (class 1259 OID 16509)
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
-- TOC entry 260 (class 1259 OID 16516)
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
-- TOC entry 261 (class 1259 OID 16522)
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
-- TOC entry 5571 (class 0 OID 0)
-- Dependencies: 261
-- Name: tb_consommationinterne_details_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_consommationinterne_details_id_seq OWNED BY public.tb_consommationinterne_details.id;


--
-- TOC entry 262 (class 1259 OID 16523)
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
-- TOC entry 5572 (class 0 OID 0)
-- Dependencies: 262
-- Name: tb_consommationinterne_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_consommationinterne_id_seq OWNED BY public.tb_consommationinterne.id;


--
-- TOC entry 263 (class 1259 OID 16524)
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
-- TOC entry 264 (class 1259 OID 16528)
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
-- TOC entry 5573 (class 0 OID 0)
-- Dependencies: 264
-- Name: tb_decaissement_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_decaissement_id_seq OWNED BY public.tb_decaissement.id;


--
-- TOC entry 265 (class 1259 OID 16529)
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
-- TOC entry 266 (class 1259 OID 16533)
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
-- TOC entry 5574 (class 0 OID 0)
-- Dependencies: 266
-- Name: tb_decaissementbq_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_decaissementbq_id_seq OWNED BY public.tb_decaissementbq.id;


--
-- TOC entry 267 (class 1259 OID 16534)
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
-- TOC entry 268 (class 1259 OID 16537)
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
-- TOC entry 5575 (class 0 OID 0)
-- Dependencies: 268
-- Name: tb_detailchange_entree_iddetail_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_detailchange_entree_iddetail_seq OWNED BY public.tb_detailchange_entree.iddetail;


--
-- TOC entry 269 (class 1259 OID 16538)
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
-- TOC entry 270 (class 1259 OID 16541)
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
-- TOC entry 5576 (class 0 OID 0)
-- Dependencies: 270
-- Name: tb_detailchange_sortie_iddetail_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_detailchange_sortie_iddetail_seq OWNED BY public.tb_detailchange_sortie.iddetail;


--
-- TOC entry 271 (class 1259 OID 16542)
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
-- TOC entry 272 (class 1259 OID 16546)
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
-- TOC entry 5577 (class 0 OID 0)
-- Dependencies: 272
-- Name: tb_encaissement_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_encaissement_id_seq OWNED BY public.tb_encaissement.id;


--
-- TOC entry 273 (class 1259 OID 16547)
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
-- TOC entry 274 (class 1259 OID 16551)
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
-- TOC entry 5578 (class 0 OID 0)
-- Dependencies: 274
-- Name: tb_encaissementbq_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_encaissementbq_id_seq OWNED BY public.tb_encaissementbq.id;


--
-- TOC entry 275 (class 1259 OID 16552)
-- Name: tb_evenement; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_evenement (
    id integer NOT NULL,
    date timestamp without time zone,
    evenements character varying(200)
);


ALTER TABLE public.tb_evenement OWNER TO postgres;

--
-- TOC entry 276 (class 1259 OID 16555)
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
-- TOC entry 5579 (class 0 OID 0)
-- Dependencies: 276
-- Name: tb_evenement_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_evenement_id_seq OWNED BY public.tb_evenement.id;


--
-- TOC entry 277 (class 1259 OID 16556)
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
-- TOC entry 278 (class 1259 OID 16559)
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
-- TOC entry 5580 (class 0 OID 0)
-- Dependencies: 278
-- Name: tb_facturecli_idfact_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_facturecli_idfact_seq OWNED BY public.tb_facturecli.idfact;


--
-- TOC entry 279 (class 1259 OID 16560)
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
-- TOC entry 280 (class 1259 OID 16564)
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
-- TOC entry 5581 (class 0 OID 0)
-- Dependencies: 280
-- Name: tb_fonction_idfonction_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_fonction_idfonction_seq OWNED BY public.tb_fonction.idfonction;


--
-- TOC entry 281 (class 1259 OID 16565)
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
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_fournisseur OWNER TO postgres;

--
-- TOC entry 282 (class 1259 OID 16569)
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
-- TOC entry 5582 (class 0 OID 0)
-- Dependencies: 282
-- Name: tb_fournisseur_idfrs_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_fournisseur_idfrs_seq OWNED BY public.tb_fournisseur.idfrs;


--
-- TOC entry 283 (class 1259 OID 16570)
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
-- TOC entry 284 (class 1259 OID 16575)
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
-- TOC entry 5583 (class 0 OID 0)
-- Dependencies: 284
-- Name: tb_infosociete_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_infosociete_id_seq OWNED BY public.tb_infosociete.id;


--
-- TOC entry 285 (class 1259 OID 16576)
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
-- TOC entry 286 (class 1259 OID 16579)
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
-- TOC entry 5584 (class 0 OID 0)
-- Dependencies: 286
-- Name: tb_inventaire_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_inventaire_id_seq OWNED BY public.tb_inventaire.id;


--
-- TOC entry 287 (class 1259 OID 16580)
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
-- TOC entry 288 (class 1259 OID 16587)
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
-- TOC entry 5585 (class 0 OID 0)
-- Dependencies: 288
-- Name: tb_inventaire_temporaire_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_inventaire_temporaire_id_seq OWNED BY public.tb_inventaire_temporaire.id;


--
-- TOC entry 289 (class 1259 OID 16588)
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
-- TOC entry 290 (class 1259 OID 16591)
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
-- TOC entry 5586 (class 0 OID 0)
-- Dependencies: 290
-- Name: tb_livraisoncli_idlivcli_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_livraisoncli_idlivcli_seq OWNED BY public.tb_livraisoncli.idlivcli;


--
-- TOC entry 291 (class 1259 OID 16592)
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
-- TOC entry 292 (class 1259 OID 16597)
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
-- TOC entry 5587 (class 0 OID 0)
-- Dependencies: 292
-- Name: tb_livraisonfrs_idlivfrs_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_livraisonfrs_idlivfrs_seq OWNED BY public.tb_livraisonfrs.idlivfrs;


--
-- TOC entry 293 (class 1259 OID 16598)
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
-- TOC entry 294 (class 1259 OID 16603)
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
-- TOC entry 5588 (class 0 OID 0)
-- Dependencies: 294
-- Name: tb_log_stock_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_log_stock_id_seq OWNED BY public.tb_log_stock.id;


--
-- TOC entry 295 (class 1259 OID 16604)
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
-- TOC entry 296 (class 1259 OID 16611)
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
-- TOC entry 5589 (class 0 OID 0)
-- Dependencies: 296
-- Name: tb_lot_peremption_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_lot_peremption_id_seq OWNED BY public.tb_lot_peremption.id;


--
-- TOC entry 297 (class 1259 OID 16612)
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
-- TOC entry 298 (class 1259 OID 16616)
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
-- TOC entry 5590 (class 0 OID 0)
-- Dependencies: 298
-- Name: tb_magasin_idmag_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_magasin_idmag_seq OWNED BY public.tb_magasin.idmag;


--
-- TOC entry 299 (class 1259 OID 16617)
-- Name: tb_menu; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_menu (
    id integer NOT NULL,
    designationmenu character varying(100),
    page character varying(50)
);


ALTER TABLE public.tb_menu OWNER TO postgres;

--
-- TOC entry 300 (class 1259 OID 16620)
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
-- TOC entry 5591 (class 0 OID 0)
-- Dependencies: 300
-- Name: tb_menu_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_menu_id_seq OWNED BY public.tb_menu.id;


--
-- TOC entry 301 (class 1259 OID 16621)
-- Name: tb_modepaiement; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_modepaiement (
    idmode integer NOT NULL,
    modedepaiement character varying(50)
);


ALTER TABLE public.tb_modepaiement OWNER TO postgres;

--
-- TOC entry 302 (class 1259 OID 16624)
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
-- TOC entry 5592 (class 0 OID 0)
-- Dependencies: 302
-- Name: tb_modepaiement_idmode_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_modepaiement_idmode_seq OWNED BY public.tb_modepaiement.idmode;


--
-- TOC entry 303 (class 1259 OID 16625)
-- Name: tb_paiement; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_paiement (
    idpaiement integer NOT NULL,
    paiement character varying(25)
);


ALTER TABLE public.tb_paiement OWNER TO postgres;

--
-- TOC entry 304 (class 1259 OID 16628)
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
-- TOC entry 5593 (class 0 OID 0)
-- Dependencies: 304
-- Name: tb_paiement_idpaiement_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_paiement_idpaiement_seq OWNED BY public.tb_paiement.idpaiement;


--
-- TOC entry 305 (class 1259 OID 16629)
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
-- TOC entry 306 (class 1259 OID 16633)
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
-- TOC entry 5594 (class 0 OID 0)
-- Dependencies: 306
-- Name: tb_peremption_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_peremption_id_seq OWNED BY public.tb_peremption.id;


--
-- TOC entry 307 (class 1259 OID 16634)
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
-- TOC entry 308 (class 1259 OID 16638)
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
-- TOC entry 5595 (class 0 OID 0)
-- Dependencies: 308
-- Name: tb_personnel_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_personnel_id_seq OWNED BY public.tb_personnel.id;


--
-- TOC entry 309 (class 1259 OID 16639)
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
-- TOC entry 310 (class 1259 OID 16643)
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
-- TOC entry 5596 (class 0 OID 0)
-- Dependencies: 310
-- Name: tb_pmtavoir_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_pmtavoir_id_seq OWNED BY public.tb_pmtavoir.id;


--
-- TOC entry 311 (class 1259 OID 16644)
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
-- TOC entry 312 (class 1259 OID 16648)
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
-- TOC entry 5597 (class 0 OID 0)
-- Dependencies: 312
-- Name: tb_pmtcom_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_pmtcom_id_seq OWNED BY public.tb_pmtcom.id;


--
-- TOC entry 313 (class 1259 OID 16649)
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
-- TOC entry 314 (class 1259 OID 16653)
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
-- TOC entry 5598 (class 0 OID 0)
-- Dependencies: 314
-- Name: tb_pmtcredit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_pmtcredit_id_seq OWNED BY public.tb_pmtcredit.id;


--
-- TOC entry 315 (class 1259 OID 16654)
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
-- TOC entry 316 (class 1259 OID 16659)
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
-- TOC entry 5599 (class 0 OID 0)
-- Dependencies: 316
-- Name: tb_pmtfacture_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_pmtfacture_id_seq OWNED BY public.tb_pmtfacture.id;


--
-- TOC entry 317 (class 1259 OID 16660)
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
-- TOC entry 318 (class 1259 OID 16665)
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
-- TOC entry 5600 (class 0 OID 0)
-- Dependencies: 318
-- Name: tb_pmtsalaire_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_pmtsalaire_id_seq OWNED BY public.tb_pmtsalaire.id;


--
-- TOC entry 319 (class 1259 OID 16666)
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
-- TOC entry 320 (class 1259 OID 16669)
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
-- TOC entry 5601 (class 0 OID 0)
-- Dependencies: 320
-- Name: tb_presencepers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_presencepers_id_seq OWNED BY public.tb_presencepers.id;


--
-- TOC entry 321 (class 1259 OID 16670)
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
-- TOC entry 322 (class 1259 OID 16674)
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
-- TOC entry 5602 (class 0 OID 0)
-- Dependencies: 322
-- Name: tb_prix_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_prix_id_seq OWNED BY public.tb_prix.id;


--
-- TOC entry 323 (class 1259 OID 16675)
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
-- TOC entry 324 (class 1259 OID 16678)
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
-- TOC entry 5603 (class 0 OID 0)
-- Dependencies: 324
-- Name: tb_proforma_idprof_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_proforma_idprof_seq OWNED BY public.tb_proforma.idprof;


--
-- TOC entry 325 (class 1259 OID 16679)
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
-- TOC entry 326 (class 1259 OID 16682)
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
-- TOC entry 5604 (class 0 OID 0)
-- Dependencies: 326
-- Name: tb_proformadetail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_proformadetail_id_seq OWNED BY public.tb_proformadetail.id;


--
-- TOC entry 327 (class 1259 OID 16683)
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
-- TOC entry 328 (class 1259 OID 16686)
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
-- TOC entry 5605 (class 0 OID 0)
-- Dependencies: 328
-- Name: tb_salairebasepers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_salairebasepers_id_seq OWNED BY public.tb_salairebasepers.id;


--
-- TOC entry 329 (class 1259 OID 16687)
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
-- TOC entry 330 (class 1259 OID 16692)
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
-- TOC entry 5606 (class 0 OID 0)
-- Dependencies: 330
-- Name: tb_sortie_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_sortie_id_seq OWNED BY public.tb_sortie.id;


--
-- TOC entry 331 (class 1259 OID 16693)
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
-- TOC entry 332 (class 1259 OID 16698)
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
-- TOC entry 5607 (class 0 OID 0)
-- Dependencies: 332
-- Name: tb_sortiedetail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_sortiedetail_id_seq OWNED BY public.tb_sortiedetail.id;


--
-- TOC entry 333 (class 1259 OID 16699)
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
-- TOC entry 334 (class 1259 OID 16703)
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
-- TOC entry 5608 (class 0 OID 0)
-- Dependencies: 334
-- Name: tb_stock_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_stock_id_seq OWNED BY public.tb_stock.id;


--
-- TOC entry 335 (class 1259 OID 16704)
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
-- TOC entry 336 (class 1259 OID 16711)
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
-- TOC entry 5609 (class 0 OID 0)
-- Dependencies: 336
-- Name: tb_suivipresence_idpresence_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_suivipresence_idpresence_seq OWNED BY public.tb_suivipresence.idpresence;


--
-- TOC entry 337 (class 1259 OID 16712)
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
-- TOC entry 338 (class 1259 OID 16715)
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
-- TOC entry 5610 (class 0 OID 0)
-- Dependencies: 338
-- Name: tb_tauxhoraire_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_tauxhoraire_id_seq OWNED BY public.tb_tauxhoraire.id;


--
-- TOC entry 339 (class 1259 OID 16716)
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
-- TOC entry 340 (class 1259 OID 16720)
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
-- TOC entry 5611 (class 0 OID 0)
-- Dependencies: 340
-- Name: tb_transfert_idtransfert_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_transfert_idtransfert_seq OWNED BY public.tb_transfert.idtransfert;


--
-- TOC entry 341 (class 1259 OID 16721)
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
-- TOC entry 342 (class 1259 OID 16724)
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
-- TOC entry 5612 (class 0 OID 0)
-- Dependencies: 342
-- Name: tb_transfertbanque_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_transfertbanque_id_seq OWNED BY public.tb_transfertbanque.id;


--
-- TOC entry 343 (class 1259 OID 16725)
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
-- TOC entry 344 (class 1259 OID 16728)
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
-- TOC entry 5613 (class 0 OID 0)
-- Dependencies: 344
-- Name: tb_transfertcaisse_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_transfertcaisse_id_seq OWNED BY public.tb_transfertcaisse.id;


--
-- TOC entry 345 (class 1259 OID 16729)
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
-- TOC entry 346 (class 1259 OID 16733)
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
-- TOC entry 5614 (class 0 OID 0)
-- Dependencies: 346
-- Name: tb_transfertdetail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_transfertdetail_id_seq OWNED BY public.tb_transfertdetail.id;


--
-- TOC entry 347 (class 1259 OID 16734)
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
-- TOC entry 348 (class 1259 OID 16735)
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
-- TOC entry 349 (class 1259 OID 16740)
-- Name: tb_typeclient; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_typeclient (
    idtypeclient integer NOT NULL,
    designationtypeclient character varying(25)
);


ALTER TABLE public.tb_typeclient OWNER TO postgres;

--
-- TOC entry 350 (class 1259 OID 16743)
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
-- TOC entry 5615 (class 0 OID 0)
-- Dependencies: 350
-- Name: tb_typeclient_idtypeclient_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_typeclient_idtypeclient_seq OWNED BY public.tb_typeclient.idtypeclient;


--
-- TOC entry 351 (class 1259 OID 16744)
-- Name: tb_typeoperation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_typeoperation (
    idtypeoperation integer NOT NULL,
    typeoperation character varying(3)
);


ALTER TABLE public.tb_typeoperation OWNER TO postgres;

--
-- TOC entry 352 (class 1259 OID 16747)
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
-- TOC entry 5616 (class 0 OID 0)
-- Dependencies: 352
-- Name: tb_typeoperation_idtypeoperation_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_typeoperation_idtypeoperation_seq OWNED BY public.tb_typeoperation.idtypeoperation;


--
-- TOC entry 353 (class 1259 OID 16748)
-- Name: tb_typepmt; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tb_typepmt (
    idtypepmt integer NOT NULL,
    typepmt character varying(50),
    deleted integer DEFAULT 0
);


ALTER TABLE public.tb_typepmt OWNER TO postgres;

--
-- TOC entry 354 (class 1259 OID 16752)
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
-- TOC entry 5617 (class 0 OID 0)
-- Dependencies: 354
-- Name: tb_typepmt_idtypepmt_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_typepmt_idtypepmt_seq OWNED BY public.tb_typepmt.idtypepmt;


--
-- TOC entry 355 (class 1259 OID 16753)
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
-- TOC entry 356 (class 1259 OID 16757)
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
-- TOC entry 5618 (class 0 OID 0)
-- Dependencies: 356
-- Name: tb_unite_idunite_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_unite_idunite_seq OWNED BY public.tb_unite.idunite;


--
-- TOC entry 357 (class 1259 OID 16758)
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
-- TOC entry 358 (class 1259 OID 16762)
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
-- TOC entry 5619 (class 0 OID 0)
-- Dependencies: 358
-- Name: tb_users_iduser_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_users_iduser_seq OWNED BY public.tb_users.iduser;


--
-- TOC entry 359 (class 1259 OID 16763)
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
-- TOC entry 360 (class 1259 OID 16768)
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
-- TOC entry 5620 (class 0 OID 0)
-- Dependencies: 360
-- Name: tb_vente_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_vente_id_seq OWNED BY public.tb_vente.id;


--
-- TOC entry 361 (class 1259 OID 16769)
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
-- TOC entry 362 (class 1259 OID 16775)
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
-- TOC entry 5621 (class 0 OID 0)
-- Dependencies: 362
-- Name: tb_ventedetail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tb_ventedetail_id_seq OWNED BY public.tb_ventedetail.id;


--
-- TOC entry 5100 (class 2604 OID 16776)
-- Name: tb_absence id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_absence ALTER COLUMN id SET DEFAULT nextval('public.tb_absence_id_seq'::regclass);


--
-- TOC entry 5101 (class 2604 OID 16777)
-- Name: tb_article idarticle; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_article ALTER COLUMN idarticle SET DEFAULT nextval('public.tb_article_idarticle_seq'::regclass);


--
-- TOC entry 5103 (class 2604 OID 16778)
-- Name: tb_autorisation id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autorisation ALTER COLUMN id SET DEFAULT nextval('public.tb_autorisation_id_seq'::regclass);


--
-- TOC entry 5104 (class 2604 OID 16779)
-- Name: tb_autre_infos id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autre_infos ALTER COLUMN id SET DEFAULT nextval('public.tb_autre_infos_id_seq'::regclass);


--
-- TOC entry 5107 (class 2604 OID 16780)
-- Name: tb_autrecreance id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autrecreance ALTER COLUMN id SET DEFAULT nextval('public.tb_autrecreance_id_seq'::regclass);


--
-- TOC entry 5108 (class 2604 OID 16781)
-- Name: tb_autredette id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autredette ALTER COLUMN id SET DEFAULT nextval('public.tb_autredette_id_seq'::regclass);


--
-- TOC entry 5110 (class 2604 OID 16782)
-- Name: tb_avancepers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avancepers ALTER COLUMN id SET DEFAULT nextval('public.tb_avancepers_id_seq'::regclass);


--
-- TOC entry 5111 (class 2604 OID 16783)
-- Name: tb_avanceprof id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avanceprof ALTER COLUMN id SET DEFAULT nextval('public.tb_avanceprof_id_seq'::regclass);


--
-- TOC entry 5112 (class 2604 OID 16784)
-- Name: tb_avancespecpers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avancespecpers ALTER COLUMN id SET DEFAULT nextval('public.tb_avancespecpers_id_seq'::regclass);


--
-- TOC entry 5113 (class 2604 OID 16785)
-- Name: tb_avoir id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avoir ALTER COLUMN id SET DEFAULT nextval('public.tb_avoir_id_seq'::regclass);


--
-- TOC entry 5115 (class 2604 OID 16786)
-- Name: tb_avoirdetail id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avoirdetail ALTER COLUMN id SET DEFAULT nextval('public.tb_avoirdetail_id_seq'::regclass);


--
-- TOC entry 5117 (class 2604 OID 16787)
-- Name: tb_banque id_banque; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_banque ALTER COLUMN id_banque SET DEFAULT nextval('public.tb_banque_id_banque_seq'::regclass);


--
-- TOC entry 5118 (class 2604 OID 16788)
-- Name: tb_baseliste id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_baseliste ALTER COLUMN id SET DEFAULT nextval('public.tb_baseliste_id_seq'::regclass);


--
-- TOC entry 5120 (class 2604 OID 16789)
-- Name: tb_categoriearticle idca; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_categoriearticle ALTER COLUMN idca SET DEFAULT nextval('public.tb_categoriearticle_idca_seq'::regclass);


--
-- TOC entry 5122 (class 2604 OID 16790)
-- Name: tb_categoriecompte idcc; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_categoriecompte ALTER COLUMN idcc SET DEFAULT nextval('public.tb_categoriecompte_idcc_seq'::regclass);


--
-- TOC entry 5123 (class 2604 OID 16791)
-- Name: tb_changement idchg; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_changement ALTER COLUMN idchg SET DEFAULT nextval('public.tb_changement_idchg_seq'::regclass);


--
-- TOC entry 5125 (class 2604 OID 16792)
-- Name: tb_chat id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_chat ALTER COLUMN id SET DEFAULT nextval('public.tb_chat_id_seq'::regclass);


--
-- TOC entry 5128 (class 2604 OID 16793)
-- Name: tb_client idclient; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_client ALTER COLUMN idclient SET DEFAULT nextval('public.tb_client_idclient_seq'::regclass);


--
-- TOC entry 5130 (class 2604 OID 16794)
-- Name: tb_codeautorisation id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_codeautorisation ALTER COLUMN id SET DEFAULT nextval('public.tb_codeautorisation_id_seq'::regclass);


--
-- TOC entry 5132 (class 2604 OID 16795)
-- Name: tb_commande idcom; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_commande ALTER COLUMN idcom SET DEFAULT nextval('public.tb_commande_idcom_seq'::regclass);


--
-- TOC entry 5134 (class 2604 OID 16796)
-- Name: tb_commandedetail id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_commandedetail ALTER COLUMN id SET DEFAULT nextval('public.tb_commandedetail_id_seq'::regclass);


--
-- TOC entry 5136 (class 2604 OID 16797)
-- Name: tb_configdb id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_configdb ALTER COLUMN id SET DEFAULT nextval('public.tb_configdb_id_seq'::regclass);


--
-- TOC entry 5137 (class 2604 OID 16798)
-- Name: tb_consommationinterne id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_consommationinterne ALTER COLUMN id SET DEFAULT nextval('public.tb_consommationinterne_id_seq'::regclass);


--
-- TOC entry 5140 (class 2604 OID 16799)
-- Name: tb_consommationinterne_details id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_consommationinterne_details ALTER COLUMN id SET DEFAULT nextval('public.tb_consommationinterne_details_id_seq'::regclass);


--
-- TOC entry 5142 (class 2604 OID 16800)
-- Name: tb_decaissement id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_decaissement ALTER COLUMN id SET DEFAULT nextval('public.tb_decaissement_id_seq'::regclass);


--
-- TOC entry 5144 (class 2604 OID 16801)
-- Name: tb_decaissementbq id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_decaissementbq ALTER COLUMN id SET DEFAULT nextval('public.tb_decaissementbq_id_seq'::regclass);


--
-- TOC entry 5146 (class 2604 OID 16802)
-- Name: tb_detailchange_entree iddetail; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_detailchange_entree ALTER COLUMN iddetail SET DEFAULT nextval('public.tb_detailchange_entree_iddetail_seq'::regclass);


--
-- TOC entry 5147 (class 2604 OID 16803)
-- Name: tb_detailchange_sortie iddetail; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_detailchange_sortie ALTER COLUMN iddetail SET DEFAULT nextval('public.tb_detailchange_sortie_iddetail_seq'::regclass);


--
-- TOC entry 5148 (class 2604 OID 16804)
-- Name: tb_encaissement id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_encaissement ALTER COLUMN id SET DEFAULT nextval('public.tb_encaissement_id_seq'::regclass);


--
-- TOC entry 5150 (class 2604 OID 16805)
-- Name: tb_encaissementbq id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_encaissementbq ALTER COLUMN id SET DEFAULT nextval('public.tb_encaissementbq_id_seq'::regclass);


--
-- TOC entry 5152 (class 2604 OID 16806)
-- Name: tb_evenement id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_evenement ALTER COLUMN id SET DEFAULT nextval('public.tb_evenement_id_seq'::regclass);


--
-- TOC entry 5153 (class 2604 OID 16807)
-- Name: tb_facturecli idfact; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_facturecli ALTER COLUMN idfact SET DEFAULT nextval('public.tb_facturecli_idfact_seq'::regclass);


--
-- TOC entry 5154 (class 2604 OID 16808)
-- Name: tb_fonction idfonction; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_fonction ALTER COLUMN idfonction SET DEFAULT nextval('public.tb_fonction_idfonction_seq'::regclass);


--
-- TOC entry 5156 (class 2604 OID 16809)
-- Name: tb_fournisseur idfrs; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_fournisseur ALTER COLUMN idfrs SET DEFAULT nextval('public.tb_fournisseur_idfrs_seq'::regclass);


--
-- TOC entry 5158 (class 2604 OID 16810)
-- Name: tb_infosociete id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_infosociete ALTER COLUMN id SET DEFAULT nextval('public.tb_infosociete_id_seq'::regclass);


--
-- TOC entry 5159 (class 2604 OID 16811)
-- Name: tb_inventaire id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_inventaire ALTER COLUMN id SET DEFAULT nextval('public.tb_inventaire_id_seq'::regclass);


--
-- TOC entry 5160 (class 2604 OID 16812)
-- Name: tb_inventaire_temporaire id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_inventaire_temporaire ALTER COLUMN id SET DEFAULT nextval('public.tb_inventaire_temporaire_id_seq'::regclass);


--
-- TOC entry 5165 (class 2604 OID 16813)
-- Name: tb_livraisoncli idlivcli; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_livraisoncli ALTER COLUMN idlivcli SET DEFAULT nextval('public.tb_livraisoncli_idlivcli_seq'::regclass);


--
-- TOC entry 5166 (class 2604 OID 16814)
-- Name: tb_livraisonfrs idlivfrs; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_livraisonfrs ALTER COLUMN idlivfrs SET DEFAULT nextval('public.tb_livraisonfrs_idlivfrs_seq'::regclass);


--
-- TOC entry 5169 (class 2604 OID 16815)
-- Name: tb_log_stock id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_log_stock ALTER COLUMN id SET DEFAULT nextval('public.tb_log_stock_id_seq'::regclass);


--
-- TOC entry 5172 (class 2604 OID 16816)
-- Name: tb_lot_peremption id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_lot_peremption ALTER COLUMN id SET DEFAULT nextval('public.tb_lot_peremption_id_seq'::regclass);


--
-- TOC entry 5175 (class 2604 OID 16817)
-- Name: tb_magasin idmag; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_magasin ALTER COLUMN idmag SET DEFAULT nextval('public.tb_magasin_idmag_seq'::regclass);


--
-- TOC entry 5177 (class 2604 OID 16818)
-- Name: tb_menu id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_menu ALTER COLUMN id SET DEFAULT nextval('public.tb_menu_id_seq'::regclass);


--
-- TOC entry 5178 (class 2604 OID 16819)
-- Name: tb_modepaiement idmode; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_modepaiement ALTER COLUMN idmode SET DEFAULT nextval('public.tb_modepaiement_idmode_seq'::regclass);


--
-- TOC entry 5179 (class 2604 OID 16820)
-- Name: tb_paiement idpaiement; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_paiement ALTER COLUMN idpaiement SET DEFAULT nextval('public.tb_paiement_idpaiement_seq'::regclass);


--
-- TOC entry 5180 (class 2604 OID 16821)
-- Name: tb_peremption id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_peremption ALTER COLUMN id SET DEFAULT nextval('public.tb_peremption_id_seq'::regclass);


--
-- TOC entry 5182 (class 2604 OID 16822)
-- Name: tb_personnel id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_personnel ALTER COLUMN id SET DEFAULT nextval('public.tb_personnel_id_seq'::regclass);


--
-- TOC entry 5184 (class 2604 OID 16823)
-- Name: tb_pmtavoir id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtavoir ALTER COLUMN id SET DEFAULT nextval('public.tb_pmtavoir_id_seq'::regclass);


--
-- TOC entry 5186 (class 2604 OID 16824)
-- Name: tb_pmtcom id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtcom ALTER COLUMN id SET DEFAULT nextval('public.tb_pmtcom_id_seq'::regclass);


--
-- TOC entry 5188 (class 2604 OID 16825)
-- Name: tb_pmtcredit id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtcredit ALTER COLUMN id SET DEFAULT nextval('public.tb_pmtcredit_id_seq'::regclass);


--
-- TOC entry 5190 (class 2604 OID 16826)
-- Name: tb_pmtfacture id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtfacture ALTER COLUMN id SET DEFAULT nextval('public.tb_pmtfacture_id_seq'::regclass);


--
-- TOC entry 5193 (class 2604 OID 16827)
-- Name: tb_pmtsalaire id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtsalaire ALTER COLUMN id SET DEFAULT nextval('public.tb_pmtsalaire_id_seq'::regclass);


--
-- TOC entry 5196 (class 2604 OID 16828)
-- Name: tb_presencepers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_presencepers ALTER COLUMN id SET DEFAULT nextval('public.tb_presencepers_id_seq'::regclass);


--
-- TOC entry 5197 (class 2604 OID 16829)
-- Name: tb_prix id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_prix ALTER COLUMN id SET DEFAULT nextval('public.tb_prix_id_seq'::regclass);


--
-- TOC entry 5199 (class 2604 OID 16830)
-- Name: tb_proforma idprof; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_proforma ALTER COLUMN idprof SET DEFAULT nextval('public.tb_proforma_idprof_seq'::regclass);


--
-- TOC entry 5200 (class 2604 OID 16831)
-- Name: tb_proformadetail id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_proformadetail ALTER COLUMN id SET DEFAULT nextval('public.tb_proformadetail_id_seq'::regclass);


--
-- TOC entry 5201 (class 2604 OID 16832)
-- Name: tb_salairebasepers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_salairebasepers ALTER COLUMN id SET DEFAULT nextval('public.tb_salairebasepers_id_seq'::regclass);


--
-- TOC entry 5202 (class 2604 OID 16833)
-- Name: tb_sortie id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_sortie ALTER COLUMN id SET DEFAULT nextval('public.tb_sortie_id_seq'::regclass);


--
-- TOC entry 5205 (class 2604 OID 16834)
-- Name: tb_sortiedetail id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_sortiedetail ALTER COLUMN id SET DEFAULT nextval('public.tb_sortiedetail_id_seq'::regclass);


--
-- TOC entry 5208 (class 2604 OID 16835)
-- Name: tb_stock id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_stock ALTER COLUMN id SET DEFAULT nextval('public.tb_stock_id_seq'::regclass);


--
-- TOC entry 5210 (class 2604 OID 16836)
-- Name: tb_suivipresence idpresence; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_suivipresence ALTER COLUMN idpresence SET DEFAULT nextval('public.tb_suivipresence_idpresence_seq'::regclass);


--
-- TOC entry 5215 (class 2604 OID 16837)
-- Name: tb_tauxhoraire id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_tauxhoraire ALTER COLUMN id SET DEFAULT nextval('public.tb_tauxhoraire_id_seq'::regclass);


--
-- TOC entry 5216 (class 2604 OID 16838)
-- Name: tb_transfert idtransfert; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfert ALTER COLUMN idtransfert SET DEFAULT nextval('public.tb_transfert_idtransfert_seq'::regclass);


--
-- TOC entry 5218 (class 2604 OID 16839)
-- Name: tb_transfertbanque id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfertbanque ALTER COLUMN id SET DEFAULT nextval('public.tb_transfertbanque_id_seq'::regclass);


--
-- TOC entry 5219 (class 2604 OID 16840)
-- Name: tb_transfertcaisse id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfertcaisse ALTER COLUMN id SET DEFAULT nextval('public.tb_transfertcaisse_id_seq'::regclass);


--
-- TOC entry 5220 (class 2604 OID 16841)
-- Name: tb_transfertdetail id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfertdetail ALTER COLUMN id SET DEFAULT nextval('public.tb_transfertdetail_id_seq'::regclass);


--
-- TOC entry 5224 (class 2604 OID 16842)
-- Name: tb_typeclient idtypeclient; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_typeclient ALTER COLUMN idtypeclient SET DEFAULT nextval('public.tb_typeclient_idtypeclient_seq'::regclass);


--
-- TOC entry 5225 (class 2604 OID 16843)
-- Name: tb_typeoperation idtypeoperation; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_typeoperation ALTER COLUMN idtypeoperation SET DEFAULT nextval('public.tb_typeoperation_idtypeoperation_seq'::regclass);


--
-- TOC entry 5226 (class 2604 OID 16844)
-- Name: tb_typepmt idtypepmt; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_typepmt ALTER COLUMN idtypepmt SET DEFAULT nextval('public.tb_typepmt_idtypepmt_seq'::regclass);


--
-- TOC entry 5228 (class 2604 OID 16845)
-- Name: tb_unite idunite; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_unite ALTER COLUMN idunite SET DEFAULT nextval('public.tb_unite_idunite_seq'::regclass);


--
-- TOC entry 5230 (class 2604 OID 16846)
-- Name: tb_users iduser; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_users ALTER COLUMN iduser SET DEFAULT nextval('public.tb_users_iduser_seq'::regclass);


--
-- TOC entry 5232 (class 2604 OID 16847)
-- Name: tb_vente id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_vente ALTER COLUMN id SET DEFAULT nextval('public.tb_vente_id_seq'::regclass);


--
-- TOC entry 5235 (class 2604 OID 16848)
-- Name: tb_ventedetail id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_ventedetail ALTER COLUMN id SET DEFAULT nextval('public.tb_ventedetail_id_seq'::regclass);


--
-- TOC entry 5238 (class 2606 OID 16850)
-- Name: tb_absence tb_absence_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_absence
    ADD CONSTRAINT tb_absence_pkey PRIMARY KEY (id);


--
-- TOC entry 5240 (class 2606 OID 16852)
-- Name: tb_article tb_article_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_article
    ADD CONSTRAINT tb_article_pkey PRIMARY KEY (idarticle);


--
-- TOC entry 5242 (class 2606 OID 16854)
-- Name: tb_autorisation tb_autorisation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autorisation
    ADD CONSTRAINT tb_autorisation_pkey PRIMARY KEY (id);


--
-- TOC entry 5244 (class 2606 OID 16856)
-- Name: tb_autre_infos tb_autre_infos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autre_infos
    ADD CONSTRAINT tb_autre_infos_pkey PRIMARY KEY (id);


--
-- TOC entry 5246 (class 2606 OID 16858)
-- Name: tb_autrecreance tb_autrecreance_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autrecreance
    ADD CONSTRAINT tb_autrecreance_pkey PRIMARY KEY (id);


--
-- TOC entry 5248 (class 2606 OID 16860)
-- Name: tb_autredette tb_autredette_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_autredette
    ADD CONSTRAINT tb_autredette_pkey PRIMARY KEY (id);


--
-- TOC entry 5250 (class 2606 OID 16862)
-- Name: tb_avancepers tb_avancepers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avancepers
    ADD CONSTRAINT tb_avancepers_pkey PRIMARY KEY (id);


--
-- TOC entry 5252 (class 2606 OID 16864)
-- Name: tb_avanceprof tb_avanceprof_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avanceprof
    ADD CONSTRAINT tb_avanceprof_pkey PRIMARY KEY (id);


--
-- TOC entry 5254 (class 2606 OID 16866)
-- Name: tb_avancespecpers tb_avancespecpers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avancespecpers
    ADD CONSTRAINT tb_avancespecpers_pkey PRIMARY KEY (id);


--
-- TOC entry 5256 (class 2606 OID 16868)
-- Name: tb_avoir tb_avoir_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avoir
    ADD CONSTRAINT tb_avoir_pkey PRIMARY KEY (id);


--
-- TOC entry 5258 (class 2606 OID 16870)
-- Name: tb_avoirdetail tb_avoirdetail_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avoirdetail
    ADD CONSTRAINT tb_avoirdetail_pkey PRIMARY KEY (id);


--
-- TOC entry 5260 (class 2606 OID 16872)
-- Name: tb_banque tb_banque_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_banque
    ADD CONSTRAINT tb_banque_pkey PRIMARY KEY (id_banque);


--
-- TOC entry 5262 (class 2606 OID 16874)
-- Name: tb_baseliste tb_baseliste_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_baseliste
    ADD CONSTRAINT tb_baseliste_pkey PRIMARY KEY (id);


--
-- TOC entry 5264 (class 2606 OID 16876)
-- Name: tb_categoriearticle tb_categoriearticle_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_categoriearticle
    ADD CONSTRAINT tb_categoriearticle_pkey PRIMARY KEY (idca);


--
-- TOC entry 5266 (class 2606 OID 16878)
-- Name: tb_categoriecompte tb_categoriecompte_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_categoriecompte
    ADD CONSTRAINT tb_categoriecompte_pkey PRIMARY KEY (idcc);


--
-- TOC entry 5271 (class 2606 OID 16880)
-- Name: tb_changement tb_changement_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_changement
    ADD CONSTRAINT tb_changement_pkey PRIMARY KEY (idchg);


--
-- TOC entry 5273 (class 2606 OID 16882)
-- Name: tb_changement tb_changement_refchg_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_changement
    ADD CONSTRAINT tb_changement_refchg_key UNIQUE (refchg);


--
-- TOC entry 5275 (class 2606 OID 16884)
-- Name: tb_chat tb_chat_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_chat
    ADD CONSTRAINT tb_chat_pkey PRIMARY KEY (id);


--
-- TOC entry 5277 (class 2606 OID 16886)
-- Name: tb_client tb_client_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_client
    ADD CONSTRAINT tb_client_pkey PRIMARY KEY (idclient);


--
-- TOC entry 5279 (class 2606 OID 16888)
-- Name: tb_codeautorisation tb_codeautorisation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_codeautorisation
    ADD CONSTRAINT tb_codeautorisation_pkey PRIMARY KEY (id);


--
-- TOC entry 5281 (class 2606 OID 16890)
-- Name: tb_commande tb_commande_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_commande
    ADD CONSTRAINT tb_commande_pkey PRIMARY KEY (idcom);


--
-- TOC entry 5283 (class 2606 OID 16892)
-- Name: tb_commandedetail tb_commandedetail_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_commandedetail
    ADD CONSTRAINT tb_commandedetail_pkey PRIMARY KEY (id);


--
-- TOC entry 5285 (class 2606 OID 16894)
-- Name: tb_configdb tb_configdb_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_configdb
    ADD CONSTRAINT tb_configdb_pkey PRIMARY KEY (id);


--
-- TOC entry 5291 (class 2606 OID 16896)
-- Name: tb_consommationinterne_details tb_consommationinterne_details_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_consommationinterne_details
    ADD CONSTRAINT tb_consommationinterne_details_pkey PRIMARY KEY (id);


--
-- TOC entry 5287 (class 2606 OID 16898)
-- Name: tb_consommationinterne tb_consommationinterne_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_consommationinterne
    ADD CONSTRAINT tb_consommationinterne_pkey PRIMARY KEY (id);


--
-- TOC entry 5289 (class 2606 OID 16900)
-- Name: tb_consommationinterne tb_consommationinterne_refconsommation_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_consommationinterne
    ADD CONSTRAINT tb_consommationinterne_refconsommation_key UNIQUE (refconsommation);


--
-- TOC entry 5293 (class 2606 OID 16902)
-- Name: tb_decaissement tb_decaissement_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_decaissement
    ADD CONSTRAINT tb_decaissement_pkey PRIMARY KEY (id);


--
-- TOC entry 5295 (class 2606 OID 16904)
-- Name: tb_decaissementbq tb_decaissementbq_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_decaissementbq
    ADD CONSTRAINT tb_decaissementbq_pkey PRIMARY KEY (id);


--
-- TOC entry 5299 (class 2606 OID 16906)
-- Name: tb_detailchange_entree tb_detailchange_entree_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_detailchange_entree
    ADD CONSTRAINT tb_detailchange_entree_pkey PRIMARY KEY (iddetail);


--
-- TOC entry 5303 (class 2606 OID 16908)
-- Name: tb_detailchange_sortie tb_detailchange_sortie_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_detailchange_sortie
    ADD CONSTRAINT tb_detailchange_sortie_pkey PRIMARY KEY (iddetail);


--
-- TOC entry 5305 (class 2606 OID 16910)
-- Name: tb_encaissement tb_encaissement_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_encaissement
    ADD CONSTRAINT tb_encaissement_pkey PRIMARY KEY (id);


--
-- TOC entry 5307 (class 2606 OID 16912)
-- Name: tb_encaissementbq tb_encaissementbq_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_encaissementbq
    ADD CONSTRAINT tb_encaissementbq_pkey PRIMARY KEY (id);


--
-- TOC entry 5309 (class 2606 OID 16914)
-- Name: tb_evenement tb_evenement_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_evenement
    ADD CONSTRAINT tb_evenement_pkey PRIMARY KEY (id);


--
-- TOC entry 5311 (class 2606 OID 16916)
-- Name: tb_facturecli tb_facturecli_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_facturecli
    ADD CONSTRAINT tb_facturecli_pkey PRIMARY KEY (idfact);


--
-- TOC entry 5313 (class 2606 OID 16918)
-- Name: tb_fonction tb_fonction_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_fonction
    ADD CONSTRAINT tb_fonction_pkey PRIMARY KEY (idfonction);


--
-- TOC entry 5315 (class 2606 OID 16920)
-- Name: tb_fournisseur tb_fournisseur_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_fournisseur
    ADD CONSTRAINT tb_fournisseur_pkey PRIMARY KEY (idfrs);


--
-- TOC entry 5317 (class 2606 OID 16922)
-- Name: tb_infosociete tb_infosociete_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_infosociete
    ADD CONSTRAINT tb_infosociete_pkey PRIMARY KEY (id);


--
-- TOC entry 5319 (class 2606 OID 16924)
-- Name: tb_inventaire tb_inventaire_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_inventaire
    ADD CONSTRAINT tb_inventaire_pkey PRIMARY KEY (id);


--
-- TOC entry 5322 (class 2606 OID 16926)
-- Name: tb_inventaire_temporaire tb_inventaire_temporaire_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_inventaire_temporaire
    ADD CONSTRAINT tb_inventaire_temporaire_pkey PRIMARY KEY (id);


--
-- TOC entry 5324 (class 2606 OID 16928)
-- Name: tb_livraisoncli tb_livraisoncli_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_livraisoncli
    ADD CONSTRAINT tb_livraisoncli_pkey PRIMARY KEY (idlivcli);


--
-- TOC entry 5326 (class 2606 OID 16930)
-- Name: tb_livraisonfrs tb_livraisonfrs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_livraisonfrs
    ADD CONSTRAINT tb_livraisonfrs_pkey PRIMARY KEY (idlivfrs);


--
-- TOC entry 5328 (class 2606 OID 16932)
-- Name: tb_log_stock tb_log_stock_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_log_stock
    ADD CONSTRAINT tb_log_stock_pkey PRIMARY KEY (id);


--
-- TOC entry 5330 (class 2606 OID 16934)
-- Name: tb_lot_peremption tb_lot_peremption_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_lot_peremption
    ADD CONSTRAINT tb_lot_peremption_pkey PRIMARY KEY (id);


--
-- TOC entry 5332 (class 2606 OID 16936)
-- Name: tb_magasin tb_magasin_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_magasin
    ADD CONSTRAINT tb_magasin_pkey PRIMARY KEY (idmag);


--
-- TOC entry 5334 (class 2606 OID 16938)
-- Name: tb_menu tb_menu_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_menu
    ADD CONSTRAINT tb_menu_pkey PRIMARY KEY (id);


--
-- TOC entry 5336 (class 2606 OID 16940)
-- Name: tb_modepaiement tb_modepaiement_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_modepaiement
    ADD CONSTRAINT tb_modepaiement_pkey PRIMARY KEY (idmode);


--
-- TOC entry 5338 (class 2606 OID 16942)
-- Name: tb_paiement tb_paiement_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_paiement
    ADD CONSTRAINT tb_paiement_pkey PRIMARY KEY (idpaiement);


--
-- TOC entry 5340 (class 2606 OID 16944)
-- Name: tb_peremption tb_peremption_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_peremption
    ADD CONSTRAINT tb_peremption_pkey PRIMARY KEY (id);


--
-- TOC entry 5342 (class 2606 OID 16946)
-- Name: tb_personnel tb_personnel_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_personnel
    ADD CONSTRAINT tb_personnel_pkey PRIMARY KEY (id);


--
-- TOC entry 5344 (class 2606 OID 16948)
-- Name: tb_pmtavoir tb_pmtavoir_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtavoir
    ADD CONSTRAINT tb_pmtavoir_pkey PRIMARY KEY (id);


--
-- TOC entry 5346 (class 2606 OID 16950)
-- Name: tb_pmtcom tb_pmtcom_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtcom
    ADD CONSTRAINT tb_pmtcom_pkey PRIMARY KEY (id);


--
-- TOC entry 5348 (class 2606 OID 16952)
-- Name: tb_pmtcredit tb_pmtcredit_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtcredit
    ADD CONSTRAINT tb_pmtcredit_pkey PRIMARY KEY (id);


--
-- TOC entry 5350 (class 2606 OID 16954)
-- Name: tb_pmtfacture tb_pmtfacture_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtfacture
    ADD CONSTRAINT tb_pmtfacture_pkey PRIMARY KEY (id);


--
-- TOC entry 5352 (class 2606 OID 16956)
-- Name: tb_pmtsalaire tb_pmtsalaire_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_pmtsalaire
    ADD CONSTRAINT tb_pmtsalaire_pkey PRIMARY KEY (id);


--
-- TOC entry 5354 (class 2606 OID 16958)
-- Name: tb_presencepers tb_presencepers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_presencepers
    ADD CONSTRAINT tb_presencepers_pkey PRIMARY KEY (id);


--
-- TOC entry 5356 (class 2606 OID 16960)
-- Name: tb_prix tb_prix_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_prix
    ADD CONSTRAINT tb_prix_pkey PRIMARY KEY (id);


--
-- TOC entry 5358 (class 2606 OID 16962)
-- Name: tb_proforma tb_proforma_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_proforma
    ADD CONSTRAINT tb_proforma_pkey PRIMARY KEY (idprof);


--
-- TOC entry 5360 (class 2606 OID 16964)
-- Name: tb_proformadetail tb_proformadetail_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_proformadetail
    ADD CONSTRAINT tb_proformadetail_pkey PRIMARY KEY (id);


--
-- TOC entry 5362 (class 2606 OID 16966)
-- Name: tb_salairebasepers tb_salairebasepers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_salairebasepers
    ADD CONSTRAINT tb_salairebasepers_pkey PRIMARY KEY (id);


--
-- TOC entry 5364 (class 2606 OID 16968)
-- Name: tb_sortie tb_sortie_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_sortie
    ADD CONSTRAINT tb_sortie_pkey PRIMARY KEY (id);


--
-- TOC entry 5366 (class 2606 OID 16970)
-- Name: tb_sortiedetail tb_sortiedetail_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_sortiedetail
    ADD CONSTRAINT tb_sortiedetail_pkey PRIMARY KEY (id);


--
-- TOC entry 5368 (class 2606 OID 16972)
-- Name: tb_stock tb_stock_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_stock
    ADD CONSTRAINT tb_stock_pkey PRIMARY KEY (id);


--
-- TOC entry 5371 (class 2606 OID 16974)
-- Name: tb_suivipresence tb_suivipresence_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_suivipresence
    ADD CONSTRAINT tb_suivipresence_pkey PRIMARY KEY (idpresence);


--
-- TOC entry 5373 (class 2606 OID 16976)
-- Name: tb_tauxhoraire tb_tauxhoraire_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_tauxhoraire
    ADD CONSTRAINT tb_tauxhoraire_pkey PRIMARY KEY (id);


--
-- TOC entry 5375 (class 2606 OID 16978)
-- Name: tb_transfert tb_transfert_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfert
    ADD CONSTRAINT tb_transfert_pkey PRIMARY KEY (idtransfert);


--
-- TOC entry 5377 (class 2606 OID 16980)
-- Name: tb_transfertbanque tb_transfertbanque_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfertbanque
    ADD CONSTRAINT tb_transfertbanque_pkey PRIMARY KEY (id);


--
-- TOC entry 5379 (class 2606 OID 16982)
-- Name: tb_transfertcaisse tb_transfertcaisse_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfertcaisse
    ADD CONSTRAINT tb_transfertcaisse_pkey PRIMARY KEY (id);


--
-- TOC entry 5381 (class 2606 OID 16984)
-- Name: tb_transfertdetail tb_transfertdetail_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transfertdetail
    ADD CONSTRAINT tb_transfertdetail_pkey PRIMARY KEY (id);


--
-- TOC entry 5383 (class 2606 OID 16986)
-- Name: tb_transporteur tb_transporteur_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_transporteur
    ADD CONSTRAINT tb_transporteur_pkey PRIMARY KEY (idtransporteur);


--
-- TOC entry 5385 (class 2606 OID 16988)
-- Name: tb_typeclient tb_typeclient_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_typeclient
    ADD CONSTRAINT tb_typeclient_pkey PRIMARY KEY (idtypeclient);


--
-- TOC entry 5387 (class 2606 OID 16990)
-- Name: tb_typeoperation tb_typeoperation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_typeoperation
    ADD CONSTRAINT tb_typeoperation_pkey PRIMARY KEY (idtypeoperation);


--
-- TOC entry 5389 (class 2606 OID 16992)
-- Name: tb_typepmt tb_typepmt_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_typepmt
    ADD CONSTRAINT tb_typepmt_pkey PRIMARY KEY (idtypepmt);


--
-- TOC entry 5391 (class 2606 OID 16994)
-- Name: tb_unite tb_unite_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_unite
    ADD CONSTRAINT tb_unite_pkey PRIMARY KEY (idunite);


--
-- TOC entry 5393 (class 2606 OID 16996)
-- Name: tb_users tb_users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_users
    ADD CONSTRAINT tb_users_pkey PRIMARY KEY (iduser);


--
-- TOC entry 5395 (class 2606 OID 16998)
-- Name: tb_vente tb_vente_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_vente
    ADD CONSTRAINT tb_vente_pkey PRIMARY KEY (id);


--
-- TOC entry 5397 (class 2606 OID 17000)
-- Name: tb_ventedetail tb_ventedetail_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_ventedetail
    ADD CONSTRAINT tb_ventedetail_pkey PRIMARY KEY (id);


--
-- TOC entry 5267 (class 1259 OID 17001)
-- Name: idx_changement_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_changement_date ON public.tb_changement USING btree (datechg);


--
-- TOC entry 5268 (class 1259 OID 17002)
-- Name: idx_changement_refchg; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_changement_refchg ON public.tb_changement USING btree (refchg);


--
-- TOC entry 5269 (class 1259 OID 17003)
-- Name: idx_changement_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_changement_user ON public.tb_changement USING btree (iduser);


--
-- TOC entry 5296 (class 1259 OID 17004)
-- Name: idx_detailchange_entree_article; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_detailchange_entree_article ON public.tb_detailchange_entree USING btree (idarticle);


--
-- TOC entry 5297 (class 1259 OID 17005)
-- Name: idx_detailchange_entree_idchg; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_detailchange_entree_idchg ON public.tb_detailchange_entree USING btree (idchg);


--
-- TOC entry 5300 (class 1259 OID 17006)
-- Name: idx_detailchange_sortie_article; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_detailchange_sortie_article ON public.tb_detailchange_sortie USING btree (idarticle);


--
-- TOC entry 5301 (class 1259 OID 17007)
-- Name: idx_detailchange_sortie_idchg; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_detailchange_sortie_idchg ON public.tb_detailchange_sortie USING btree (idchg);


--
-- TOC entry 5320 (class 1259 OID 17008)
-- Name: idx_inv_temp_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_inv_temp_date ON public.tb_inventaire_temporaire USING btree (date_creation);


--
-- TOC entry 5369 (class 1259 OID 17009)
-- Name: idx_suivipresence_date_personnel; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_suivipresence_date_personnel ON public.tb_suivipresence USING btree (datepresence, idpersonnel);


--
-- TOC entry 5399 (class 2606 OID 17010)
-- Name: tb_chat fk_destinataire; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_chat
    ADD CONSTRAINT fk_destinataire FOREIGN KEY (id_destinataire) REFERENCES public.tb_users(iduser);


--
-- TOC entry 5400 (class 2606 OID 17015)
-- Name: tb_chat fk_expediteur; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_chat
    ADD CONSTRAINT fk_expediteur FOREIGN KEY (id_expediteur) REFERENCES public.tb_users(iduser);


--
-- TOC entry 5398 (class 2606 OID 17020)
-- Name: tb_avanceprof tb_avanceprof_idpers_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tb_avanceprof
    ADD CONSTRAINT tb_avanceprof_idpers_fkey FOREIGN KEY (idpers) REFERENCES public.tb_personnel(id);


-- Completed on 2026-04-01 11:10:05

--
-- PostgreSQL database dump complete
--

\unrestrict fIKjh6jTqcXSYczaU0QDHlm3DraUqWVzyE5JBseFu7fB9g4iqT7fIhPe6SqJQSr

