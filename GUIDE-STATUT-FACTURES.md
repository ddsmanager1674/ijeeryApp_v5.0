# 📖 Guide Utilisateur - Système de Statut des Factures

## 📑 Table des Matières
1. [Vue d'ensemble](#overview)
2. [Accès à la liste des factures](#access)
3. [Filtrage par statut](#filtering)
4. [Actions disponibles](#actions)
5. [Types de statuts](#statuses)
6. [Exemples pratiques](#examples)

---

## <a id="overview"></a>1️⃣ Vue d'ensemble

Le système de gestion des statuts de factures vous permet de:
- 📊 Voir le statut de chaque facture en un coup d'œil
- 🔍 Filtrer les factures par statut
- 📄 Réimprimer les factures validées
- ❌ Annuler les factures en attente
- 📈 Gérer efficacement votre flux de facturation

---

## <a id="access"></a>2️⃣ Accès à la Liste des Factures

### Chemin d'Accès
```
Menu Principal → Facturation → 📋 Liste des Factures (Archives)
```

### Interface Principale

La fenêtre Liste des Factures contient:

1. **Barre de Recherche en haut:** Recherche textuelle, sélection de dates, **filtre statut**
2. **Tableau principal:** Affichage de toutes les factures filtrées
3. **Colonne "Statut":** La 5ème colonne affiche l'état de chaque facture

---

## <a id="filtering"></a>3️⃣ Filtrage par Statut

### Étapes

1. **Localiser le dropdown "Statut"** dans la barre de recherche (en haut à gauche)
   
2. **Cliquer sur le dropdown** pour voir les options disponibles:
   - `Tout` - Affiche toutes les factures (quel que soit le statut)
   - `Validé` - Affiche UNIQUEMENT les factures confirmées (défaut)
   - `En attente` - Affiche les factures en cours de traitement
   - `Annulé` - Affiche les factures annulées/invalidées

3. **Sélectionner le statut désiré**
   - Le tableau se met à jour automatiquement
   - Les factures correspondantes s'affichent

### Exemple
```
Vous voulez voir UNIQUEMENT les factures en attente de paiement:
1. Dropdown "Statut" → Sélectionner "En attente"
2. Le tableau affiche uniquement les factures avec statut "En attente"
```

---

## <a id="actions"></a>4️⃣ Actions Disponibles

### Actions sur le Tableau Principal

| Action | Description |
|--------|-------------|
| 🔍 **Filtrer** | Actualise le tableau avec les critères de recherche |
| 📊 **Excel** | Exporte tous les résultats en fichier Excel |

### Actions sur les Factures Individuelles

**Double-cliquez** sur une facture pour ouvrir sa fenêtre de détails:

#### Si Statut = "Validé" ✅
```
Bouton disponible: 🖨️ Réimprimer (Duplicata)
Fonction: Génère un PDF avec la mention "DUPLICATA"
Raison: Vous avez besoin une copie de la facture (bordereau, pièce jointe, etc.)
```

#### Si Statut = "En attente" ⏳
```
Bouton disponible: ❌ Annuler Facture
Fonction: Marque la facture comme annulée dans le système
Raison: La facture contient une erreur ou ne doit pas être traitée
Confirmation requise: OUI (pour éviter les annulations accidentelles)
```

#### Si Statut = "Annulé" ❌
```
Aucun bouton d'action
Affichage: ⚠️ Facture Annulée (message informatif)
Raison: La facture ne peut plus être modifiée, c'est un état final
```

---

## <a id="statuses"></a>5️⃣ Types de Statuts

### 📋 État: "En attente" ⏳

**Signification:** La facture est en cours de traitement/validation

**Caractéristiques:**
- 🔴 Non encore confirmée au client
- ⏱️ En attente de vérification
- 🎯 Actions possibles: Annuler

**Transition vers:** "Validé" (par validation en base de données)

**Exemple:**
```
Une facture vient d'être créée → Statut automatique: "En attente"
L'utilisateur la valide → Statut passe à: "Validé"
```

---

### ✅ État: "Validé"

**Signification:** La facture est confirmée et officialisée

**Caractéristiques:**
- 🟢 Facture confirmée
- ✔️ Peut être réimprimée à tout moment
- 🎯 Actions possibles: Réimprimer (Duplicata)

**Transition vers:** "Annulé" (manuelle si erreur)

**Exemple:**
```
La facture a été validée par le responsable → Statut: "Validé"
Un client demande une copie → Bouton "Réimprimer" disponible
```

---

### ❌ État: "Annulé"

**Signification:** La facture a été invalidée et n'est plus valide

**Caractéristiques:**
- 🔴 Facture supprimée logiquement
- 🔒 Non modifiable
- ⛔ Aucune action possible

**Comment y arriver:**
1. Ou la facture était en "En attente" → utilisateur clique "Annuler"
2. Ou une merveille administrative → statut changé manuellement en base

**Exemple:**
```
Une facture avait une erreur → Utilisateur la sélectionne → Clique "Annuler"
Statut passe à "Annulé" → Message: "⚠️ Facture Annulée"
```

---

## <a id="examples"></a>6️⃣ Exemples Pratiques

### Scénario 1: Réimprimer une Facture Validée

```
Situation: Un client demande une copie d'une facture déjà confirmée

Étapes:
1. Ouvrir "Liste des Factures (Archives)" du menu
2. Le filtre par défaut est "Validé" ✅
3. Rechercher la facture (par numéro ou nom du client)
4. Double-cliquer sur la facture
5. Fenêtre de détail s'ouvre
6. Cliquer sur 🖨️ "Réimprimer (Duplicata)"
7. Fichier PDF généré automatiquement sur le Bureau
8. Le PDF s'ouvre et peut être imprimé

Résultat: Un PDF avec la mention "DUPLICATA" en rouge
```

### Scénario 2: Annuler une Facture en Attente

```
Situation: Un facture contient une erreur et doit être annulée

Étapes:
1. Ouvrir "Liste des Factures (Archives)"
2. Dropdown "Statut" → Sélectionner "En attente"
3. Rechercher la facture défectueuse
4. Double-cliquer sur la facture
5. Fenêtre de détail s'ouvre
6. Cliquer sur ❌ "Annuler Facture"
7. Dialog: "Voulez-vous annuler cette facture ?"
8. Répondre OUI pour confirmer
9. Succès! Facture annulée

Changements observés:
- Statut passe à "Annulé"
- La liste des factures se recharge automatiquement
- Aucun bouton n'est plus disponible
```

### Scénario 3: Filtrer par Statut pour Étude

```
Situation: Vous devez analyser les factures en attente de paiement

Étapes:
1. Ouvrir "Liste des Factures (Archives)"
2. Dropdown "Statut" → Sélectionner "En attente"
3. Ajouter un filtre de date pour un mois spécifique
4. Cliquer sur 🔍 "Filtrer"
5. Le tableau montre UNIQUEMENT les factures de ce mois avec statut "En attente"

Résultat: Vous voyez clairement quelles factures sont en cours de traitement
```

---

## ⚙️ Paramètres Techniques

### Valeurs de Statut dans la Base de Données
Les trois statuts autorisés sont:
- `"Validé"`
- `"En attente"`
- `"Annulé"`

**Important:** Les majuscules et accents doivent correspondre exactement pour qu'une facture s'affiche dans le filtre.

### Statut par Défaut
Quand vous ouvrez la liste des factures:
- 🔵 Le dropdown "Statut" est pré-rempli avec: **"Validé"**
- 🎯 Cela affiche UNIQUEMENT les factures validées (plus pratique pour l'utilisateur)

### Comportement du Filtrage
```
Avant: Vous voyez TOUTES les factures (quel que soit le statut)
Après: Vous voyez UNIQUEMENT celles du statut sélectionné
```

---

## 📝 Notes Importantes

1. **Confirmation obligatoire:** L'annulation demande toujours une confirmation pour éviter les accidents

2. **Recharge automatique:** Après une annulation, la liste se recharge automatiquement

3. **Pas de modification directe:** Vous ne pouvez pas modifier le statut directement dans le tableau
   - Pour annuler: Double-cliquez → Bouton "Annuler"
   - Pour valider: Modification en base de données seulement

4. **PDF Duplicata:** Le label "DUPLICATA" est apposé automatiquement sur chaque réimpression (visible en rouge)

5. **Historique:** Les factures annulées restent visibles si vous sélectionnez le filtre "Annulé"
   - Elles ne disparaissent jamais (audit trail important)

---

## 🆘 Aide & Dépannage

### Je ne vois pas le bouton "Annuler Facture"
**Raison:** La facture n'a pas le statut "En attente"
**Solution:** Vérifiez le statut de la facture (colonne "Statut" du tableau)

### Le tableau ne se met pas à jour quand je change le filtre
**Raison:** Peut-être un problème de calcul
**Solution:** Cliquez sur le bouton 🔍 "Filtrer" pour forcer la mise à jour

### Je n'arrive pas à annuler une facture
**Causes possibles:**
- La facture n'est pas en statut "En attente"
- Problème de connexion à la base de données
- Permissions insuffisantes

**Solution:** Contactez votre administrateur si le problème persiste

---

## 📞 Support

Pour toute question ou problème:
- 📧 Email: [Support Email]
- 📞 Téléphone: [Support Phone]
- 💬 Chat: [Support Chat Link]

---

**Document créé:** 2026-02-06  
**Dernière mise à jour:** 2026-02-06  
**Version:** 1.0
