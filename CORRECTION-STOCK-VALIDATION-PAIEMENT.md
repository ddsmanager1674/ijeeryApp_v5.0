# 🔧 CORRECTION CRITIQUE - Incohérence Stock Validation Paiement

## 🚨 Problème Identifié

Lors de la validation d'une facture EN_ATTENTE via double-clic dans `page_factureListe.py`:
- ❌ Erreur "Stock insuffisant" s'affiche même si `page_stock.py` montre du stock disponible
- ❌ Les ventes sont validées alors qu'il y a assez de stock
- ❌ **CAUSE RACINE**: Incohérence entre le calcul du stock dans deux pages

## 🎯 Cause Racine Découverte

### Dans `page_stock.py` (CORRECT ✅)
```python
# Ligne 193
INNER JOIN tb_vente v ON vd.idvente = v.id AND v.deleted = 0 AND v.statut = 'VALIDEE'
```
**Logique**: Compter **UNIQUEMENT** les ventes VALIDÉE

### Dans `page_pmtFacture.py` (INCORRECT ❌ - AVANT)
```python
# Avant correction
cursor.execute(
    "SELECT COALESCE(SUM(qtvente), 0) FROM tb_ventedetail 
     WHERE idarticle = %s AND idunite = %s AND deleted = 0 AND idmag = %s",
    (idarticle, idu_boucle, idmag)
)
```
**Logique**: Compter **TOUTES** les ventes (EN_ATTENTE + VALIDÉE + autres)

## 🔴 Conséquence - Scénario Concret

**Situation initiale:**
- Stock physique = 100 unités
- Facture F1 créée (EN_ATTENTE) : 50 unités
- Aucune vente validée yet

**Affichages observations:**
1. **page_stock.py** (correct):
   - Calcul: 100 - (ventes VALIDÉE seulement = 0) = **100 unités disponibles** ✅
   
2. **page_pmtFacture.py** (avant correction):
   - Calcul: 100 - (TOUTES ventes = 50 de F1 EN_ATTENTE) = **50 unités** ❌
   - Conclusion: "Stock insuffisant pour la facture F1" (même si on a 100!) ❌

**PARADOXE**: La facture qu'on essaye de valider était ELLE-MÊME compté comme vente déjà effectuée!

## ✅ Correction Appliquée

### Avant (BUGUÉ)
```python
cursor.execute(
    "SELECT COALESCE(SUM(qtvente), 0) FROM tb_ventedetail 
     WHERE idarticle = %s AND idunite = %s AND deleted = 0 AND idmag = %s",
    (idarticle, idu_boucle, idmag)
)
ventes = cursor.fetchone()[0] or 0
```

### Après (CORRECT)
```python
# Ventes (UNIQUEMENT VALIDÉES - cohérent avec page_stock.py)
cursor.execute(
    """SELECT COALESCE(SUM(vd.qtvente), 0) 
       FROM tb_ventedetail vd 
       INNER JOIN tb_vente v ON vd.idvente = v.id 
       WHERE vd.idarticle = %s AND vd.idunite = %s AND vd.deleted = 0 
       AND v.deleted = 0 AND v.statut = 'VALIDEE' AND v.idmag = %s""",
    (idarticle, idu_boucle, idmag)
)
ventes = cursor.fetchone()[0] or 0
print(f"  📤 Ventes (tb_ventedetail - VALIDÉE uniquement): {ventes}")
```

## 📋 Changements Effectués

| Fichier | Ligne | Modification |
|---------|-------|--------------|
| `pages/page_pmtFacture.py` | ~192 | Ajout JOIN tb_vente + filtre statut VALIDEE |
| `dist/iJeery_V5.0/_internal/pages/page_pmtFacture.py` | ~192 | Identical correction (version compilée) |

## 🔄 Impact du Flux de Vente

### Avant la correction
```
Vendeur crée facture EN_ATTENTE (50 unités)
           ↓
Caissier double-clic pour valider
           ↓
✅ ventes = 50 (de cette facture EN_ATTENTE)
❌ Stock calculé = 100 - 50 = 50 restant
❌ Si facture demande > 50, ERREUR
❌ MÊME SI le stock physique = 100 !
```

### Après la correction
```
Vendeur crée facture EN_ATTENTE (50 unités)
           ↓
Caissier double-clic pour valider
           ↓
✅ ventes = 0 (EN_ATTENTE pas comptée)
✅ Stock calculé = 100 - 0 = 100 disponible
✅ facture de 50 unités → ACCEPTÉE ✅
```

## 🧪 Test de Validation

Pour vérifier la correction fonctionne:

1. **Créer une facture EN_ATTENTE** pour article X avec 50 unités
   - Supposons stock disponible = 100

2. **Double-clic la facture** dans `page_factureListe.py`

3. **Résultat attendu** (après correction):
   - ✅ Pas d'erreur "Stock insuffisant"
   - ✅ Montant = correct
   - ✅ Stock = 100 disponible (pas 50)
   - ✅ Validation du paiement réussit

4. **Cache synchronisé**:
   - Stock final après validation = 100 - 50 = 50 ✅

## 📊 Cohérence Garantie

Après cette correction:
- ✅ **page_stock.py** : Stock disponible (ventes VALIDÉE uniquement)
- ✅ **page_pmtFacture.py** : Stock disponible (ventes VALIDÉE uniquement)
- ✅ **Même formule**: (REC + TIN + INV + AVO) - (VEN_VALIDEE + SOR + TOUT)

## 💡 Leçon Apprise

**L'incohérence provenait de:**
1. Deux pages calculant le stock différemment
2. Une incluant les ventes EN_ATTENTE, l'autre non
3. Résultat: Une facture EN_ATTENTE était comptée DANS LE CALCUL où elle devrait être VALIDÉE

**La solution:**
- Tous les calculs doivent filtrer sur `v.statut = 'VALIDEE'`
- Un seul réservoir de stock cohérent
- Pas de double-comptage

---

**Status**: ✅ CORRIGÉ  
**Version**: 2026-02-14  
**Fichiers modifiés**: 2 (source + dist)
