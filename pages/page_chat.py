# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              iJeery — pages/page_chat.py                                    ║
║              Messagerie Interne — Style Google Chat                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ARCHITECTURE                                                               ║
║  ┌─────────────────────────────────────────────────────────────────────┐   ║
║  │ Col 0 (w=280)          │ Col 1 (weight=1)                           │   ║
║  │ ┌──────────────────┐   │ ┌─────────────────────────────────────┐   │   ║
║  │ │ Bandeau MIDNIGHT │   │ │ Bandeau entête conversation         │   │   ║
║  │ │ Avatar + Nom     │   │ ├─────────────────────────────────────┤   │   ║
║  │ ├──────────────────┤   │ │                                     │   │   ║
║  │ │ Barre recherche  │   │ │  Zone messages (bulles)  weight=1   │   │   ║
║  │ ├──────────────────┤   │ │                                     │   │   ║
║  │ │                  │   │ ├─────────────────────────────────────┤   │   ║
║  │ │ Liste contacts   │   │ │ Zone saisie + bouton Envoyer        │   │   ║
║  │ │ (scrollable)     │   │ └─────────────────────────────────────┘   │   ║
║  │ └──────────────────┘   └─────────────────────────────────────────  │   ║
║  └─────────────────────────────────────────────────────────────────────┘   ║
║                                                                              ║
║  TABLES DB UTILISÉES                                                        ║
║    tb_chat    (id, id_expediteur, id_destinataire, message, date_envoi, lu) ║
║    tb_users   (iduser, nomuser, prenomuser, username, …)                    ║
║                                                                              ║
║  AUCUNE TABLE SUPPLÉMENTAIRE REQUISE — structure existante suffisante       ║
║                                                                              ║
║  AUTO-REFRESH toutes les 4 secondes (réduit depuis 5s pour réactivité)     ║
╚══════════════════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  REQUÊTES SQL IMPORTANTES (référence commentée)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1) Charger la liste des contacts triée par dernier message :
     SELECT DISTINCT ON (other_id)
         other_id, other_name, message, date_envoi, lu, id_expediteur
     FROM (
         SELECT  -- messages envoyés
             id_destinataire AS other_id,
             (SELECT CONCAT(prenomuser,' ',nomuser) FROM tb_users WHERE iduser=id_destinataire) AS other_name,
             message, date_envoi, lu, id_expediteur
         FROM tb_chat WHERE id_expediteur = %s
         UNION ALL
         SELECT  -- messages reçus
             id_expediteur AS other_id,
             (SELECT CONCAT(prenomuser,' ',nomuser) FROM tb_users WHERE iduser=id_expediteur) AS other_name,
             message, date_envoi, lu, id_expediteur
         FROM tb_chat WHERE id_destinataire = %s
     ) sub
     ORDER BY other_id, date_envoi DESC

  2) Charger l'historique d'une conversation :
     SELECT id, id_expediteur, message, date_envoi, lu
     FROM tb_chat
     WHERE (id_expediteur=%s AND id_destinataire=%s)
        OR (id_expediteur=%s AND id_destinataire=%s)
     ORDER BY date_envoi ASC

  3) Envoyer un message :
     INSERT INTO tb_chat (id_expediteur, id_destinataire, message, lu)
     VALUES (%s, %s, %s, 0)

  4) Marquer comme lu :
     UPDATE tb_chat SET lu=1
     WHERE id_expediteur=%s AND id_destinataire=%s AND lu=0

  5) Compter les non-lus par expéditeur :
     SELECT id_expediteur, COUNT(*) FROM tb_chat
     WHERE id_destinataire=%s AND lu=0
     GROUP BY id_expediteur
"""

import customtkinter as ctk
from tkinter import messagebox
import psycopg2
import json
from datetime import datetime
import tkinter as tk
from resource_utils import get_config_path, safe_file_read
from app_theme import Colors, Fonts


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES VISUELLES LOCALES
# ══════════════════════════════════════════════════════════════════════════════

SIDEBAR_W       = 280          # largeur fixe de la sidebar
AVATAR_SIZE     = 36           # diamètre des avatars dans la sidebar
AVATAR_MSG_SIZE = 32           # diamètre des avatars dans les bulles
REFRESH_MS      = 4000         # intervalle auto-refresh en ms

# Palette d'avatars — couleurs vives assignées par ordre d'apparition
AVATAR_PALETTE = [
    "#3498DB",   # bleu
    "#9B59B6",   # violet
    "#E74C3C",   # rouge
    "#27AE60",   # vert
    "#F39C12",   # orange
    "#1ABC9C",   # turquoise
    "#E91E63",   # rose
    "#FF5722",   # orange foncé
    "#607D8B",   # bleu-gris
    "#795548",   # marron
]

# Bulle "moi" : fond PRIMARY bleu, texte blanc
BUBBLE_ME_BG    = Colors.PRIMARY
BUBBLE_ME_FG    = "#FFFFFF"

# Bulle "autre" : fond gris très clair, texte foncé
BUBBLE_OTHER_BG = "#E8ECF0"
BUBBLE_OTHER_FG = Colors.TEXT_PRIMARY

# Fond de la zone de messages
CHAT_BG         = "#F0F3F5"


# ══════════════════════════════════════════════════════════════════════════════
# WIDGET : AVATAR CIRCULAIRE (Canvas)
# ══════════════════════════════════════════════════════════════════════════════

class AvatarCanvas(tk.Canvas):
    """
    Dessine un cercle coloré avec les initiales d'un utilisateur.
    Utilisé dans la sidebar ET dans les bulles de messages.

    Paramètres :
        parent   — widget parent
        initials — 1 ou 2 lettres à afficher au centre
        color    — couleur de fond du cercle (hex)
        size     — diamètre en pixels
    """

    def __init__(self, parent, initials: str, color: str, size: int = 36):
        super().__init__(
            parent,
            width=size, height=size,
            bg=Colors.BG_CARD,
            highlightthickness=0,
            bd=0,
        )
        self._size     = size
        self._initials = initials[:2].upper()
        self._color    = color
        self._draw()

    def _draw(self):
        """Dessine le fond circulaire et les initiales centrées."""
        s = self._size
        pad = 1
        # Cercle plein
        self.create_oval(
            pad, pad, s - pad, s - pad,
            fill=self._color, outline="",
        )
        # Initiales en blanc
        font_size = max(8, s // 3)
        self.create_text(
            s // 2, s // 2,
            text=self._initials,
            fill="#FFFFFF",
            font=("Roboto", font_size, "bold"),
        )

    def update_bg(self, bg: str):
        """Met à jour la couleur de fond du canvas (pour que le cercle soit correctement découpé)."""
        self.configure(bg=bg)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════

class PageChat(ctk.CTkFrame):
    """
    Page de messagerie interne iJeery.

    Paramètres :
        master       — widget parent (CTkFrame de l'app principale)
        session_data — dict {"iduser": int, "username": str, …}
    """

    def __init__(self, master, session_data=None):
        super().__init__(master, fg_color=Colors.BG_PAGE)

        # ── Session ───────────────────────────────────────────────────────────
        if session_data is None:
            session_data = {}

        self.id_user_connecte  = session_data.get('iduser')
        self.nom_user_connecte = session_data.get('username', 'Utilisateur')

        if self.id_user_connecte is None:
            messagebox.showerror("Erreur", "Session invalide. Veuillez vous reconnecter.")
            return

        # ── État ──────────────────────────────────────────────────────────────
        self.destinataire_actuel   = None   # iduser du contact sélectionné
        self.nom_destinataire      = ""     # nom affiché du contact
        self.contacts              = {}     # {iduser: {"name":…, "color":…, "btn":…}}
        self.contacts_order        = []     # liste ordonnée des iduser pour tri sidebar
        self._last_msg_count       = 0      # pour détecter les nouveaux messages
        self._refresh_job          = None   # référence after() pour annulation propre
        self._building_messages    = False  # verrou anti-reentrance

        # ── Couleur avatar moi ────────────────────────────────────────────────
        self._my_color = AVATAR_PALETTE[self.id_user_connecte % len(AVATAR_PALETTE)]
        self._my_initials = self._get_initials(self.nom_user_connecte)

        # ── Chargement profil complet depuis DB ───────────────────────────────
        self._profil = self._charger_profil_complet()

        # ── Construction UI ───────────────────────────────────────────────────
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()       # Col 0
        self._build_chat_panel()    # Col 1

        # ── Chargement initial ────────────────────────────────────────────────
        self.charger_contacts()
        self._show_welcome_screen()

        # ── Démarrer le polling ───────────────────────────────────────────────
        self._start_refresh()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — CONSTRUCTION UI
    # ══════════════════════════════════════════════════════════════════════════

    def _build_sidebar(self):
        """
        Construit la colonne gauche :
          - Bandeau haut (avatar + nom utilisateur connecté)
          - Barre de recherche contacts
          - Liste scrollable des conversations
        """
        sidebar = ctk.CTkFrame(
            self,
            width=SIDEBAR_W,
            fg_color=Colors.BG_CARD,
            corner_radius=0,
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(2, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)

        # ── Bandeau utilisateur connecté ──────────────────────────────────────
        top = ctk.CTkFrame(sidebar, fg_color=Colors.MIDNIGHT, corner_radius=0, height=64)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_propagate(False)
        top.grid_columnconfigure(1, weight=1)

        # Canvas avatar
        self._my_avatar_canvas = AvatarCanvas(
            top, self._my_initials, self._my_color, size=38,
        )
        self._my_avatar_canvas.configure(bg=Colors.MIDNIGHT)
        self._my_avatar_canvas.grid(row=0, column=0, padx=(12, 8), pady=13)

        ctk.CTkLabel(
            top,
            text=self.nom_user_connecte,
            font=Fonts.bold(13),
            text_color=Colors.TEXT_ON_DARK,
            anchor="w",
        ).grid(row=0, column=1, sticky="w")

        # Indicateur "En ligne"
        ctk.CTkLabel(
            top,
            text="● En ligne",
            font=Fonts.small(9),
            text_color=Colors.SUCCESS,
            anchor="w",
        ).grid(row=0, column=2, padx=(0, 12), sticky="e")

        # ── Barre de recherche ────────────────────────────────────────────────
        search_bar = ctk.CTkFrame(sidebar, fg_color=Colors.BG_PAGE, corner_radius=0, height=48)
        search_bar.grid(row=1, column=0, sticky="ew")
        search_bar.grid_propagate(False)
        search_bar.grid_columnconfigure(0, weight=1)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_change)

        self.entry_search = ctk.CTkEntry(
            search_bar,
            textvariable=self.search_var,
            placeholder_text="🔍  Rechercher…",
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            height=30, corner_radius=20,
            font=Fonts.input(11),
        )
        self.entry_search.grid(row=0, column=0, padx=10, pady=9, sticky="ew")

        # ── Liste des contacts ────────────────────────────────────────────────
        self.scroll_contacts = ctk.CTkScrollableFrame(
            sidebar,
            fg_color=Colors.BG_CARD,
            corner_radius=0,
        )
        self.scroll_contacts.grid(row=2, column=0, sticky="nsew")
        self.scroll_contacts.grid_columnconfigure(0, weight=1)

        # Label "aucun contact" affiché si liste vide
        self.lbl_no_contact = ctk.CTkLabel(
            self.scroll_contacts,
            text="Aucun collaborateur trouvé",
            font=Fonts.label(11),
            text_color=Colors.TEXT_MUTED,
        )

    def _build_chat_panel(self):
        """
        Construit la colonne droite :
          - Entête contact (avatar + nom + statut)
          - Zone d'affichage des messages (Canvas scrollable)
          - Zone de saisie
        """
        self.chat_panel = ctk.CTkFrame(self, fg_color=CHAT_BG, corner_radius=0)
        self.chat_panel.grid(row=0, column=1, sticky="nsew")
        self.chat_panel.grid_rowconfigure(1, weight=1)
        self.chat_panel.grid_columnconfigure(0, weight=1)

        # ── Entête conversation ───────────────────────────────────────────────
        self.chat_header = ctk.CTkFrame(
            self.chat_panel,
            fg_color=Colors.BG_CARD,
            corner_radius=0,
            height=60,
        )
        self.chat_header.grid(row=0, column=0, sticky="ew")
        self.chat_header.grid_propagate(False)
        self.chat_header.grid_columnconfigure(1, weight=1)

        # Avatar entête (sera recréé à chaque sélection)
        self.header_avatar_frame = ctk.CTkFrame(
            self.chat_header, fg_color="transparent", width=44, height=44,
        )
        self.header_avatar_frame.grid(row=0, column=0, padx=(14, 8), pady=8)

        self.header_name_lbl = ctk.CTkLabel(
            self.chat_header,
            text="",
            font=Fonts.bold(14),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        )
        self.header_name_lbl.grid(row=0, column=1, sticky="w", pady=(14, 2))

        self.header_sub_lbl = ctk.CTkLabel(
            self.chat_header,
            text="",
            font=Fonts.small(10),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        )
        self.header_sub_lbl.grid(row=0, column=1, sticky="sw", pady=(0, 8))

        # Séparateur fin sous l'entête
        ctk.CTkFrame(
            self.chat_panel, fg_color=Colors.BORDER, height=1, corner_radius=0,
        ).grid(row=0, column=0, sticky="sew")

        # ── Zone messages : Frame conteneur + Canvas + Scrollbar ──────────────
        msg_container = ctk.CTkFrame(self.chat_panel, fg_color=CHAT_BG, corner_radius=0)
        msg_container.grid(row=1, column=0, sticky="nsew")
        msg_container.grid_rowconfigure(0, weight=1)
        msg_container.grid_columnconfigure(0, weight=1)

        # Canvas tkinter natif — permet le positionnement libre des bulles
        self.msg_canvas = tk.Canvas(
            msg_container,
            bg=CHAT_BG,
            highlightthickness=0,
            bd=0,
        )
        self.msg_canvas.grid(row=0, column=0, sticky="nsew")

        msg_scroll = ctk.CTkScrollbar(msg_container, command=self.msg_canvas.yview)
        msg_scroll.grid(row=0, column=1, sticky="ns")
        self.msg_canvas.configure(yscrollcommand=msg_scroll.set)

        # Frame intérieure du canvas — c'est ici qu'on place les bulles
        self.msg_inner = ctk.CTkFrame(self.msg_canvas, fg_color=CHAT_BG, corner_radius=0)
        self._canvas_window = self.msg_canvas.create_window(
            (0, 0), window=self.msg_inner, anchor="nw",
        )
        self.msg_inner.grid_columnconfigure(0, weight=1)

        # Redimensionnement automatique du canvas
        self.msg_inner.bind("<Configure>", self._on_inner_configure)
        self.msg_canvas.bind("<Configure>", self._on_canvas_configure)

        # Scroll molette
        self.msg_canvas.bind_all("<MouseWheel>",  self._on_mousewheel)
        self.msg_canvas.bind_all("<Button-4>",    self._on_mousewheel)
        self.msg_canvas.bind_all("<Button-5>",    self._on_mousewheel)

        # ── Zone de saisie ────────────────────────────────────────────────────
        input_bar = ctk.CTkFrame(
            self.chat_panel,
            fg_color=Colors.BG_CARD,
            corner_radius=0,
            height=62,
        )
        input_bar.grid(row=2, column=0, sticky="ew")
        input_bar.grid_propagate(False)
        input_bar.grid_columnconfigure(0, weight=1)

        # Séparateur fin au-dessus de la saisie
        ctk.CTkFrame(
            input_bar, fg_color=Colors.BORDER, height=1, corner_radius=0,
        ).grid(row=0, column=0, columnspan=2, sticky="ew")

        self.entry_msg = ctk.CTkEntry(
            input_bar,
            placeholder_text="  Écrivez un message…  (Entrée pour envoyer)",
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            height=36, corner_radius=20,
            font=Fonts.input(12),
        )
        self.entry_msg.grid(row=1, column=0, padx=(12, 8), pady=12, sticky="ew")
        self.entry_msg.bind("<Return>", lambda e: self.envoyer_message())

        self.btn_send = ctk.CTkButton(
            input_bar,
            text="Envoyer ➤",
            font=Fonts.bold(11),
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            height=36, corner_radius=20, width=100,
            command=self.envoyer_message,
        )
        self.btn_send.grid(row=1, column=1, padx=(0, 12), pady=12)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — PAGE D'ACCUEIL (aucune conversation sélectionnée)
    # ══════════════════════════════════════════════════════════════════════════

    def _show_welcome_screen(self):
        """
        Affiche la page de bienvenue dans la zone de messages.
        Appelée au démarrage et quand aucun contact n'est sélectionné.
        """
        self._clear_msg_inner()
        self._update_header_empty()

        # Centrage vertical via un frame expansible
        welcome = ctk.CTkFrame(self.msg_inner, fg_color=CHAT_BG, corner_radius=0)
        welcome.grid(row=0, column=0, sticky="nsew", padx=40, pady=60)
        welcome.grid_columnconfigure(0, weight=1)
        self.msg_inner.grid_rowconfigure(0, weight=1)

        # Icône de salutation
        ctk.CTkLabel(
            welcome,
            text="👋",
            font=ctk.CTkFont(size=56),
        ).grid(row=0, column=0, pady=(0, 16))

        # Texte de bienvenue
        ctk.CTkLabel(
            welcome,
            text=f"Bienvenue, {self.nom_user_connecte} !",
            font=Fonts.title(22),
            text_color=Colors.TEXT_PRIMARY,
        ).grid(row=1, column=0, pady=(0, 6))

        ctk.CTkLabel(
            welcome,
            text="Sélectionnez une conversation dans la liste\npour commencer à discuter avec vos collègues.",
            font=Fonts.body(13),
            text_color=Colors.TEXT_SECONDARY,
            justify="center",
        ).grid(row=2, column=0, pady=(0, 30))

        # ── Card Profil ───────────────────────────────────────────────────────
        profil_card = ctk.CTkFrame(
            welcome,
            fg_color=Colors.BG_CARD,
            corner_radius=12,
        )
        profil_card.grid(row=3, column=0, pady=0, ipadx=20, ipady=14)
        profil_card.grid_columnconfigure(1, weight=1)

        # Avatar grand format dans la card
        av = AvatarCanvas(profil_card, self._my_initials, self._my_color, size=52)
        av.configure(bg=Colors.BG_CARD)
        av.grid(row=0, column=0, rowspan=4, padx=(20, 16), pady=14, sticky="w")

        _lkw = dict(font=Fonts.label(10), text_color=Colors.TEXT_MUTED, anchor="w")
        _vkw = dict(font=Fonts.bold(12), text_color=Colors.TEXT_PRIMARY, anchor="w")

        p = self._profil  # dict chargé depuis DB

        ctk.CTkLabel(profil_card, text="Nom complet", **_lkw).grid(
            row=0, column=1, sticky="w", padx=(0, 20), pady=(12, 0))
        ctk.CTkLabel(profil_card, text=p.get("nom_complet", self.nom_user_connecte), **_vkw).grid(
            row=0, column=2, sticky="w", padx=(0, 20))

        ctk.CTkLabel(profil_card, text="Identifiant", **_lkw).grid(
            row=1, column=1, sticky="w")
        ctk.CTkLabel(profil_card, text=p.get("username", "—"), **_vkw).grid(
            row=1, column=2, sticky="w")

        ctk.CTkLabel(profil_card, text="Fonction", **_lkw).grid(
            row=2, column=1, sticky="w")
        ctk.CTkLabel(profil_card, text=p.get("fonction", "—"), **_vkw).grid(
            row=2, column=2, sticky="w")

        ctk.CTkLabel(profil_card, text="Magasin", **_lkw).grid(
            row=3, column=1, sticky="w", pady=(0, 12))
        ctk.CTkLabel(profil_card, text=p.get("magasin", "—"), **_vkw).grid(
            row=3, column=2, sticky="w", pady=(0, 12))

    def _update_header_empty(self):
        """Vide l'entête conversation quand aucun contact n'est sélectionné."""
        # Effacer l'avatar précédent
        for w in self.header_avatar_frame.winfo_children():
            w.destroy()
        self.header_name_lbl.configure(text="")
        self.header_sub_lbl.configure(text="")

    def _update_header(self, name: str, color: str):
        """Met à jour l'entête avec le nom et l'avatar du contact sélectionné."""
        for w in self.header_avatar_frame.winfo_children():
            w.destroy()
        av = AvatarCanvas(self.header_avatar_frame, self._get_initials(name), color, size=38)
        av.configure(bg=Colors.BG_CARD)
        av.pack()
        self.header_name_lbl.configure(text=name)
        self.header_sub_lbl.configure(text="Collaborateur")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — SIDEBAR : LISTE DES CONTACTS
    # ══════════════════════════════════════════════════════════════════════════

    def charger_contacts(self):
        """
        Charge la liste des utilisateurs depuis tb_users
        et les affiche dans la sidebar avec avatar + dernier message.

        SQL utilisé :
            SELECT iduser, CONCAT(prenomuser,' ',nomuser) AS nom
            FROM tb_users
            WHERE iduser != %s AND deleted=0 AND active=1
            ORDER BY nomuser ASC
        """
        # Vider la liste actuelle
        for w in self.scroll_contacts.winfo_children():
            w.destroy()
        self.contacts = {}
        self.contacts_order = []

        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            # Récupérer tous les utilisateurs actifs sauf soi-même
            cur.execute("""
                SELECT iduser,
                       TRIM(CONCAT(COALESCE(prenomuser,''), ' ', COALESCE(nomuser,''))) AS nom_complet,
                       username
                FROM tb_users
                WHERE iduser != %s
                  AND COALESCE(deleted, 0) = 0
                  AND COALESCE(active,  1) = 1
                ORDER BY nomuser ASC
            """, (self.id_user_connecte,))
            rows = cur.fetchall()

            for idx, row in enumerate(rows):
                iduser = row[0]
                nom    = (row[1] or row[2] or "Utilisateur").strip()
                color  = AVATAR_PALETTE[idx % len(AVATAR_PALETTE)]

                self.contacts[iduser] = {
                    "name":  nom,
                    "color": color,
                    "btn":   None,
                    "last_msg":  "",
                    "last_time": None,
                    "unread": 0,
                }
                self.contacts_order.append(iduser)

            cur.close()
        except Exception as e:
            print(f"[PageChat] Erreur charger_contacts: {e}")
        finally:
            conn.close()

        # Récupérer les derniers messages pour le tri et l'aperçu
        self._charger_derniers_messages()
        self._trier_et_afficher_contacts()

    def _charger_derniers_messages(self):
        """
        Pour chaque contact, récupère :
          - le dernier message échangé (aperçu)
          - l'heure du dernier message (pour le tri)
          - le nombre de messages non lus

        SQL :
            SELECT other_id, message, date_envoi, unread
            FROM (
                SELECT id_destinataire AS other_id, message, date_envoi,
                       CASE WHEN lu=0 AND id_expediteur!=:me THEN 1 ELSE 0 END AS unread,
                       ROW_NUMBER() OVER (PARTITION BY id_destinataire ORDER BY date_envoi DESC) rn
                FROM tb_chat WHERE id_expediteur = :me
                UNION ALL
                SELECT id_expediteur AS other_id, message, date_envoi,
                       CASE WHEN lu=0 THEN 1 ELSE 0 END AS unread,
                       ROW_NUMBER() OVER (PARTITION BY id_expediteur ORDER BY date_envoi DESC) rn
                FROM tb_chat WHERE id_destinataire = :me
            ) sub WHERE rn=1
        """
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            me = self.id_user_connecte
            cur.execute("""
                SELECT
                    other_id,
                    message,
                    date_envoi,
                    SUM(unread_flag) AS nb_unread
                FROM (
                    -- Messages que j'ai envoyés
                    SELECT
                        id_destinataire            AS other_id,
                        message,
                        date_envoi,
                        0                          AS unread_flag
                    FROM tb_chat
                    WHERE id_expediteur = %s

                    UNION ALL

                    -- Messages que j'ai reçus
                    SELECT
                        id_expediteur              AS other_id,
                        message,
                        date_envoi,
                        CASE WHEN lu = 0 THEN 1 ELSE 0 END AS unread_flag
                    FROM tb_chat
                    WHERE id_destinataire = %s
                ) raw
                -- On garde le dernier message par contact
                INNER JOIN (
                    SELECT
                        CASE
                            WHEN id_expediteur = %s THEN id_destinataire
                            ELSE id_expediteur
                        END AS other_id2,
                        MAX(date_envoi) AS max_date
                    FROM tb_chat
                    WHERE id_expediteur = %s OR id_destinataire = %s
                    GROUP BY other_id2
                ) latest
                ON raw.other_id = latest.other_id2
                AND raw.date_envoi = latest.max_date
                GROUP BY raw.other_id, raw.message, raw.date_envoi
            """, (me, me, me, me, me))

            rows = cur.fetchall()
            for row in rows:
                other_id  = row[0]
                message   = row[1] or ""
                date_env  = row[2]
                nb_unread = int(row[3] or 0)
                if other_id in self.contacts:
                    self.contacts[other_id]["last_msg"]  = message[:45] + ("…" if len(message) > 45 else "")
                    self.contacts[other_id]["last_time"] = date_env
                    self.contacts[other_id]["unread"]    = nb_unread

            # Retrier l'ordre par date décroissante
            self.contacts_order.sort(
                key=lambda uid: self.contacts[uid]["last_time"] or datetime.min,
                reverse=True,
            )
            cur.close()
        except Exception as e:
            print(f"[PageChat] Erreur _charger_derniers_messages: {e}")
        finally:
            conn.close()

    def _trier_et_afficher_contacts(self, filtre: str = ""):
        """
        (Re)construit les boutons de la sidebar dans l'ordre de contacts_order.
        Applique un filtre texte si fourni.
        """
        for w in self.scroll_contacts.winfo_children():
            w.destroy()

        filtre_lower = filtre.strip().lower()
        visible = 0

        for iduser in self.contacts_order:
            info = self.contacts[iduser]
            nom  = info["name"]

            # Filtre recherche
            if filtre_lower and filtre_lower not in nom.lower():
                continue

            visible += 1

            # ── Ligne contact ─────────────────────────────────────────────────
            # Fond actif si c'est le destinataire sélectionné
            is_active = (iduser == self.destinataire_actuel)
            row_bg = Colors.PRIMARY_LIGHT if is_active else Colors.BG_CARD
            row_hover = Colors.BG_HOVER_ROW

            row_frame = ctk.CTkFrame(
                self.scroll_contacts,
                fg_color=row_bg,
                corner_radius=8,
                cursor="hand2",
            )
            row_frame.grid(sticky="ew", padx=6, pady=2)
            row_frame.grid_columnconfigure(1, weight=1)

            # Avatar
            av = AvatarCanvas(row_frame, self._get_initials(nom), info["color"],
                              size=AVATAR_SIZE)
            av.configure(bg=row_bg)
            av.grid(row=0, column=0, rowspan=2, padx=(10, 8), pady=8, sticky="w")

            # Nom
            ctk.CTkLabel(
                row_frame,
                text=nom,
                font=Fonts.bold(12) if info["unread"] > 0 else Fonts.body(12),
                text_color=Colors.TEXT_PRIMARY,
                anchor="w",
            ).grid(row=0, column=1, sticky="sw", pady=(8, 0))

            # Aperçu dernier message
            last_preview = info["last_msg"] or "Pas encore de message"
            ctk.CTkLabel(
                row_frame,
                text=last_preview,
                font=Fonts.small(10),
                text_color=Colors.TEXT_SECONDARY if info["unread"] == 0 else Colors.PRIMARY,
                anchor="w",
                wraplength=150,
            ).grid(row=1, column=1, sticky="nw", pady=(0, 8))

            # Heure + badge non-lus (colonne droite)
            right_col = ctk.CTkFrame(row_frame, fg_color="transparent")
            right_col.grid(row=0, column=2, rowspan=2, padx=(0, 10), pady=6, sticky="e")

            # Heure du dernier message
            if info["last_time"]:
                heure = self._format_time(info["last_time"])
                ctk.CTkLabel(
                    right_col,
                    text=heure,
                    font=Fonts.small(9),
                    text_color=Colors.TEXT_MUTED,
                ).pack(anchor="e")

            # Badge rouge non-lus
            if info["unread"] > 0:
                badge = ctk.CTkLabel(
                    right_col,
                    text=str(info["unread"]),
                    font=Fonts.badge(9),
                    text_color=Colors.TEXT_ON_DARK,
                    fg_color=Colors.DANGER,
                    corner_radius=10,
                    width=20, height=20,
                )
                badge.pack(anchor="e", pady=(2, 0))

            # Binding clic sur toute la ligne
            _uid = iduser
            _nom = nom
            _clr = info["color"]
            for widget in [row_frame, av] + list(row_frame.winfo_children()):
                try:
                    widget.bind(
                        "<Button-1>",
                        lambda e, u=_uid, n=_nom, c=_clr: self.selectionner_contact(u, n, c),
                    )
                except Exception:
                    pass

            # Stocker référence
            self.contacts[iduser]["btn"] = row_frame

        # Message si aucun résultat
        if visible == 0:
            self.lbl_no_contact.configure(
                master=self.scroll_contacts,
                text="Aucun collaborateur trouvé" if filtre_lower else "Aucun utilisateur",
            )
            self.lbl_no_contact.grid(padx=10, pady=20)

    def _on_search_change(self, *args):
        """Déclenché à chaque frappe dans la barre de recherche."""
        self._trier_et_afficher_contacts(filtre=self.search_var.get())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4 — SÉLECTION D'UN CONTACT
    # ══════════════════════════════════════════════════════════════════════════

    def selectionner_contact(self, iduser: int, nom: str, color: str):
        """
        Appelée au clic sur un contact.
        Met à jour l'état, marque les messages comme lus, charge la conversation.
        """
        self.destinataire_actuel = iduser
        self.nom_destinataire    = nom

        # Mettre à jour l'entête
        self._update_header(nom, color)

        # Marquer les messages reçus de ce contact comme lus
        self.marquer_comme_lu(iduser)

        # Remettre unread à 0 localement
        if iduser in self.contacts:
            self.contacts[iduser]["unread"] = 0

        # Rafraîchir la sidebar (retire le badge)
        self._trier_et_afficher_contacts(filtre=self.search_var.get())

        # Charger la conversation
        self.charger_messages()

        # Focus sur le champ de saisie
        self.entry_msg.focus_set()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 5 — AFFICHAGE DES MESSAGES (bulles)
    # ══════════════════════════════════════════════════════════════════════════

    def charger_messages(self):
        """
        Charge l'historique de la conversation depuis tb_chat et affiche les bulles.

        SQL :
            SELECT id, id_expediteur, message, date_envoi, lu
            FROM tb_chat
            WHERE (id_expediteur=%s AND id_destinataire=%s)
               OR (id_expediteur=%s AND id_destinataire=%s)
            ORDER BY date_envoi ASC
        """
        if not self.destinataire_actuel or self._building_messages:
            return

        self._building_messages = True
        self._clear_msg_inner()

        conn = self.connect_db()
        if not conn:
            self._building_messages = False
            return

        try:
            cur = conn.cursor()
            me   = self.id_user_connecte
            dest = self.destinataire_actuel

            cur.execute("""
                SELECT id, id_expediteur, message, date_envoi, lu
                FROM tb_chat
                WHERE (id_expediteur = %s AND id_destinataire = %s)
                   OR (id_expediteur = %s AND id_destinataire = %s)
                ORDER BY date_envoi ASC
            """, (me, dest, dest, me))

            messages = cur.fetchall()
            self._last_msg_count = len(messages)

            if not messages:
                # Afficher un message "début de conversation"
                ctk.CTkLabel(
                    self.msg_inner,
                    text="Début de la conversation",
                    font=Fonts.small(10),
                    text_color=Colors.TEXT_MUTED,
                ).grid(row=0, column=0, pady=20)
            else:
                # Afficher chaque bulle
                prev_date_str = ""
                for idx, msg in enumerate(messages):
                    msg_id       = msg[0]
                    id_exp       = msg[1]
                    texte        = msg[2] or ""
                    date_env     = msg[3]
                    lu           = msg[4]
                    is_me        = (id_exp == me)

                    # ── Séparateur de date ─────────────────────────────────────
                    date_str = date_env.strftime("%d %B %Y") if date_env else ""
                    if date_str != prev_date_str:
                        prev_date_str = date_str
                        self._add_date_separator(idx * 2, date_str)

                    # ── Bulle de message ───────────────────────────────────────
                    self._add_bubble(
                        row   = idx * 2 + 1,
                        texte = texte,
                        heure = date_env.strftime("%H:%M") if date_env else "",
                        is_me = is_me,
                        lu    = bool(lu),
                        nom_expediteur = self.nom_destinataire if not is_me else self.nom_user_connecte,
                        color_avatar   = (
                            self._my_color if is_me
                            else self.contacts.get(dest, {}).get("color", AVATAR_PALETTE[0])
                        ),
                    )

            cur.close()
        except Exception as e:
            print(f"[PageChat] Erreur charger_messages: {e}")
        finally:
            conn.close()
            self._building_messages = False

        # Scroll vers le bas après construction
        self.msg_inner.update_idletasks()
        self.msg_canvas.yview_moveto(1.0)

    def _add_date_separator(self, row: int, date_str: str):
        """Affiche un séparateur centré avec la date (ex: '08 mars 2026')."""
        sep_frame = ctk.CTkFrame(
            self.msg_inner,
            fg_color=CHAT_BG,
            corner_radius=0,
        )
        sep_frame.grid(row=row, column=0, sticky="ew", padx=20, pady=(12, 4))
        sep_frame.grid_columnconfigure(0, weight=1)
        sep_frame.grid_columnconfigure(2, weight=1)

        ctk.CTkFrame(sep_frame, fg_color=Colors.BORDER, height=1, corner_radius=0).grid(
            row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkLabel(
            sep_frame,
            text=date_str,
            font=Fonts.small(9),
            text_color=Colors.TEXT_MUTED,
        ).grid(row=0, column=1)
        ctk.CTkFrame(sep_frame, fg_color=Colors.BORDER, height=1, corner_radius=0).grid(
            row=0, column=2, sticky="ew", padx=(8, 0))

    def _add_bubble(self, row: int, texte: str, heure: str,
                    is_me: bool, lu: bool,
                    nom_expediteur: str, color_avatar: str):
        """
        Crée une bulle de message dans msg_inner.

        Structure (is_me=False, message reçu) :
          [Avatar] [Bulle : Nom / Texte / Heure]   ←·· aligné à gauche

        Structure (is_me=True, message envoyé) :
                   [Bulle : Texte / Heure + lu] [Avatar]   ··→ aligné à droite
        """
        # Frame wrapper de la ligne (pleine largeur)
        line = ctk.CTkFrame(self.msg_inner, fg_color=CHAT_BG, corner_radius=0)
        line.grid(row=row, column=0, sticky="ew", padx=12, pady=2)
        line.grid_columnconfigure(1 if not is_me else 0, weight=1)

        initials = self._get_initials(nom_expediteur)

        if is_me:
            # ── Message envoyé — droite ────────────────────────────────────
            # Spacer gauche
            ctk.CTkFrame(line, fg_color=CHAT_BG, width=0).grid(row=0, column=0, sticky="ew")

            # Bulle
            bubble = ctk.CTkFrame(
                line,
                fg_color=BUBBLE_ME_BG,
                corner_radius=16,
            )
            bubble.grid(row=0, column=1, sticky="e", padx=(60, 6))

            ctk.CTkLabel(
                bubble,
                text=texte,
                font=Fonts.body(12),
                text_color=BUBBLE_ME_FG,
                wraplength=320,
                justify="left",
                anchor="w",
            ).grid(row=0, column=0, padx=(12, 12), pady=(8, 2), sticky="w")

            # Heure + indicateur lu
            lu_icon = "✓✓" if lu else "✓"
            lu_color = "#A8D5FF" if lu else "#C8E6FF"
            meta = ctk.CTkFrame(bubble, fg_color=BUBBLE_ME_BG, corner_radius=0)
            meta.grid(row=1, column=0, padx=(12, 12), pady=(0, 6), sticky="e")

            ctk.CTkLabel(
                meta,
                text=f"{heure}  {lu_icon}",
                font=Fonts.small(9),
                text_color=lu_color,
            ).pack(side="right")

            # Avatar à droite
            av = AvatarCanvas(line, initials, color_avatar, size=AVATAR_MSG_SIZE)
            av.configure(bg=CHAT_BG)
            av.grid(row=0, column=2, padx=(0, 4), pady=4, sticky="se")

        else:
            # ── Message reçu — gauche ──────────────────────────────────────
            # Avatar à gauche
            av = AvatarCanvas(line, initials, color_avatar, size=AVATAR_MSG_SIZE)
            av.configure(bg=CHAT_BG)
            av.grid(row=0, column=0, padx=(4, 6), pady=4, sticky="sw")

            # Bulle
            bubble = ctk.CTkFrame(
                line,
                fg_color=BUBBLE_OTHER_BG,
                corner_radius=16,
            )
            bubble.grid(row=0, column=1, sticky="w", padx=(0, 60))

            # Nom expéditeur
            ctk.CTkLabel(
                bubble,
                text=nom_expediteur,
                font=Fonts.bold(10),
                text_color=color_avatar,
                anchor="w",
            ).grid(row=0, column=0, padx=(12, 12), pady=(6, 0), sticky="w")

            ctk.CTkLabel(
                bubble,
                text=texte,
                font=Fonts.body(12),
                text_color=BUBBLE_OTHER_FG,
                wraplength=320,
                justify="left",
                anchor="w",
            ).grid(row=1, column=0, padx=(12, 12), pady=(2, 2), sticky="w")

            # Heure
            ctk.CTkLabel(
                bubble,
                text=heure,
                font=Fonts.small(9),
                text_color=Colors.TEXT_MUTED,
                anchor="e",
            ).grid(row=2, column=0, padx=(12, 12), pady=(0, 6), sticky="e")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 6 — ENVOI DE MESSAGE
    # ══════════════════════════════════════════════════════════════════════════

    def envoyer_message(self):
        """
        Insère un message dans tb_chat et rafraîchit la vue.

        SQL :
            INSERT INTO tb_chat (id_expediteur, id_destinataire, message, lu)
            VALUES (%s, %s, %s, 0)
        """
        texte = self.entry_msg.get().strip()
        if not texte or not self.destinataire_actuel:
            return

        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO tb_chat (id_expediteur, id_destinataire, message, lu)
                VALUES (%s, %s, %s, 0)
            """, (self.id_user_connecte, self.destinataire_actuel, texte))
            conn.commit()
            cur.close()

            # Vider le champ
            self.entry_msg.delete(0, "end")

            # Rafraîchir les messages et la sidebar
            self.charger_messages()
            self._charger_derniers_messages()
            self._trier_et_afficher_contacts(filtre=self.search_var.get())

        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'envoyer le message : {e}")
        finally:
            conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 7 — MARQUAGE LU
    # ══════════════════════════════════════════════════════════════════════════

    def marquer_comme_lu(self, id_expediteur: int):
        """
        Marque tous les messages reçus de id_expediteur comme lus.

        SQL :
            UPDATE tb_chat SET lu=1
            WHERE id_expediteur=%s AND id_destinataire=%s AND lu=0
        """
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE tb_chat SET lu = 1
                WHERE id_expediteur = %s
                  AND id_destinataire = %s
                  AND lu = 0
            """, (id_expediteur, self.id_user_connecte))
            conn.commit()
            cur.close()
        except Exception as e:
            print(f"[PageChat] Erreur marquer_comme_lu: {e}")
        finally:
            conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 8 — AUTO-REFRESH (polling toutes les 4s)
    # ══════════════════════════════════════════════════════════════════════════

    def auto_refresh(self):
        """Alias de compatibilité — utilise _refresh_loop en interne."""
        self._refresh_loop()

    def _start_refresh(self):
        """Démarre la boucle de polling."""
        self._refresh_job = self.after(REFRESH_MS, self._refresh_loop)

    def _refresh_loop(self):
        """
        Boucle principale du polling :
          1. Vérifie les nouveaux messages pour tous les contacts
          2. Si un contact actif a de nouveaux messages → recharge la conversation
          3. Actualise les badges de la sidebar
        """
        try:
            self._verifier_nouveaux_messages()
        except Exception as e:
            print(f"[PageChat] Erreur refresh: {e}")
        finally:
            # Toujours reprogram­mer même en cas d'erreur
            self._refresh_job = self.after(REFRESH_MS, self._refresh_loop)

    def _verifier_nouveaux_messages(self):
        """
        Vérifie s'il y a des messages non-lus et met à jour badges + conversation.

        SQL :
            SELECT id_expediteur, COUNT(*) AS nb
            FROM tb_chat
            WHERE id_destinataire=%s AND lu=0
            GROUP BY id_expediteur
        """
        conn = self.connect_db()
        if not conn:
            return
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id_expediteur, COUNT(*) AS nb
                FROM tb_chat
                WHERE id_destinataire = %s AND lu = 0
                GROUP BY id_expediteur
            """, (self.id_user_connecte,))
            non_lus = {row[0]: row[1] for row in cur.fetchall()}
            cur.close()

            sidebar_changed = False

            for iduser, nb in non_lus.items():
                if iduser not in self.contacts:
                    continue
                old_unread = self.contacts[iduser]["unread"]

                if iduser == self.destinataire_actuel:
                    # Conversation ouverte → marquer lu + recharger si nouveau message
                    if nb > 0:
                        self.marquer_comme_lu(iduser)
                        self.charger_messages()
                        self._charger_derniers_messages()
                        sidebar_changed = True
                elif nb != old_unread:
                    # Nouveau message non-lu d'un autre contact → badge + bip
                    if nb > old_unread:
                        self.bell()
                    self.contacts[iduser]["unread"] = nb
                    sidebar_changed = True

            # Effacer les badges pour les contacts qui n'ont plus de non-lus
            for iduser in self.contacts:
                if iduser not in non_lus and self.contacts[iduser]["unread"] > 0:
                    self.contacts[iduser]["unread"] = 0
                    sidebar_changed = True

            if sidebar_changed:
                self._charger_derniers_messages()
                self._trier_et_afficher_contacts(filtre=self.search_var.get())

        except Exception as e:
            print(f"[PageChat] Erreur _verifier_nouveaux_messages: {e}")
        finally:
            conn.close()

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 9 — BASE DE DONNÉES
    # ══════════════════════════════════════════════════════════════════════════

    def connect_db(self):
        """Ouvre une connexion PostgreSQL depuis config.json."""
        try:
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
            return psycopg2.connect(**config['database'])
        except Exception as e:
            print(f"[PageChat] Erreur connect_db: {e}")
            return None

    def _charger_profil_complet(self) -> dict:
        """
        Charge les informations complètes de l'utilisateur connecté
        en joignant tb_users, tb_fonction et tb_magasin.

        SQL :
            SELECT u.username,
                   CONCAT(u.prenomuser,' ',u.nomuser) AS nom_complet,
                   u.contactuser,
                   f.designationfonction,
                   m.designationmag
            FROM tb_users u
            LEFT JOIN tb_fonction f ON u.idfonction = f.idfonction
            LEFT JOIN tb_magasin  m ON u.idmag      = m.idmag
            WHERE u.iduser = %s
        """
        profil = {
            "nom_complet": self.nom_user_connecte,
            "username":    self.nom_user_connecte,
            "contact":     "—",
            "fonction":    "—",
            "magasin":     "—",
        }
        conn = self.connect_db()
        if not conn:
            return profil
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    u.username,
                    TRIM(CONCAT(COALESCE(u.prenomuser,''), ' ', COALESCE(u.nomuser,''))) AS nom_complet,
                    COALESCE(u.contactuser, '—')           AS contact,
                    COALESCE(f.designationfonction, '—')   AS fonction,
                    COALESCE(m.designationmag, '—')        AS magasin
                FROM tb_users u
                LEFT JOIN tb_fonction f ON u.idfonction = f.idfonction
                LEFT JOIN tb_magasin  m ON u.idmag      = m.idmag
                WHERE u.iduser = %s
            """, (self.id_user_connecte,))
            row = cur.fetchone()
            if row:
                profil["username"]    = row[0] or profil["username"]
                profil["nom_complet"] = (row[1] or "").strip() or profil["nom_complet"]
                profil["contact"]     = row[2]
                profil["fonction"]    = row[3]
                profil["magasin"]     = row[4]
            cur.close()
        except Exception as e:
            print(f"[PageChat] Erreur _charger_profil_complet: {e}")
        finally:
            conn.close()
        return profil

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 10 — UTILITAIRES
    # ══════════════════════════════════════════════════════════════════════════

    def _get_initials(self, nom: str) -> str:
        """
        Extrait 1 ou 2 initiales d'un nom.
        Ex: "Jean Dupont" → "JD", "Admin" → "AD"
        """
        parts = nom.strip().split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        elif len(nom) >= 2:
            return nom[:2].upper()
        return nom.upper()

    def _format_time(self, dt: datetime) -> str:
        """
        Formate une datetime pour l'affichage dans la sidebar.
        - Aujourd'hui → "14:32"
        - Hier → "Hier"
        - Autre → "08/03"
        """
        if not dt:
            return ""
        now  = datetime.now()
        diff = (now.date() - dt.date()).days
        if diff == 0:
            return dt.strftime("%H:%M")
        elif diff == 1:
            return "Hier"
        elif diff < 7:
            jours = ["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"]
            return jours[dt.weekday()]
        else:
            return dt.strftime("%d/%m")

    def _clear_msg_inner(self):
        """Détruit tous les widgets enfants de msg_inner."""
        for w in self.msg_inner.winfo_children():
            w.destroy()

    def _on_inner_configure(self, event):
        """Met à jour la scrollregion quand la frame intérieure change de taille."""
        self.msg_canvas.configure(scrollregion=self.msg_canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        """Étire la frame intérieure à la largeur du canvas."""
        self.msg_canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        """Gère le scroll molette (Windows + Linux)."""
        if event.num == 4:
            self.msg_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.msg_canvas.yview_scroll(1, "units")
        else:
            self.msg_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


# ══════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE AUTONOME (test)
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = ctk.CTk()
    app.title("iJeery — Chat Interne (test)")
    app.geometry("1100x700")
    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure(0, weight=1)

    session = {"iduser": 1, "username": "Admin"}
    page = PageChat(app, session)
    page.grid(row=0, column=0, sticky="nsew")

    app.mainloop()
