import customtkinter as ctk
from tkinter import messagebox
import psycopg2
import json
from datetime import datetime
from resource_utils import get_config_path, safe_file_read


class PageChat(ctk.CTkFrame):
    def __init__(self, master, session_data=None):
        # Utilisation de super().__init__ sans appeler de méthodes de fenêtre (geometry, title)
        super().__init__(master)
        
        # Gestion du cas où session_data n'est pas fourni
        if session_data is None:
            session_data = {}
        
        self.id_user_connecte = session_data.get('iduser')
        self.nom_user_connecte = session_data.get('username')
        
        # Vérification que les données de session sont valides
        if self.id_user_connecte is None or self.nom_user_connecte is None:
            messagebox.showerror("Erreur", "Données de session invalides. Veuillez vous reconnecter.")
            return
        
        self.destinataire_actuel = None 
        self.boutons_contact = {} 

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        
        ctk.CTkLabel(self.sidebar, text="Collaborateurs", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold")).pack(pady=10)
        self.scroll_contacts = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.scroll_contacts.pack(fill="both", expand=True, padx=5, pady=5)
        
        # --- CHAT AREA ---
        self.chat_container = ctk.CTkFrame(self, fg_color="transparent")
        self.chat_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.chat_container.grid_rowconfigure(1, weight=1)
        self.chat_container.grid_columnconfigure(0, weight=1)

        self.header_chat = ctk.CTkLabel(self.chat_container, text="Sélectionnez un collègue", font=ctk.CTkFont(family="Segoe UI", size=14))
        self.header_chat.grid(row=0, column=0, pady=10)

        self.text_display = ctk.CTkTextbox(self.chat_container, state="disabled", wrap="word")
        self.text_display.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        self.input_frame = ctk.CTkFrame(self.chat_container, fg_color="transparent")
        self.input_frame.grid(row=2, column=0, sticky="ew", pady=10)
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.entry_msg = ctk.CTkEntry(self.input_frame, placeholder_text="Écrivez votre message...")
        self.entry_msg.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.entry_msg.bind("<Return>", lambda e: self.envoyer_message())

        self.btn_send = ctk.CTkButton(self.input_frame, text="Envoyer", width=100, command=self.envoyer_message)
        self.btn_send.grid(row=0, column=1)

        self.charger_employes()
        self.auto_refresh()

    def connect_db(self):
        try:
            with open(get_config_path('config.json')) as f:
                config = json.load(f)
                db_config = config['database']
            return psycopg2.connect(**db_config)
        except Exception as err:
            messagebox.showerror("Erreur de connexion", f"Impossible de se connecter à la base de données: {err}")
            return None

    def charger_employes(self):
        for widget in self.scroll_contacts.winfo_children():
            widget.destroy()
        self.boutons_contact = {}

        conn = self.connect_db()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("SELECT iduser, username FROM tb_users WHERE iduser != %s AND deleted = 0", (self.id_user_connecte,))
                for row in cur.fetchall():
                    btn = ctk.CTkButton(
                        self.scroll_contacts, text=row[1], 
                        fg_color="transparent", text_color=("black", "white"),
                        anchor="w", command=lambda r=row: self.selectionner_contact(r)
                    )
                    btn.pack(fill="x", pady=2)
                    self.boutons_contact[row[0]] = {"btn": btn, "name": row[1]}
                cur.close()
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du chargement des employés: {e}")
            finally: 
                conn.close()

    def marquer_comme_lu(self, id_expediteur):
        """Met à jour la DB pour dire que les messages sont lus"""
        conn = self.connect_db()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("UPDATE tb_chat SET lu = 1 WHERE id_expediteur = %s AND id_destinataire = %s AND lu = 0",
                            (id_expediteur, self.id_user_connecte))
                conn.commit()
                cur.close()
            except Exception as e:
                print(f"Erreur lors du marquage comme lu: {e}")
            finally: 
                conn.close()

    def selectionner_contact(self, user_info):
        self.destinataire_actuel = user_info[0]
        # Reset visuel du bouton (retrait du point rouge)
        self.boutons_contact[user_info[0]]["btn"].configure(text=user_info[1], text_color=("black", "white"))
        self.header_chat.configure(text=f"Discussion avec {user_info[1]}", text_color="#1f6aa5")
        
        self.marquer_comme_lu(user_info[0])
        self.charger_messages()

    def charger_messages(self):
        if not self.destinataire_actuel: 
            return
        conn = self.connect_db()
        if conn:
            try:
                cur = conn.cursor()
                query = """SELECT id_expediteur, message, date_envoi FROM tb_chat 
                           WHERE (id_expediteur = %s AND id_destinataire = %s)
                           OR (id_expediteur = %s AND id_destinataire = %s)
                           ORDER BY date_envoi ASC"""
                cur.execute(query, (self.id_user_connecte, self.destinataire_actuel, self.destinataire_actuel, self.id_user_connecte))
                messages = cur.fetchall()
                
                self.text_display.configure(state="normal")
                self.text_display.delete("1.0", "end")
                for msg in messages:
                    prefix = "Moi : " if msg[0] == self.id_user_connecte else f"{self.boutons_contact[msg[0]]['name']} : "
                    date_str = msg[2].strftime('%H:%M') if msg[2] else ""
                    self.text_display.insert("end", f"[{date_str}] {prefix}{msg[1]}\n\n")
                self.text_display.see("end")
                self.text_display.configure(state="disabled")
                cur.close()
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du chargement des messages: {e}")
            finally: 
                conn.close()

    def envoyer_message(self):
        msg_text = self.entry_msg.get().strip()
        if not msg_text or not self.destinataire_actuel: 
            return
        conn = self.connect_db()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("INSERT INTO tb_chat (id_expediteur, id_destinataire, message, lu) VALUES (%s, %s, %s, 0)",
                            (self.id_user_connecte, self.destinataire_actuel, msg_text))
                conn.commit()
                self.entry_msg.delete(0, "end")
                cur.close()
                self.charger_messages()
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de l'envoi du message: {e}")
            finally: 
                conn.close()

    def verifier_nouveaux_messages(self):
        conn = self.connect_db()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("SELECT id_expediteur FROM tb_chat WHERE id_destinataire = %s AND lu = 0", (self.id_user_connecte,))
                nouveaux = cur.fetchall()
                
                if nouveaux:
                    self.bell()  # 🔊 BIP
                    for row in nouveaux:
                        id_exp = row[0]
                        if id_exp in self.boutons_contact and id_exp != self.destinataire_actuel:
                            nom = self.boutons_contact[id_exp]["name"]
                            self.boutons_contact[id_exp]["btn"].configure(text=f"● {nom}", text_color="red")
                        elif id_exp == self.destinataire_actuel:
                            # Si on est déjà sur la discussion, on marque comme lu immédiatement
                            self.marquer_comme_lu(id_exp)
                            self.charger_messages()
                cur.close()
            except Exception as e:
                print(f"Erreur lors de la vérification des nouveaux messages: {e}")
            finally: 
                conn.close()

    def auto_refresh(self):
        self.verifier_nouveaux_messages()
        self.after(5000, self.auto_refresh)

# --- BLOC DE TEST SÉCURISÉ ---
if __name__ == "__main__":
    root = ctk.CTk()
    root.geometry("900x600")
    root.title("IJEERY Chat")
    
    # Configuration de la grille pour la fenêtre root
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(0, weight=1)

    session = {"iduser": 1, "username": "Admin"}
    
    # On ajoute la page avec grid()
    chat_page = PageChat(root, session)
    chat_page.grid(row=0, column=0, sticky="nsew")
    
    root.mainloop()