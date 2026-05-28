## Scripts SQL iJeery (V5.0)

Ce dossier contient les scripts SQL “officiels” du projet. L’objectif est de savoir **quoi exécuter**, **quand**, et **dans quel ordre**.

### Ordre recommandé

- **Base neuve (recommandé)**:
  1) `ijeery_schema_vide.sql`
  2) `ijeery_seed_minimal.sql`

- **Base existante (déjà en prod / déjà utilisée)**:
  - `script_de_mis_a_jour.sql`
  - (optionnel) `_menus_admin_export.sql` si tu veux réinjecter menus/droits.

---

### `ijeery_schema_vide.sql` — structure complète, base vierge

- **But**: crée toute la structure PostgreSQL (tables, séquences, contraintes, index) avec **0 donnée métier**.
- **À utiliser quand**: tu crées une **nouvelle base** iJeery.
- **Attention**: ce script fait `DROP SCHEMA public CASCADE` puis recrée `public` → **destructif** (à ne pas lancer sur une base déjà utilisée).

Exécution (exemple):

```bash
psql -U postgres -d ijeery_vierge -f sql/ijeery_schema_vide.sql
```

---

### `ijeery_seed_minimal.sql` — données minimales de démarrage

- **But**: insère les données minimales (référentiels + menus + droits admin + utilisateur `admin`).
- **À utiliser quand**: juste après `ijeery_schema_vide.sql`.
- **Remarque**: contient un **compte par défaut** `admin/admin` (à changer après installation).

Exécution (exemple):

```bash
psql -U postgres -d ijeery_vierge -f sql/ijeery_seed_minimal.sql
```

---

### `script_de_mis_a_jour.sql` — migration / alignement d’une base existante

- **But**: mettre à jour une base existante pour la rendre compatible avec la version courante du logiciel.
- **Contenu**: création de tables manquantes, ajout de colonnes, ajout de contraintes/index, ajustements ciblés.
- **Propriété**: majoritairement **idempotent** (`IF NOT EXISTS`, blocs `DO $$ ... $$`) → peut être relancé sans casser si déjà appliqué.
- **À utiliser quand**: tu as une base déjà en service et tu déploies une nouvelle version.

Exécution (exemple):

```bash
psql -v ON_ERROR_STOP=1 -U postgres -d ijeery_votre_base -f sql/script_de_mis_a_jour.sql
```

---

### `_menus_admin_export.sql` — menus + autorisations (export)

- **But**: injecter (ou réinjecter) la liste des menus (`tb_menu`) et une base d’autorisations (`tb_autorisation`).
- **À utiliser quand**:
  - tu veux mettre à jour les menus/droits sans rejouer tout le `seed`,
  - ou tu as besoin de recharger rapidement la configuration “menus admin”.
- **Attention**: ce script fait des `INSERT` “en dur”. Sur une base déjà configurée, ça peut provoquer des doublons/conflits selon l’état.

Exécution (exemple):

```bash
psql -v ON_ERROR_STOP=1 -U postgres -d ijeery_votre_base -f sql/_menus_admin_export.sql
```

