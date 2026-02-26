import customtkinter as ctk
from pages.page_personnelAjout import PagePeronnelAjout
from pages.page_personnel import PagePersonnel

class PageMainPersonnel(ctk.CTkFrame):
    """Version Frame de MainApp pour intégration dans app_main"""
    def __init__(self, master, db_conn=None, session_data=None, **kwargs):
        super().__init__(master, **kwargs)
        
        # Stocker les paramètres nécessaires
        self.db_conn = db_conn
        self.session_data = session_data
        
        # Configuration du frame principal
        self.configure(fg_color="#ecf0f1")
        
        # Conteneur central
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Afficher la page par défaut
        self.afficher_formulaire()

    def vider_ecran(self):
        """Vide le conteneur"""
        for child in self.container.winfo_children():
            child.destroy()

    def afficher_formulaire(self):
        """Affiche le formulaire d'ajout de personnel"""
        self.vider_ecran()
        try:
            # Essayer avec db_conn et session_data
            self.page = PagePeronnelAjout(
                self.container, 
                self.afficher_liste,
                db_conn=self.db_conn,
                session_data=self.session_data
            )
        except TypeError:
            # Si ça ne marche pas, essayer sans ces paramètres
            self.page = PagePeronnelAjout(
                self.container, 
                self.afficher_liste
            )
        
        self.page.pack(fill="both", expand=True)

    def afficher_liste(self):
        """Affiche la liste du personnel"""
        self.vider_ecran()
        # PagePersonnel n'accepte que 2 paramètres : parent et callback_ajout
        self.page = PagePersonnel(
            self.container, 
            self.afficher_formulaire  # callback_ajout pour revenir au formulaire
        )
        self.page.pack(fill="both", expand=True)


# Garder MainApp pour compatibilité si utilisé ailleurs
class MainApp(ctk.CTk):
    """Version fenêtre standalone (pour usage indépendant)"""
    def __init__(self):
        super().__init__()
        self.title("Système de Gestion du Personnel")
        self.geometry("1200x800")
        
        # Conteneur central
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)
        
        # Afficher la page par défaut
        self.afficher_formulaire()

    def vider_ecran(self):
        for child in self.container.winfo_children():
            child.destroy()

    def afficher_formulaire(self):
        self.vider_ecran()
        self.page = PagePeronnelAjout(self.container, self.afficher_liste)
        self.page.pack(fill="both", expand=True)

    def afficher_liste(self):
        self.vider_ecran()
        self.page = PagePersonnel(self.container, self.afficher_formulaire)
        self.page.pack(fill="both", expand=True)


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()