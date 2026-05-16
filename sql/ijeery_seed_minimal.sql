-- =============================================================================
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
INSERT INTO tb_fonction (idfonction, designationfonction, dateregistre, idautorisation, deleted) VALUES
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

-- Menus exportés depuis sarah_gros
INSERT INTO tb_menu (id, designationmenu, page) VALUES
  (1, 'Caisse', 'PageCaisse'),
  (2, 'TABLEAU DE BORD', 'page_home'),
  (3, 'Article', 'PageArticle'),
  (4, 'Article Liste', 'page_listeArticle'),
  (5, 'Article Fournisseur', 'PageArticleFrs'),
  (6, 'Article Mouvement', 'PageArticleMouvement'),
  (7, 'Avoir', 'PageAvoir'),
  (8, 'Catégorie Articl', 'PageCategorieArticle'),
  (9, 'Catégorie Compt', 'PageCategorieCompte'),
  (10, 'Client', 'PageClient'),
  (11, 'Client Crédi', 'PageClientCredit'),
  (12, 'Commande Frs', 'PageCommandeFrs'),
  (13, 'Config DB', 'DatabaseConfig'),
  (14, 'Decaissement', 'PageDecaissement'),
  (15, 'Encaissement', 'PageEncaissement'),
  (16, 'DecaissementBq', 'PageDecaissementBq'),
  (17, 'EncaissementBq', 'PageEncaissementBq'),
  (18, 'Facture Liste', 'PageFactureListe'),
  (19, 'Fonction', 'PageFonction'),
  (20, 'Fournisseur', 'PageFournisseur'),
  (21, 'Fournisseur Dettes', 'PageFrsDette'),
  (22, 'Information Article', 'PageInfoArticle'),
  (23, 'Bon de Réceptio', 'PageBonReception'),
  (24, 'Magasin', 'PageMagasin'),
  (25, 'Menu', 'PageMenu'),
  (26, 'Paiement Client', 'PagePmtFacture'),
  (27, 'Paiement Fournisseur', 'PagePmtFrs'),
  (28, 'Prix Liste', 'PagePrixListe'),
  (29, 'Prix Saisie', 'PagePrixSaisie'),
  (30, 'Proforma', 'PageCommandeCli'),
  (31, 'Init DB', 'DBInitializerApp'),
  (32, 'Salaire Base', 'PageSalaireBase'),
  (33, 'Sauvegarde', 'PageSauvegarde'),
  (34, 'Sortie Article', 'PageSortie'),
  (35, 'Stock Article', 'PageStock'),
  (36, 'Transfert Article', 'PageTransfert'),
  (37, 'Transfert Banque', 'PageTransfertBanque'),
  (38, 'Transfert Caisse', 'PageTransfertCaisse'),
  (39, 'Taux Horaire', 'PageTauxHoraire'),
  (40, 'Type de paiement', 'PageTypePmt'),
  (41, 'Unité Articl', 'PageUnite'),
  (42, 'Users', 'PageUsers'),
  (43, 'Ventes', 'PageVente'),
  (44, 'Mouvement Stock', 'PageInfoMouvementStock'),
  (45, 'Autorisation', 'PageAutorisation'),
  (46, 'Liste Personnel', 'AppMain'),
  (47, 'Avance 15e', 'PageAVQ'),
  (48, 'Avance Spéciale', 'FenetreAvanceSpec'),
  (49, 'Nouveau SB', 'PageSalaireBase'),
  (50, 'Etat de Salaire', 'PageSalaireEtatSB'),
  (51, 'Salaire Horaire', 'PageEtatSalaireHoraire'),
  (52, 'Paiement Salaire', 'PageValidationSalaire'),
  (53, 'Utilisateurs', 'PageUsers'),
  (54, 'Suivi Commande', 'PageSuiviCommande'),
  (55, 'Prix d''article', 'PagePrixListe'),
  (56, 'Ajout Banque', 'PageBanqueNv'),
  (57, 'Banque', 'PageBanque'),
  (58, 'Base Liste', 'PageBaseListe'),
  (59, 'Ventes par Dépôt', 'PageVenteParMsin'),
  (60, 'Livraison Client', 'PageLivraisonClient'),
  (61, 'Stock Livraison', 'PageStockLivraison'),
  (62, 'Autorisation Admin', 'PageCodeAutorisation'),
  (63, 'Absence', 'PageAbsence'),
  (64, 'Facturation', 'PageFacturation'),
  (65, 'CHAT INTERNE', 'PageChat'),
  (66, 'Mouvement d''article', 'PageArticleMouvement'),
  (67, 'Liste Facture', 'PageFactureListe'),
  (68, 'Liste mouvements', 'PageListeMouvement'),
  (69, 'Prix de revient', 'PagePrixRevient'),
  (70, 'Péremption d''article', 'PageGestionPeremption'),
  (71, 'Stock Alerte', 'PageStockAlerte'),
  (72, 'Inventaire du Jour', 'PageInventaireJour'),
  (73, 'Marge Commerciale', 'PageStock'),
  (74, 'Suivi de présence', 'PageSuiviPresence'),
  (75, 'Gérer Personnels', 'PagePersonnelCRUD'),
  (76, 'Présence Personnel', 'PagePresencePersonnel'),
  (77, 'Présence', 'PagePresence'),
  (78, 'Evenements', 'PageEvenement'),
  (79, 'BLOC: TABLEAU DE BORD', ''),
  (80, 'BLOC: CHAT INTERNE', ''),
  (81, 'BLOC: COMMERCIALE', ''),
  (82, 'BLOC: PERSONNEL', ''),
  (83, 'BLOC: TRÉSORERIE', ''),
  (84, 'BLOC: BASE DE DONNÉES', ''),
  (85, 'Paramètres', ''),
  (86, 'Historiques livraison', ''),
  (87, 'Bon de Livraison', '');

-- Droits administrateur : tous les menus
INSERT INTO tb_autorisation (idfonction, idmenu)
SELECT 1, id FROM tb_menu
WHERE NOT EXISTS (
  SELECT 1 FROM tb_autorisation a WHERE a.idfonction = 1 AND a.idmenu = tb_menu.id
);

INSERT INTO tb_users (
  iduser, nomuser, prenomuser, adresseuser, contactuser,
  username, password, idfonction, idmag, active, dateregistre, deleted
) VALUES (
  1, 'Administrateur', 'Système', '', '',
  'admin', 'admin', 1, 1, 1, CURRENT_TIMESTAMP, 0
);

-- Synchronisation des séquences
SELECT setval('public.tb_autorisation_id_seq', (SELECT COALESCE(MAX(id), 1) FROM tb_autorisation), true);
SELECT setval('public.tb_fonction_idfonction_seq', 1, true);
SELECT setval('public.tb_magasin_idmag_seq', 1, true);
SELECT setval('public.tb_typeoperation_idtypeoperation_seq', 2, true);
SELECT setval('public.tb_modepaiement_idmode_seq', 8, true);
SELECT setval('public.tb_typepmt_idtypepmt_seq', 2, true);
SELECT setval('public.tb_typeclient_idtypeclient_seq', 2, true);
SELECT setval('public.tb_categoriecompte_idcc_seq', 5, true);
SELECT setval('public.tb_categoriearticle_idca_seq', 1, true);
SELECT setval('public.tb_infosociete_id_seq', 1, true);
SELECT setval('public.tb_configdb_id_seq', 1, true);
SELECT setval('public.tb_transporteur_idtransporteur_seq', 1, true);
SELECT setval('public.tb_codeautorisation_id_seq', 1, true);
SELECT setval('public.tb_users_iduser_seq', 1, true);
SELECT setval('public.tb_menu_id_seq', 87, true);
COMMIT;
