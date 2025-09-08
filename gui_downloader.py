# gui_commcare_downloader.py
# -*- coding: utf-8 -*-
import os, sys, threading, queue, logging
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import shutil

MODULE_NAME = "commcare_downloader"
ID_ENV_FILENAME = "id_cc.env"

try:
    downloader = __import__(MODULE_NAME)
except Exception as e:
    raise SystemExit(
        f"Impossible d'importer le module '{MODULE_NAME}'. "
        f"Place ton script comme '{MODULE_NAME}.py' dans ce dossier.\nErreur: {e}"
    )

log_queue = queue.Queue()

class TkQueueHandler(logging.Handler):
    def emit(self, record):
        try: log_queue.put_nowait(record)
        except Exception: pass

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
formatter = logging.Formatter(LOG_FORMAT, datefmt="%H:%M:%S")
root_logger = logging.getLogger(); root_logger.setLevel(logging.INFO)
gui_handler = TkQueueHandler(); gui_handler.setFormatter(formatter); root_logger.addHandler(gui_handler)
for h in list(root_logger.handlers):
    if h is not gui_handler:
        root_logger.removeHandler(h)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CommCare Smart Downloader — GUI")
        self.geometry("980x680")
        self.minsize(900, 600)
        self.state('zoomed')  # Plein écran au lancement
        self.running_thread = None
        self.keep_env_file = tk.BooleanVar(value=False)
        self.headless_var = tk.BooleanVar(value=False)
        self.email_var = tk.StringVar()
        self.pass_var = tk.StringVar()
        default_dir = str(Path.home() / "Downloads")
        self.dir_var = tk.StringVar(value=default_dir)
        self.base_vars = []
        self._build_ui()
        self._load_expected_bases()
        self._poll_log_queue()

    def _build_ui(self):
        form = ttk.Frame(self, padding=10); form.pack(fill="x")
        row1 = ttk.Frame(form); row1.pack(fill="x", pady=(0,8))
        ttk.Label(row1, text="Email:", width=12).pack(side="left")
        ttk.Entry(row1, textvariable=self.email_var, width=40).pack(side="left", padx=(0,10))
        ttk.Label(row1, text="Mot de passe:", width=14).pack(side="left")
        pwd = ttk.Entry(row1, textvariable=self.pass_var, width=30, show="•"); pwd.pack(side="left", padx=(0,10))
        ttk.Checkbutton(row1, text="Afficher", command=lambda: pwd.config(show="" if pwd.cget("show")=="•" else "•")).pack(side="left")
        row2 = ttk.Frame(form); row2.pack(fill="x", pady=(0,8))
        ttk.Label(row2, text="Dossier téléchargement:", width=20).pack(side="left")
        ttk.Entry(row2, textvariable=self.dir_var).pack(side="left", fill="x", expand=True, padx=(0,6))
        ttk.Button(row2, text="Parcourir…", command=self._browse_dir).pack(side="left", padx=(0,10))
        ttk.Checkbutton(row2, text="Headless (sans fenêtre Chrome)", variable=self.headless_var).pack(side="left")
        row3 = ttk.Frame(form); row3.pack(fill="x", pady=(0,8))
        ttk.Checkbutton(row3, text="Conserver id_cc.env (ne pas supprimer après)", variable=self.keep_env_file).pack(side="left")
        sel = ttk.LabelFrame(self, text="Exports CommCare à télécharger", padding=10); sel.pack(fill="both", expand=False, padx=10, pady=(0,10))
        canvas = tk.Canvas(sel, height=200); scroll = ttk.Scrollbar(sel, orient="vertical", command=canvas.yview)
        self.list_frame = ttk.Frame(canvas)
        self.list_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=self.list_frame, anchor="nw"); canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True); scroll.pack(side="right", fill="y")

        # --- Lancer button just after export box ---
        lancer_frame = ttk.Frame(self, padding=(10,0,10,0)); lancer_frame.pack(fill="x")
        self.run_btn = ttk.Button(lancer_frame, text="▶ Lancer le téléchargement", command=self._on_run, width=25); self.run_btn.pack(side="left")

        # --- Encadré Call App ---
        callapp_frame = ttk.LabelFrame(self, text="Exécution Call App", padding=10)
        callapp_frame.pack(fill="x", expand=False, padx=10, pady=(0,10))
        callapp_row = ttk.Frame(callapp_frame)
        callapp_row.pack(fill="x", pady=(0,4))
        ttk.Label(callapp_row, text="Date de début:").pack(side="left")
        self.start_date_var = tk.StringVar()
        self.end_date_var = tk.StringVar()
        self.start_date_entry = ttk.Entry(callapp_row, textvariable=self.start_date_var, width=12)
        self.start_date_entry.pack(side="left", padx=(2,10))
        ttk.Label(callapp_row, text="Date de fin:").pack(side="left")
        self.end_date_entry = ttk.Entry(callapp_row, textvariable=self.end_date_var, width=12)
        self.end_date_entry.pack(side="left", padx=(2,10))
        ttk.Button(callapp_row, text="Exécuter Call App", command=self._on_callapp_run).pack(side="left", padx=(10,0))

        # --- Encadré Dashboard PVVIH ---
        self._build_dashboard_frame()

        btns = ttk.Frame(self, padding=(10,0,10,10)); btns.pack(fill="x")
        ttk.Button(btns, text="🧹 Effacer logs", command=self._clear_logs).pack(side="left", padx=6)
        ttk.Button(btns, text="📂 Ouvrir dossier", command=self._open_folder).pack(side="left")
        ttk.Button(btns, text="Quitter", command=self._on_quit).pack(side="right")
        logs_box = ttk.LabelFrame(self, text="Logs", padding=8); logs_box.pack(fill="both", expand=True, padx=10, pady=(0,10))
        self.text = tk.Text(logs_box, wrap="word"); self.text.pack(side="left", fill="both", expand=True)
        tscroll = ttk.Scrollbar(logs_box, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=tscroll.set); tscroll.pack(side="right", fill="y")
        self.text.tag_configure("INFO", foreground="#0a5")
        self.text.tag_configure("WARNING", foreground="#c90")
        self.text.tag_configure("ERROR", foreground="#d11")
        self.text.tag_configure("CRITICAL", foreground="#d11", underline=True)
        self.status = ttk.Label(self, text="Prêt.", anchor="w", relief="sunken"); self.status.pack(fill="x", side="bottom")

    def _build_dashboard_frame(self):
        dashboard_frame = ttk.LabelFrame(self, text="Dashboard PVVIH", padding=10)
        dashboard_frame.pack(fill="x", expand=False, padx=10, pady=(0,10))
        dashboard_row = ttk.Frame(dashboard_frame)
        dashboard_row.pack(fill="x", pady=(0,4))
        ttk.Button(dashboard_row, text="Ouvrir le Dashboard PVVIH", command=self._open_dashboard_pvvih).pack(side="left", padx=(2,10))
        # Nouveau bouton pour lancer RStudio
        ttk.Button(dashboard_row, text="Ouvrir RStudio", command=self._run_rstudio).pack(side="left", padx=(2,10))
        ttk.Button(dashboard_row, text="Exécuter run_all.sh", command=self._on_run_all_sh).pack(side="left", padx=(2,10))

    def _run_rstudio(self):
        import subprocess
        try:
            subprocess.Popen([sys.executable, "lancer_rstudio.py"], cwd=os.getcwd())
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de lancer RStudio : {e}")

    def _open_dashboard_pvvih(self):
        import webbrowser
        webbrowser.open_new("https://massonmoise.shinyapps.io/dashboard-pvvih/")

    def _on_callapp_run(self):
        import subprocess
        import threading

        def run_and_log():
            try:
                # Récupère les dates depuis le GUI si besoin
                start_date = self.start_date_var.get().strip()
                end_date = self.end_date_var.get().strip()
                args = [sys.executable, "call-app.py"]
                if start_date:
                    args += ["--start_date", start_date]
                if end_date:
                    args += ["--end_date", end_date]
                # Lance le script et capture stdout/stderr
                proc = subprocess.Popen(
                    args,
                    cwd=os.getcwd(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                # Affiche la sortie en temps réel dans le log du GUI
                for line in proc.stdout:
                    self._append_log(line.rstrip(), "INFO")
                proc.wait()
                if proc.returncode == 0:
                    self._append_log("call-app.py terminé avec succès.", "INFO")
                else:
                    self._append_log(f"call-app.py terminé avec une erreur (code {proc.returncode}).", "ERROR")
            except Exception as e:
                self._append_log(f"Erreur lors de l'exécution de call-app.py : {e}", "ERROR")
            finally:
                self.after(0, lambda: self.run_btn.config(state="normal"))

        self.run_btn.config(state="disabled")
        self._append_log("\n=== Exécution de call-app.py ===\n", "INFO")
        threading.Thread(target=run_and_log, daemon=True).start()

    def _load_expected_bases(self):
        bases = list(getattr(downloader, "EXPECTED_BASES", [])) or list(getattr(downloader, "EXPORT_URLS", {}).keys())
        bases = sorted(bases, key=str.lower)
        # Mapping programme
        PROGRAM_CATEGORIES = {
            "CALL":[],
            "PTME": [],
            "OEV": [],
            "MUSO": [],
            "GARDENS": []
        }
        for b in bases:
            b_low = b.lower()
            if "appels" in b_low or "visite" in b_low:
                PROGRAM_CATEGORIES["CALL"].append(b)            
            elif "ptme with" in b_low or "officiel" in b_low or "mother" in b_low:
                PROGRAM_CATEGORIES["PTME"].append(b)
            elif "child" in b_low or "caseid" in b_low or "household_child" in b_low:
                PROGRAM_CATEGORIES["OEV"].append(b)
            elif "muso" in b_low:
                PROGRAM_CATEGORIES["MUSO"].append(b)
            else :
                PROGRAM_CATEGORIES["GARDENS"].append(b)
                
        head = ttk.Frame(self.list_frame); head.pack(fill="x")
        self.select_all_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(head, text="(Tout sélectionner / désélectionner)", variable=self.select_all_var, command=self._toggle_all).pack(side="left")
        ttk.Label(head, text="  —  Exécuter uniquement les éléments cochés").pack(side="left")

        self.category_frames = {}
        # Affichage horizontal : 5 colonnes, tous les programmes sur une seule ligne
        cats = [cat for cat in ["CALL","PTME", "OEV", "MUSO", "GARDENS"] if PROGRAM_CATEGORIES[cat]]
        n_col = 5
        grid_frame = ttk.Frame(self.list_frame)
        grid_frame.pack(fill="x", padx=2, pady=2)
        self.program_select_vars = {}
        self.program_base_vars = {cat: [] for cat in cats}
        self.program_checkbuttons = {cat: [] for cat in cats}
        def update_program_var(cat):
            # Met à jour la case programme selon l'état de toutes les cases enfants
            all_checked = all(v.get() for _, v in self.program_base_vars[cat])
            all_unchecked = all(not v.get() for _, v in self.program_base_vars[cat])
            if all_checked:
                self.program_select_vars[cat].set(True)
            elif all_unchecked:
                self.program_select_vars[cat].set(False)
            else:
                # État intermédiaire (ni tout coché ni tout décoché)
                self.program_select_vars[cat].set(False)
        for idx, cat in enumerate(cats):
            lf = ttk.LabelFrame(grid_frame, text=cat, padding=(6,2,6,6))
            lf.grid(row=0, column=idx, sticky="nsew", padx=6, pady=4)
            self.category_frames[cat] = lf
            prog_var = tk.BooleanVar(value=True)
            self.program_select_vars[cat] = prog_var
            def make_toggle(cat=cat):
                def toggle():
                    val = self.program_select_vars[cat].get()
                    for _, v in self.program_base_vars[cat]:
                        v.set(val)
                return toggle
            ttk.Checkbutton(lf, text="Tout sélectionner/désélectionner", variable=prog_var, command=make_toggle(cat)).pack(anchor="w", pady=(0,2))
            for b in PROGRAM_CATEGORIES[cat]:
                var = tk.BooleanVar(value=True)
                def make_child_callback(cat=cat, var=var):
                    def cb(*args):
                        update_program_var(cat)
                    return cb
                var.trace_add('write', make_child_callback(cat, var))
                ttk.Checkbutton(lf, text=b, variable=var).pack(anchor="w")
                self.base_vars.append((b, var))
                self.program_base_vars[cat].append((b, var))
        for c in range(n_col):
            grid_frame.grid_columnconfigure(c, weight=1)

    def _toggle_all(self):
        for _, v in self.base_vars: v.set(self.select_all_var.get())

    def _browse_dir(self):
        d = filedialog.askdirectory(initialdir=self.dir_var.get() or str(Path.home()))
        if d: self.dir_var.set(d)

    def _open_folder(self):
        path = self.dir_var.get(); p = Path(path)
        if not p.exists(): messagebox.showerror("Erreur", f"Dossier introuvable: {p}"); return
        try:
            if sys.platform.startswith("win"): os.startfile(str(p))
            elif sys.platform == "darwin": os.system(f"open '{p}'")
            else: os.system(f"xdg-open '{p}'")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'ouvrir le dossier: {e}")

    def _clear_logs(self): self.text.delete("1.0", "end")
    def _append_log(self, text, level="INFO"): self.text.insert("end", text, level); self.text.see("end")

    def _poll_log_queue(self):
        import queue as q
        try:
            while True:
                record = log_queue.get_nowait()
                msg = formatter.format(record) + "\n"
                level = record.levelname if record.levelname in ("INFO","WARNING","ERROR","CRITICAL") else "INFO"
                self._append_log(msg, level); self.status.config(text=f"Dernier message: {record.levelname}")
        except q.Empty: pass
        self.after(120, self._poll_log_queue)

    def _on_run(self):
        if self.running_thread and self.running_thread.is_alive():
            messagebox.showinfo("En cours", "Un téléchargement est déjà en cours.")
            return
        
        selected = [b for (b,v) in self.base_vars if v.get()]
        if not selected: 
            messagebox.showwarning("Sélection vide", "Coche au moins un export à exécuter.")
            return
        
        dl_dir = self.dir_var.get().strip()
        if not dl_dir: 
            messagebox.showwarning("Dossier manquant", "Choisis un dossier de téléchargement.")
            return
        
        Path(dl_dir).mkdir(parents=True, exist_ok=True)
        
        # Configuration du downloader
        downloader.DOWNLOAD_DIR = dl_dir
        downloader.HEADLESS = bool(self.headless_var.get())
        downloader.EXPECTED_BASES = selected
        
        email = self.email_var.get().strip()
        password = self.pass_var.get().strip()
        
        if not email or not password:
            if not messagebox.askyesno("Sans identifiants","EMAIL/PASSWORD non renseignés.\nLe script essaiera d'utiliser un id_cc.env existant.\nContinuer ?"):
                return
        
        def write_env():
            if not email or not password: return None
            Path(ID_ENV_FILENAME).write_text(f"EMAIL={email}\nPASSWORD={password}\n", encoding="utf-8")
            return Path(ID_ENV_FILENAME)
        
        env_path = write_env()
        
        self.run_btn.config(state="disabled")
        self.status.config(text="Exécution en cours…")
        self._append_log("\n=== LANCEMENT DU TÉLÉCHARGEMENT ===\n", "INFO")
        
        def worker():
            try:
                downloader.main_enhanced()
            except Exception as e:
                logging.getLogger().exception(f"Erreur pendant l'exécution: {e}")
            finally:
                if env_path and not self.keep_env_file.get():
                    try: 
                        Path(env_path).unlink(missing_ok=True)
                        logging.getLogger().info("Fichier id_cc.env temporaire supprimé.")
                    except Exception: 
                        pass
                self.after(0, lambda: self.run_btn.config(state="normal"))
                self.after(0, lambda: self.status.config(text="Terminé."))
        
        self.running_thread = threading.Thread(target=worker, daemon=True)
        self.running_thread.start()

    def _on_quit(self):
        if self.running_thread and self.running_thread.is_alive():
            if not messagebox.askyesno("Quitter ?", "Un traitement est en cours. Quitter quand même ?"): return
        self.destroy()

    def _on_run_all_sh(self):
        import subprocess
        import threading

        def run_and_log():
            try:
                import shutil
                bash_path = shutil.which("bash") or shutil.which("wsl")
                if bash_path:
                    cmd = [bash_path, "run_all.sh"]
                else:
                    messagebox.showerror("Erreur", "Aucun interpréteur bash trouvé (installez Git Bash ou WSL).")
                    return

                proc = subprocess.Popen(
                    cmd,
                    cwd=os.getcwd(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    bufsize=1
                )
                for line in proc.stdout:
                    self._append_log(line.rstrip(), "INFO")
                proc.wait()
                if proc.returncode == 0:
                    self._append_log("run_all.sh terminé avec succès.", "INFO")
                else:
                    self._append_log(f"run_all.sh terminé avec une erreur (code {proc.returncode}).", "ERROR")
            except Exception as e:
                self._append_log(f"Erreur lors de l'exécution de run_all.sh : {e}", "ERROR")

        self._append_log("\n=== Exécution de run_all.sh ===\n", "INFO")
        threading.Thread(target=run_and_log, daemon=True).start()

if __name__ == "__main__":
    app = App()
    app.mainloop()
