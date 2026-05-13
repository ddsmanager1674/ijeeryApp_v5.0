-- Auto-généré depuis `Structure database.sql` (pg_dump)
-- Idempotent: crée tables/séquences/colonnes si absentes, applique defaults de séquence.
SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;

-- Sequence: tb_absence_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_absence_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_absence_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_article_idarticle_seq
DO $$
BEGIN
  IF to_regclass('public.tb_article_idarticle_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_article_idarticle_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_autorisation_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_autorisation_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_autorisation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_autre_infos_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_autre_infos_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_autre_infos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_autrecreance_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_autrecreance_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_autrecreance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_autredette_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_autredette_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_autredette_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_avancepers_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_avancepers_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_avancepers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_avanceprof_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_avanceprof_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_avanceprof_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_avancespecpers_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_avancespecpers_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_avancespecpers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_avoir_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_avoir_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_avoir_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_avoirdetail_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_avoirdetail_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_avoirdetail_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_banque_id_banque_seq
DO $$
BEGIN
  IF to_regclass('public.tb_banque_id_banque_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_banque_id_banque_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_baseliste_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_baseliste_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_baseliste_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_categoriearticle_idca_seq
DO $$
BEGIN
  IF to_regclass('public.tb_categoriearticle_idca_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_categoriearticle_idca_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_categoriecompte_idcc_seq
DO $$
BEGIN
  IF to_regclass('public.tb_categoriecompte_idcc_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_categoriecompte_idcc_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_changement_idchg_seq
DO $$
BEGIN
  IF to_regclass('public.tb_changement_idchg_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_changement_idchg_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_chat_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_chat_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_chat_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_client_idclient_seq
DO $$
BEGIN
  IF to_regclass('public.tb_client_idclient_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_client_idclient_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_codeautorisation_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_codeautorisation_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_codeautorisation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_commande_idcom_seq
DO $$
BEGIN
  IF to_regclass('public.tb_commande_idcom_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_commande_idcom_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_commandedetail_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_commandedetail_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_commandedetail_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_configdb_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_configdb_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_configdb_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_consommationinterne_details_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_consommationinterne_details_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_consommationinterne_details_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_consommationinterne_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_consommationinterne_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_consommationinterne_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_decaissement_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_decaissement_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_decaissement_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_decaissementbq_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_decaissementbq_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_decaissementbq_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_detailchange_entree_iddetail_seq
DO $$
BEGIN
  IF to_regclass('public.tb_detailchange_entree_iddetail_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_detailchange_entree_iddetail_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_detailchange_sortie_iddetail_seq
DO $$
BEGIN
  IF to_regclass('public.tb_detailchange_sortie_iddetail_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_detailchange_sortie_iddetail_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_encaissement_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_encaissement_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_encaissement_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_encaissementbq_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_encaissementbq_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_encaissementbq_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_entree_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_entree_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_entree_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_entreedetail_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_entreedetail_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_entreedetail_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_evenement_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_evenement_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_evenement_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_facturecli_idfact_seq
DO $$
BEGIN
  IF to_regclass('public.tb_facturecli_idfact_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_facturecli_idfact_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_fonction_idfonction_seq
DO $$
BEGIN
  IF to_regclass('public.tb_fonction_idfonction_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_fonction_idfonction_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_fournisseur_idfrs_seq
DO $$
BEGIN
  IF to_regclass('public.tb_fournisseur_idfrs_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_fournisseur_idfrs_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_infosociete_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_infosociete_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_infosociete_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_inventaire_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_inventaire_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_inventaire_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_inventaire_temporaire_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_inventaire_temporaire_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_inventaire_temporaire_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_livraisoncli_attente_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_livraisoncli_attente_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_livraisoncli_attente_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_livraisoncli_idlivcli_seq
DO $$
BEGIN
  IF to_regclass('public.tb_livraisoncli_idlivcli_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_livraisoncli_idlivcli_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_livraisonfrs_idlivfrs_seq
DO $$
BEGIN
  IF to_regclass('public.tb_livraisonfrs_idlivfrs_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_livraisonfrs_idlivfrs_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_log_stock_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_log_stock_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_log_stock_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_lot_peremption_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_lot_peremption_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_lot_peremption_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_magasin_idmag_seq
DO $$
BEGIN
  IF to_regclass('public.tb_magasin_idmag_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_magasin_idmag_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_menu_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_menu_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_menu_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_modepaiement_idmode_seq
DO $$
BEGIN
  IF to_regclass('public.tb_modepaiement_idmode_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_modepaiement_idmode_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_paiement_idpaiement_seq
DO $$
BEGIN
  IF to_regclass('public.tb_paiement_idpaiement_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_paiement_idpaiement_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_peremption_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_peremption_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_peremption_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_personnel_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_personnel_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_personnel_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_pmtavoir_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_pmtavoir_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_pmtavoir_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_pmtcom_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_pmtcom_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_pmtcom_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_pmtcredit_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_pmtcredit_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_pmtcredit_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_pmtfacture_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_pmtfacture_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_pmtfacture_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_pmtsalaire_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_pmtsalaire_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_pmtsalaire_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_presencepers_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_presencepers_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_presencepers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_prix_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_prix_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_prix_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_proforma_idprof_seq
DO $$
BEGIN
  IF to_regclass('public.tb_proforma_idprof_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_proforma_idprof_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_proformadetail_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_proformadetail_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_proformadetail_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_salairebasepers_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_salairebasepers_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_salairebasepers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_sortie_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_sortie_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_sortie_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_sortiedetail_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_sortiedetail_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_sortiedetail_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_stock_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_stock_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_stock_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_suivipresence_idpresence_seq
DO $$
BEGIN
  IF to_regclass('public.tb_suivipresence_idpresence_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_suivipresence_idpresence_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_tauxhoraire_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_tauxhoraire_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_tauxhoraire_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_transfert_idtransfert_seq
DO $$
BEGIN
  IF to_regclass('public.tb_transfert_idtransfert_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_transfert_idtransfert_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_transfertbanque_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_transfertbanque_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_transfertbanque_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_transfertcaisse_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_transfertcaisse_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_transfertcaisse_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_transfertdetail_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_transfertdetail_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_transfertdetail_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_transporteur_idtransporteur_seq
DO $$
BEGIN
  IF to_regclass('public.tb_transporteur_idtransporteur_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_transporteur_idtransporteur_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_typeclient_idtypeclient_seq
DO $$
BEGIN
  IF to_regclass('public.tb_typeclient_idtypeclient_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_typeclient_idtypeclient_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_typeoperation_idtypeoperation_seq
DO $$
BEGIN
  IF to_regclass('public.tb_typeoperation_idtypeoperation_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_typeoperation_idtypeoperation_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_typepmt_idtypepmt_seq
DO $$
BEGIN
  IF to_regclass('public.tb_typepmt_idtypepmt_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_typepmt_idtypepmt_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_unite_idunite_seq
DO $$
BEGIN
  IF to_regclass('public.tb_unite_idunite_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_unite_idunite_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_users_iduser_seq
DO $$
BEGIN
  IF to_regclass('public.tb_users_iduser_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_users_iduser_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_vente_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_vente_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_vente_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Sequence: tb_ventedetail_id_seq
DO $$
BEGIN
  IF to_regclass('public.tb_ventedetail_id_seq') IS NULL THEN
    EXECUTE 'CREATE SEQUENCE public.tb_ventedetail_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;';
  END IF;
END $$;

-- Table: event_logs
CREATE TABLE IF NOT EXISTS public.event_logs (
    id_log timestamp with time zone DEFAULT clock_timestamp() NOT NULL,
    description text NOT NULL,
    "user" character varying(150),
    datetime timestamp with time zone DEFAULT now() NOT NULL
);;

ALTER TABLE IF EXISTS public.event_logs ADD COLUMN IF NOT EXISTS id_log timestamp with time zone DEFAULT clock_timestamp() NOT NULL;
ALTER TABLE IF EXISTS public.event_logs ADD COLUMN IF NOT EXISTS description text NOT NULL;
ALTER TABLE IF EXISTS public.event_logs ADD COLUMN IF NOT EXISTS "user" character varying(150);
ALTER TABLE IF EXISTS public.event_logs ADD COLUMN IF NOT EXISTS datetime timestamp with time zone DEFAULT now() NOT NULL;

-- Table: tb_absence
CREATE TABLE IF NOT EXISTS public.tb_absence (
    id integer NOT NULL,
    idpers integer,
    date timestamp without time zone,
    observation character varying(120),
    nbreheureabs double precision
);;

ALTER TABLE IF EXISTS public.tb_absence ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_absence ADD COLUMN IF NOT EXISTS idpers integer;
ALTER TABLE IF EXISTS public.tb_absence ADD COLUMN IF NOT EXISTS date timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_absence ADD COLUMN IF NOT EXISTS observation character varying(120);
ALTER TABLE IF EXISTS public.tb_absence ADD COLUMN IF NOT EXISTS nbreheureabs double precision;

-- Table: tb_article
CREATE TABLE IF NOT EXISTS public.tb_article (
    idarticle integer NOT NULL,
    designation character varying(150),
    idca integer,
    alert integer,
    deleted integer DEFAULT 0,
    idmag integer,
    alertdepot double precision
);;

ALTER TABLE IF EXISTS public.tb_article ADD COLUMN IF NOT EXISTS idarticle integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_article ADD COLUMN IF NOT EXISTS designation character varying(150);
ALTER TABLE IF EXISTS public.tb_article ADD COLUMN IF NOT EXISTS idca integer;
ALTER TABLE IF EXISTS public.tb_article ADD COLUMN IF NOT EXISTS alert integer;
ALTER TABLE IF EXISTS public.tb_article ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;
ALTER TABLE IF EXISTS public.tb_article ADD COLUMN IF NOT EXISTS idmag integer;
ALTER TABLE IF EXISTS public.tb_article ADD COLUMN IF NOT EXISTS alertdepot double precision;

-- Table: tb_autorisation
CREATE TABLE IF NOT EXISTS public.tb_autorisation (
    id integer NOT NULL,
    idfonction integer,
    idmenu integer
);;

ALTER TABLE IF EXISTS public.tb_autorisation ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_autorisation ADD COLUMN IF NOT EXISTS idfonction integer;
ALTER TABLE IF EXISTS public.tb_autorisation ADD COLUMN IF NOT EXISTS idmenu integer;

-- Table: tb_autre_infos
CREATE TABLE IF NOT EXISTS public.tb_autre_infos (
    id integer NOT NULL,
    intitule character varying(250) DEFAULT ''::character varying,
    valeur character varying(1000) DEFAULT ''::character varying
);;

ALTER TABLE IF EXISTS public.tb_autre_infos ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_autre_infos ADD COLUMN IF NOT EXISTS intitule character varying(250) DEFAULT ''::character varying;
ALTER TABLE IF EXISTS public.tb_autre_infos ADD COLUMN IF NOT EXISTS valeur character varying(1000) DEFAULT ''::character varying;

-- Table: tb_autrecreance
CREATE TABLE IF NOT EXISTS public.tb_autrecreance (
    id integer NOT NULL,
    idclient integer,
    dateregistre timestamp without time zone,
    numfact character varying(50),
    montant double precision,
    dateecheance date
);;

ALTER TABLE IF EXISTS public.tb_autrecreance ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_autrecreance ADD COLUMN IF NOT EXISTS idclient integer;
ALTER TABLE IF EXISTS public.tb_autrecreance ADD COLUMN IF NOT EXISTS dateregistre timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_autrecreance ADD COLUMN IF NOT EXISTS numfact character varying(50);
ALTER TABLE IF EXISTS public.tb_autrecreance ADD COLUMN IF NOT EXISTS montant double precision;
ALTER TABLE IF EXISTS public.tb_autrecreance ADD COLUMN IF NOT EXISTS dateecheance date;

-- Table: tb_autredette
CREATE TABLE IF NOT EXISTS public.tb_autredette (
    id integer NOT NULL,
    idfrs integer,
    dateregistre timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    numfact character varying(50),
    montant double precision,
    dateecheance date
);;

ALTER TABLE IF EXISTS public.tb_autredette ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_autredette ADD COLUMN IF NOT EXISTS idfrs integer;
ALTER TABLE IF EXISTS public.tb_autredette ADD COLUMN IF NOT EXISTS dateregistre timestamp without time zone DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE IF EXISTS public.tb_autredette ADD COLUMN IF NOT EXISTS numfact character varying(50);
ALTER TABLE IF EXISTS public.tb_autredette ADD COLUMN IF NOT EXISTS montant double precision;
ALTER TABLE IF EXISTS public.tb_autredette ADD COLUMN IF NOT EXISTS dateecheance date;

-- Table: tb_avancepers
CREATE TABLE IF NOT EXISTS public.tb_avancepers (
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
);;

ALTER TABLE IF EXISTS public.tb_avancepers ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_avancepers ADD COLUMN IF NOT EXISTS datepmt timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_avancepers ADD COLUMN IF NOT EXISTS refpmt character varying(50);
ALTER TABLE IF EXISTS public.tb_avancepers ADD COLUMN IF NOT EXISTS mtpaye double precision;
ALTER TABLE IF EXISTS public.tb_avancepers ADD COLUMN IF NOT EXISTS idtypeoperation integer;
ALTER TABLE IF EXISTS public.tb_avancepers ADD COLUMN IF NOT EXISTS idpers integer;
ALTER TABLE IF EXISTS public.tb_avancepers ADD COLUMN IF NOT EXISTS observation character varying(100);
ALTER TABLE IF EXISTS public.tb_avancepers ADD COLUMN IF NOT EXISTS id_banque integer;
ALTER TABLE IF EXISTS public.tb_avancepers ADD COLUMN IF NOT EXISTS iduser integer;
ALTER TABLE IF EXISTS public.tb_avancepers ADD COLUMN IF NOT EXISTS idmode integer;

-- Table: tb_avanceprof
CREATE TABLE IF NOT EXISTS public.tb_avanceprof (
    id integer NOT NULL,
    refpmt character varying(50),
    idpers integer,
    mtpaye double precision,
    observation character varying(120),
    datepmt timestamp without time zone,
    etat integer,
    idtypeoperation integer,
    iduser integer
);;

ALTER TABLE IF EXISTS public.tb_avanceprof ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_avanceprof ADD COLUMN IF NOT EXISTS refpmt character varying(50);
ALTER TABLE IF EXISTS public.tb_avanceprof ADD COLUMN IF NOT EXISTS idpers integer;
ALTER TABLE IF EXISTS public.tb_avanceprof ADD COLUMN IF NOT EXISTS mtpaye double precision;
ALTER TABLE IF EXISTS public.tb_avanceprof ADD COLUMN IF NOT EXISTS observation character varying(120);
ALTER TABLE IF EXISTS public.tb_avanceprof ADD COLUMN IF NOT EXISTS datepmt timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_avanceprof ADD COLUMN IF NOT EXISTS etat integer;
ALTER TABLE IF EXISTS public.tb_avanceprof ADD COLUMN IF NOT EXISTS idtypeoperation integer;
ALTER TABLE IF EXISTS public.tb_avanceprof ADD COLUMN IF NOT EXISTS iduser integer;

-- Table: tb_avancespecpers
CREATE TABLE IF NOT EXISTS public.tb_avancespecpers (
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
);;

ALTER TABLE IF EXISTS public.tb_avancespecpers ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_avancespecpers ADD COLUMN IF NOT EXISTS idpers integer;
ALTER TABLE IF EXISTS public.tb_avancespecpers ADD COLUMN IF NOT EXISTS refpmt character varying(50);
ALTER TABLE IF EXISTS public.tb_avancespecpers ADD COLUMN IF NOT EXISTS mtpaye double precision;
ALTER TABLE IF EXISTS public.tb_avancespecpers ADD COLUMN IF NOT EXISTS idtypeoperation integer;
ALTER TABLE IF EXISTS public.tb_avancespecpers ADD COLUMN IF NOT EXISTS nbremboursement double precision;
ALTER TABLE IF EXISTS public.tb_avancespecpers ADD COLUMN IF NOT EXISTS observation character varying(120);
ALTER TABLE IF EXISTS public.tb_avancespecpers ADD COLUMN IF NOT EXISTS datepmt timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_avancespecpers ADD COLUMN IF NOT EXISTS id_banque integer;
ALTER TABLE IF EXISTS public.tb_avancespecpers ADD COLUMN IF NOT EXISTS idmode integer;
ALTER TABLE IF EXISTS public.tb_avancespecpers ADD COLUMN IF NOT EXISTS iduser integer;

-- Table: tb_avoir
CREATE TABLE IF NOT EXISTS public.tb_avoir (
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
);;

ALTER TABLE IF EXISTS public.tb_avoir ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_avoir ADD COLUMN IF NOT EXISTS refavoir character varying(50);
ALTER TABLE IF EXISTS public.tb_avoir ADD COLUMN IF NOT EXISTS idclient integer;
ALTER TABLE IF EXISTS public.tb_avoir ADD COLUMN IF NOT EXISTS iduser integer;
ALTER TABLE IF EXISTS public.tb_avoir ADD COLUMN IF NOT EXISTS mtavoir double precision;
ALTER TABLE IF EXISTS public.tb_avoir ADD COLUMN IF NOT EXISTS idmode integer;
ALTER TABLE IF EXISTS public.tb_avoir ADD COLUMN IF NOT EXISTS observation character varying(150);
ALTER TABLE IF EXISTS public.tb_avoir ADD COLUMN IF NOT EXISTS dateregistre timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_avoir ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;
ALTER TABLE IF EXISTS public.tb_avoir ADD COLUMN IF NOT EXISTS dateavoir timestamp without time zone;

-- Table: tb_avoirdetail
CREATE TABLE IF NOT EXISTS public.tb_avoirdetail (
    id integer NOT NULL,
    idmag integer,
    idarticle integer,
    idunite integer,
    qtavoir double precision,
    prixunit double precision,
    deleted integer DEFAULT 0,
    idavoir integer
);;

ALTER TABLE IF EXISTS public.tb_avoirdetail ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_avoirdetail ADD COLUMN IF NOT EXISTS idmag integer;
ALTER TABLE IF EXISTS public.tb_avoirdetail ADD COLUMN IF NOT EXISTS idarticle integer;
ALTER TABLE IF EXISTS public.tb_avoirdetail ADD COLUMN IF NOT EXISTS idunite integer;
ALTER TABLE IF EXISTS public.tb_avoirdetail ADD COLUMN IF NOT EXISTS qtavoir double precision;
ALTER TABLE IF EXISTS public.tb_avoirdetail ADD COLUMN IF NOT EXISTS prixunit double precision;
ALTER TABLE IF EXISTS public.tb_avoirdetail ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;
ALTER TABLE IF EXISTS public.tb_avoirdetail ADD COLUMN IF NOT EXISTS idavoir integer;

-- Table: tb_banque
CREATE TABLE IF NOT EXISTS public.tb_banque (
    id_banque integer NOT NULL,
    nombanque character varying(75),
    adresse character varying(120),
    numcompte integer,
    iduser integer
);;

ALTER TABLE IF EXISTS public.tb_banque ADD COLUMN IF NOT EXISTS id_banque integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_banque ADD COLUMN IF NOT EXISTS nombanque character varying(75);
ALTER TABLE IF EXISTS public.tb_banque ADD COLUMN IF NOT EXISTS adresse character varying(120);
ALTER TABLE IF EXISTS public.tb_banque ADD COLUMN IF NOT EXISTS numcompte integer;
ALTER TABLE IF EXISTS public.tb_banque ADD COLUMN IF NOT EXISTS iduser integer;

-- Table: tb_baseliste
CREATE TABLE IF NOT EXISTS public.tb_baseliste (
    id integer NOT NULL,
    nombase character varying(75),
    designationbase character varying(75),
    deleted integer DEFAULT 0
);;

ALTER TABLE IF EXISTS public.tb_baseliste ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_baseliste ADD COLUMN IF NOT EXISTS nombase character varying(75);
ALTER TABLE IF EXISTS public.tb_baseliste ADD COLUMN IF NOT EXISTS designationbase character varying(75);
ALTER TABLE IF EXISTS public.tb_baseliste ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;

-- Table: tb_categoriearticle
CREATE TABLE IF NOT EXISTS public.tb_categoriearticle (
    idca integer NOT NULL,
    designationcat character varying(150),
    deleted integer DEFAULT 0
);;

ALTER TABLE IF EXISTS public.tb_categoriearticle ADD COLUMN IF NOT EXISTS idca integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_categoriearticle ADD COLUMN IF NOT EXISTS designationcat character varying(150);
ALTER TABLE IF EXISTS public.tb_categoriearticle ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;

-- Table: tb_categoriecompte
CREATE TABLE IF NOT EXISTS public.tb_categoriecompte (
    idcc integer NOT NULL,
    categoriecompte character varying(100)
);;

ALTER TABLE IF EXISTS public.tb_categoriecompte ADD COLUMN IF NOT EXISTS idcc integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_categoriecompte ADD COLUMN IF NOT EXISTS categoriecompte character varying(100);

-- Table: tb_changement
CREATE TABLE IF NOT EXISTS public.tb_changement (
    idchg integer NOT NULL,
    refchg character varying(20) NOT NULL,
    datechg timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    iduser integer NOT NULL,
    note text
);;

ALTER TABLE IF EXISTS public.tb_changement ADD COLUMN IF NOT EXISTS idchg integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_changement ADD COLUMN IF NOT EXISTS refchg character varying(20) NOT NULL;
ALTER TABLE IF EXISTS public.tb_changement ADD COLUMN IF NOT EXISTS datechg timestamp without time zone DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE IF EXISTS public.tb_changement ADD COLUMN IF NOT EXISTS iduser integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_changement ADD COLUMN IF NOT EXISTS note text;

-- Table: tb_chat
CREATE TABLE IF NOT EXISTS public.tb_chat (
    id integer NOT NULL,
    id_expediteur integer NOT NULL,
    id_destinataire integer NOT NULL,
    message text NOT NULL,
    date_envoi timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    lu integer DEFAULT 0
);;

ALTER TABLE IF EXISTS public.tb_chat ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_chat ADD COLUMN IF NOT EXISTS id_expediteur integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_chat ADD COLUMN IF NOT EXISTS id_destinataire integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_chat ADD COLUMN IF NOT EXISTS message text NOT NULL;
ALTER TABLE IF EXISTS public.tb_chat ADD COLUMN IF NOT EXISTS date_envoi timestamp without time zone DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE IF EXISTS public.tb_chat ADD COLUMN IF NOT EXISTS lu integer DEFAULT 0;

-- Table: tb_client
CREATE TABLE IF NOT EXISTS public.tb_client (
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
);;

ALTER TABLE IF EXISTS public.tb_client ADD COLUMN IF NOT EXISTS idclient integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_client ADD COLUMN IF NOT EXISTS nomcli character varying(100);
ALTER TABLE IF EXISTS public.tb_client ADD COLUMN IF NOT EXISTS contactcli character varying(50);
ALTER TABLE IF EXISTS public.tb_client ADD COLUMN IF NOT EXISTS adressecli character varying(150);
ALTER TABLE IF EXISTS public.tb_client ADD COLUMN IF NOT EXISTS nifcli character varying(20);
ALTER TABLE IF EXISTS public.tb_client ADD COLUMN IF NOT EXISTS statcli character varying(20);
ALTER TABLE IF EXISTS public.tb_client ADD COLUMN IF NOT EXISTS cifcli character varying(20);
ALTER TABLE IF EXISTS public.tb_client ADD COLUMN IF NOT EXISTS credit double precision;
ALTER TABLE IF EXISTS public.tb_client ADD COLUMN IF NOT EXISTS idtypeclient integer;
ALTER TABLE IF EXISTS public.tb_client ADD COLUMN IF NOT EXISTS dateregistre timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_client ADD COLUMN IF NOT EXISTS blocked integer;
ALTER TABLE IF EXISTS public.tb_client ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;

-- Table: tb_codeautorisation
CREATE TABLE IF NOT EXISTS public.tb_codeautorisation (
    id integer NOT NULL,
    code character varying(10),
    iduser integer,
    deleted integer DEFAULT 0,
    username character varying(50)
);;

ALTER TABLE IF EXISTS public.tb_codeautorisation ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_codeautorisation ADD COLUMN IF NOT EXISTS code character varying(10);
ALTER TABLE IF EXISTS public.tb_codeautorisation ADD COLUMN IF NOT EXISTS iduser integer;
ALTER TABLE IF EXISTS public.tb_codeautorisation ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;
ALTER TABLE IF EXISTS public.tb_codeautorisation ADD COLUMN IF NOT EXISTS username character varying(50);

-- Table: tb_commande
CREATE TABLE IF NOT EXISTS public.tb_commande (
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
);;

ALTER TABLE IF EXISTS public.tb_commande ADD COLUMN IF NOT EXISTS idcom integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_commande ADD COLUMN IF NOT EXISTS refcom character varying(50);
ALTER TABLE IF EXISTS public.tb_commande ADD COLUMN IF NOT EXISTS datecom timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_commande ADD COLUMN IF NOT EXISTS iduser integer;
ALTER TABLE IF EXISTS public.tb_commande ADD COLUMN IF NOT EXISTS idfrs integer;
ALTER TABLE IF EXISTS public.tb_commande ADD COLUMN IF NOT EXISTS descriptioncom character varying(150);
ALTER TABLE IF EXISTS public.tb_commande ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;
ALTER TABLE IF EXISTS public.tb_commande ADD COLUMN IF NOT EXISTS datemodif timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_commande ADD COLUMN IF NOT EXISTS totcmd double precision;
ALTER TABLE IF EXISTS public.tb_commande ADD COLUMN IF NOT EXISTS idtransportuer integer;

-- Table: tb_commandedetail
CREATE TABLE IF NOT EXISTS public.tb_commandedetail (
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
);;

ALTER TABLE IF EXISTS public.tb_commandedetail ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_commandedetail ADD COLUMN IF NOT EXISTS idcom integer;
ALTER TABLE IF EXISTS public.tb_commandedetail ADD COLUMN IF NOT EXISTS idarticle integer;
ALTER TABLE IF EXISTS public.tb_commandedetail ADD COLUMN IF NOT EXISTS idunite integer;
ALTER TABLE IF EXISTS public.tb_commandedetail ADD COLUMN IF NOT EXISTS qtcmd double precision;
ALTER TABLE IF EXISTS public.tb_commandedetail ADD COLUMN IF NOT EXISTS qtlivre double precision;
ALTER TABLE IF EXISTS public.tb_commandedetail ADD COLUMN IF NOT EXISTS punitcmd double precision;
ALTER TABLE IF EXISTS public.tb_commandedetail ADD COLUMN IF NOT EXISTS typemouvement integer;
ALTER TABLE IF EXISTS public.tb_commandedetail ADD COLUMN IF NOT EXISTS total double precision;
ALTER TABLE IF EXISTS public.tb_commandedetail ADD COLUMN IF NOT EXISTS dateperemption date;
ALTER TABLE IF EXISTS public.tb_commandedetail ADD COLUMN IF NOT EXISTS idfrs integer;
ALTER TABLE IF EXISTS public.tb_commandedetail ADD COLUMN IF NOT EXISTS montant_charge double precision DEFAULT 0;

-- Table: tb_configdb
CREATE TABLE IF NOT EXISTS public.tb_configdb (
    id integer NOT NULL,
    dbname character varying(50),
    username character varying(50),
    password character varying(100),
    host character varying(100),
    port integer
);;

ALTER TABLE IF EXISTS public.tb_configdb ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_configdb ADD COLUMN IF NOT EXISTS dbname character varying(50);
ALTER TABLE IF EXISTS public.tb_configdb ADD COLUMN IF NOT EXISTS username character varying(50);
ALTER TABLE IF EXISTS public.tb_configdb ADD COLUMN IF NOT EXISTS password character varying(100);
ALTER TABLE IF EXISTS public.tb_configdb ADD COLUMN IF NOT EXISTS host character varying(100);
ALTER TABLE IF EXISTS public.tb_configdb ADD COLUMN IF NOT EXISTS port integer;

-- Table: tb_consommationinterne
CREATE TABLE IF NOT EXISTS public.tb_consommationinterne (
    id integer NOT NULL,
    refconsommation character varying(50) NOT NULL,
    dateregistre timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    observation text,
    iduser integer NOT NULL,
    valeur_totale numeric(15,2) DEFAULT 0
);;

ALTER TABLE IF EXISTS public.tb_consommationinterne ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_consommationinterne ADD COLUMN IF NOT EXISTS refconsommation character varying(50) NOT NULL;
ALTER TABLE IF EXISTS public.tb_consommationinterne ADD COLUMN IF NOT EXISTS dateregistre timestamp without time zone DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE IF EXISTS public.tb_consommationinterne ADD COLUMN IF NOT EXISTS observation text;
ALTER TABLE IF EXISTS public.tb_consommationinterne ADD COLUMN IF NOT EXISTS iduser integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_consommationinterne ADD COLUMN IF NOT EXISTS valeur_totale numeric(15,2) DEFAULT 0;

-- Table: tb_consommationinterne_details
CREATE TABLE IF NOT EXISTS public.tb_consommationinterne_details (
    id integer NOT NULL,
    idconsommation integer NOT NULL,
    idarticle integer NOT NULL,
    idunite integer NOT NULL,
    idmag integer NOT NULL,
    qtconsomme numeric(10,2) NOT NULL,
    prixunit numeric(12,2) NOT NULL,
    montant_total numeric(15,2) GENERATED ALWAYS AS ((qtconsomme * prixunit)) STORED,
    observation text
);;

ALTER TABLE IF EXISTS public.tb_consommationinterne_details ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_consommationinterne_details ADD COLUMN IF NOT EXISTS idconsommation integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_consommationinterne_details ADD COLUMN IF NOT EXISTS idarticle integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_consommationinterne_details ADD COLUMN IF NOT EXISTS idunite integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_consommationinterne_details ADD COLUMN IF NOT EXISTS idmag integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_consommationinterne_details ADD COLUMN IF NOT EXISTS qtconsomme numeric(10,2) NOT NULL;
ALTER TABLE IF EXISTS public.tb_consommationinterne_details ADD COLUMN IF NOT EXISTS prixunit numeric(12,2) NOT NULL;
ALTER TABLE IF EXISTS public.tb_consommationinterne_details ADD COLUMN IF NOT EXISTS montant_total numeric(15,2) GENERATED ALWAYS AS ((qtconsomme * prixunit)) STORED;
ALTER TABLE IF EXISTS public.tb_consommationinterne_details ADD COLUMN IF NOT EXISTS observation text;

-- Table: tb_decaissement
CREATE TABLE IF NOT EXISTS public.tb_decaissement (
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
);;

ALTER TABLE IF EXISTS public.tb_decaissement ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_decaissement ADD COLUMN IF NOT EXISTS refpmt character varying(50);
ALTER TABLE IF EXISTS public.tb_decaissement ADD COLUMN IF NOT EXISTS idcc integer;
ALTER TABLE IF EXISTS public.tb_decaissement ADD COLUMN IF NOT EXISTS mtpaye double precision;
ALTER TABLE IF EXISTS public.tb_decaissement ADD COLUMN IF NOT EXISTS observation character varying(150);
ALTER TABLE IF EXISTS public.tb_decaissement ADD COLUMN IF NOT EXISTS idtypeoperation integer DEFAULT 2;
ALTER TABLE IF EXISTS public.tb_decaissement ADD COLUMN IF NOT EXISTS datepmt timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_decaissement ADD COLUMN IF NOT EXISTS idpaiment integer;
ALTER TABLE IF EXISTS public.tb_decaissement ADD COLUMN IF NOT EXISTS id_banque integer;
ALTER TABLE IF EXISTS public.tb_decaissement ADD COLUMN IF NOT EXISTS iduser integer;
ALTER TABLE IF EXISTS public.tb_decaissement ADD COLUMN IF NOT EXISTS idmode integer;

-- Table: tb_decaissementbq
CREATE TABLE IF NOT EXISTS public.tb_decaissementbq (
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
);;

ALTER TABLE IF EXISTS public.tb_decaissementbq ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_decaissementbq ADD COLUMN IF NOT EXISTS refpmt character varying(50);
ALTER TABLE IF EXISTS public.tb_decaissementbq ADD COLUMN IF NOT EXISTS idcc integer;
ALTER TABLE IF EXISTS public.tb_decaissementbq ADD COLUMN IF NOT EXISTS mtpaye double precision;
ALTER TABLE IF EXISTS public.tb_decaissementbq ADD COLUMN IF NOT EXISTS observation character varying(150);
ALTER TABLE IF EXISTS public.tb_decaissementbq ADD COLUMN IF NOT EXISTS idtypeoperation integer DEFAULT 2;
ALTER TABLE IF EXISTS public.tb_decaissementbq ADD COLUMN IF NOT EXISTS datepmt timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_decaissementbq ADD COLUMN IF NOT EXISTS idpaiment integer;
ALTER TABLE IF EXISTS public.tb_decaissementbq ADD COLUMN IF NOT EXISTS id_banque integer;
ALTER TABLE IF EXISTS public.tb_decaissementbq ADD COLUMN IF NOT EXISTS iduser integer;
ALTER TABLE IF EXISTS public.tb_decaissementbq ADD COLUMN IF NOT EXISTS idmode integer;

-- Table: tb_detailchange_entree
CREATE TABLE IF NOT EXISTS public.tb_detailchange_entree (
    iddetail integer NOT NULL,
    idchg integer NOT NULL,
    idarticle integer NOT NULL,
    idunite integer NOT NULL,
    idmagasin integer NOT NULL,
    quantite_entree numeric(10,2) NOT NULL
);;

ALTER TABLE IF EXISTS public.tb_detailchange_entree ADD COLUMN IF NOT EXISTS iddetail integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_detailchange_entree ADD COLUMN IF NOT EXISTS idchg integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_detailchange_entree ADD COLUMN IF NOT EXISTS idarticle integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_detailchange_entree ADD COLUMN IF NOT EXISTS idunite integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_detailchange_entree ADD COLUMN IF NOT EXISTS idmagasin integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_detailchange_entree ADD COLUMN IF NOT EXISTS quantite_entree numeric(10,2) NOT NULL;

-- Table: tb_detailchange_sortie
CREATE TABLE IF NOT EXISTS public.tb_detailchange_sortie (
    iddetail integer NOT NULL,
    idchg integer NOT NULL,
    idarticle integer NOT NULL,
    idunite integer NOT NULL,
    idmagasin integer NOT NULL,
    quantite_sortie numeric(10,2) NOT NULL
);;

ALTER TABLE IF EXISTS public.tb_detailchange_sortie ADD COLUMN IF NOT EXISTS iddetail integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_detailchange_sortie ADD COLUMN IF NOT EXISTS idchg integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_detailchange_sortie ADD COLUMN IF NOT EXISTS idarticle integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_detailchange_sortie ADD COLUMN IF NOT EXISTS idunite integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_detailchange_sortie ADD COLUMN IF NOT EXISTS idmagasin integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_detailchange_sortie ADD COLUMN IF NOT EXISTS quantite_sortie numeric(10,2) NOT NULL;

-- Table: tb_encaissement
CREATE TABLE IF NOT EXISTS public.tb_encaissement (
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
);;

ALTER TABLE IF EXISTS public.tb_encaissement ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_encaissement ADD COLUMN IF NOT EXISTS refpmt character varying(50);
ALTER TABLE IF EXISTS public.tb_encaissement ADD COLUMN IF NOT EXISTS idcc integer;
ALTER TABLE IF EXISTS public.tb_encaissement ADD COLUMN IF NOT EXISTS mtpaye double precision;
ALTER TABLE IF EXISTS public.tb_encaissement ADD COLUMN IF NOT EXISTS observation character varying(150);
ALTER TABLE IF EXISTS public.tb_encaissement ADD COLUMN IF NOT EXISTS idtypeoperation integer DEFAULT 1;
ALTER TABLE IF EXISTS public.tb_encaissement ADD COLUMN IF NOT EXISTS datepmt timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_encaissement ADD COLUMN IF NOT EXISTS idpaiment integer;
ALTER TABLE IF EXISTS public.tb_encaissement ADD COLUMN IF NOT EXISTS id_banque integer;
ALTER TABLE IF EXISTS public.tb_encaissement ADD COLUMN IF NOT EXISTS iduser integer;
ALTER TABLE IF EXISTS public.tb_encaissement ADD COLUMN IF NOT EXISTS idmode integer;

-- Table: tb_encaissementbq
CREATE TABLE IF NOT EXISTS public.tb_encaissementbq (
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
);;

ALTER TABLE IF EXISTS public.tb_encaissementbq ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_encaissementbq ADD COLUMN IF NOT EXISTS refpmt character varying(50);
ALTER TABLE IF EXISTS public.tb_encaissementbq ADD COLUMN IF NOT EXISTS idcc integer;
ALTER TABLE IF EXISTS public.tb_encaissementbq ADD COLUMN IF NOT EXISTS mtpaye double precision;
ALTER TABLE IF EXISTS public.tb_encaissementbq ADD COLUMN IF NOT EXISTS observation character varying(150);
ALTER TABLE IF EXISTS public.tb_encaissementbq ADD COLUMN IF NOT EXISTS idtypeoperation integer DEFAULT 1;
ALTER TABLE IF EXISTS public.tb_encaissementbq ADD COLUMN IF NOT EXISTS datepmt timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_encaissementbq ADD COLUMN IF NOT EXISTS idpaiment integer;
ALTER TABLE IF EXISTS public.tb_encaissementbq ADD COLUMN IF NOT EXISTS id_banque integer;
ALTER TABLE IF EXISTS public.tb_encaissementbq ADD COLUMN IF NOT EXISTS iduser integer;
ALTER TABLE IF EXISTS public.tb_encaissementbq ADD COLUMN IF NOT EXISTS idmode integer;

-- Table: tb_entree
CREATE TABLE IF NOT EXISTS public.tb_entree (
    id integer NOT NULL,
    refentree character varying(50),
    iduser integer,
    dateregistre timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    description character varying(150),
    deleted integer DEFAULT 0
);;

ALTER TABLE IF EXISTS public.tb_entree ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_entree ADD COLUMN IF NOT EXISTS refentree character varying(50);
ALTER TABLE IF EXISTS public.tb_entree ADD COLUMN IF NOT EXISTS iduser integer;
ALTER TABLE IF EXISTS public.tb_entree ADD COLUMN IF NOT EXISTS dateregistre timestamp without time zone DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE IF EXISTS public.tb_entree ADD COLUMN IF NOT EXISTS description character varying(150);
ALTER TABLE IF EXISTS public.tb_entree ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;

-- Table: tb_entreedetail
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
);;

ALTER TABLE IF EXISTS public.tb_entreedetail ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_entreedetail ADD COLUMN IF NOT EXISTS idmag integer;
ALTER TABLE IF EXISTS public.tb_entreedetail ADD COLUMN IF NOT EXISTS idarticle integer;
ALTER TABLE IF EXISTS public.tb_entreedetail ADD COLUMN IF NOT EXISTS idunite integer;
ALTER TABLE IF EXISTS public.tb_entreedetail ADD COLUMN IF NOT EXISTS qtentree double precision;
ALTER TABLE IF EXISTS public.tb_entreedetail ADD COLUMN IF NOT EXISTS typemouvement integer DEFAULT 1;
ALTER TABLE IF EXISTS public.tb_entreedetail ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;
ALTER TABLE IF EXISTS public.tb_entreedetail ADD COLUMN IF NOT EXISTS identree integer;
ALTER TABLE IF EXISTS public.tb_entreedetail ADD COLUMN IF NOT EXISTS motif character varying(250);

-- Table: tb_evenement
CREATE TABLE IF NOT EXISTS public.tb_evenement (
    id integer NOT NULL,
    date timestamp without time zone,
    evenements character varying(200)
);;

ALTER TABLE IF EXISTS public.tb_evenement ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_evenement ADD COLUMN IF NOT EXISTS date timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_evenement ADD COLUMN IF NOT EXISTS evenements character varying(200);

-- Table: tb_facturecli
CREATE TABLE IF NOT EXISTS public.tb_facturecli (
    idfact integer NOT NULL,
    reffact character varying(50),
    refvente character varying(50),
    idmod integer,
    idclient integer,
    iduser integer,
    mtpaye double precision,
    dateregistre timestamp without time zone
);;

ALTER TABLE IF EXISTS public.tb_facturecli ADD COLUMN IF NOT EXISTS idfact integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_facturecli ADD COLUMN IF NOT EXISTS reffact character varying(50);
ALTER TABLE IF EXISTS public.tb_facturecli ADD COLUMN IF NOT EXISTS refvente character varying(50);
ALTER TABLE IF EXISTS public.tb_facturecli ADD COLUMN IF NOT EXISTS idmod integer;
ALTER TABLE IF EXISTS public.tb_facturecli ADD COLUMN IF NOT EXISTS idclient integer;
ALTER TABLE IF EXISTS public.tb_facturecli ADD COLUMN IF NOT EXISTS iduser integer;
ALTER TABLE IF EXISTS public.tb_facturecli ADD COLUMN IF NOT EXISTS mtpaye double precision;
ALTER TABLE IF EXISTS public.tb_facturecli ADD COLUMN IF NOT EXISTS dateregistre timestamp without time zone;

-- Table: tb_fonction
CREATE TABLE IF NOT EXISTS public.tb_fonction (
    idfonction integer NOT NULL,
    designationfonction character varying(50),
    dateregistre timestamp without time zone,
    idautorisation integer,
    deleted integer DEFAULT 0
);;

ALTER TABLE IF EXISTS public.tb_fonction ADD COLUMN IF NOT EXISTS idfonction integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_fonction ADD COLUMN IF NOT EXISTS designationfonction character varying(50);
ALTER TABLE IF EXISTS public.tb_fonction ADD COLUMN IF NOT EXISTS dateregistre timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_fonction ADD COLUMN IF NOT EXISTS idautorisation integer;
ALTER TABLE IF EXISTS public.tb_fonction ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;

-- Table: tb_fournisseur
CREATE TABLE IF NOT EXISTS public.tb_fournisseur (
    idfrs integer NOT NULL,
    nomfrs character varying(150),
    contactfrs character varying(50),
    adressefrs character varying(150),
    niffrs character varying(20),
    statfrs character varying(20),
    ciffrs character varying(20),
    dateregistre timestamp without time zone,
    deleted integer DEFAULT 0
);;

ALTER TABLE IF EXISTS public.tb_fournisseur ADD COLUMN IF NOT EXISTS idfrs integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_fournisseur ADD COLUMN IF NOT EXISTS nomfrs character varying(150);
ALTER TABLE IF EXISTS public.tb_fournisseur ADD COLUMN IF NOT EXISTS contactfrs character varying(50);
ALTER TABLE IF EXISTS public.tb_fournisseur ADD COLUMN IF NOT EXISTS adressefrs character varying(150);
ALTER TABLE IF EXISTS public.tb_fournisseur ADD COLUMN IF NOT EXISTS niffrs character varying(20);
ALTER TABLE IF EXISTS public.tb_fournisseur ADD COLUMN IF NOT EXISTS statfrs character varying(20);
ALTER TABLE IF EXISTS public.tb_fournisseur ADD COLUMN IF NOT EXISTS ciffrs character varying(20);
ALTER TABLE IF EXISTS public.tb_fournisseur ADD COLUMN IF NOT EXISTS dateregistre timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_fournisseur ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;

-- Table: tb_infosociete
CREATE TABLE IF NOT EXISTS public.tb_infosociete (
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
);;

ALTER TABLE IF EXISTS public.tb_infosociete ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_infosociete ADD COLUMN IF NOT EXISTS nomsociete character varying(100);
ALTER TABLE IF EXISTS public.tb_infosociete ADD COLUMN IF NOT EXISTS adressesociete character varying(150);
ALTER TABLE IF EXISTS public.tb_infosociete ADD COLUMN IF NOT EXISTS contactsociete character varying(50);
ALTER TABLE IF EXISTS public.tb_infosociete ADD COLUMN IF NOT EXISTS villesociete character varying(100);
ALTER TABLE IF EXISTS public.tb_infosociete ADD COLUMN IF NOT EXISTS nifsociete character varying(50);
ALTER TABLE IF EXISTS public.tb_infosociete ADD COLUMN IF NOT EXISTS statsociete character varying(50);
ALTER TABLE IF EXISTS public.tb_infosociete ADD COLUMN IF NOT EXISTS cifsociete character varying(50);
ALTER TABLE IF EXISTS public.tb_infosociete ADD COLUMN IF NOT EXISTS ambleme character varying(200);
ALTER TABLE IF EXISTS public.tb_infosociete ADD COLUMN IF NOT EXISTS autre character varying(100);

-- Table: tb_inventaire
CREATE TABLE IF NOT EXISTS public.tb_inventaire (
    id integer NOT NULL,
    qtinventaire double precision,
    observation character varying(100),
    date timestamp without time zone,
    iduser integer,
    idmag integer,
    codearticle character varying(50)
);;

ALTER TABLE IF EXISTS public.tb_inventaire ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_inventaire ADD COLUMN IF NOT EXISTS qtinventaire double precision;
ALTER TABLE IF EXISTS public.tb_inventaire ADD COLUMN IF NOT EXISTS observation character varying(100);
ALTER TABLE IF EXISTS public.tb_inventaire ADD COLUMN IF NOT EXISTS date timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_inventaire ADD COLUMN IF NOT EXISTS iduser integer;
ALTER TABLE IF EXISTS public.tb_inventaire ADD COLUMN IF NOT EXISTS idmag integer;
ALTER TABLE IF EXISTS public.tb_inventaire ADD COLUMN IF NOT EXISTS codearticle character varying(50);

-- Table: tb_inventaire_temporaire
CREATE TABLE IF NOT EXISTS public.tb_inventaire_temporaire (
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
);;

ALTER TABLE IF EXISTS public.tb_inventaire_temporaire ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_inventaire_temporaire ADD COLUMN IF NOT EXISTS date_creation timestamp without time zone DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE IF EXISTS public.tb_inventaire_temporaire ADD COLUMN IF NOT EXISTS date_mise_ajour timestamp without time zone DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE IF EXISTS public.tb_inventaire_temporaire ADD COLUMN IF NOT EXISTS idarticle integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_inventaire_temporaire ADD COLUMN IF NOT EXISTS idunite integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_inventaire_temporaire ADD COLUMN IF NOT EXISTS idmagasin integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_inventaire_temporaire ADD COLUMN IF NOT EXISTS qte_corrige numeric(12,3) NOT NULL;
ALTER TABLE IF EXISTS public.tb_inventaire_temporaire ADD COLUMN IF NOT EXISTS iduser integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_inventaire_temporaire ADD COLUMN IF NOT EXISTS iduserverificateur integer;
ALTER TABLE IF EXISTS public.tb_inventaire_temporaire ADD COLUMN IF NOT EXISTS statut character varying(20) DEFAULT 'Non vérifié'::character varying;
ALTER TABLE IF EXISTS public.tb_inventaire_temporaire ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;
ALTER TABLE IF EXISTS public.tb_inventaire_temporaire ADD COLUMN IF NOT EXISTS observation character varying(255);
ALTER TABLE IF EXISTS public.tb_inventaire_temporaire ADD COLUMN IF NOT EXISTS qt_stock double precision;

-- Table: tb_livraisoncli
CREATE TABLE IF NOT EXISTS public.tb_livraisoncli (
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
);;

ALTER TABLE IF EXISTS public.tb_livraisoncli ADD COLUMN IF NOT EXISTS idlivcli integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_livraisoncli ADD COLUMN IF NOT EXISTS reflivcli character varying(50);
ALTER TABLE IF EXISTS public.tb_livraisoncli ADD COLUMN IF NOT EXISTS refvente character varying(50);
ALTER TABLE IF EXISTS public.tb_livraisoncli ADD COLUMN IF NOT EXISTS idmag integer;
ALTER TABLE IF EXISTS public.tb_livraisoncli ADD COLUMN IF NOT EXISTS idarticle integer;
ALTER TABLE IF EXISTS public.tb_livraisoncli ADD COLUMN IF NOT EXISTS idunite integer;
ALTER TABLE IF EXISTS public.tb_livraisoncli ADD COLUMN IF NOT EXISTS qtlivrecli double precision;
ALTER TABLE IF EXISTS public.tb_livraisoncli ADD COLUMN IF NOT EXISTS dateregistre timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_livraisoncli ADD COLUMN IF NOT EXISTS iduser integer;
ALTER TABLE IF EXISTS public.tb_livraisoncli ADD COLUMN IF NOT EXISTS qtvente double precision;
ALTER TABLE IF EXISTS public.tb_livraisoncli ADD COLUMN IF NOT EXISTS idclient integer;

-- Table: tb_livraisoncli_attente
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
);;

ALTER TABLE IF EXISTS public.tb_livraisoncli_attente ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_livraisoncli_attente ADD COLUMN IF NOT EXISTS refvente character varying(50);
ALTER TABLE IF EXISTS public.tb_livraisoncli_attente ADD COLUMN IF NOT EXISTS idarticle integer;
ALTER TABLE IF EXISTS public.tb_livraisoncli_attente ADD COLUMN IF NOT EXISTS idunite integer;
ALTER TABLE IF EXISTS public.tb_livraisoncli_attente ADD COLUMN IF NOT EXISTS idmag integer;
ALTER TABLE IF EXISTS public.tb_livraisoncli_attente ADD COLUMN IF NOT EXISTS idclient integer;
ALTER TABLE IF EXISTS public.tb_livraisoncli_attente ADD COLUMN IF NOT EXISTS qt_a_livrer double precision;
ALTER TABLE IF EXISTS public.tb_livraisoncli_attente ADD COLUMN IF NOT EXISTS qt_bl double precision DEFAULT 0;
ALTER TABLE IF EXISTS public.tb_livraisoncli_attente ADD COLUMN IF NOT EXISTS statut character varying(20) DEFAULT 'EN_ATTENTE'::character varying;
ALTER TABLE IF EXISTS public.tb_livraisoncli_attente ADD COLUMN IF NOT EXISTS dateregistre timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_livraisoncli_attente ADD COLUMN IF NOT EXISTS iduser integer;

-- Table: tb_livraisonfrs
CREATE TABLE IF NOT EXISTS public.tb_livraisonfrs (
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
);;

ALTER TABLE IF EXISTS public.tb_livraisonfrs ADD COLUMN IF NOT EXISTS idlivfrs integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_livraisonfrs ADD COLUMN IF NOT EXISTS reflivfrs character varying(50);
ALTER TABLE IF EXISTS public.tb_livraisonfrs ADD COLUMN IF NOT EXISTS idcom integer;
ALTER TABLE IF EXISTS public.tb_livraisonfrs ADD COLUMN IF NOT EXISTS idarticle integer;
ALTER TABLE IF EXISTS public.tb_livraisonfrs ADD COLUMN IF NOT EXISTS idunite integer;
ALTER TABLE IF EXISTS public.tb_livraisonfrs ADD COLUMN IF NOT EXISTS qtlivrefrs double precision;
ALTER TABLE IF EXISTS public.tb_livraisonfrs ADD COLUMN IF NOT EXISTS dateregistre timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_livraisonfrs ADD COLUMN IF NOT EXISTS typemouvement integer;
ALTER TABLE IF EXISTS public.tb_livraisonfrs ADD COLUMN IF NOT EXISTS idmag integer;
ALTER TABLE IF EXISTS public.tb_livraisonfrs ADD COLUMN IF NOT EXISTS iduser integer;
ALTER TABLE IF EXISTS public.tb_livraisonfrs ADD COLUMN IF NOT EXISTS factfrs character varying(50);
ALTER TABLE IF EXISTS public.tb_livraisonfrs ADD COLUMN IF NOT EXISTS datepaiement date;
ALTER TABLE IF EXISTS public.tb_livraisonfrs ADD COLUMN IF NOT EXISTS dateperemption date;
ALTER TABLE IF EXISTS public.tb_livraisonfrs ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;
ALTER TABLE IF EXISTS public.tb_livraisonfrs ADD COLUMN IF NOT EXISTS a_payer integer DEFAULT 0;

-- Table: tb_log_evenements
CREATE TABLE IF NOT EXISTS public.tb_log_evenements (
    id_log timestamp with time zone DEFAULT clock_timestamp() NOT NULL,
    description text NOT NULL,
    "user" character varying(150),
    datetime timestamp with time zone DEFAULT now() NOT NULL
);;

ALTER TABLE IF EXISTS public.tb_log_evenements ADD COLUMN IF NOT EXISTS id_log timestamp with time zone DEFAULT clock_timestamp() NOT NULL;
ALTER TABLE IF EXISTS public.tb_log_evenements ADD COLUMN IF NOT EXISTS description text NOT NULL;
ALTER TABLE IF EXISTS public.tb_log_evenements ADD COLUMN IF NOT EXISTS "user" character varying(150);
ALTER TABLE IF EXISTS public.tb_log_evenements ADD COLUMN IF NOT EXISTS datetime timestamp with time zone DEFAULT now() NOT NULL;

-- Table: tb_log_stock
CREATE TABLE IF NOT EXISTS public.tb_log_stock (
    id integer NOT NULL,
    idmag integer,
    ancien_stock double precision,
    nouveau_stock double precision,
    date_action timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    iduser integer,
    type_action character varying(50) DEFAULT 'INVENTAIRE'::character varying,
    codearticle character varying(50)
);;

ALTER TABLE IF EXISTS public.tb_log_stock ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_log_stock ADD COLUMN IF NOT EXISTS idmag integer;
ALTER TABLE IF EXISTS public.tb_log_stock ADD COLUMN IF NOT EXISTS ancien_stock double precision;
ALTER TABLE IF EXISTS public.tb_log_stock ADD COLUMN IF NOT EXISTS nouveau_stock double precision;
ALTER TABLE IF EXISTS public.tb_log_stock ADD COLUMN IF NOT EXISTS date_action timestamp without time zone DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE IF EXISTS public.tb_log_stock ADD COLUMN IF NOT EXISTS iduser integer;
ALTER TABLE IF EXISTS public.tb_log_stock ADD COLUMN IF NOT EXISTS type_action character varying(50) DEFAULT 'INVENTAIRE'::character varying;
ALTER TABLE IF EXISTS public.tb_log_stock ADD COLUMN IF NOT EXISTS codearticle character varying(50);

-- Table: tb_lot_peremption
CREATE TABLE IF NOT EXISTS public.tb_lot_peremption (
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
);;

ALTER TABLE IF EXISTS public.tb_lot_peremption ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_lot_peremption ADD COLUMN IF NOT EXISTS id_article integer;
ALTER TABLE IF EXISTS public.tb_lot_peremption ADD COLUMN IF NOT EXISTS id_unite integer;
ALTER TABLE IF EXISTS public.tb_lot_peremption ADD COLUMN IF NOT EXISTS quantite numeric;
ALTER TABLE IF EXISTS public.tb_lot_peremption ADD COLUMN IF NOT EXISTS date_peremption date;
ALTER TABLE IF EXISTS public.tb_lot_peremption ADD COLUMN IF NOT EXISTS priorite integer;
ALTER TABLE IF EXISTS public.tb_lot_peremption ADD COLUMN IF NOT EXISTS date_entree date;
ALTER TABLE IF EXISTS public.tb_lot_peremption ADD COLUMN IF NOT EXISTS type_source character varying(20);
ALTER TABLE IF EXISTS public.tb_lot_peremption ADD COLUMN IF NOT EXISTS id_source integer;
ALTER TABLE IF EXISTS public.tb_lot_peremption ADD COLUMN IF NOT EXISTS id_split integer;
ALTER TABLE IF EXISTS public.tb_lot_peremption ADD COLUMN IF NOT EXISTS date_creation timestamp without time zone DEFAULT now();
ALTER TABLE IF EXISTS public.tb_lot_peremption ADD COLUMN IF NOT EXISTS note text;
ALTER TABLE IF EXISTS public.tb_lot_peremption ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;
ALTER TABLE IF EXISTS public.tb_lot_peremption ADD COLUMN IF NOT EXISTS idmag integer;

-- Table: tb_magasin
CREATE TABLE IF NOT EXISTS public.tb_magasin (
    idmag integer NOT NULL,
    designationmag character varying(50),
    adressemag character varying(50),
    livraison integer,
    deleted integer DEFAULT 0
);;

ALTER TABLE IF EXISTS public.tb_magasin ADD COLUMN IF NOT EXISTS idmag integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_magasin ADD COLUMN IF NOT EXISTS designationmag character varying(50);
ALTER TABLE IF EXISTS public.tb_magasin ADD COLUMN IF NOT EXISTS adressemag character varying(50);
ALTER TABLE IF EXISTS public.tb_magasin ADD COLUMN IF NOT EXISTS livraison integer;
ALTER TABLE IF EXISTS public.tb_magasin ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;

-- Table: tb_menu
CREATE TABLE IF NOT EXISTS public.tb_menu (
    id integer NOT NULL,
    designationmenu character varying(100),
    page character varying(50)
);;

ALTER TABLE IF EXISTS public.tb_menu ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_menu ADD COLUMN IF NOT EXISTS designationmenu character varying(100);
ALTER TABLE IF EXISTS public.tb_menu ADD COLUMN IF NOT EXISTS page character varying(50);

-- Table: tb_modepaiement
CREATE TABLE IF NOT EXISTS public.tb_modepaiement (
    idmode integer NOT NULL,
    modedepaiement character varying(50)
);;

ALTER TABLE IF EXISTS public.tb_modepaiement ADD COLUMN IF NOT EXISTS idmode integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_modepaiement ADD COLUMN IF NOT EXISTS modedepaiement character varying(50);

-- Table: tb_paiement
CREATE TABLE IF NOT EXISTS public.tb_paiement (
    idpaiement integer NOT NULL,
    paiement character varying(25)
);;

ALTER TABLE IF EXISTS public.tb_paiement ADD COLUMN IF NOT EXISTS idpaiement integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_paiement ADD COLUMN IF NOT EXISTS paiement character varying(25);

-- Table: tb_peremption
CREATE TABLE IF NOT EXISTS public.tb_peremption (
    id integer NOT NULL,
    idcom integer,
    idarticle integer,
    idmag integer,
    dateper timestamp without time zone,
    deleted integer DEFAULT 0
);;

ALTER TABLE IF EXISTS public.tb_peremption ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_peremption ADD COLUMN IF NOT EXISTS idcom integer;
ALTER TABLE IF EXISTS public.tb_peremption ADD COLUMN IF NOT EXISTS idarticle integer;
ALTER TABLE IF EXISTS public.tb_peremption ADD COLUMN IF NOT EXISTS idmag integer;
ALTER TABLE IF EXISTS public.tb_peremption ADD COLUMN IF NOT EXISTS dateper timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_peremption ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;

-- Table: tb_personnel
CREATE TABLE IF NOT EXISTS public.tb_personnel (
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
);;

ALTER TABLE IF EXISTS public.tb_personnel ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_personnel ADD COLUMN IF NOT EXISTS nom character varying(50);
ALTER TABLE IF EXISTS public.tb_personnel ADD COLUMN IF NOT EXISTS prenom character varying(50);
ALTER TABLE IF EXISTS public.tb_personnel ADD COLUMN IF NOT EXISTS datenaissance date;
ALTER TABLE IF EXISTS public.tb_personnel ADD COLUMN IF NOT EXISTS adresse character varying(100);
ALTER TABLE IF EXISTS public.tb_personnel ADD COLUMN IF NOT EXISTS cin character varying(20);
ALTER TABLE IF EXISTS public.tb_personnel ADD COLUMN IF NOT EXISTS contact character varying(50);
ALTER TABLE IF EXISTS public.tb_personnel ADD COLUMN IF NOT EXISTS idfonction integer;
ALTER TABLE IF EXISTS public.tb_personnel ADD COLUMN IF NOT EXISTS matricule character varying(12);
ALTER TABLE IF EXISTS public.tb_personnel ADD COLUMN IF NOT EXISTS sexe character varying(15);
ALTER TABLE IF EXISTS public.tb_personnel ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;

-- Table: tb_pmtavoir
CREATE TABLE IF NOT EXISTS public.tb_pmtavoir (
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
);;

ALTER TABLE IF EXISTS public.tb_pmtavoir ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_pmtavoir ADD COLUMN IF NOT EXISTS datepmt timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_pmtavoir ADD COLUMN IF NOT EXISTS mtpaye double precision;
ALTER TABLE IF EXISTS public.tb_pmtavoir ADD COLUMN IF NOT EXISTS observation character varying(150);
ALTER TABLE IF EXISTS public.tb_pmtavoir ADD COLUMN IF NOT EXISTS idtypeoperation integer DEFAULT 1;
ALTER TABLE IF EXISTS public.tb_pmtavoir ADD COLUMN IF NOT EXISTS deleted integer;
ALTER TABLE IF EXISTS public.tb_pmtavoir ADD COLUMN IF NOT EXISTS refvente character varying(50);
ALTER TABLE IF EXISTS public.tb_pmtavoir ADD COLUMN IF NOT EXISTS refavoir character varying(50);
ALTER TABLE IF EXISTS public.tb_pmtavoir ADD COLUMN IF NOT EXISTS id_banque integer;
ALTER TABLE IF EXISTS public.tb_pmtavoir ADD COLUMN IF NOT EXISTS iduser integer;
ALTER TABLE IF EXISTS public.tb_pmtavoir ADD COLUMN IF NOT EXISTS idmode integer;

-- Table: tb_pmtcom
CREATE TABLE IF NOT EXISTS public.tb_pmtcom (
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
);;

ALTER TABLE IF EXISTS public.tb_pmtcom ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_pmtcom ADD COLUMN IF NOT EXISTS datepmt timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_pmtcom ADD COLUMN IF NOT EXISTS mtpaye double precision;
ALTER TABLE IF EXISTS public.tb_pmtcom ADD COLUMN IF NOT EXISTS observation character varying(150);
ALTER TABLE IF EXISTS public.tb_pmtcom ADD COLUMN IF NOT EXISTS idtypeoperation integer DEFAULT 2;
ALTER TABLE IF EXISTS public.tb_pmtcom ADD COLUMN IF NOT EXISTS idfrs integer;
ALTER TABLE IF EXISTS public.tb_pmtcom ADD COLUMN IF NOT EXISTS refcom character varying(50);
ALTER TABLE IF EXISTS public.tb_pmtcom ADD COLUMN IF NOT EXISTS idmode integer;
ALTER TABLE IF EXISTS public.tb_pmtcom ADD COLUMN IF NOT EXISTS idpaiment integer;
ALTER TABLE IF EXISTS public.tb_pmtcom ADD COLUMN IF NOT EXISTS factfrs character varying(50);
ALTER TABLE IF EXISTS public.tb_pmtcom ADD COLUMN IF NOT EXISTS refpmt character varying(100);
ALTER TABLE IF EXISTS public.tb_pmtcom ADD COLUMN IF NOT EXISTS id_banque integer;
ALTER TABLE IF EXISTS public.tb_pmtcom ADD COLUMN IF NOT EXISTS iduser integer;

-- Table: tb_pmtcredit
CREATE TABLE IF NOT EXISTS public.tb_pmtcredit (
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
);;

ALTER TABLE IF EXISTS public.tb_pmtcredit ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_pmtcredit ADD COLUMN IF NOT EXISTS datepmt timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_pmtcredit ADD COLUMN IF NOT EXISTS mtpaye double precision;
ALTER TABLE IF EXISTS public.tb_pmtcredit ADD COLUMN IF NOT EXISTS observation character varying(150);
ALTER TABLE IF EXISTS public.tb_pmtcredit ADD COLUMN IF NOT EXISTS idtypeoperation integer DEFAULT 1;
ALTER TABLE IF EXISTS public.tb_pmtcredit ADD COLUMN IF NOT EXISTS idclient integer;
ALTER TABLE IF EXISTS public.tb_pmtcredit ADD COLUMN IF NOT EXISTS refvente character varying(50);
ALTER TABLE IF EXISTS public.tb_pmtcredit ADD COLUMN IF NOT EXISTS idmode integer;
ALTER TABLE IF EXISTS public.tb_pmtcredit ADD COLUMN IF NOT EXISTS idpaiment integer;
ALTER TABLE IF EXISTS public.tb_pmtcredit ADD COLUMN IF NOT EXISTS refpmt character varying(50);
ALTER TABLE IF EXISTS public.tb_pmtcredit ADD COLUMN IF NOT EXISTS id_banque integer;
ALTER TABLE IF EXISTS public.tb_pmtcredit ADD COLUMN IF NOT EXISTS iduser integer;

-- Table: tb_pmtfacture
CREATE TABLE IF NOT EXISTS public.tb_pmtfacture (
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
);;

ALTER TABLE IF EXISTS public.tb_pmtfacture ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_pmtfacture ADD COLUMN IF NOT EXISTS datepmt timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_pmtfacture ADD COLUMN IF NOT EXISTS mtpaye double precision;
ALTER TABLE IF EXISTS public.tb_pmtfacture ADD COLUMN IF NOT EXISTS observation character varying(150);
ALTER TABLE IF EXISTS public.tb_pmtfacture ADD COLUMN IF NOT EXISTS idtypeoperation integer DEFAULT 1;
ALTER TABLE IF EXISTS public.tb_pmtfacture ADD COLUMN IF NOT EXISTS refpmt character varying(100);
ALTER TABLE IF EXISTS public.tb_pmtfacture ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;
ALTER TABLE IF EXISTS public.tb_pmtfacture ADD COLUMN IF NOT EXISTS refvente character varying(50);
ALTER TABLE IF EXISTS public.tb_pmtfacture ADD COLUMN IF NOT EXISTS idclient integer;
ALTER TABLE IF EXISTS public.tb_pmtfacture ADD COLUMN IF NOT EXISTS idmode integer;
ALTER TABLE IF EXISTS public.tb_pmtfacture ADD COLUMN IF NOT EXISTS id_banque integer;
ALTER TABLE IF EXISTS public.tb_pmtfacture ADD COLUMN IF NOT EXISTS iduser integer;
ALTER TABLE IF EXISTS public.tb_pmtfacture ADD COLUMN IF NOT EXISTS dateecheance date;

-- Table: tb_pmtsalaire
CREATE TABLE IF NOT EXISTS public.tb_pmtsalaire (
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
);;

ALTER TABLE IF EXISTS public.tb_pmtsalaire ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_pmtsalaire ADD COLUMN IF NOT EXISTS datepmt date;
ALTER TABLE IF EXISTS public.tb_pmtsalaire ADD COLUMN IF NOT EXISTS refpmt character varying(50);
ALTER TABLE IF EXISTS public.tb_pmtsalaire ADD COLUMN IF NOT EXISTS mtpaye double precision;
ALTER TABLE IF EXISTS public.tb_pmtsalaire ADD COLUMN IF NOT EXISTS idtypeoperation integer DEFAULT 2;
ALTER TABLE IF EXISTS public.tb_pmtsalaire ADD COLUMN IF NOT EXISTS idpers integer;
ALTER TABLE IF EXISTS public.tb_pmtsalaire ADD COLUMN IF NOT EXISTS observation character varying(100);
ALTER TABLE IF EXISTS public.tb_pmtsalaire ADD COLUMN IF NOT EXISTS id_banque integer;
ALTER TABLE IF EXISTS public.tb_pmtsalaire ADD COLUMN IF NOT EXISTS idmode integer DEFAULT 1;
ALTER TABLE IF EXISTS public.tb_pmtsalaire ADD COLUMN IF NOT EXISTS iduser integer;

-- Table: tb_presencepers
CREATE TABLE IF NOT EXISTS public.tb_presencepers (
    id integer NOT NULL,
    idpers integer,
    nbheure double precision,
    date timestamp without time zone
);;

ALTER TABLE IF EXISTS public.tb_presencepers ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_presencepers ADD COLUMN IF NOT EXISTS idpers integer;
ALTER TABLE IF EXISTS public.tb_presencepers ADD COLUMN IF NOT EXISTS nbheure double precision;
ALTER TABLE IF EXISTS public.tb_presencepers ADD COLUMN IF NOT EXISTS date timestamp without time zone;

-- Table: tb_prix
CREATE TABLE IF NOT EXISTS public.tb_prix (
    id integer NOT NULL,
    idarticle integer,
    idunite integer,
    prix double precision,
    dateregistre timestamp without time zone,
    iduser integer,
    deleted integer DEFAULT 0
);;

ALTER TABLE IF EXISTS public.tb_prix ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_prix ADD COLUMN IF NOT EXISTS idarticle integer;
ALTER TABLE IF EXISTS public.tb_prix ADD COLUMN IF NOT EXISTS idunite integer;
ALTER TABLE IF EXISTS public.tb_prix ADD COLUMN IF NOT EXISTS prix double precision;
ALTER TABLE IF EXISTS public.tb_prix ADD COLUMN IF NOT EXISTS dateregistre timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_prix ADD COLUMN IF NOT EXISTS iduser integer;
ALTER TABLE IF EXISTS public.tb_prix ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;

-- Table: tb_proforma
CREATE TABLE IF NOT EXISTS public.tb_proforma (
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
);;

ALTER TABLE IF EXISTS public.tb_proforma ADD COLUMN IF NOT EXISTS idprof integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_proforma ADD COLUMN IF NOT EXISTS refprof character varying(50);
ALTER TABLE IF EXISTS public.tb_proforma ADD COLUMN IF NOT EXISTS idclient integer;
ALTER TABLE IF EXISTS public.tb_proforma ADD COLUMN IF NOT EXISTS iduser integer;
ALTER TABLE IF EXISTS public.tb_proforma ADD COLUMN IF NOT EXISTS mtprof double precision;
ALTER TABLE IF EXISTS public.tb_proforma ADD COLUMN IF NOT EXISTS observation character varying(150);
ALTER TABLE IF EXISTS public.tb_proforma ADD COLUMN IF NOT EXISTS dateprof timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_proforma ADD COLUMN IF NOT EXISTS deleted integer;
ALTER TABLE IF EXISTS public.tb_proforma ADD COLUMN IF NOT EXISTS datemodif timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_proforma ADD COLUMN IF NOT EXISTS statut character varying(50);
ALTER TABLE IF EXISTS public.tb_proforma ADD COLUMN IF NOT EXISTS datefacturation timestamp without time zone;

-- Table: tb_proformadetail
CREATE TABLE IF NOT EXISTS public.tb_proformadetail (
    id integer NOT NULL,
    idprof integer,
    idmag integer,
    idarticle integer,
    idunite integer,
    qtprof double precision,
    prixunit double precision,
    qtlivprof double precision,
    total double precision
);;

ALTER TABLE IF EXISTS public.tb_proformadetail ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_proformadetail ADD COLUMN IF NOT EXISTS idprof integer;
ALTER TABLE IF EXISTS public.tb_proformadetail ADD COLUMN IF NOT EXISTS idmag integer;
ALTER TABLE IF EXISTS public.tb_proformadetail ADD COLUMN IF NOT EXISTS idarticle integer;
ALTER TABLE IF EXISTS public.tb_proformadetail ADD COLUMN IF NOT EXISTS idunite integer;
ALTER TABLE IF EXISTS public.tb_proformadetail ADD COLUMN IF NOT EXISTS qtprof double precision;
ALTER TABLE IF EXISTS public.tb_proformadetail ADD COLUMN IF NOT EXISTS prixunit double precision;
ALTER TABLE IF EXISTS public.tb_proformadetail ADD COLUMN IF NOT EXISTS qtlivprof double precision;
ALTER TABLE IF EXISTS public.tb_proformadetail ADD COLUMN IF NOT EXISTS total double precision;

-- Table: tb_salairebasepers
CREATE TABLE IF NOT EXISTS public.tb_salairebasepers (
    id integer NOT NULL,
    idpers integer,
    montant double precision,
    date timestamp without time zone
);;

ALTER TABLE IF EXISTS public.tb_salairebasepers ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_salairebasepers ADD COLUMN IF NOT EXISTS idpers integer;
ALTER TABLE IF EXISTS public.tb_salairebasepers ADD COLUMN IF NOT EXISTS montant double precision;
ALTER TABLE IF EXISTS public.tb_salairebasepers ADD COLUMN IF NOT EXISTS date timestamp without time zone;

-- Table: tb_sortie
CREATE TABLE IF NOT EXISTS public.tb_sortie (
    id integer NOT NULL,
    refsortie character varying(50),
    iduser integer,
    dateregistre timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    description character varying(150),
    deleted integer DEFAULT 0
);;

ALTER TABLE IF EXISTS public.tb_sortie ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_sortie ADD COLUMN IF NOT EXISTS refsortie character varying(50);
ALTER TABLE IF EXISTS public.tb_sortie ADD COLUMN IF NOT EXISTS iduser integer;
ALTER TABLE IF EXISTS public.tb_sortie ADD COLUMN IF NOT EXISTS dateregistre timestamp without time zone DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE IF EXISTS public.tb_sortie ADD COLUMN IF NOT EXISTS description character varying(150);
ALTER TABLE IF EXISTS public.tb_sortie ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;

-- Table: tb_sortiedetail
CREATE TABLE IF NOT EXISTS public.tb_sortiedetail (
    id integer NOT NULL,
    idmag integer,
    idarticle integer,
    idunite integer,
    qtsortie double precision,
    typemouvement integer DEFAULT 2,
    deleted integer DEFAULT 0,
    idsortie integer,
    motif character varying(250)
);;

ALTER TABLE IF EXISTS public.tb_sortiedetail ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_sortiedetail ADD COLUMN IF NOT EXISTS idmag integer;
ALTER TABLE IF EXISTS public.tb_sortiedetail ADD COLUMN IF NOT EXISTS idarticle integer;
ALTER TABLE IF EXISTS public.tb_sortiedetail ADD COLUMN IF NOT EXISTS idunite integer;
ALTER TABLE IF EXISTS public.tb_sortiedetail ADD COLUMN IF NOT EXISTS qtsortie double precision;
ALTER TABLE IF EXISTS public.tb_sortiedetail ADD COLUMN IF NOT EXISTS typemouvement integer DEFAULT 2;
ALTER TABLE IF EXISTS public.tb_sortiedetail ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;
ALTER TABLE IF EXISTS public.tb_sortiedetail ADD COLUMN IF NOT EXISTS idsortie integer;
ALTER TABLE IF EXISTS public.tb_sortiedetail ADD COLUMN IF NOT EXISTS motif character varying(250);

-- Table: tb_stock
CREATE TABLE IF NOT EXISTS public.tb_stock (
    id integer NOT NULL,
    idmag integer,
    qtstock double precision,
    qtalert double precision,
    deleted integer DEFAULT 0,
    codearticle character varying(50)
);;

ALTER TABLE IF EXISTS public.tb_stock ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_stock ADD COLUMN IF NOT EXISTS idmag integer;
ALTER TABLE IF EXISTS public.tb_stock ADD COLUMN IF NOT EXISTS qtstock double precision;
ALTER TABLE IF EXISTS public.tb_stock ADD COLUMN IF NOT EXISTS qtalert double precision;
ALTER TABLE IF EXISTS public.tb_stock ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;
ALTER TABLE IF EXISTS public.tb_stock ADD COLUMN IF NOT EXISTS codearticle character varying(50);

-- Table: tb_suivipresence
CREATE TABLE IF NOT EXISTS public.tb_suivipresence (
    idpresence integer NOT NULL,
    datepresence date NOT NULL,
    idpersonnel integer NOT NULL,
    matin character varying(15) DEFAULT 'en_attente'::character varying,
    apresmidi character varying(15) DEFAULT 'en_attente'::character varying,
    observation character varying(255),
    deleted integer DEFAULT 0,
    dateregistre timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);;

ALTER TABLE IF EXISTS public.tb_suivipresence ADD COLUMN IF NOT EXISTS idpresence integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_suivipresence ADD COLUMN IF NOT EXISTS datepresence date NOT NULL;
ALTER TABLE IF EXISTS public.tb_suivipresence ADD COLUMN IF NOT EXISTS idpersonnel integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_suivipresence ADD COLUMN IF NOT EXISTS matin character varying(15) DEFAULT 'en_attente'::character varying;
ALTER TABLE IF EXISTS public.tb_suivipresence ADD COLUMN IF NOT EXISTS apresmidi character varying(15) DEFAULT 'en_attente'::character varying;
ALTER TABLE IF EXISTS public.tb_suivipresence ADD COLUMN IF NOT EXISTS observation character varying(255);
ALTER TABLE IF EXISTS public.tb_suivipresence ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;
ALTER TABLE IF EXISTS public.tb_suivipresence ADD COLUMN IF NOT EXISTS dateregistre timestamp without time zone DEFAULT CURRENT_TIMESTAMP;

-- Table: tb_tauxhoraire
CREATE TABLE IF NOT EXISTS public.tb_tauxhoraire (
    id integer NOT NULL,
    tauxhoraire double precision,
    idpers integer,
    dateregistre timestamp without time zone
);;

ALTER TABLE IF EXISTS public.tb_tauxhoraire ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_tauxhoraire ADD COLUMN IF NOT EXISTS tauxhoraire double precision;
ALTER TABLE IF EXISTS public.tb_tauxhoraire ADD COLUMN IF NOT EXISTS idpers integer;
ALTER TABLE IF EXISTS public.tb_tauxhoraire ADD COLUMN IF NOT EXISTS dateregistre timestamp without time zone;

-- Table: tb_transfert
CREATE TABLE IF NOT EXISTS public.tb_transfert (
    idtransfert integer NOT NULL,
    reftransfert character varying(50),
    iduser integer,
    idmagsortie integer,
    idmagentree integer,
    dateregistre timestamp without time zone,
    description character varying(150),
    deleted integer DEFAULT 0
);;

ALTER TABLE IF EXISTS public.tb_transfert ADD COLUMN IF NOT EXISTS idtransfert integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_transfert ADD COLUMN IF NOT EXISTS reftransfert character varying(50);
ALTER TABLE IF EXISTS public.tb_transfert ADD COLUMN IF NOT EXISTS iduser integer;
ALTER TABLE IF EXISTS public.tb_transfert ADD COLUMN IF NOT EXISTS idmagsortie integer;
ALTER TABLE IF EXISTS public.tb_transfert ADD COLUMN IF NOT EXISTS idmagentree integer;
ALTER TABLE IF EXISTS public.tb_transfert ADD COLUMN IF NOT EXISTS dateregistre timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_transfert ADD COLUMN IF NOT EXISTS description character varying(150);
ALTER TABLE IF EXISTS public.tb_transfert ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;

-- Table: tb_transfertbanque
CREATE TABLE IF NOT EXISTS public.tb_transfertbanque (
    id integer NOT NULL,
    datepmt date,
    refpmt character varying(50),
    mtpaye double precision,
    idtypeoperation integer,
    observation character varying(100),
    id_banque integer,
    idmode integer,
    iduser integer
);;

ALTER TABLE IF EXISTS public.tb_transfertbanque ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_transfertbanque ADD COLUMN IF NOT EXISTS datepmt date;
ALTER TABLE IF EXISTS public.tb_transfertbanque ADD COLUMN IF NOT EXISTS refpmt character varying(50);
ALTER TABLE IF EXISTS public.tb_transfertbanque ADD COLUMN IF NOT EXISTS mtpaye double precision;
ALTER TABLE IF EXISTS public.tb_transfertbanque ADD COLUMN IF NOT EXISTS idtypeoperation integer;
ALTER TABLE IF EXISTS public.tb_transfertbanque ADD COLUMN IF NOT EXISTS observation character varying(100);
ALTER TABLE IF EXISTS public.tb_transfertbanque ADD COLUMN IF NOT EXISTS id_banque integer;
ALTER TABLE IF EXISTS public.tb_transfertbanque ADD COLUMN IF NOT EXISTS idmode integer;
ALTER TABLE IF EXISTS public.tb_transfertbanque ADD COLUMN IF NOT EXISTS iduser integer;

-- Table: tb_transfertcaisse
CREATE TABLE IF NOT EXISTS public.tb_transfertcaisse (
    id integer NOT NULL,
    datepmt date,
    refpmt character varying(50),
    mtpaye double precision,
    idtypeoperation integer,
    observation character varying(100),
    id_banque integer,
    iduser integer,
    idmode integer
);;

ALTER TABLE IF EXISTS public.tb_transfertcaisse ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_transfertcaisse ADD COLUMN IF NOT EXISTS datepmt date;
ALTER TABLE IF EXISTS public.tb_transfertcaisse ADD COLUMN IF NOT EXISTS refpmt character varying(50);
ALTER TABLE IF EXISTS public.tb_transfertcaisse ADD COLUMN IF NOT EXISTS mtpaye double precision;
ALTER TABLE IF EXISTS public.tb_transfertcaisse ADD COLUMN IF NOT EXISTS idtypeoperation integer;
ALTER TABLE IF EXISTS public.tb_transfertcaisse ADD COLUMN IF NOT EXISTS observation character varying(100);
ALTER TABLE IF EXISTS public.tb_transfertcaisse ADD COLUMN IF NOT EXISTS id_banque integer;
ALTER TABLE IF EXISTS public.tb_transfertcaisse ADD COLUMN IF NOT EXISTS iduser integer;
ALTER TABLE IF EXISTS public.tb_transfertcaisse ADD COLUMN IF NOT EXISTS idmode integer;

-- Table: tb_transfertdetail
CREATE TABLE IF NOT EXISTS public.tb_transfertdetail (
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
);;

ALTER TABLE IF EXISTS public.tb_transfertdetail ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_transfertdetail ADD COLUMN IF NOT EXISTS idarticle integer;
ALTER TABLE IF EXISTS public.tb_transfertdetail ADD COLUMN IF NOT EXISTS idunite integer;
ALTER TABLE IF EXISTS public.tb_transfertdetail ADD COLUMN IF NOT EXISTS qttransfertsortie double precision;
ALTER TABLE IF EXISTS public.tb_transfertdetail ADD COLUMN IF NOT EXISTS qttransfertentree double precision;
ALTER TABLE IF EXISTS public.tb_transfertdetail ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;
ALTER TABLE IF EXISTS public.tb_transfertdetail ADD COLUMN IF NOT EXISTS idtransfert integer;
ALTER TABLE IF EXISTS public.tb_transfertdetail ADD COLUMN IF NOT EXISTS idmagsortie integer;
ALTER TABLE IF EXISTS public.tb_transfertdetail ADD COLUMN IF NOT EXISTS idmagentree integer;
ALTER TABLE IF EXISTS public.tb_transfertdetail ADD COLUMN IF NOT EXISTS qttransfert double precision;
ALTER TABLE IF EXISTS public.tb_transfertdetail ADD COLUMN IF NOT EXISTS description character varying(250);

-- Table: tb_transporteur
CREATE TABLE IF NOT EXISTS public.tb_transporteur (
    idtransporteur integer DEFAULT nextval('public.tb_transporteur_idtransporteur_seq'::regclass) NOT NULL,
    nom character varying(150) NOT NULL,
    contact character varying(100),
    adresse character varying(200),
    deleted integer DEFAULT 0
);;

ALTER TABLE IF EXISTS public.tb_transporteur ADD COLUMN IF NOT EXISTS idtransporteur integer DEFAULT nextval('public.tb_transporteur_idtransporteur_seq'::regclass) NOT NULL;
ALTER TABLE IF EXISTS public.tb_transporteur ADD COLUMN IF NOT EXISTS nom character varying(150) NOT NULL;
ALTER TABLE IF EXISTS public.tb_transporteur ADD COLUMN IF NOT EXISTS contact character varying(100);
ALTER TABLE IF EXISTS public.tb_transporteur ADD COLUMN IF NOT EXISTS adresse character varying(200);
ALTER TABLE IF EXISTS public.tb_transporteur ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;

-- Table: tb_typeclient
CREATE TABLE IF NOT EXISTS public.tb_typeclient (
    idtypeclient integer NOT NULL,
    designationtypeclient character varying(25)
);;

ALTER TABLE IF EXISTS public.tb_typeclient ADD COLUMN IF NOT EXISTS idtypeclient integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_typeclient ADD COLUMN IF NOT EXISTS designationtypeclient character varying(25);

-- Table: tb_typeoperation
CREATE TABLE IF NOT EXISTS public.tb_typeoperation (
    idtypeoperation integer NOT NULL,
    typeoperation character varying(3)
);;

ALTER TABLE IF EXISTS public.tb_typeoperation ADD COLUMN IF NOT EXISTS idtypeoperation integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_typeoperation ADD COLUMN IF NOT EXISTS typeoperation character varying(3);

-- Table: tb_typepmt
CREATE TABLE IF NOT EXISTS public.tb_typepmt (
    idtypepmt integer NOT NULL,
    typepmt character varying(50),
    deleted integer DEFAULT 0
);;

ALTER TABLE IF EXISTS public.tb_typepmt ADD COLUMN IF NOT EXISTS idtypepmt integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_typepmt ADD COLUMN IF NOT EXISTS typepmt character varying(50);
ALTER TABLE IF EXISTS public.tb_typepmt ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;

-- Table: tb_unite
CREATE TABLE IF NOT EXISTS public.tb_unite (
    idunite integer NOT NULL,
    codearticle character varying(20),
    idarticle integer,
    designationunite character varying(50),
    niveau integer,
    qtunite double precision,
    poids double precision,
    deleted integer DEFAULT 0
);;

ALTER TABLE IF EXISTS public.tb_unite ADD COLUMN IF NOT EXISTS idunite integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_unite ADD COLUMN IF NOT EXISTS codearticle character varying(20);
ALTER TABLE IF EXISTS public.tb_unite ADD COLUMN IF NOT EXISTS idarticle integer;
ALTER TABLE IF EXISTS public.tb_unite ADD COLUMN IF NOT EXISTS designationunite character varying(50);
ALTER TABLE IF EXISTS public.tb_unite ADD COLUMN IF NOT EXISTS niveau integer;
ALTER TABLE IF EXISTS public.tb_unite ADD COLUMN IF NOT EXISTS qtunite double precision;
ALTER TABLE IF EXISTS public.tb_unite ADD COLUMN IF NOT EXISTS poids double precision;
ALTER TABLE IF EXISTS public.tb_unite ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;

-- Table: tb_users
CREATE TABLE IF NOT EXISTS public.tb_users (
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
);;

ALTER TABLE IF EXISTS public.tb_users ADD COLUMN IF NOT EXISTS iduser integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_users ADD COLUMN IF NOT EXISTS nomuser character varying(50);
ALTER TABLE IF EXISTS public.tb_users ADD COLUMN IF NOT EXISTS prenomuser character varying(50);
ALTER TABLE IF EXISTS public.tb_users ADD COLUMN IF NOT EXISTS adresseuser character varying(100);
ALTER TABLE IF EXISTS public.tb_users ADD COLUMN IF NOT EXISTS contactuser character varying(50);
ALTER TABLE IF EXISTS public.tb_users ADD COLUMN IF NOT EXISTS username character varying(50);
ALTER TABLE IF EXISTS public.tb_users ADD COLUMN IF NOT EXISTS password character varying(50);
ALTER TABLE IF EXISTS public.tb_users ADD COLUMN IF NOT EXISTS idfonction integer;
ALTER TABLE IF EXISTS public.tb_users ADD COLUMN IF NOT EXISTS idmag integer;
ALTER TABLE IF EXISTS public.tb_users ADD COLUMN IF NOT EXISTS active integer;
ALTER TABLE IF EXISTS public.tb_users ADD COLUMN IF NOT EXISTS dateregistre timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_users ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;

-- Table: tb_vente
CREATE TABLE IF NOT EXISTS public.tb_vente (
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
);;

ALTER TABLE IF EXISTS public.tb_vente ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_vente ADD COLUMN IF NOT EXISTS refvente character varying(50);
ALTER TABLE IF EXISTS public.tb_vente ADD COLUMN IF NOT EXISTS idclient integer;
ALTER TABLE IF EXISTS public.tb_vente ADD COLUMN IF NOT EXISTS iduser integer;
ALTER TABLE IF EXISTS public.tb_vente ADD COLUMN IF NOT EXISTS totmtvente double precision;
ALTER TABLE IF EXISTS public.tb_vente ADD COLUMN IF NOT EXISTS dateregistre timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_vente ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;
ALTER TABLE IF EXISTS public.tb_vente ADD COLUMN IF NOT EXISTS description character varying(150);
ALTER TABLE IF EXISTS public.tb_vente ADD COLUMN IF NOT EXISTS dateupdate timestamp without time zone;
ALTER TABLE IF EXISTS public.tb_vente ADD COLUMN IF NOT EXISTS idmag integer;
ALTER TABLE IF EXISTS public.tb_vente ADD COLUMN IF NOT EXISTS idmode integer;
ALTER TABLE IF EXISTS public.tb_vente ADD COLUMN IF NOT EXISTS statut character varying(20) DEFAULT 'EN_ATTENTE'::character varying;

-- Table: tb_ventedetail
CREATE TABLE IF NOT EXISTS public.tb_ventedetail (
    id integer NOT NULL,
    idmag integer,
    idarticle integer,
    idunite integer,
    qtvente double precision,
    prixunit double precision,
    deleted integer DEFAULT 0,
    idvente integer,
    remise numeric
);;

ALTER TABLE IF EXISTS public.tb_ventedetail ADD COLUMN IF NOT EXISTS id integer NOT NULL;
ALTER TABLE IF EXISTS public.tb_ventedetail ADD COLUMN IF NOT EXISTS idmag integer;
ALTER TABLE IF EXISTS public.tb_ventedetail ADD COLUMN IF NOT EXISTS idarticle integer;
ALTER TABLE IF EXISTS public.tb_ventedetail ADD COLUMN IF NOT EXISTS idunite integer;
ALTER TABLE IF EXISTS public.tb_ventedetail ADD COLUMN IF NOT EXISTS qtvente double precision;
ALTER TABLE IF EXISTS public.tb_ventedetail ADD COLUMN IF NOT EXISTS prixunit double precision;
ALTER TABLE IF EXISTS public.tb_ventedetail ADD COLUMN IF NOT EXISTS deleted integer DEFAULT 0;
ALTER TABLE IF EXISTS public.tb_ventedetail ADD COLUMN IF NOT EXISTS idvente integer;
ALTER TABLE IF EXISTS public.tb_ventedetail ADD COLUMN IF NOT EXISTS remise numeric;

-- Defaults (nextval...)
ALTER TABLE IF EXISTS public.tb_absence ALTER COLUMN id SET DEFAULT nextval('public.tb_absence_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_article ALTER COLUMN idarticle SET DEFAULT nextval('public.tb_article_idarticle_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_autorisation ALTER COLUMN id SET DEFAULT nextval('public.tb_autorisation_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_autre_infos ALTER COLUMN id SET DEFAULT nextval('public.tb_autre_infos_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_autrecreance ALTER COLUMN id SET DEFAULT nextval('public.tb_autrecreance_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_autredette ALTER COLUMN id SET DEFAULT nextval('public.tb_autredette_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_avancepers ALTER COLUMN id SET DEFAULT nextval('public.tb_avancepers_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_avanceprof ALTER COLUMN id SET DEFAULT nextval('public.tb_avanceprof_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_avancespecpers ALTER COLUMN id SET DEFAULT nextval('public.tb_avancespecpers_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_avoir ALTER COLUMN id SET DEFAULT nextval('public.tb_avoir_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_avoirdetail ALTER COLUMN id SET DEFAULT nextval('public.tb_avoirdetail_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_banque ALTER COLUMN id_banque SET DEFAULT nextval('public.tb_banque_id_banque_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_baseliste ALTER COLUMN id SET DEFAULT nextval('public.tb_baseliste_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_categoriearticle ALTER COLUMN idca SET DEFAULT nextval('public.tb_categoriearticle_idca_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_categoriecompte ALTER COLUMN idcc SET DEFAULT nextval('public.tb_categoriecompte_idcc_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_changement ALTER COLUMN idchg SET DEFAULT nextval('public.tb_changement_idchg_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_chat ALTER COLUMN id SET DEFAULT nextval('public.tb_chat_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_client ALTER COLUMN idclient SET DEFAULT nextval('public.tb_client_idclient_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_codeautorisation ALTER COLUMN id SET DEFAULT nextval('public.tb_codeautorisation_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_commande ALTER COLUMN idcom SET DEFAULT nextval('public.tb_commande_idcom_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_commandedetail ALTER COLUMN id SET DEFAULT nextval('public.tb_commandedetail_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_configdb ALTER COLUMN id SET DEFAULT nextval('public.tb_configdb_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_consommationinterne ALTER COLUMN id SET DEFAULT nextval('public.tb_consommationinterne_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_consommationinterne_details ALTER COLUMN id SET DEFAULT nextval('public.tb_consommationinterne_details_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_decaissement ALTER COLUMN id SET DEFAULT nextval('public.tb_decaissement_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_decaissementbq ALTER COLUMN id SET DEFAULT nextval('public.tb_decaissementbq_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_detailchange_entree ALTER COLUMN iddetail SET DEFAULT nextval('public.tb_detailchange_entree_iddetail_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_detailchange_sortie ALTER COLUMN iddetail SET DEFAULT nextval('public.tb_detailchange_sortie_iddetail_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_encaissement ALTER COLUMN id SET DEFAULT nextval('public.tb_encaissement_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_encaissementbq ALTER COLUMN id SET DEFAULT nextval('public.tb_encaissementbq_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_entree ALTER COLUMN id SET DEFAULT nextval('public.tb_entree_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_entreedetail ALTER COLUMN id SET DEFAULT nextval('public.tb_entreedetail_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_evenement ALTER COLUMN id SET DEFAULT nextval('public.tb_evenement_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_facturecli ALTER COLUMN idfact SET DEFAULT nextval('public.tb_facturecli_idfact_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_fonction ALTER COLUMN idfonction SET DEFAULT nextval('public.tb_fonction_idfonction_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_fournisseur ALTER COLUMN idfrs SET DEFAULT nextval('public.tb_fournisseur_idfrs_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_infosociete ALTER COLUMN id SET DEFAULT nextval('public.tb_infosociete_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_inventaire ALTER COLUMN id SET DEFAULT nextval('public.tb_inventaire_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_inventaire_temporaire ALTER COLUMN id SET DEFAULT nextval('public.tb_inventaire_temporaire_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_livraisoncli ALTER COLUMN idlivcli SET DEFAULT nextval('public.tb_livraisoncli_idlivcli_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_livraisoncli_attente ALTER COLUMN id SET DEFAULT nextval('public.tb_livraisoncli_attente_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_livraisonfrs ALTER COLUMN idlivfrs SET DEFAULT nextval('public.tb_livraisonfrs_idlivfrs_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_log_stock ALTER COLUMN id SET DEFAULT nextval('public.tb_log_stock_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_lot_peremption ALTER COLUMN id SET DEFAULT nextval('public.tb_lot_peremption_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_magasin ALTER COLUMN idmag SET DEFAULT nextval('public.tb_magasin_idmag_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_menu ALTER COLUMN id SET DEFAULT nextval('public.tb_menu_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_modepaiement ALTER COLUMN idmode SET DEFAULT nextval('public.tb_modepaiement_idmode_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_paiement ALTER COLUMN idpaiement SET DEFAULT nextval('public.tb_paiement_idpaiement_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_peremption ALTER COLUMN id SET DEFAULT nextval('public.tb_peremption_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_personnel ALTER COLUMN id SET DEFAULT nextval('public.tb_personnel_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_pmtavoir ALTER COLUMN id SET DEFAULT nextval('public.tb_pmtavoir_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_pmtcom ALTER COLUMN id SET DEFAULT nextval('public.tb_pmtcom_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_pmtcredit ALTER COLUMN id SET DEFAULT nextval('public.tb_pmtcredit_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_pmtfacture ALTER COLUMN id SET DEFAULT nextval('public.tb_pmtfacture_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_pmtsalaire ALTER COLUMN id SET DEFAULT nextval('public.tb_pmtsalaire_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_presencepers ALTER COLUMN id SET DEFAULT nextval('public.tb_presencepers_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_prix ALTER COLUMN id SET DEFAULT nextval('public.tb_prix_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_proforma ALTER COLUMN idprof SET DEFAULT nextval('public.tb_proforma_idprof_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_proformadetail ALTER COLUMN id SET DEFAULT nextval('public.tb_proformadetail_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_salairebasepers ALTER COLUMN id SET DEFAULT nextval('public.tb_salairebasepers_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_sortie ALTER COLUMN id SET DEFAULT nextval('public.tb_sortie_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_sortiedetail ALTER COLUMN id SET DEFAULT nextval('public.tb_sortiedetail_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_stock ALTER COLUMN id SET DEFAULT nextval('public.tb_stock_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_suivipresence ALTER COLUMN idpresence SET DEFAULT nextval('public.tb_suivipresence_idpresence_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_tauxhoraire ALTER COLUMN id SET DEFAULT nextval('public.tb_tauxhoraire_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_transfert ALTER COLUMN idtransfert SET DEFAULT nextval('public.tb_transfert_idtransfert_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_transfertbanque ALTER COLUMN id SET DEFAULT nextval('public.tb_transfertbanque_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_transfertcaisse ALTER COLUMN id SET DEFAULT nextval('public.tb_transfertcaisse_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_transfertdetail ALTER COLUMN id SET DEFAULT nextval('public.tb_transfertdetail_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_typeclient ALTER COLUMN idtypeclient SET DEFAULT nextval('public.tb_typeclient_idtypeclient_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_typeoperation ALTER COLUMN idtypeoperation SET DEFAULT nextval('public.tb_typeoperation_idtypeoperation_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_typepmt ALTER COLUMN idtypepmt SET DEFAULT nextval('public.tb_typepmt_idtypepmt_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_unite ALTER COLUMN idunite SET DEFAULT nextval('public.tb_unite_idunite_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_users ALTER COLUMN iduser SET DEFAULT nextval('public.tb_users_iduser_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_vente ALTER COLUMN id SET DEFAULT nextval('public.tb_vente_id_seq'::regclass);
ALTER TABLE IF EXISTS public.tb_ventedetail ALTER COLUMN id SET DEFAULT nextval('public.tb_ventedetail_id_seq'::regclass);
