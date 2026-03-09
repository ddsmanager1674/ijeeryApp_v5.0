import customtkinter as ctk
from tkinter import ttk, messagebox
import psycopg2
import json
import os
from datetime import datetime
from reportlab.lib.pagesizes import A5
from reportlab.pdfgen import canvas
from tkcalendar import DateEntry
from typing import Optional, Dict, Any, List

class PageLivraisonClient(ctk.CTkFrame):
    def __init__(self, master, id_user_connecte: Optional[int] = None) -> None:
        super().__init__(master)
        if id_user_connecte is None:
            messagebox.showerror("Erreur", "Aucun utilisateur connecté. Veuillez vous reconnecter.")
            self.id_user_connecte = None
        else:
            self.id_user_connecte = id_user_connecte
            print(f"✅ Utilisateur connecté - ID: {self.id_user_connecte}")
        
        # ✅ CORRECTION 1: Définir user_id comme alias de id_user_connecte
        self.user_id = self.id_user_connecte
        
        self.conn: Optional[psycopg2.connection] = None
        self.selected_ref_vente = None
        self.selected_id_client = None
        self.selected_id_mag = None
        
        self.grid_columnconfigure(0, weight=1)
        self.setup_ui()

    def connect_db(self):
        """Connexion qui remonte d'un niveau pour trouver config.json à la racine"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(current_dir)
            config_path = os.path.join(root_dir, 'config.json')

            with open(config_path, 'r') as f:
                config = json.load(f)
                db_config = config['database']
            return psycopg2.connect(**db_config)
        except Exception as e:
            messagebox.showerror("Erreur de chemin", f"Impossible de trouver config.json à la racine.\nErreur: {e}")
            return None

    def _configure_table_alternating_colors(self, tree):
        """Configure les couleurs alternées d'un Treeview."""
        tree.tag_configure("row_even", background="#FFFFFF")
        tree.tag_configure("row_odd", background="#F3F7FF")

    def _refresh_table_alternating_colors(self, tree):
        """Réapplique les couleurs alternées sans écraser les autres tags éventuels."""
        for idx, item in enumerate(tree.get_children()):
            tags = tuple(t for t in tree.item(item, "tags") if t not in ("row_even", "row_odd"))
            alt_tag = "row_even" if idx % 2 == 0 else "row_odd"
            tree.item(item, tags=tags + (alt_tag,))

    def generate_bl_ref(self):
        year = datetime.now().year
        conn = self.connect_db()
        if conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM tb_livraisoncli WHERE EXTRACT(YEAR FROM dateregistre) = %s", (year,))
            count = cur.fetchone()[0] + 1
            conn.close()
            return f"{year}-BL-{count:05d}"
        return f"{year}-BL-00001"

    def setup_ui(self):
        # --- Barre supérieure ---
        header = ctk.CTkFrame(self)
        header.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(header, text=f"Date: {datetime.now().strftime('%d/%m/%Y')}").pack(side="left", padx=10)
        
        self.bl_var = ctk.StringVar(value=self.generate_bl_ref())
        ctk.CTkLabel(header, text="BL N°:").pack(side="left", padx=5)
        self.ent_bl = ctk.CTkEntry(header, textvariable=self.bl_var, state="readonly", width=140)
        self.ent_bl.pack(side="left")

        ctk.CTkButton(header, text="Charger Facture", command=self.ouvrir_selection_facture, fg_color="#1f538d").pack(side="right", padx=10)

        # --- Infos Client ---
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(fill="x", padx=10, pady=5)
        self.lbl_client = ctk.CTkLabel(info_frame, text="Client: ---", font=("Arial", 13, "bold"))
        self.lbl_client.pack(side="left", padx=10)
        self.lbl_facture = ctk.CTkLabel(info_frame, text="N° Facture: ---", font=("Arial", 13))
        self.lbl_facture.pack(side="right", padx=10)

        # --- Tableau ---
        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Colonnes visibles et colonnes cachées pour les IDs
        cols = ("code", "nom", "unite", "qt_vente", "qt_livre", "id_art", "id_unite", "id_mag")
        self.tree = ttk.Treeview(self.tree_frame, columns=cols, show="headings", height=15)
        self._configure_table_alternating_colors(self.tree)
        
        # Configuration des colonnes visibles
        col_config = [
            ("code", "Code Article", 120),
            ("nom", "Désignation", 250),
            ("unite", "Unité", 100),
            ("qt_vente", "Qté Vendue", 100),
            ("qt_livre", "Qté à Livrer", 100)
        ]
        
        for col, text, width in col_config:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="center")
        
        # Colonnes cachées pour les IDs
        for col in cols[5:]:
            self.tree.column(col, width=0, stretch=False)

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True, side="left")
        
        self.tree.bind("<Double-1>", self.modifier_quantite)

        # --- Label d'instruction ---
        ctk.CTkLabel(self, text="💡 Double-cliquez sur une ligne pour modifier la quantité à livrer", 
                     font=("Arial", 11), text_color="gray").pack(pady=5)

        # --- Actions ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(btn_frame, text="Annuler / Vider", fg_color="#e74c3c", 
                      command=self.reinitialiser, width=150).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Enregistrer & Imprimer PDF", fg_color="#27ae60", 
                      command=self.enregistrer_livraison, width=200).pack(side="right", padx=5)

    def ouvrir_selection_facture(self):
        top = ctk.CTkToplevel(self)
        top.title("Sélectionner Facture")
        top.geometry("700x550")
        top.attributes('-topmost', True)

        # Filtre Date
        filter_frame = ctk.CTkFrame(top)
        filter_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(filter_frame, text="Date :").pack(side="left", padx=5)

        cal_container = ctk.CTkFrame(filter_frame, fg_color="transparent")
        cal_container.pack(side="left", padx=5)

        ent_date = DateEntry(cal_container, 
                             width=12, 
                             background='darkblue',
                             foreground='white', 
                             borderwidth=2,
                             date_pattern='yyyy-mm-dd',
                             locale='fr_FR')
        ent_date.pack(padx=2, pady=2)

        tree_f = ttk.Treeview(top, columns=("ref", "client", "date", "idcli", "idmag"), show="headings")
        self._configure_table_alternating_colors(tree_f)
        
        col_config = [
            ("ref", "N° Facture", 150),
            ("client", "Nom Client", 250),
            ("date", "Date", 150)
        ]
        
        for c, t, w in col_config:
            tree_f.heading(c, text=t)
            tree_f.column(c, width=w)
        
        tree_f.column("idcli", width=0, stretch=False)
        tree_f.column("idmag", width=0, stretch=False)
        
        tree_f.pack(fill="both", expand=True, padx=10, pady=5)

        def charger(date_val=None):
            for i in tree_f.get_children(): 
                tree_f.delete(i)
            self._refresh_table_alternating_colors(tree_f)
            conn = self.connect_db()
            if conn:
                cur = conn.cursor()
                try:
                    query_base = """
                        SELECT v.refvente, c.nomcli, v.dateregistre, v.idclient, v.idmag 
                        FROM tb_vente v 
                        JOIN tb_client c ON v.idclient = c.idclient 
                        WHERE (
                            SELECT COALESCE(SUM(vd.qtvente), 0) 
                            FROM tb_ventedetail vd WHERE vd.idvente = v.id
                        ) > (
                            SELECT COALESCE(SUM(l.qtlivrecli), 0) 
                            FROM tb_livraisoncli l WHERE l.refvente = v.refvente
                        )
                    """
                    
                    if date_val:
                        cur.execute(query_base + " AND CAST(v.dateregistre AS DATE) = %s ORDER BY v.dateregistre DESC", (date_val,))
                    else:
                        cur.execute(query_base + " ORDER BY v.dateregistre DESC LIMIT 50")
                    
                    for r in cur.fetchall():
                        date_formatted = r[2].strftime('%d/%m/%Y') if hasattr(r[2], 'strftime') else str(r[2])
                        tree_f.insert("", "end", values=(r[0], r[1], date_formatted, r[3], r[4]))
                    self._refresh_table_alternating_colors(tree_f)
                except Exception as e:
                    messagebox.showerror("Erreur", f"Erreur lors du chargement: {e}")
                finally:
                    conn.close()
        
        def valider():
            sel = tree_f.selection()
            if sel:
                v = tree_f.item(sel)['values']
                self.charger_details_facture(v[0], v[1], v[3], v[4])
                top.destroy()
            else:
                messagebox.showwarning("Sélection", "Veuillez sélectionner une facture.")

        ctk.CTkButton(top, text="Choisir cette facture", command=valider, 
                      fg_color="#27ae60", width=200).pack(pady=10)
        
        charger()

    def charger_details_facture(self, ref, nom, idcli, idmag):
        self.selected_ref_vente = ref
        self.selected_id_client = idcli
        self.selected_id_mag = idmag
        
        self.lbl_client.configure(text=f"Client: {nom}")
        self.lbl_facture.configure(text=f"N° Facture: {ref}")
        
        for i in self.tree.get_children(): 
            self.tree.delete(i)
        self._refresh_table_alternating_colors(self.tree)
        
        conn = self.connect_db()
        if conn:
            cur = conn.cursor()
            try:
                # 1. Récupérer l'ID de la vente
                cur.execute("SELECT id FROM tb_vente WHERE refvente = %s", (ref,))
                result = cur.fetchone()
                
                if not result:
                    messagebox.showwarning("Erreur", "Facture introuvable.")
                    conn.close()
                    return
                
                idvente = result[0]
                
                # 2. Requête modifiée pour calculer le reliquat (Reste à livrer)
                # On fait la différence entre la quantité vendue et la somme des quantités déjà livrées
                query = """
                    SELECT 
                        u.codearticle, 
                        a.designation, 
                        u.designationunite, 
                        vd.qtvente, 
                        (vd.qtvente - COALESCE((
                            SELECT SUM(l.qtlivrecli) 
                            FROM tb_livraisoncli l 
                            WHERE l.refvente = %s 
                            AND l.idarticle = vd.idarticle 
                            AND l.idunite = vd.idunite
                        ), 0)) as reste_a_livrer,
                        vd.idarticle, 
                        vd.idunite,
                        vd.idmag
                    FROM tb_ventedetail vd 
                    JOIN tb_article a ON vd.idarticle = a.idarticle
                    JOIN tb_unite u ON vd.idunite = u.idunite
                    WHERE vd.idvente = %s
                    ORDER BY a.designation
                """
                
                cur.execute(query, (ref, idvente))
                
                rows = cur.fetchall()
                if not rows:
                    messagebox.showwarning("Aucune donnée", "Aucun article trouvé pour cette facture.")
                else:
                    for r in rows:
                        reste = float(r[4])
                        # On n'affiche que les lignes où il reste quelque chose à livrer (optionnel)
                        if reste > 0:
                            self.tree.insert("", "end", values=(
                                r[0],  # code article
                                r[1],  # désignation
                                r[2],  # unité
                                r[3],  # qté initiale vendue
                                reste, # qté à livrer (Calculée : Vendu - Déjà livré)
                                r[5],  # id article
                                r[6],  # id unite
                                r[7]   # id mag
                            ))
                    self._refresh_table_alternating_colors(self.tree)
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du chargement des détails: {e}")
            finally:
                conn.close()

    def modifier_quantite(self, event):
        selection = self.tree.selection()
        if not selection:
            return
            
        item = selection[0]
        v = self.tree.item(item)['values']
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Modifier la quantité")
        dialog.geometry("400x200")
        dialog.attributes('-topmost', True)
        
        ctk.CTkLabel(dialog, text=f"Article: {v[1]}", font=("Arial", 12, "bold")).pack(pady=10)
        ctk.CTkLabel(dialog, text=f"Quantité vendue: {v[3]}").pack(pady=5)
        
        frame = ctk.CTkFrame(dialog)
        frame.pack(pady=10)
        
        ctk.CTkLabel(frame, text="Quantité à livrer:").pack(side="left", padx=5)
        entry = ctk.CTkEntry(frame, width=100)
        entry.insert(0, str(v[4]))
        entry.pack(side="left", padx=5)
        entry.focus()
        
        def valider():
            new_val = entry.get()
            try:
                val_new = float(new_val)
                if val_new < 0:
                    messagebox.showwarning("Erreur", "La quantité ne peut pas être négative.")
                elif val_new > float(v[3]):
                    messagebox.showwarning("Erreur", f"La quantité livrée ({val_new}) dépasse la quantité vendue ({v[3]}).")
                else:
                    lst = list(v)
                    lst[4] = val_new
                    self.tree.item(item, values=lst)
                    dialog.destroy()
            except ValueError:
                messagebox.showerror("Erreur", "Veuillez entrer un nombre valide.")
        
        btn_frame = ctk.CTkFrame(dialog)
        btn_frame.pack(pady=10)
        
        ctk.CTkButton(btn_frame, text="Valider", command=valider, fg_color="#27ae60").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Annuler", command=dialog.destroy, fg_color="#e74c3c").pack(side="left", padx=5)
        
        entry.bind("<Return>", lambda e: valider())

    def reinitialiser(self):
        self.selected_ref_vente = None
        self.selected_id_client = None
        self.selected_id_mag = None
        self.lbl_client.configure(text="Client: ---")
        self.lbl_facture.configure(text="N° Facture: ---")
        for i in self.tree.get_children(): 
            self.tree.delete(i)
        self._refresh_table_alternating_colors(self.tree)
        self.bl_var.set(self.generate_bl_ref())

    def enregistrer_livraison(self):
        # Vérifier user_id au début
        if self.user_id is None:
            messagebox.showerror("Erreur", "Aucun utilisateur connecté. Impossible d'enregistrer.")
            return
            
        if not self.selected_ref_vente:
            messagebox.showwarning("Attention", "Veuillez d'abord charger une facture.")
            return
        
        lignes = self.tree.get_children()
        if not lignes:
            messagebox.showwarning("Attention", "Aucun article à livrer.")
            return
        
        # Vérifier qu'il y a au moins UN article avec une quantité > 0
        # pour ne pas générer un BL vide inutilement
        has_delivery = any(float(self.tree.item(i)['values'][4]) > 0 for i in lignes)
        
        if not has_delivery:
            messagebox.showwarning("Attention", "Aucun article n'a de quantité à livrer (toutes les lignes sont à 0).")
            return

        refliv = self.bl_var.get()
        conn = self.connect_db()
        if conn:
            try:
                cur = conn.cursor()
                
                for i in lignes:
                    v = self.tree.item(i)['values']
                    qt_livre = float(v[4])
                    
                    # On enregistre même si qt_livre est 0 pour garder la trace du reliquat
                    # OU vous pouvez garder le IF pour n'enregistrer que ce qui sort réellement
                    cur.execute("""
                        INSERT INTO tb_livraisoncli 
                        (reflivcli, refvente, idmag, idarticle, idunite, qtvente, qtlivrecli, dateregistre, iduser, idclient)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        refliv,
                        self.selected_ref_vente,
                        v[7],
                        v[5],
                        v[6],
                        v[3],
                        qt_livre, # Accepte maintenant 0
                        datetime.now(),
                        self.user_id,
                        self.selected_id_client
                    ))
                
                conn.commit()
                
                # Générer le PDF (le PDF filtrera automatiquement les lignes à 0 pour la clarté)
                self.imprimer_pdf(refliv)
                
                messagebox.showinfo("Succès", f"Bon de livraison {refliv} enregistré avec succès !")
                self.reinitialiser()
                
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement: {e}")
                import traceback
                traceback.print_exc()
            finally:
                conn.close()

    def imprimer_pdf(self, refliv):
        try:
            path = f"Livraison_{refliv.replace('-', '_')}.pdf"
            c = canvas.Canvas(path, pagesize=A5)
            w, h = A5
            
            info_soc = {}
            nom_user = ""
            conn = self.connect_db()
            if conn:
                cur = conn.cursor()
                cur.execute("SELECT nomsociete, adressesociete, contactsociete, villesociete, nifsociete, statsociete, cifsociete FROM tb_infosociete LIMIT 1")
                res = cur.fetchone()
                if res:
                    info_soc = {
                        'nom': res[0], 'adr': res[1], 'tel': res[2], 
                        'ville': res[3], 'nif': res[4], 'stat': res[5], 'cif': res[6]
                    }
                
                # ✅ CORRECTION 3: Utiliser self.user_id ici aussi
                cur.execute("SELECT nomuser, prenomuser FROM tb_users WHERE iduser = %s", (self.user_id,))
                u = cur.fetchone()
                if u:
                    nom_user = f"{u[0]} {u[1]}"
                conn.close()

            c.setFont("Helvetica-Bold", 12)
            c.drawString(30, h-30, info_soc.get('nom', "MA SOCIÉTÉ").upper())
            
            c.setFont("Helvetica", 8)
            y_head = h-42
            c.drawString(30, y_head, f"{info_soc.get('adr', '')} - {info_soc.get('ville', '')}")
            c.drawString(30, y_head-10, f"Contact: {info_soc.get('tel', '')}")
            c.drawString(30, y_head-20, f"NIF: {info_soc.get('nif', '')} | STAT: {info_soc.get('stat', '')} | CIF: {info_soc.get('cif', '')}")

            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(w/2, h-85, "BON DE LIVRAISON")
            
            c.setFont("Helvetica", 9)
            c.drawString(30, h-110, f"BL N°: {refliv}")
            c.drawString(30, h-122, f"Facture: {self.selected_ref_vente}")
            c.drawString(w-180, h-110, f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            c.drawString(w-180, h-122, f"Client: {self.lbl_client.cget('text').replace('Client: ', '')}")
            
            y_pre_table = h-145
            c.setFont("Helvetica-Oblique", 9)
            c.drawString(30, y_pre_table, f"Etabli par: {nom_user}")
            
            y = y_pre_table - 15
            c.setLineWidth(1)
            c.line(30, y, w-30, y)
            
            c.setFont("Helvetica-Bold", 9)
            c.drawString(35, y-15, "Désignation")
            c.drawString(w-150, y-15, "Unité")
            c.drawString(w-80, y-15, "Qté Livrée")
            
            c.setLineWidth(0.5)
            c.line(30, y-18, w-30, y-18)
            
            y -= 35
            c.setFont("Helvetica", 8)
            
            for i in self.tree.get_children():
                v = self.tree.item(i)['values']
                qt_livre = float(v[4])
                
                if qt_livre > 0:
                    designation = str(v[1])[:35]
                    c.drawString(35, y, designation)
                    c.drawString(w-150, y, str(v[2]))
                    c.drawString(w-75, y, str(qt_livre))
                    y -= 15
                    
                    if y < 60:
                        c.showPage()
                        y = h - 50
            
            c.setFont("Helvetica-Oblique", 8)
            c.drawString(30, 40, "Signature du livreur: _______________")
            c.drawString(w-180, 40, "Signature du client: _______________")
            
            c.save()
            
            import sys
            if os.name == 'nt': 
                os.startfile(path)
            else:
                import subprocess
                cmd = 'open' if sys.platform == 'darwin' else 'xdg-open'
                subprocess.call([cmd, path])
            
        except Exception as e:
            messagebox.showerror("Erreur PDF", f"Erreur lors de la génération du PDF: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    root = ctk.CTk()
    root.title("Gestion des Livraisons Client")
    root.geometry("900x600")
    
    USER_ID = 1 
    
    app = PageLivraisonClient(root, id_user_connecte=USER_ID)
    app.pack(fill="both", expand=True)
    root.mainloop()
