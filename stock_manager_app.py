"""
╔══════════════════════════════════════════════════════════════════════════╗
║           APPLICATION DE DÉMONSTRATION — STOCK MANAGER                  ║
║           Toutes les méthodes illustrées avec exemples concrets          ║
╚══════════════════════════════════════════════════════════════════════════╝

Dépendances :
    pip install rich psycopg2-binary

Lancement :
    python stock_manager_app.py
"""

# ─── Imports ──────────────────────────────────────────────────────────────────
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule
from rich import box
from rich.columns import Columns
from rich.padding import Padding
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.live import Live
from rich.spinner import Spinner
from datetime import datetime
import time

# Import du gestionnaire de stock
from stock_manager import StockManager

# ─── Console globale (gère les couleurs et l'affichage) ───────────────────────
console = Console()

# ─── Configuration de la connexion ────────────────────────────────────────────
# ⚙️  Modifiez ces paramètres selon votre environnement
DB_CONFIG = {
    "host"    : "localhost",
    "port"    : 5432,
    "dbname"  : "sarah_gros",        # ← remplacez par le nom de votre base
    "user"    : "postgres",
    "password": "root",     # ← remplacez par votre mot de passe
}


# ══════════════════════════════════════════════════════════════════════════════
#  FONCTIONS D'AFFICHAGE (helpers visuels)
# ══════════════════════════════════════════════════════════════════════════════

def afficher_titre_section(titre: str, icone: str = "📦"):
    """Affiche un titre de section avec une barre colorée."""
    console.print()
    console.print(Rule(f"  {icone}  {titre}  ", style="bold cyan"))
    console.print()


def afficher_succes(message: str):
    """Affiche un message de succès en vert."""
    console.print(f"  [bold green]✅  {message}[/bold green]")


def afficher_erreur(message: str):
    """Affiche un message d'erreur en rouge."""
    console.print(f"  [bold red]❌  {message}[/bold red]")


def afficher_info(message: str):
    """Affiche une information en jaune."""
    console.print(f"  [bold yellow]ℹ️   {message}[/bold yellow]")


def afficher_alerte(message: str):
    """Affiche une alerte en rouge vif."""
    console.print(f"  [bold red on white]🚨  {message}[/bold red on white]")


def attendre_chargement(message: str = "Chargement..."):
    """Affiche un spinner pendant un court délai simulé."""
    with console.status(f"[cyan]{message}[/cyan]", spinner="dots"):
        time.sleep(0.4)


def tableau_vide(message: str = "Aucun résultat trouvé."):
    """Affiche un message quand un tableau est vide."""
    console.print(f"  [dim italic]⚠️  {message}[/dim italic]")
    console.print()


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — CONNEXION
# ══════════════════════════════════════════════════════════════════════════════

def connexion_base(config: dict) -> StockManager:
    """
    Tente de se connecter à la base PostgreSQL.
    Affiche le résultat avec couleur et icône.

    Retourne l'instance StockManager ou None en cas d'échec.
    """
    afficher_titre_section("CONNEXION À LA BASE DE DONNÉES", "🔌")

    console.print(Panel(
        f"[cyan]Hôte    :[/cyan]  [white]{config['host']}:{config['port']}[/white]\n"
        f"[cyan]Base    :[/cyan]  [white]{config['dbname']}[/white]\n"
        f"[cyan]Utilisateur :[/cyan]  [white]{config['user']}[/white]",
        title="[bold blue]Paramètres de connexion[/bold blue]",
        border_style="blue",
        padding=(1, 2),
    ))

    try:
        attendre_chargement("Connexion en cours...")
        sm = StockManager(**config)
        afficher_succes(f"Connexion établie avec succès à '{config['dbname']}'")
        return sm
    except ConnectionError as e:
        afficher_erreur(str(e))
        afficher_info("Vérifiez vos paramètres DB_CONFIG en haut du fichier.")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — UNITÉS D'UN ARTICLE
# ══════════════════════════════════════════════════════════════════════════════

def demo_get_unites_article(sm: StockManager, idarticle: int):
    """
    Affiche les unités d'un article avec leur facteur de conversion.

    Méthode : sm.get_unites_article(idarticle)
    """
    afficher_titre_section("UNITÉS DE MESURE D'UN ARTICLE", "📐")
    afficher_info(f"Article ID = {idarticle} | Toutes les unités avec leur facteur vers la base")

    attendre_chargement("Récupération des unités...")
    unites = sm.get_unites_article(idarticle)

    if not unites:
        tableau_vide(f"Aucune unité trouvée pour l'article {idarticle}.")
        return

    tableau = Table(
        title=f"📐 Unités de l'article #{idarticle}",
        box=box.ROUNDED,
        border_style="cyan",
        header_style="bold white on blue",
        show_lines=True,
    )
    tableau.add_column("ID Unité",         style="dim",         justify="center")
    tableau.add_column("Désignation",      style="bold white",  justify="left")
    tableau.add_column("Niveau",           style="cyan",        justify="center")
    tableau.add_column("Qté / niv. préc.", style="yellow",      justify="center")
    tableau.add_column("Facteur → Base",   style="bold green",  justify="center")

    for u in unites:
        niveau = int(u['niveau'])
        couleur_ligne = "white" if niveau == 0 else "default"
        badge_base = " [bold green](BASE)[/bold green]" if niveau == 0 else ""

        tableau.add_row(
            str(u['idunite']),
            f"[{couleur_ligne}]{u['designationunite']}[/{couleur_ligne}]{badge_base}",
            str(niveau),
            str(u['qtunite']),
            f"[bold green]× {u['facteur_vers_base']:.0f}[/bold green]",
        )

    console.print(tableau)
    console.print()
    afficher_info("Le facteur → Base indique combien d'unités de base représente 1 unité de ce niveau.")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 3 — STOCK EN UNITÉ DE BASE
# ══════════════════════════════════════════════════════════════════════════════

def demo_get_stock_article_base(sm: StockManager, idarticle: int, idmagasin: int = 0):
    """
    Affiche le stock d'un article en unité de base.

    Méthode : sm.get_stock_article_base(idarticle, idmagasin, date_fin)
    """
    afficher_titre_section("STOCK EN UNITÉ DE BASE", "🏷️")
    afficher_info(
        f"Article ID = {idarticle} | "
        f"Magasin = {'TOUS' if idmagasin == 0 else idmagasin}"
    )

    attendre_chargement("Calcul du stock en cours...")

    # Exemple 1 : stock actuel (tous magasins)
    stock = sm.get_stock_article_base(idarticle=idarticle, idmagasin=0)

    # Exemple 2 : stock à une date précise
    stock_historique = sm.get_stock_article_base(
        idarticle=idarticle,
        idmagasin=0,
        date_fin="2025-06-30"
    )

    # Exemple 3 : stock dans un magasin précis
    stock_mag = sm.get_stock_article_base(
        idarticle=idarticle,
        idmagasin=idmagasin,
    ) if idmagasin != 0 else None

    # ── Carte résumé ──────────────────────────────────────────────
    valeur_stock = float(stock.get('stock_en_base', 0))
    couleur_stock = "bold green" if valeur_stock > 0 else "bold red"

    console.print(Panel(
        f"[bold white]Article   :[/bold white]  [cyan]{stock.get('designation', '?')}[/cyan]\n"
        f"[bold white]Unité base:[/bold white]  [yellow]{stock.get('unite_base', '?')}[/yellow]\n"
        f"[bold white]Stock     :[/bold white]  [{couleur_stock}]{valeur_stock:,.2f}[/{couleur_stock}] "
        f"[dim]{stock.get('unite_base', '')}[/dim]\n"
        f"[bold white]Magasin   :[/bold white]  [white]{stock.get('idmagasin', 'TOUS')}[/white]\n"
        f"[bold white]Calculé au:[/bold white]  [dim]{stock.get('date_calcul')}[/dim]",
        title="[bold green]📊 Stock actuel — tous magasins[/bold green]",
        border_style="green",
        padding=(1, 3),
    ))

    # ── Stock historique (à une date passée) ──────────────────────
    val_hist = float(stock_historique.get('stock_en_base', 0))
    console.print(Panel(
        f"[bold white]Stock au 30/06/2025 :[/bold white]  "
        f"[yellow]{val_hist:,.2f}[/yellow] "
        f"[dim]{stock_historique.get('unite_base', '')}[/dim]",
        title="[bold yellow]🕐 Stock à une date passée (date_fin='2025-06-30')[/bold yellow]",
        border_style="yellow",
        padding=(1, 3),
    ))

    # ── Stock magasin précis ───────────────────────────────────────
    if stock_mag:
        val_mag = float(stock_mag.get('stock_en_base', 0))
        console.print(Panel(
            f"[bold white]Magasin #{idmagasin} :[/bold white]  "
            f"[cyan]{val_mag:,.2f}[/cyan] "
            f"[dim]{stock_mag.get('unite_base', '')}[/dim]",
            title=f"[bold cyan]🏪 Stock dans le magasin #{idmagasin}[/bold cyan]",
            border_style="cyan",
            padding=(1, 3),
        ))


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 4 — STOCK CONVERTI PAR UNITÉ
# ══════════════════════════════════════════════════════════════════════════════

def demo_get_stock_article_par_unite(sm: StockManager, idarticle: int, idunite: int):
    """
    Affiche le stock converti dans une unité précise.

    Méthode : sm.get_stock_article_par_unite(idarticle, idunite, idmagasin, date_fin)
    """
    afficher_titre_section("STOCK CONVERTI DANS UNE UNITÉ PRÉCISE", "🔄")
    afficher_info(f"Article ID = {idarticle} | Convertir en idunite = {idunite}")

    attendre_chargement("Conversion en cours...")
    resultat = sm.get_stock_article_par_unite(
        idarticle=idarticle,
        idunite=idunite,
        idmagasin=0,
    )

    stock_base   = float(resultat.get('stock_en_base', 0))
    stock_unite  = int(resultat.get('stock_dans_unite', 0))
    reste_base   = float(resultat.get('reste_en_base', 0))
    facteur      = float(resultat.get('facteur_conversion', 1))
    unite_cible  = resultat.get('designationunite', '?')
    unite_base   = resultat.get('unite_base', '?')

    # Barre visuelle de conversion
    # On échappe les valeurs dynamiques pour éviter que Rich
    # interprète d'éventuels crochets dans les noms d'unités
    from rich.markup import escape as esc
    explication = (
        f"[dim]1 {esc(unite_cible)} = {facteur:.0f} {esc(unite_base)}[/dim]\n"
        f"[dim]Stock total : {stock_base:,.2f} {esc(unite_base)}[/dim]\n\n"
        f"[bold white]Résultat :[/bold white]  "
        f"[bold cyan]{stock_unite}[/bold cyan] [cyan]{esc(unite_cible)}[/cyan]"
        f"  +  "
        f"[yellow]{reste_base:.2f}[/yellow] [dim]{esc(unite_base)}[/dim] [dim](reste)[/dim]"
    )

    console.print(Panel(
        explication,
        title=f"[bold cyan]🔄 Conversion → {esc(unite_cible).upper()}[/bold cyan]",
        border_style="cyan",
        padding=(1, 3),
    ))

    # Tableau récapitulatif
    tableau = Table(box=box.SIMPLE_HEAVY, border_style="dim")
    tableau.add_column("Paramètre",  style="bold white", min_width=25)
    tableau.add_column("Valeur",     style="cyan",       min_width=20)

    tableau.add_row("Article",                 f"{resultat.get('designation', '?')} (#{idarticle})")
    tableau.add_row("Unité cible",             unite_cible)
    tableau.add_row("Facteur de conversion",   f"1 {unite_cible} = {facteur:.0f} {unite_base}")
    tableau.add_row("Stock total (base)",      f"{stock_base:,.2f} {unite_base}")
    tableau.add_row("Stock (unité cible)",     f"[bold green]{stock_unite} {unite_cible}[/bold green]")
    tableau.add_row("Reste (non converti)",    f"[yellow]{reste_base:.2f} {unite_base}[/yellow]")

    console.print(tableau)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 5 — STOCK PAR MAGASIN
# ══════════════════════════════════════════════════════════════════════════════

def demo_get_stock_article_par_magasin(sm: StockManager, idarticle: int):
    """
    Affiche le stock d'un article ventilé par magasin.

    Méthode : sm.get_stock_article_par_magasin(idarticle, date_fin)
    """
    afficher_titre_section("STOCK VENTILÉ PAR MAGASIN", "🏪")
    afficher_info(f"Article ID = {idarticle} | Détail par magasin")

    attendre_chargement("Récupération par magasin...")
    lignes = sm.get_stock_article_par_magasin(idarticle=idarticle)

    if not lignes:
        tableau_vide("Aucun mouvement trouvé pour cet article.")
        return

    tableau = Table(
        title=f"🏪 Stock de l'article #{idarticle} — par magasin",
        box=box.ROUNDED,
        border_style="magenta",
        header_style="bold white on dark_magenta",
        show_lines=True,
    )
    tableau.add_column("ID Mag",       style="dim",           justify="center")
    tableau.add_column("Magasin",      style="bold white",    justify="left")
    tableau.add_column("Stock (base)", style="bold green",    justify="right")
    tableau.add_column("Unité base",   style="yellow",        justify="center")

    total = 0.0
    for ligne in lignes:
        val = float(ligne.get('stock_en_base', 0))
        total += val
        couleur = "bold green" if val > 0 else "bold red"
        tableau.add_row(
            str(ligne.get('idmag', '?')),
            str(ligne.get('designationmag', '?')),
            f"[{couleur}]{val:,.2f}[/{couleur}]",
            str(ligne.get('unite_base', '?')),
        )

    # Ligne total
    tableau.add_row(
        "─", "[bold]TOTAL[/bold]",
        f"[bold cyan]{total:,.2f}[/bold cyan]",
        str(lignes[0].get('unite_base', '?')) if lignes else "",
        style="on grey23",
    )

    console.print(tableau)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 6 — STOCK DE TOUS LES ARTICLES
# ══════════════════════════════════════════════════════════════════════════════

def demo_get_stock_tous_articles(sm: StockManager, idmagasin: int = 0):
    """
    Affiche le stock de tous les articles actifs.

    Méthode : sm.get_stock_tous_articles(idmagasin, date_fin)
    """
    afficher_titre_section("STOCK DE TOUS LES ARTICLES", "📋")
    afficher_info(f"Magasin = {'TOUS' if idmagasin == 0 else idmagasin} | Articles actifs uniquement")

    attendre_chargement("Chargement du stock global...")
    articles = sm.get_stock_tous_articles(idmagasin=idmagasin)

    if not articles:
        tableau_vide("Aucun article trouvé.")
        return

    # Compteurs statistiques
    nb_ok      = sum(1 for a in articles if not a['en_alerte'])
    nb_alerte  = sum(1 for a in articles if a['en_alerte'])
    nb_zero    = sum(1 for a in articles if float(a['stock_en_base']) <= 0)

    # Panneau statistiques
    stats_text = (
        f"[bold white]Total articles :[/bold white]  [cyan]{len(articles)}[/cyan]   "
        f"[bold green]✅ OK : {nb_ok}[/bold green]   "
        f"[bold red]🚨 En alerte : {nb_alerte}[/bold red]   "
        f"[bold red]⬛ Stock nul : {nb_zero}[/bold red]"
    )
    console.print(Panel(stats_text, border_style="dim", padding=(0, 2)))
    console.print()

    tableau = Table(
        title="📋 Stock global — tous les articles",
        box=box.ROUNDED,
        border_style="blue",
        header_style="bold white on navy_blue",
        show_lines=False,
    )
    tableau.add_column("ID",          style="dim",          justify="center", width=6)
    tableau.add_column("Désignation", style="white",        justify="left",   min_width=25)
    tableau.add_column("Catégorie",   style="dim cyan",     justify="left",   min_width=15)
    tableau.add_column("Stock",       style="bold",         justify="right",  width=12)
    tableau.add_column("Unité",       style="yellow",       justify="center", width=10)
    tableau.add_column("Seuil 🔔",   style="dim",          justify="center", width=8)
    tableau.add_column("État",        justify="center",     width=10)

    for a in articles:
        val       = float(a.get('stock_en_base', 0))
        seuil     = float(a.get('seuil_alerte', 0))
        en_alerte = a.get('en_alerte', False)

        if en_alerte and val <= 0:
            couleur_stock = "bold red"
            etat = "[bold red]⬛ VIDE[/bold red]"
        elif en_alerte:
            couleur_stock = "bold red"
            etat = "[bold red]🚨 ALERTE[/bold red]"
        else:
            couleur_stock = "bold green"
            etat = "[bold green]✅ OK[/bold green]"

        tableau.add_row(
            str(a.get('idarticle')),
            str(a.get('designation', '?')),
            str(a.get('categorie') or '-'),
            f"[{couleur_stock}]{val:,.2f}[/{couleur_stock}]",
            str(a.get('unite_base', '?')),
            str(int(seuil)),
            etat,
        )

    console.print(tableau)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 7 — HISTORIQUE DES MOUVEMENTS
# ══════════════════════════════════════════════════════════════════════════════

def demo_get_mouvements_article(
    sm: StockManager,
    idarticle: int,
    idmagasin: int = 0,
    date_debut: str = None,
    date_fin: str = None,
):
    """
    Affiche l'historique de tous les mouvements d'un article.

    Méthode : sm.get_mouvements_article(idarticle, idmagasin, type_mouvement, date_debut, date_fin)
    """
    afficher_titre_section("HISTORIQUE DES MOUVEMENTS", "📜")
    afficher_info(
        f"Article #{idarticle} | "
        f"Magasin : {'TOUS' if idmagasin == 0 else idmagasin} | "
        f"Du {date_debut or '(début)'} au {date_fin or '(aujourd hui)'}"
    )

    # ── Tous les mouvements ──────────────────────────────────────
    attendre_chargement("Chargement de l'historique...")
    mouvements = sm.get_mouvements_article(
        idarticle=idarticle,
        idmagasin=idmagasin,
        date_debut=date_debut,
        date_fin=date_fin,
    )

    if not mouvements:
        tableau_vide("Aucun mouvement enregistré pour cet article.")
        return

    tableau = Table(
        title=f"📜 Historique — Article #{idarticle} ({len(mouvements)} lignes)",
        box=box.ROUNDED,
        border_style="green",
        header_style="bold white on dark_green",
        show_lines=True,
    )
    tableau.add_column("Date",         style="dim",         justify="center", min_width=18)
    tableau.add_column("Type",         style="white",       justify="left",   min_width=18)
    tableau.add_column("Sens",         justify="center",    width=10)
    tableau.add_column("Magasin",      style="cyan",        justify="left",   min_width=15)
    tableau.add_column("Unité",        style="yellow",      justify="center", min_width=10)
    tableau.add_column("Qté orig.",    style="dim",         justify="right",  width=10)
    tableau.add_column("Qté base",     style="bold",        justify="right",  width=12)

    for m in mouvements[:50]:  # Limiter à 50 lignes pour l'affichage
        sens = m.get('sens', '')
        if sens == 'ENTREE':
            badge_sens  = "[bold green]▲ ENTRÉE[/bold green]"
            couleur_qte = "bold green"
            prefixe     = "+"
        else:
            badge_sens  = "[bold red]▼ SORTIE[/bold red]"
            couleur_qte = "bold red"
            prefixe     = "-"

        date_str = str(m.get('date_mouvement', ''))[:16]
        qte_base = float(m.get('quantite_en_base', 0))

        tableau.add_row(
            date_str,
            str(m.get('type_mouvement', '?')),
            badge_sens,
            str(m.get('designationmag', f"Mag #{m.get('idmag', '?')}")),
            str(m.get('designationunite', '?')),
            f"{float(m.get('quantite_originale', 0)):,.2f}",
            f"[{couleur_qte}]{prefixe}{qte_base:,.2f}[/{couleur_qte}]",
        )

    console.print(tableau)

    if len(mouvements) > 50:
        afficher_info(f"Seules les 50 premières lignes affichées sur {len(mouvements)} total.")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 8 — MOUVEMENTS PAR TYPE PRÉCIS
# ══════════════════════════════════════════════════════════════════════════════

def demo_get_mouvements_par_type(
    sm: StockManager,
    idarticle: int,
    type_operation: str = "VENTE",
    date_debut: str = None,
    date_fin: str = None,
):
    """
    Affiche les mouvements filtrés par type précis (ex: VENTE, LIVRAISON…).

    Méthode : sm.get_mouvements_par_type(idarticle, type_operation, ...)
    """
    afficher_titre_section(f"MOUVEMENTS PAR TYPE : {type_operation}", "🔍")
    afficher_info(
        f"Article #{idarticle} | Type = {type_operation} | "
        f"Du {date_debut or '(début)'} au {date_fin or '(aujourd hui)'}"
    )

    # Légende des types disponibles
    console.print(Padding(
        "[dim]Types disponibles :[/dim]  "
        "[green]LIVRAISON  INVENTAIRE  AVOIR  CHANGEMENT_ENTREE  TRANSFERT_ENTREE[/green]  "
        "[red]VENTE  SORTIE  CONSOMMATION  CHANGEMENT_SORTIE  TRANSFERT_SORTIE[/red]",
        pad=(0, 2),
    ))
    console.print()

    attendre_chargement(f"Filtrage des {type_operation}...")
    try:
        mouvements = sm.get_mouvements_par_type(
            idarticle=idarticle,
            type_operation=type_operation,
            date_debut=date_debut,
            date_fin=date_fin,
        )
    except ValueError as e:
        afficher_erreur(str(e))
        return

    if not mouvements:
        tableau_vide(f"Aucun mouvement de type '{type_operation}' trouvé.")
        return

    # Déterminer la couleur selon entrée/sortie
    est_entree = type_operation in sm.TYPES_ENTREE
    couleur_border = "green" if est_entree else "red"
    icone_sens     = "▲ ENTRÉE" if est_entree else "▼ SORTIE"

    total_qte_base = sum(float(m.get('quantite_en_base', 0)) for m in mouvements)

    # Résumé
    console.print(Panel(
        f"[bold white]Type       :[/bold white]  [cyan]{type_operation}[/cyan]\n"
        f"[bold white]Sens       :[/bold white]  "
        f"[{'bold green' if est_entree else 'bold red'}]{icone_sens}[/{'bold green' if est_entree else 'bold red'}]\n"
        f"[bold white]Nb lignes  :[/bold white]  [white]{len(mouvements)}[/white]\n"
        f"[bold white]Total base :[/bold white]  "
        f"[{'bold green' if est_entree else 'bold red'}]{total_qte_base:,.2f}[/{'bold green' if est_entree else 'bold red'}]",
        border_style=couleur_border,
        padding=(1, 3),
    ))

    tableau = Table(
        title=f"🔍 {type_operation} — Article #{idarticle}",
        box=box.SIMPLE_HEAD,
        border_style=couleur_border,
        header_style=f"bold white on {'dark_green' if est_entree else 'dark_red'}",
    )
    tableau.add_column("Date",       style="dim",    justify="center", min_width=18)
    tableau.add_column("Magasin",    style="cyan",   justify="left",   min_width=15)
    tableau.add_column("Unité",      style="yellow", justify="center", min_width=10)
    tableau.add_column("Qté orig.",  style="dim",    justify="right",  width=10)
    tableau.add_column("Qté base",   style=f"bold {'green' if est_entree else 'red'}", justify="right", width=12)

    for m in mouvements[:50]:
        tableau.add_row(
            str(m.get('date_mouvement', ''))[:16],
            str(m.get('designationmag') or f"Mag #{m.get('idmag', '?')}"),
            str(m.get('designationunite', '?')),
            f"{float(m.get('quantite_originale', 0)):,.2f}",
            f"{float(m.get('quantite_en_base', 0)):,.2f}",
        )

    console.print(tableau)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 9 — ARTICLES EN ALERTE
# ══════════════════════════════════════════════════════════════════════════════

def demo_get_articles_en_alerte(sm: StockManager, idmagasin: int = 0):
    """
    Affiche les articles dont le stock est en dessous du seuil d'alerte.

    Méthode : sm.get_articles_en_alerte(idmagasin, date_fin)
    """
    afficher_titre_section("ARTICLES EN ALERTE DE STOCK", "🚨")
    afficher_info(
        f"Magasin = {'TOUS' if idmagasin == 0 else idmagasin} | "
        f"Articles dont stock ≤ seuil d'alerte"
    )

    attendre_chargement("Vérification des alertes...")
    alertes = sm.get_articles_en_alerte(idmagasin=idmagasin)

    if not alertes:
        afficher_succes("✨ Aucun article en alerte ! Tous les stocks sont suffisants.")
        console.print()
        return

    # Bannière d'avertissement
    console.print(Panel(
        f"[bold red]⚠️  {len(alertes)} article(s) nécessitent un réapprovisionnement urgent ![/bold red]",
        border_style="bold red",
        padding=(0, 3),
    ))
    console.print()

    tableau = Table(
        title=f"🚨 Articles en alerte ({len(alertes)} articles)",
        box=box.ROUNDED,
        border_style="red",
        header_style="bold white on dark_red",
        show_lines=True,
    )
    tableau.add_column("ID",          style="dim",        justify="center", width=6)
    tableau.add_column("Désignation", style="bold white", justify="left",   min_width=25)
    tableau.add_column("Stock actuel",style="bold red",   justify="right",  width=14)
    tableau.add_column("Seuil 🔔",   style="yellow",     justify="right",  width=10)
    tableau.add_column("Écart",       style="bold",       justify="right",  width=12)
    tableau.add_column("Unité",       style="dim",        justify="center", width=10)

    for a in alertes:
        stock  = float(a.get('stock_en_base', 0))
        seuil  = float(a.get('seuil_alerte', 0))
        ecart  = float(a.get('ecart_par_rapport_alerte', 0))

        couleur_ecart = "bold red" if ecart < 0 else "yellow"
        icone_critique = "⬛" if stock <= 0 else "🟡"

        tableau.add_row(
            str(a.get('idarticle')),
            f"{icone_critique} {a.get('designation', '?')}",
            f"[bold red]{stock:,.2f}[/bold red]",
            f"{seuil:,.0f}",
            f"[{couleur_ecart}]{ecart:,.2f}[/{couleur_ecart}]",
            str(a.get('unite_base', '?')),
        )

    console.print(tableau)
    afficher_info("L'écart négatif indique le manque par rapport au seuil minimal.")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 10 — RÉSUMÉ SUR UNE PÉRIODE
# ══════════════════════════════════════════════════════════════════════════════

def demo_get_resume_mouvements_periode(
    sm: StockManager,
    idarticle: int,
    date_debut: str,
    date_fin: str,
    idmagasin: int = 0,
):
    """
    Affiche un résumé entrées/sorties/stock net sur une période donnée.

    Méthode : sm.get_resume_mouvements_periode(idarticle, date_debut, date_fin, idmagasin)
    """
    afficher_titre_section("RÉSUMÉ DES MOUVEMENTS SUR UNE PÉRIODE", "📊")
    afficher_info(f"Article #{idarticle} | Du {date_debut} au {date_fin}")

    attendre_chargement("Calcul du résumé...")
    resume = sm.get_resume_mouvements_periode(
        idarticle=idarticle,
        date_debut=date_debut,
        date_fin=date_fin,
        idmagasin=idmagasin,
    )

    stock_debut  = float(resume.get('stock_debut_periode', 0))
    tot_entrees  = float(resume.get('total_entrees_periode', 0))
    tot_sorties  = float(resume.get('total_sorties_periode', 0))
    stock_fin    = float(resume.get('stock_fin_periode', 0))
    unite_base   = resume.get('unite_base', '?')
    detail       = resume.get('detail_par_type', {})

    # ── Panneau principal ─────────────────────────────────────────
    couleur_fin = "bold green" if stock_fin > stock_debut else "bold red"
    fleche = "📈" if stock_fin >= stock_debut else "📉"

    console.print(Panel(
        f"[bold white]Article         :[/bold white]  [cyan]{resume.get('designation', '?')}[/cyan]\n"
        f"[bold white]Période         :[/bold white]  [white]{date_debut}  →  {date_fin}[/white]\n\n"
        f"[bold white]Stock début     :[/bold white]  [yellow]{stock_debut:,.2f} {unite_base}[/yellow]\n"
        f"[bold green]  + Entrées     :[/bold green]  [bold green]+{tot_entrees:,.2f} {unite_base}[/bold green]\n"
        f"[bold red]  - Sorties     :[/bold red]  [bold red]-{tot_sorties:,.2f} {unite_base}[/bold red]\n"
        f"[bold white]────────────────────────────────[/bold white]\n"
        f"[bold white]Stock fin       :[/bold white]  [{couleur_fin}]{fleche} {stock_fin:,.2f} {unite_base}[/{couleur_fin}]",
        title="[bold blue]📊 Bilan de la période[/bold blue]",
        border_style="blue",
        padding=(1, 3),
    ))

    # ── Détail par type de mouvement ──────────────────────────────
    if detail:
        tableau_detail = Table(
            title="🔎 Détail par type de mouvement",
            box=box.SIMPLE_HEAD,
            border_style="dim",
            header_style="bold white",
        )
        tableau_detail.add_column("Type mouvement", style="white",      min_width=22)
        tableau_detail.add_column("Sens",           justify="center",   width=12)
        tableau_detail.add_column("Quantité (base)",style="bold",       justify="right", width=18)

        for type_mvt, quantite in sorted(detail.items()):
            est_entree = type_mvt in sm.TYPES_ENTREE
            badge = "[bold green]▲ ENTRÉE[/bold green]" if est_entree else "[bold red]▼ SORTIE[/bold red]"
            couleur_qte = "bold green" if est_entree else "bold red"
            prefixe = "+" if est_entree else "-"
            tableau_detail.add_row(
                type_mvt,
                badge,
                f"[{couleur_qte}]{prefixe}{float(quantite):,.2f}[/{couleur_qte}]",
            )

        console.print(tableau_detail)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 10 — TRACÉ COMPLET DE TOUS LES MOUVEMENTS D'UN ARTICLE
# ══════════════════════════════════════════════════════════════════════════════

def demo_trace_mouvements_article(
    sm: StockManager,
    idarticle: int,
    date_debut: str = None,
    date_fin: str = None,
):
    """
    Affiche le tracé chronologique complet de tous les mouvements
    d'un article — toutes unités, tous magasins confondus —
    avec le stock cumulé recalculé après chaque mouvement.

    Méthode : sm.get_trace_mouvements_article(idarticle, date_debut, date_fin)
    """
    afficher_titre_section(
        "TRACÉ COMPLET DES MOUVEMENTS — TOUTES UNITÉS & MAGASINS", "🗂️"
    )
    afficher_info(
        f"Article #{idarticle}  |  "
        f"Du {date_debut or '(début)'} au {date_fin or '(aujourd\'hui)'}"
    )

    attendre_chargement("Récupération et calcul du tracé complet...")
    lignes = sm.get_trace_mouvements_article(
        idarticle=idarticle,
        date_debut=date_debut,
        date_fin=date_fin,
    )

    if not lignes:
        tableau_vide("Aucun mouvement trouvé pour cet article.")
        return

    # ── Récupérer l'unité de base pour l'affichage ───────────────
    unite_base_label = ""
    for l in lignes:
        if int(l.get('niveau_unite', 99)) == 0:
            unite_base_label = str(l.get('designation_unite', ''))
            break

    # ── Statistiques rapides ─────────────────────────────────────
    nb_entrees   = sum(1 for l in lignes if l.get('sens') == 'ENTREE')
    nb_sorties   = sum(1 for l in lignes if l.get('sens') == 'SORTIE')
    stock_final  = float(lignes[-1].get('stock_apres_mouvement', 0)) if lignes else 0.0
    designation  = lignes[0].get('designation_article', '?') if lignes else '?'

    couleur_stock_final = "bold green" if stock_final > 0 else "bold red"

    console.print(Panel(
        f"[bold white]Article      :[/bold white]  [cyan]{designation}[/cyan]  "
        f"[dim](#{idarticle})[/dim]\n"
        f"[bold white]Total lignes :[/bold white]  [white]{len(lignes)}[/white]  "
        f"([bold green]▲ {nb_entrees} entrées[/bold green]  /  "
        f"[bold red]▼ {nb_sorties} sorties[/bold red])\n"
        f"[bold white]Stock final  :[/bold white]  "
        f"[{couleur_stock_final}]{stock_final:,.2f}[/{couleur_stock_final}] "
        f"[dim]{unite_base_label}[/dim]",
        title="[bold white]🗂️  Résumé du tracé[/bold white]",
        border_style="cyan",
        padding=(1, 3),
    ))
    console.print()

    # ── Tableau principal ─────────────────────────────────────────
    tableau = Table(
        title=(
            f"🗂️  Tracé complet — {designation}  "
            f"({'du ' + date_debut if date_debut else 'depuis le début'}  →  "
            f"{'au ' + date_fin if date_fin else 'aujourd\'hui'})"
        ),
        box=box.ROUNDED,
        border_style="cyan",
        header_style="bold white on dark_cyan",
        show_lines=True,
        expand=True,
    )

    tableau.add_column("Date & Heure",       style="dim",         justify="center", min_width=17, no_wrap=True)
    tableau.add_column("Code Article",       style="dim yellow",  justify="center", min_width=12, no_wrap=True)
    tableau.add_column("Désignation",        style="bold white",  justify="left",   min_width=20)
    tableau.add_column("Unité",              style="yellow",      justify="center", min_width=10)
    tableau.add_column("Magasin",            style="cyan",        justify="left",   min_width=14)
    tableau.add_column("Type Mouvement",     style="white",       justify="left",   min_width=18)
    tableau.add_column("Sens",               justify="center",    min_width=10)
    tableau.add_column("Quantité",           justify="right",     min_width=10)
    tableau.add_column(
        f"Stock après [{unite_base_label}]",
        justify="right",
        min_width=14,
        style="bold",
    )

    for ligne in lignes:
        sens         = ligne.get('sens', '')
        qte_orig     = float(ligne.get('quantite_originale', 0))
        qte_base     = float(ligne.get('quantite_en_base', 0))
        stock_apres  = float(ligne.get('stock_apres_mouvement', 0))
        type_mvt     = str(ligne.get('type_mouvement', '?'))
        date_str     = str(ligne.get('date_mouvement', ''))[:16]
        mag_label    = str(
            ligne.get('designation_magasin')
            or f"Mag #{ligne.get('idmag', '?')}"
        )

        # ── Couleurs selon le sens ────────────────────────────────
        if sens == 'ENTREE':
            badge_sens   = "[bold green]▲ ENTREE[/bold green]"
            couleur_qte  = "bold green"
            prefixe_qte  = "+"
        else:
            badge_sens   = "[bold red]▼ SORTIE[/bold red]"
            couleur_qte  = "bold red"
            prefixe_qte  = "-"

        # Couleur du stock après mouvement
        if stock_apres <= 0:
            couleur_stock = "bold red"
            icone_stock   = "⬛"
        elif stock_apres < 10:      # seuil bas — ajustez selon vos données
            couleur_stock = "bold yellow"
            icone_stock   = "🟡"
        else:
            couleur_stock = "bold green"
            icone_stock   = "🟢"

        tableau.add_row(
            date_str,
            str(ligne.get('codearticle', '?')),
            str(ligne.get('designation_article', '?')),
            str(ligne.get('designation_unite', '?')),
            mag_label,
            type_mvt,
            badge_sens,
            f"[{couleur_qte}]{prefixe_qte}{qte_orig:,.2f}[/{couleur_qte}]",
            f"[{couleur_stock}]{icone_stock} {stock_apres:,.2f}[/{couleur_stock}]",
        )

    console.print(tableau)
    console.print()

    # ── Note si lignes tronquées ──────────────────────────────────
    afficher_info(
        f"Total : {len(lignes)} mouvement(s) affiché(s).  "
        f"Stock final en unité de base : {stock_final:,.2f} {unite_base_label}"
    )


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 11 — STOCK À UNE DATE & HEURE PRÉCISE
# ══════════════════════════════════════════════════════════════════════════════

def demo_get_stock_a_date_precise(
    sm          : StockManager,
    idarticle   : int,
    idunite     : int,
    idmagasin   : int,
    datetime_c  : str,
):
    """
    Affiche le stock d'un article dans une unité et un magasin précis,
    à un instant exact (date ET heure).

    Méthode : sm.get_stock_a_date_precise(idarticle, idunite, idmagasin, datetime_cible)
    """
    afficher_titre_section("STOCK À UNE DATE & HEURE PRÉCISE", "🎯")
    afficher_info(
        f"Article #{idarticle}  |  Unité #{idunite}  |  "
        f"Magasin #{idmagasin}  |  À : [bold white]{datetime_c}[/bold white]"
    )

    attendre_chargement("Calcul du stock à l'instant demandé...")

    resultat = sm.get_stock_a_date_precise(
        idarticle     = idarticle,
        idunite       = idunite,
        idmagasin     = idmagasin,
        datetime_cible= datetime_c,
    )

    # ── Extraire les valeurs ──────────────────────────────────────
    stock_base    = float(resultat.get('stock_en_base', 0))
    stock_unite   = int(resultat.get('stock_dans_unite', 0))
    reste_base    = float(resultat.get('reste_en_base', 0))
    facteur       = float(resultat.get('facteur_conversion', 1))
    designation   = resultat.get('designation_article') or f'Article #{idarticle}'
    nom_unite     = resultat.get('designation_unite')   or f'Unité #{idunite}'
    nom_mag       = resultat.get('designation_magasin') or f'Magasin #{idmagasin}'
    unite_base_lb = resultat.get('unite_base') or '?'

    from rich.markup import escape as esc

    # ── Couleur selon niveau de stock ────────────────────────────
    if stock_base <= 0:
        couleur_stock = "bold red"
        icone_stock   = "⬛"
        etat_stock    = "STOCK VIDE"
    else:
        couleur_stock = "bold green"
        icone_stock   = "✅"
        etat_stock    = "EN STOCK"

    # ── Panneau principal ─────────────────────────────────────────
    console.print(Panel(
        f"[bold white]Article      :[/bold white]  [cyan]{esc(designation)}[/cyan]  "
        f"[dim](#{idarticle})[/dim]\n"
        f"[bold white]Magasin      :[/bold white]  [cyan]{esc(nom_mag)}[/cyan]  "
        f"[dim](#{idmagasin})[/dim]\n"
        f"[bold white]Unité        :[/bold white]  [yellow]{esc(nom_unite)}[/yellow]  "
        f"[dim](1 {esc(nom_unite)} = {facteur:.0f} {esc(unite_base_lb)})[/dim]\n"
        f"[bold white]Instant      :[/bold white]  [bold white]{esc(datetime_c)}[/bold white]\n\n"
        f"[bold white]─────────────────────────────────────────────[/bold white]\n"
        f"[bold white]Stock base   :[/bold white]  "
        f"[{couleur_stock}]{stock_base:,.2f} {esc(unite_base_lb)}[/{couleur_stock}]\n"
        f"[bold white]Stock unité  :[/bold white]  "
        f"[{couleur_stock}]{stock_unite} {esc(nom_unite)}[/{couleur_stock}]"
        f"  +  [yellow]{reste_base:.2f} {esc(unite_base_lb)}[/yellow] [dim](reste)[/dim]\n"
        f"[bold white]État         :[/bold white]  "
        f"[{couleur_stock}]{icone_stock}  {etat_stock}[/{couleur_stock}]",
        title="[bold white]🎯  Résultat du stock ponctuel[/bold white]",
        border_style="cyan",
        padding=(1, 4),
    ))

    # ── Tableau récapitulatif des paramètres ──────────────────────
    console.print()
    tableau = Table(
        title="🔎 Détail du calcul",
        box=box.SIMPLE_HEAD,
        border_style="dim",
        header_style="bold white",
        min_width=55,
    )
    tableau.add_column("Paramètre",   style="bold white",  min_width=28)
    tableau.add_column("Valeur",      style="cyan",        min_width=25)

    tableau.add_row("Article",             f"{esc(designation)} (#{idarticle})")
    tableau.add_row("Magasin",             f"{esc(nom_mag)} (#{idmagasin})")
    tableau.add_row("Unité demandée",      f"{esc(nom_unite)} (#{idunite})")
    tableau.add_row("Unité de base",       esc(unite_base_lb))
    tableau.add_row("Facteur conversion",  f"1 {esc(nom_unite)} = {facteur:.0f} {esc(unite_base_lb)}")
    tableau.add_row("Instant de référence",esc(datetime_c))
    tableau.add_row("─" * 28,             "─" * 25)
    tableau.add_row(
        "Stock en unité de base",
        f"[{'bold green' if stock_base > 0 else 'bold red'}]{stock_base:,.2f} {esc(unite_base_lb)}[/{'bold green' if stock_base > 0 else 'bold red'}]",
    )
    tableau.add_row(
        f"Stock en {esc(nom_unite)}",
        f"[{'bold green' if stock_unite > 0 else 'bold red'}]{stock_unite} {esc(nom_unite)}[/{'bold green' if stock_unite > 0 else 'bold red'}]",
    )
    tableau.add_row(
        "Reste (non converti)",
        f"[yellow]{reste_base:.2f} {esc(unite_base_lb)}[/yellow]",
    )

    console.print(tableau)
    console.print()
    afficher_info(
        "Le stock est calculé en cumulant tous les mouvements "
        f"jusqu'au {datetime_c} inclus pour le magasin #{idmagasin}."
    )


# ══════════════════════════════════════════════════════════════════════════════
#  MENU INTERACTIF
# ══════════════════════════════════════════════════════════════════════════════

def afficher_menu_principal():
    """Affiche le menu principal de l'application."""
    console.print()
    console.print(Rule(style="bold blue"))
    console.print(Panel(
        "[bold cyan]1[/bold cyan]  📐  Unités de mesure d'un article\n"
        "[bold cyan]2[/bold cyan]  🏷️   Stock en unité de base\n"
        "[bold cyan]3[/bold cyan]  🔄  Stock converti dans une unité précise\n"
        "[bold cyan]4[/bold cyan]  🏪  Stock ventilé par magasin\n"
        "[bold cyan]5[/bold cyan]  📋  Stock de tous les articles\n"
        "[bold cyan]6[/bold cyan]  📜  Historique de tous les mouvements\n"
        "[bold cyan]7[/bold cyan]  🔍  Mouvements par type (VENTE, LIVRAISON…)\n"
        "[bold cyan]8[/bold cyan]  🚨  Articles en alerte de stock\n"
        "[bold cyan]9[/bold cyan]  📊  Résumé sur une période\n"
        "[bold cyan]10[/bold cyan] 🗂️   Tracé complet — tous mouvements + stock après\n"
        "[bold cyan]11[/bold cyan] 🎯  Stock à une date & heure précise\n"
        "[bold cyan]0[/bold cyan]  🚪  Quitter",
        title="[bold white]MENU PRINCIPAL — STOCK MANAGER[/bold white]",
        border_style="bold blue",
        padding=(1, 3),
    ))
    console.print(Rule(style="bold blue"))


def lancer_menu_interactif(sm: StockManager):
    """Boucle principale du menu interactif."""
    while True:
        afficher_menu_principal()
        choix = Prompt.ask(
            "\n  [bold cyan]Votre choix[/bold cyan]",
            choices=["0","1","2","3","4","5","6","7","8","9","10","11"],
        )

        if choix == "0":
            afficher_succes("À bientôt ! Fermeture de l'application.")
            sm.fermer_connexion()
            break

        # Saisie des paramètres communs
        if choix in ["1","2","3","4","6","7","9","10"]:
            idarticle = IntPrompt.ask("  [yellow]ID Article[/yellow]", default=1)

        if choix == "1":
            demo_get_unites_article(sm, idarticle)

        elif choix == "2":
            idmag = IntPrompt.ask("  [yellow]ID Magasin (0=tous)[/yellow]", default=0)
            demo_get_stock_article_base(sm, idarticle, idmag)

        elif choix == "3":
            idunite = IntPrompt.ask("  [yellow]ID Unité cible[/yellow]", default=1)
            demo_get_stock_article_par_unite(sm, idarticle, idunite)

        elif choix == "4":
            demo_get_stock_article_par_magasin(sm, idarticle)

        elif choix == "5":
            idmag = IntPrompt.ask("  [yellow]ID Magasin (0=tous)[/yellow]", default=0)
            demo_get_stock_tous_articles(sm, idmag)

        elif choix == "6":
            idmag     = IntPrompt.ask("  [yellow]ID Magasin (0=tous)[/yellow]", default=0)
            date_deb  = Prompt.ask("  [yellow]Date début AAAA-MM-JJ (Enter=aucune)[/yellow]", default="")
            date_fin  = Prompt.ask("  [yellow]Date fin   AAAA-MM-JJ (Enter=aucune)[/yellow]", default="")
            demo_get_mouvements_article(
                sm, idarticle, idmag,
                date_deb or None,
                date_fin or None,
            )

        elif choix == "7":
            console.print(
                "  [dim]Types : LIVRAISON | INVENTAIRE | AVOIR | CHANGEMENT_ENTREE | "
                "TRANSFERT_ENTREE | VENTE | SORTIE | CONSOMMATION | "
                "CHANGEMENT_SORTIE | TRANSFERT_SORTIE[/dim]"
            )
            type_op  = Prompt.ask("  [yellow]Type de mouvement[/yellow]", default="VENTE")
            date_deb = Prompt.ask("  [yellow]Date début (Enter=aucune)[/yellow]", default="")
            date_fin = Prompt.ask("  [yellow]Date fin   (Enter=aucune)[/yellow]", default="")
            demo_get_mouvements_par_type(
                sm, idarticle, type_op.upper(),
                date_deb or None,
                date_fin or None,
            )

        elif choix == "8":
            idmag = IntPrompt.ask("  [yellow]ID Magasin (0=tous)[/yellow]", default=0)
            demo_get_articles_en_alerte(sm, idmag)

        elif choix == "9":
            idmag    = IntPrompt.ask("  [yellow]ID Magasin (0=tous)[/yellow]", default=0)
            date_deb = Prompt.ask("  [yellow]Date début AAAA-MM-JJ[/yellow]", default="2025-01-01")
            date_fin = Prompt.ask("  [yellow]Date fin   AAAA-MM-JJ[/yellow]", default="2025-12-31")
            demo_get_resume_mouvements_periode(sm, idarticle, date_deb, date_fin, idmag)

        elif choix == "10":
            date_deb = Prompt.ask(
                "  [yellow]Date début AAAA-MM-JJ (Enter=aucune)[/yellow]", default=""
            )
            date_fin = Prompt.ask(
                "  [yellow]Date fin   AAAA-MM-JJ (Enter=aucune)[/yellow]", default=""
            )
            demo_trace_mouvements_article(
                sm, idarticle,
                date_deb or None,
                date_fin or None,
            )

        elif choix == "11":
            idarticle   = IntPrompt.ask("  [yellow]ID Article[/yellow]",          default=1)
            idunite     = IntPrompt.ask("  [yellow]ID Unité[/yellow]",             default=1)
            idmagasin   = IntPrompt.ask("  [yellow]ID Magasin[/yellow]",           default=1)
            datetime_c  = Prompt.ask(
                "  [yellow]Date & Heure  AAAA-MM-JJ HH:MM:SS[/yellow]",
                default=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            demo_get_stock_a_date_precise(sm, idarticle, idunite, idmagasin, datetime_c)

        # Pause avant de retourner au menu
        console.print()
        Prompt.ask("  [dim]Appuyez sur Entrée pour continuer…[/dim]", default="")


# ══════════════════════════════════════════════════════════════════════════════
#  POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════════════════════════

def main():
    """Point d'entrée principal de l'application."""

    # ── Bannière de démarrage ──────────────────────────────────────
    console.print()
    console.print(Panel(
        Text.assemble(
            ("  ╔══════════════════════════════════════╗\n", "bold blue"),
            ("  ║  ", "bold blue"),
            ("📦  STOCK MANAGER  ", "bold white"),
            ("                    ║\n", "bold blue"),
            ("  ║  ", "bold blue"),
            ("Application de démonstration         ", "dim white"),
            ("║\n", "bold blue"),
            ("  ╚══════════════════════════════════════╝", "bold blue"),
        ),
        border_style="bright_blue",
        padding=(1, 5),
    ))

    console.print(Padding(
        "[dim]Toutes les méthodes du StockManager illustrées avec couleurs et tableaux.[/dim]",
        pad=(0, 4),
    ))
    console.print()

    # ── Connexion ──────────────────────────────────────────────────
    sm = connexion_base(DB_CONFIG)
    if sm is None:
        console.print()
        afficher_erreur("Impossible de démarrer : connexion échouée.")
        afficher_info("Modifiez DB_CONFIG en haut du fichier, puis relancez.")
        return

    # ── Menu interactif ────────────────────────────────────────────
    lancer_menu_interactif(sm)


if __name__ == "__main__":
    main()