# 📦 FORMULE CORRECTE DU CALCUL DE STOCK

## 🎯 FORMULE GÉNÉRALE

```
STOCK_AFFICHÉ = RÉSERVOIR_COMMUN ÷ COEFFICIENT_HIÉRARCHIQUE
```

Où :

### RÉSERVOIR_COMMUN (solde_base)
```
RÉSERVOIR = (REC + TIN + INV + AVO) - (VEN + SOR + TOUT)

Avec tous les mouvements convertis en UNITÉ DE BASE
```

### Mouvements (7 sources)

| Type | Opération | Source | Formule |
|------|-----------|--------|---------|
| **REC** (Réception) | **+** | tb_livraisonfrs | `qtlivrefrs × qtunite_source` |
| **VEN** (Vente) | **−** | tb_ventedetail | `qtvente × qtunite_source` |
| **SOR** (Sortie) | **−** | tb_sortiedetail | `qtsortie × qtunite_source` |
| **TIN** (Transfert IN) | **+** | tb_transfertdetail (idmagentree) | `qttransfert × qtunite_source` |
| **TOUT** (Transfert OUT) | **−** | tb_transfertdetail (idmagsortie) | `qttransfert × qtunite_source` |
| **INV** (Inventaire) | **+** | tb_inventaire | `qtinventaire × qtunite_source` |
| **AVO** (Avoir) | **+** | tb_avoirdetail | `qtavoir × qtunite_source` |

#### ⚠️ Notes importantes :
- **AVO (Avoirs)** : AUGMENTENT le stock car ils annulent des ventes (retour de marchandises)
- **qtunite_source** : Le coefficient de conversion de l'unité source
- **Inventaires** : Comptés UNE SEULE FOIS par article (via l'unité de base)

---

## 🔄 COEFFICIENT HIÉRARCHIQUE

### Concept

Quand un article a plusieurs unités avec hiérarchie :
- U1 : PIECE (qtunite = 1)
- U2 : BOITE (qtunite = 10) → 1 BOITE = 10 PIECE
- U3 : CARTON (qtunite = 50) → 1 CARTON = 50 PIECE = 5 BOITE

### Calcul du coefficient

```
coeff_hierarchique = ∏ qtunite[1..n]  (produit cumulatif)
```

Exemple hiérarchique multi-niveau :
- U1 (niveau 0) : coeff = 1
- U2 (niveau 1) : coeff = 1 × 10 = 10
- U3 (niveau 2) : coeff = 10 × 50 = 500

### Application

Pour afficher le stock en unité U_i :

```
Stock_Ui = RÉSERVOIR / coeff_hierarchique[i]
```

Exemple numérique :
- Réservoir = 10 000 PIECE
- Stock en PIECE : 10 000 / 1 = 10 000 PIECE
- Stock en BOITE : 10 000 / 10 = 1 000 BOITE
- Stock en CARTON : 10 000 / 500 = 20 CARTON

---

## 📊 ALGORITHME COMPLET

```
ÉTAPE 1 : Récupérer toutes les unités de l'article
  └─ Pour chaque unité : récupérer designation, qtunite, niveau

ÉTAPE 2 : Récupérer tous les mouvements (7 types)
  ├─ Pour chaque mouvement : récupérer quantité, unité_source
  └─ Convertir en unité de base : quantité × qtunite_source

ÉTAPE 3 : Calculer le solde_base par (idarticle, idmag)
  └─ Formule : SUM(entrées convertis) - SUM(sorties convertis)
     Où entrées = REC + TIN + INV + AVO
     Et  sorties = VEN + SOR + TOUT

ÉTAPE 4 : Calculer le coefficient hiérarchique pour chaque unité
  └─ coeff[i] = exp( SUM ( ln(qtunite[j]) ) pour j de 0 à i )

ÉTAPE 5 : Afficher le stock pour chaque unité
  └─ Stock_Ui = solde_base ÷ coeff[i]
```

---

## 🧮 EXEMPLE COMPLET

**Article** : Code '0070374501' (Désignation: "Aiguille")
**Magasin** : 1

### Étape 1 : Les unités de l'article

| Unité | qtunite | Coefficient |
|-------|---------|------------|
| PIECE | 1 | 1 |
| BOITE | 50 | 50 |
| CARTON | 10 | 500 |

### Étape 2 : Tous les mouvements (en unité source)

**Réceptions** (tb_livraisonfrs) :
- PIECE : 100
- BOITE : 2

**Ventes validées** (tb_ventedetail) :
- PIECE : 50
- BOITE : 1

**Transferts IN** : 0

**Transferts OUT** : 0

**Sorties** (tb_sortiedetail) :
- PIECE : 10

**Inventaires** (tb_inventaire) :
- PIECE : 3

**Avoirs** (tb_avoirdetail) : 0

### Étape 3 : Convertir en unité de base

| Mouvement | Type | Quantité | qtunite_source | Quantité convertis |
|-----------|------|----------|-----------------|-------------------|
| Réception PIECE | + | 100 | 1 | +100 |
| Réception BOITE | + | 2 | 50 | +100 |
| Vente PIECE | − | 50 | 1 | −50 |
| Vente BOITE | − | 1 | 50 | −50 |
| Sortie PIECE | − | 10 | 1 | −10 |
| Inventaire PIECE | + | 3 | 1 | +3 |

### Étape 4 : Calculer le solde_base

```
solde_base = (100 + 100 + 3 + 0) - (50 + 50 + 10 + 0)
           = 203 - 110
           = 93 PIECE (dans le réservoir)
```

### Étape 5 : Afficher le stock par unité

| Unité | Coefficient | Calcul | Stock affiché |
|-------|-------------|--------|---------------|
| PIECE | 1 | 93 ÷ 1 | **93 PIECE** |
| BOITE | 50 | 93 ÷ 50 | **1,86 BOITE** |
| CARTON | 500 | 93 ÷ 500 | **0,186 CARTON** |

---

## ✅ POINTS CLÉS

1. **Un seul réservoir commun** pour toutes les unités d'un même article dans un magasin
2. **Toutes les unités partagent le même solde** via conversion en unité de base
3. **Les avoirs AUGMENTENT** le stock (annulation de vente)
4. **Inventaires comptés UNE FOIS** via l'unité de base uniquement
5. **Coefficient hiérarchique** = produit cumulatif des qtunite de la chaîne
6. **Division finale** = solde_base ÷ coeff[unité_affichée]

---

## 🔗 IMPLÉMENTATION SQL (PostgreSQL)

Voir les fichiers :
- `REQUETE_AFFICHAGE_STOCK.sql` → Tableau complet
- `REQUETE_STOCK_UN_ARTICLE.sql` → Debugg d'un article
- `GUIDE_REQUETES_STOCK.sql` → Documentation avec exemples

---

## 🚀 DANS LE CODE PYTHON

La fonction `calculer_stock_article_reel()` dans `page_pmtFacture.py` implémente cette formule exactement :

1. Boucle sur chaque unité de l'article
2. Récupère les 7 types de mouvements
3. Applique le coefficient qtunite_source lors de la somme
4. Calcule solde_base pour ce mouvement
5. Divise par le coefficient hiérarchique
6. Retourne le stock affiché
