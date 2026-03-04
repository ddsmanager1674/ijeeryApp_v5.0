# Implémentation du Menu "Prix de Revient"

## Résumé des modifications

Ajout d'un nouveau menu **"Prix de Revient"** dans la section **Commerciale** pour consulter la liste des prix de revient (coûts d'achat) des articles auprès des fournisseurs.

## Fichiers créés et modifiés

### 1. **CRÉÉ: `pages/page_prixRevient.py`** (Nouvelle page)
   - **Classe**: `PagePrixRevient(ctk.CTkFrame)`
   - **Fonctionnalités**:
     - Tableau principal avec 5 colonnes:
       - **Code Article**: Code numérique affiché sur 10 caractères (formaté)
       - **Désignation**: Nom de l'article
       - **Unité**: Unité de vente/stockage
       - **Fournisseur**: Dernier fournisseur ayant livré cet article
       - **Dernier Prix**: Dernier prix de retient enregistré
     
     - **Système de recherche**: Barre de recherche pour filtrer par:
       - Code article
       - Désignation
       - Fournisseur
       - Description ou wording
     
     - **Filtres avancés** (frame supérieur):
       - Combo-box "Fournisseur" - Filtre par fournisseur spécifique
       - Combo-box "Unité" - Filtre par unité de vente
       - Bouton "Actualiser" - Rechargement des données
     
     - **Design**:
       - Lignes alternées (blanc/bleu clair) pour meilleure lisibilité
       - Lignes en rouge pour les prix à zéro
       - Scrollbars verticals et horizontaux
       - Font moderne "Segoe UI"
     
     - **Base de données**:
       - Récupère le dernier fournisseur via jointure sur `tb_livraisonfrs` et `tb_commande`
       - Récupère les prix depuis `tb_prix` (table des prix de vente)
       - Affiche "Aucun fournisseur" si aucune livraison n'existe

### 2. **MODIFIÉ: `app_main.py`**

   **Ligne ~76**: Ajout de l'import
   ```python
   from pages.page_prixRevient import PagePrixRevient
   ```

   **Ligne ~393**: Ajout du mapping dans `page_mapping`
   ```python
   "PagePrixRevient" : PagePrixRevient,
   ```

   **Ligne ~1375-1378**: Ajout du bouton menu dans `show_commerciale_submenu()`
   ```python
   if "Prix de revient" in self.authorized_menus:
       btn_pr = ctk.CTkButton(self.admin_submenu_frame, text="📊 Prix de Revient", 
                              corner_radius=10, height=40,
                              fg_color="#034787", text_color="white", 
                              hover_color="#0565c9", font=("Arial", 12), 
                              command=lambda: self.show_page(self.page_mapping["PagePrixRevient"]))
       btn_pr.pack(pady=2, padx=5, fill="x")
   ```

## Comment activer le menu

Le menu "Prix de Revient" s'affichera dans le menu **Commerciale** seulement si l'utilisateur a la permission **"Prix de revient"** assignée dans la base de données des permissions.

### Options:
1. **Ajouter via la base de dados**:
   - Ajouter une entrée dans la table `tb_menu` avec:
     - `designationmenu = "Prix de revient"`
     - `page = "page_prixRevient"`
   
   - Ajouter la permission dans les autorisations de l'utilisateur/rôle

2. **Ou modifier le code** (Développement uniquement):
   - Si vous désirez que le menu soit toujours visible, changez:
   ```python
   if "Prix de revient" in self.authorized_menus:
   ```
   en:
   ```python
   if True:  # Always show for testing
   ```

## Requête SQL utilisée

```sql
SELECT 
    LPAD(u.codearticle::TEXT, 10, '0') as code,
    a.designation,
    u.designationunite,
    COALESCE(f.nomFrs, 'Aucun fournisseur') as fournisseur,
    COALESCE(p.prix, 0) as dernier_prix
FROM tb_unite u
INNER JOIN tb_article a ON u.idarticle = a.idarticle
LEFT JOIN tb_prix p ON u.idunite = p.idunite
LEFT JOIN (
    -- Récupérer le dernier fournisseur pour chaque article/unité via les commandes
    SELECT DISTINCT ON (lf.idunite)
        lf.idunite,
        com.idfrs,
        com.dateCom
    FROM tb_livraisonfrs lf
    INNER JOIN tb_commande com ON lf.idCom = com.idCom
    WHERE com.deleted = 0
    ORDER BY lf.idunite, com.dateCom DESC
) derniere_livraison ON u.idunite = derniere_livraison.idunite
LEFT JOIN tb_fournisseur f ON derniere_livraison.idfrs = f.idfrs
WHERE a.deleted = 0 AND u.deleted = 0
```

## Fonctionnalités détaillées

### Recherche
- Recherche en temps réel (on KeyRelease)
- Insensible à la casse
- Wildcards automatiques (% avant et après le terme)

### Filtres
- **Filtre Fournisseur**: Affiche uniquement les articles du fournisseur sélectionné
- **Filtre Unité**: Affiche uniquement les articles avec l'unité sélectionnée
- Les deux filtres peuvent être combinés
- Le combo fournisseurs se charge automatiquement depuis la base de données

### Affichage des données
- Chargement asynchrone dans un thread séparé pour ne pas bloquer l'interface
- Compteur d'articles affichant le nombre de résultats
- Protection contre les destructions multiples du widget
- Gestion des widgets non-existants

### Formatage
- Les prix sont formatés au format français: `1 234,56`
- Les prix à zéro sont affichés en rouge
- Les codes articles sont affichés sur 10 caractères (LPAD)

## Notes d'implémentation

1. **Pas de double-clic pour édition**: Contrairement à `PagePrixListe`, cette page de visualisation n'ouvre pas d'écran d'édition au double-clic.

2. **Source des prix**: Les prix affichés proviennent de la table `tb_prix` qui est répartie selon les unités. Pour avoir un prix de revient accurate, il faudrait potentiellement avoir une table dédiée aux coûts d'achat (actuellement, la structure DB n'a pas de colonne prix dans `tb_livraisonfrs` ou `tb_commandeDetail`).

3. **Fournisseur**: Le fournisseur affiché est le dernier à avoir livré cet article (dernière commande + livraison).

## Tests recommandés

1. Vérifier les permissions de l'utilisateur ont accès à "Prix de revient"
2. Tester la recherche avec différents termes
3. Tester les filtres individuellement et combinés
4. Tester le tri (clic sur les en-têtes si applicable)
5. Tester le rechargement des données

## Considérations futures

- Ajouter la possibilité de modifier les prix de revient directement
- Ajouter un historique des prix de revient
- Implémenter une colonne de prix d'achat dans `tb_livraisonfrs` ou `tb_commandeDetail`
- Ajouter l'export des données (PDF, Excel)
- Ajouter des graphiques de tendances de prix
