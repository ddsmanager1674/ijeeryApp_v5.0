# Analyse - Page Article Mouvement

## 🎯 Objectif
Afficher l'historique complet des mouvements de stock avec filtrage par article, type de document, magasin et plage de dates.

---

## 📊 Structure Actuelle

### Tables Sources (7 types de mouvements)
| Type | Table Source | détail | Logique |
|------|---|---|---|
| **Entrée** | tb_livraisonfrs | Livraisons des fournisseurs | Augmente le stock |
| **Sortie** | tb_sortie + tb_sortiedetail | Sorties générales | Diminue le stock |
| **Vente** | tb_vente + tb_ventedetail | Sorties via facturation | Diminue le stock |
| **Transfert** | tb_transfert (2 mouvements) | Inter-magasins (sortie + entrée) | Sortie d'un magasin, entrée dans un autre |
| **Inventaire** | tb_inventaire | Ajustements d'inventaire | Augmente/diminue selon observation |
| **Avoir** | tb_avoir + tb_avoirdetail | Retours clients | Augmente le stock |

### Colonnes du Tableau
```
Date | Référence | Désignation Article | Unité | Entrée | Sortie | Solde | Magasin | Utilisateur
```

### Filtres Disponibles
1. **Recherche Article** - Dynamique (nom ou code)
2. **Type de Document** - ComboBox (Tous, Entrée, Sortie, Vente, Transfert, Inventaire, Avoir)
3. **Magasin** - ComboBox (dynamique depuis tb_magasin)
4. **Dates** - DateEntry début/fin
5. **Bouton** - "Appliquer filtres"

---

## ⚠️ Problèmes Identifiés

### 1. **Recherche d'Article Inefficace**
- ❌ `<KeyRelease>` déclenche `filtrer_article_dynamique()` à CHAQUE frappe
- ❌ Cela appelle `load_mouvements()` qui recharge L'ENTIER tableau
- ❌ Requêtes répétées à chaque caractère tapé

**Impact**: Lenteur, charge DB excessive

### 2. **Requêtes SQL Non Optimisées**
- ❌ 7 requêtes distinctes (une par type) exécutées séquentiellement
- ❌ Tri des mouvements EN PYTHON (`sort()`) après récupération
- ❌ Pas de LIMIT sur les résultats
- ❌ JOIN inutiles quand article est sélectionné

**Impact**: Temps de requête long, "gel" de l'application

### 3. **Gestion Cohérence Données**
- ❌ Indices des tuples fragiles (8-9 colonnes selon requête)
- ❌ Pas de validation article_sélectionné avant chargement
- ❌ Conversion d'unités récalculée à CHAQUE mouvement

**Impact**: Risque de bugs après modifications

### 4. **Filtres Non Synchronisés**
- ✅ Bouton "Appliquer filtres" existe et appelle `load_mouvements()`
- ❌ Recherche d'article se déclenche indépendamment du bouton
- ❌ Pas de feedback utilisateur pendant le chargement

**Impact**: UX confuse, attentes non alignées

---

## ✅ Solutions Proposées

### 1. **Recherche d'Article**
```python
# AVANT: <KeyRelease> -> filtrer_article_dynamique() -> load_mouvements()
# APRÈS: 
# - <Enter> ou clic bouton "Rechercher" -> filtrer_article_dynamique()
# - Sinon réinitialiser à la saisie si besoin
```

### 2. **Requêtes SQL Optimisées**
```sql
-- Utiliser UNION pour combiner les 7 mouvement types en UNE seule requête
-- Trier EN SQL (ORDER BY date)
-- Utiliser LIMIT si nécessaire
```

### 3. **Structure Tuple Unifiée**
```python
# Tous les mouvements retournent: 
# (date, reference, article_designation, type_doc, entree, sortie, magasin, user, idunite)
# Index: 0, 1, 2, 3, 4, 5, 6, 7, 8
```

### 4. **Filtres Synchronisés**
```
Recherche Article (KeyRelease) -> Recharge si article trouvé
+ Type Doc (ComboBox, pas auto-run)
+ Magasin (ComboBox, pas auto-run)
+ Dates (DateEntry)
↓
Bouton "Appliquer filtres" -> load_mouvements() avec TOUS les filtres
```

---

## 📋 Checklist Fixes

- [ ] Supprimer `<KeyRelease>` du champ recherche article
- [ ] Ajouter bouton "Rechercher" ou utiliser `<Return>` key
- [ ] Créer requête UNION combinée pour tous les mouvements
- [ ] Standardiser les indices des tuples
- [ ] Ajouter spinner/loader pendant chargement
- [ ] Tester cohérence des données
- [ ] Tester tous les filtres

---

## 🔍 Structure Requête UNION Proposée

```sql
SELECT 
    date, 
    reference, 
    article_designation, 
    'Type',  -- 'Entrée', 'Sortie', 'Vente', etc
    COALESCE(entree, 0),
    COALESCE(sortie, 0),
    magasin,
    username,
    idunite
FROM (
    SELECT ... FROM tb_livraisonfrs   -- Entrées
    UNION ALL
    SELECT ... FROM tb_sortie         -- Sorties
    UNION ALL
    ...
) AS mouvements
WHERE DATE BETWEEN ? AND ?
  AND (article: %s OU NULL)
  AND (type: %s OU NULL)
  AND (magasin: %s OU NULL)
ORDER BY date ASC, reference
```

---

## 🎨 UX/UX Améliorations

1. **Feedback clairs**: "Chargement en cours..." spinner
2. **Validation**: Message si aucun mouvement trouvé
3. **Cohérence**: Tous les filtres se déclenchent ensemble via le bouton
4. **Performance**: Requêtes < 1s
5. **Accessibilité**: Touches raccourcies (Enter pour recherche)
