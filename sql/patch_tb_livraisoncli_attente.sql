-- iJeery v5.0 — Backlog BL (sortie immédiate)
-- Règle métier: la vente sort le stock immédiatement (tb_ventedetail),
-- le BL (tb_livraisoncli) est un document logistique.
--
-- Cette table stocke les demandes de BL ("en attente"), indépendantes du stock.

CREATE TABLE IF NOT EXISTS public.tb_livraisoncli_attente (
    id serial PRIMARY KEY,
    refvente character varying(50) NOT NULL,
    idmag integer NOT NULL,
    idclient integer NOT NULL,
    idarticle integer NOT NULL,
    idunite integer NOT NULL,
    qt_a_livrer double precision NOT NULL DEFAULT 0,
    qt_bl double precision NOT NULL DEFAULT 0,
    statut character varying(20) NOT NULL DEFAULT 'EN_ATTENTE',
    dateregistre timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    iduser integer,
    CONSTRAINT tb_livraisoncli_attente_uk UNIQUE (refvente, idmag, idarticle, idunite)
);

CREATE INDEX IF NOT EXISTS idx_livcli_attente_statut
    ON public.tb_livraisoncli_attente (statut);

CREATE INDEX IF NOT EXISTS idx_livcli_attente_refvente
    ON public.tb_livraisoncli_attente (refvente);

