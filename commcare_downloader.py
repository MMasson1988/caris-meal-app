# -*- coding: utf-8 -*-
"""
CommCare Smart Downloader - Version corrigée et stabilisée
- Clic "Download" factorisé et robuste
- Suppression des blocs imbriqués sources d'erreurs
"""

import os
import re
import time
import glob
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# Selenium imports
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains

from utils import file_matches_today

# ===================== CONFIG =====================
DOWNLOAD_DIR = r"C:\Users\caris-app\caris-dashboard-app\data"

# Liste des bases (sans date ni extension)
EXPECTED_BASES = [
    "Caris Health Agent - Enfant - Visite Enfant",
    "Caris Health Agent - Enfant - APPELS OEV",
    "Caris Health Agent - Femme PMTE  - Visite PTME",
    "Caris Health Agent - Femme PMTE  - Ration & Autres Visites",
    "Caris Health Agent - Enfant - Ration et autres visites",
    "Caris Health Agent - Femme PMTE  - APPELS PTME",
    "muso_groupes",
    "muso_beneficiaries",
    "Household mother",
    "Ajout de menages ptme [officiel]",
    "PTME WITH PATIENT CODE",
    "household_child",
    "All_child_PatientCode_CaseID",
    "MUSO - Members - PPI Questionnaires",
    "muso_household_2022",
    "All Gardens",
]

# Mapping des bases vers les URLs CommCare
EXPORT_URLS = {
    "Caris Health Agent - Enfant - Visite Enfant": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/form/download/7d960d6c03d9d6c35a8d083c288e7c8d/",
    "Caris Health Agent - Enfant - APPELS OEV": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/form/download/f817d728df7d0070b29160e54a22765b/",
    "Caris Health Agent - Femme PMTE  - Visite PTME": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/form/download/4fde80e15e96e8214eb58d5761049f0f/",
    "Caris Health Agent - Femme PMTE  - Ration & Autres Visites": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/form/download/c5c5e2292ad223156f72620c6e0fd99f/",
    "Caris Health Agent - Enfant - Ration et autres visites": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/form/download/bc95b54ff93a6c62c22a2e2f17852a90/",
    "Caris Health Agent - Femme PMTE  - APPELS PTME": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/form/download/c1a3280f5e34a2b6078439f9b59ad72c/",
    "Household mother": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/3eb9f92d8d82501ebe5c8cb89b83dbba/",
    "Ajout de menages ptme [officiel]": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/form/download/269567f0b84da5a1767712e519ced62e/",
    "PTME WITH PATIENT CODE": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/af6c4186011182dfda68a84536231f68/",
    "household_child": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/f6ddce2133f8d233d9fbd9341220ed6f/",
    "All_child_PatientCode_CaseID": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/0379abcdafdf9979863c2d634792b5a8/",
    "muso_groupes": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/462626788779f3781f9b9ebcce200225/",
    "muso_beneficiaries": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/f831c9c92760a38d24b3829df5621d20/",
    "MUSO - Members - PPI Questionnaires": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/form/download/f5daab6b0cc722a5db175e9ad86d8cda/",
    "muso_household_2022": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/462626788779f3781f9b9ebcce2b1a37/",
    "All Gardens": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/789629a97bddd10b4648d5138d17908e/",
}

# Retries & timeouts
MAX_RETRIES_PER_FILE = 3
MAX_GLOBAL_PASSES = 3
VERIFICATION_TIMEOUT = 60
HEAVY_FILE_TIMEOUT = 180  # 3 minutes pour les gros fichiers
HEADLESS = False

# Fichiers lourds nécessitant plus de temps
HEAVY_FILES = [
    "muso_beneficiaries",
    "muso_household_2022",
]

# ===================== LOGGING =====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("commcare-downloader")

# ===================== UTILS =====================
def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def expected_filename_for_today(base: str, sep: str = " ") -> str:
    # Nom attendu spécial pour "Household mother" (sans "(created ...)")
    if base.lower() == "household mother":
        return f"household mother {today_str()}.xlsx"
    # Affichage indicatif pour les autres
    return f"{base}{sep}(created XXXX-XX-XX) {today_str()}.xlsx"

def list_xlsx(folder: str) -> List[str]:
    return [os.path.basename(p) for p in glob.glob(os.path.join(folder, "*.xlsx"))]

def list_partial_downloads(folder: str) -> List[str]:
    return glob.glob(os.path.join(folder, "*.crdownload"))

def cleanup_orphan_crdownload(folder: str) -> None:
    for p in list_partial_downloads(folder):
        try:
            os.remove(p)
        except Exception:
            pass

def cleanup_duplicate_files(folder: str) -> None:
    """Nettoie les fichiers dupliqués en gardant le plus récent."""
    ensure_dir(folder)
    files = list_xlsx(folder)
    file_groups: Dict[str, List[str]] = {}
    for filename in files:
        for base in EXPECTED_BASES:
            if file_matches_today(base, filename):
                file_groups.setdefault(base, []).append(filename)
                break

    for base, group_files in file_groups.items():
        if len(group_files) > 1:
            log.info(f"Fichiers dupliqués trouvés pour {base}: {group_files}")
            group_files.sort(key=lambda f: os.path.getmtime(os.path.join(folder, f)))
            for file_to_delete in group_files[:-1]:
                try:
                    os.remove(os.path.join(folder, file_to_delete))
                    log.info(f"Fichier dupliqué supprimé: {file_to_delete}")
                except Exception as e:
                    log.warning(f"Impossible de supprimer {file_to_delete}: {e}")

def human_list(items: List[str]) -> str:
    return "[" + ", ".join(items) + "]" if items else "[]"

# ===================== PATTERN (matching des fichiers du jour) =====================
def build_pattern_with_today(base: str) -> re.Pattern:
    date = today_str()
    base_esc = re.escape(base)

    # Fichiers simplifiés (sans "(created ...)"), comparer en insensitive
    simple_pattern_files = {
        "household mother",
        "ajout de menages ptme [officiel]",
        "ptme with patient code",
        "household_child",
        "all_child_patientcode_caseid",
        "all gardens",
    }

    # Fichiers avec "(created <DATE_FIXE>)"
    special_pattern_files = {
        "muso_groupes": r"muso_groupes\s*\(created\s+2025-03-25\)\s+",
        "muso_beneficiaries": r"muso_beneficiaries\s*\(created\s+2025-03-25\)\s+",
        "muso_household_2022": r"muso_household_2022\s*\(created\s+2025-03-25\)\s+",
        "All Gardens": r"All Gardens\s*\(created\s+2025-03-25\)\s+",
    }

    if base.lower() in simple_pattern_files:
        # ex: "household mother 2025-08-14.xlsx" (ou " (1).xlsx")
        pat = rf"^{base_esc}\s+{re.escape(date)}(?:\s+\(\d+\))?\.xlsx$"
    elif base in special_pattern_files:
        special_prefix = special_pattern_files[base]
        pat = rf"^{special_prefix}{re.escape(date)}(?:\s+\(\d+\))?\.xlsx$"
    else:
        # ex: "Caris Health Agent ... (created 2025-01-01) 2025-08-14.xlsx"
        pat = rf"^{base_esc}\s*\(created\s+\d{{4}}-\d{{2}}-\d{{2}}\)\s+{re.escape(date)}\.xlsx$"

    return re.compile(pat, re.IGNORECASE)

def file_matches_today(base: str, filename: str) -> bool:
    # Normalisation pour éviter les faux négatifs (casse, espaces)
    today = today_str()
    base_norm = base.lower().replace(" ", "_")
    fname_norm = os.path.basename(filename).lower().replace(" ", "_")
    # Pattern robuste pour tous les cas
    pat = re.compile(rf"^{re.escape(base_norm)}(\s*\(created\s+\d{{4}}-\d{{2}}-\d{{2}}\))?\s+{today}(?:\s+\(\d+\))?\.xlsx$")
    return bool(pat.match(fname_norm))

# ===================== VERIFICATION =====================
def check_existing_files(expected_bases: List[str], folder_path: str) -> Tuple[List[str], Dict[str, List[str]]]:
    ensure_dir(folder_path)
    present = list_xlsx(folder_path)
    present_map: Dict[str, List[str]] = {}
    missing_bases: List[str] = []
    for base in expected_bases:
        matches = [f for f in present if file_matches_today(base, f)]
        present_map[base] = matches
        if not matches:
            missing_bases.append(base)
    return missing_bases, present_map

def _file_size_stable(path: str, wait_interval: float = 1.5) -> bool:
    try:
        s1 = os.path.getsize(path)
        time.sleep(wait_interval)
        s2 = os.path.getsize(path)
        return s1 > 0 and s1 == s2
    except Exception:
        return False

def verify_download_success_for_base(base: str, folder_path: str, timeout: int = VERIFICATION_TIMEOUT) -> Optional[str]:
    actual_timeout = HEAVY_FILE_TIMEOUT if base in HEAVY_FILES else timeout
    log.info(f"Vérification du téléchargement pour {base} (timeout: {actual_timeout}s)")
    pat = build_pattern_with_today(base)
    end = time.time() + actual_timeout

    while time.time() < end:
        if list_partial_downloads(folder_path):
            log.info(f"Téléchargement en cours pour {base}...")
            time.sleep(2.0)

        for f in list_xlsx(folder_path):
            if pat.match(f):
                full = os.path.join(folder_path, f)
                if _file_size_stable(full, wait_interval=2.0):
                    return full
        time.sleep(2.0)
    return None

# ===================== SELENIUM HELPERS =====================
def unfreeze_interface(driver):
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        driver.execute_script("arguments[0].click();", body)
        time.sleep(0.5)
        actions = ActionChains(driver)
        actions.move_by_offset(50, 50).click().perform()
        time.sleep(0.3)
        actions.move_by_offset(-50, -50).perform()
        body.send_keys(Keys.ESCAPE)
        time.sleep(0.5)
    except Exception as e:
        log.warning(f"Erreur lors du deblocage de l'interface : {e}")

def set_date_range(driver, start_date="2021-01-01", end_date=None):
    if end_date is None:
        end_date = today_str()
    try:
        date_input = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.ID, "id_date_range"))
        )
        date_input.click(); time.sleep(0.5)
        date_input.clear(); time.sleep(0.5)
        date_input.send_keys(Keys.CONTROL + "a"); time.sleep(0.2)
        date_input.send_keys(Keys.DELETE); time.sleep(0.5)
        date_range_value = f"{start_date} to {end_date}"
        date_input.send_keys(date_range_value)
        log.info(f"Plage de dates saisie : {date_range_value}")
        date_input.send_keys(Keys.TAB); time.sleep(0.5)
        unfreeze_interface(driver); time.sleep(2)
    except Exception as e:
        log.warning(f"Erreur lors de la definition de la plage de dates : {e}")
        try:
            unfreeze_interface(driver)
        except Exception:
            pass

def click_any_download_link(driver, timeout_seconds: int) -> bool:
    """
    Tente de cliquer un lien/bouton de téléchargement présent dans la modale #download-progress.
    Retourne True si un clic a pu être effectué, False sinon.
    """
    candidates = [
        (By.CSS_SELECTOR, "#download-progress a[href$='.xlsx']"),
        (By.CSS_SELECTOR, "#download-progress form a"),
        (By.CSS_SELECTOR, "#download-progress a"),
        (By.XPATH, "//div[@id='download-progress']//a[contains(., 'Download') or contains(., 'Télécharger')]"),
        (By.XPATH, "//a[contains(@href, 'download') and contains(@href, '.xlsx')]"),
        (By.XPATH, "//button[contains(., 'Download') or contains(., 'Télécharger')]"),
        (By.CSS_SELECTOR, "a[href*='download']"),
    ]

    end = time.time() + timeout_seconds
    while time.time() < end:
        for loc in candidates:
            try:
                a = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(loc))
            except TimeoutException:
                continue

            try:
                # Scroll + click JS (fiable)
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", a)
                time.sleep(0.8)
                driver.execute_script("arguments[0].click();", a)
                log.info("✅ Lien/bouton de téléchargement cliqué.")
                return True
            except StaleElementReferenceException:
                # Retenter une fois
                try:
                    a = WebDriverWait(driver, 5).until(EC.element_to_be_clickable(loc))
                    driver.execute_script("arguments[0].click();", a)
                    log.info("✅ Clic réussi après stale element.")
                    return True
                except Exception as e:
                    log.debug(f"Clic après stale échoué: {e}")
            except Exception as e:
                log.debug(f"Clic échoué: {e}")

        # courte pause avant nouvel essai
        time.sleep(2)

    return False

# ===================== DÉCLENCHEUR DOWNLOAD =====================
def trigger_download(export_base: str, driver) -> None:
    if export_base not in EXPORT_URLS:
        log.error(f"URL non trouvee pour l'export : {export_base}")
        return

    export_url = EXPORT_URLS[export_base]
    log.info(f"Acces a l'URL d'export : {export_url}")

    is_heavy_file = export_base in HEAVY_FILES
    preparation_timeout = 600 if export_base in ["muso_household_2022", "muso_beneficiaries"] else (300 if is_heavy_file else 180)
    log.info(f"Timeout de préparation: {preparation_timeout}s ({'GROS FICHIER' if is_heavy_file else 'fichier normal'})")

    try:
        driver.get(export_url)
        time.sleep(3)
        set_date_range(driver, "2021-01-01")
        time.sleep(2)

        # Bouton Prepare/Download
        prepare_locators = [
            (By.CSS_SELECTOR, "#download-export-form button[type='submit']"),
            (By.CSS_SELECTOR, "#download-export-form .btn-primary"),
            (By.XPATH, "//div[@id='download-export-form']//button[contains(@class,'btn')]"),
        ]
        clicked = False
        for loc in prepare_locators:
            try:
                btn = WebDriverWait(driver, 30).until(EC.element_to_be_clickable(loc))
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                btn.click()
                clicked = True
                break
            except TimeoutException:
                continue

        if not clicked:
            raise TimeoutException("Bouton de preparation introuvable.")

        # Attendre la modale et la génération
        try:
            log.info("Attente de la modale de téléchargement…")
            WebDriverWait(driver, 120).until(EC.visibility_of_element_located((By.ID, "download-progress")))
            log.info("Modale détectée, attente de génération…")
            time.sleep(60 if is_heavy_file else 30)
        except TimeoutException:
            log.warning("⚠️ Modale non détectée dans le délai — on continue quand même.")

        # Chercher et cliquer un lien/bouton de téléchargement
        if not click_any_download_link(driver, preparation_timeout):
            # Diagnostic
            log.error("❌ Aucun lien/bouton de téléchargement cliquable détecté.")
            try:
                snippet = driver.page_source[:2000]
                log.error(f"Page source (début): {snippet}")
            except Exception:
                pass
            raise TimeoutException("Impossible de cliquer sur le lien de téléchargement.")

        log.info(f"Téléchargement déclenché pour {export_base}")

    except Exception as e:
        log.error(f"Erreur lors du declenchement du telechargement pour {export_base}: {e}")
        raise

# ===================== TÉLÉCHARGEMENT + VÉRIF =====================
def download_with_verification(export_base: str, driver, max_retries: int = MAX_RETRIES_PER_FILE) -> bool:
    target_hint = expected_filename_for_today(export_base)
    actual_retries = 2 if export_base in HEAVY_FILES else max_retries

    for attempt in range(1, actual_retries + 1):
        # Vérifie si le fichier existe déjà AVANT de tenter quoi que ce soit (sécurité renforcée)
        if any(file_matches_today(export_base, f) for f in list_xlsx(DOWNLOAD_DIR)):
            log.info(f"⏩ Fichier déjà présent pour {export_base} (avant tentative {attempt}). Aucun téléchargement lancé.")
            return True

        log.info(f"Téléchargement de {target_hint} (tentative {attempt}/{actual_retries})…")
        cleanup_orphan_crdownload(DOWNLOAD_DIR)

        try:
            trigger_download(export_base, driver)
        except Exception as e:
            log.error(f"Erreur pendant le déclenchement pour {export_base}: {e}")

        # Timeout spécial pour muso_beneficiaries (10 min)
        if export_base == "muso_beneficiaries":
            timeout = 600
        else:
            timeout = HEAVY_FILE_TIMEOUT if export_base in HEAVY_FILES else VERIFICATION_TIMEOUT
        path = verify_download_success_for_base(export_base, DOWNLOAD_DIR, timeout=timeout)
        if path:
            size_mb = os.path.getsize(path) / (1024 * 1024)
            log.info("🎉 Téléchargement vérifié: %s (%.1f MB)", os.path.basename(path), size_mb)
            return True

        log.warning("Non confirmé pour %s (tentative %d)", target_hint, attempt)
        cleanup_orphan_crdownload(DOWNLOAD_DIR)

    log.error("Échec après %d tentatives pour %s", actual_retries, target_hint)
    return False

def start_chrome(download_dir: str, headless: bool = HEADLESS):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--disable-dev-shm-usage")

    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.default_content_settings.popups": 0,
        "plugins.always_open_pdf_externally": True,
    }
    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(options=options)
    return driver

def commcare_login(driver, email: str, password: str, first_export_url: str):
    driver.get(first_export_url)

    user = WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.ID, "id_auth-username")))
    pwd = WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.ID, "id_auth-password")))

    user.clear(); user.send_keys(email.strip())
    pwd.clear();  pwd.send_keys(password.strip())

    login_btn = driver.find_element(By.XPATH, "//form[.//input[@id='id_auth-username']]//button[@type='submit']")
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", login_btn)
    login_btn.click()

    try:
        WebDriverWait(driver, 2).until(lambda d: "/login" not in d.current_url)
    except Exception:
        pwd.send_keys(Keys.RETURN)

    try:
        WebDriverWait(driver, 30).until(
            lambda d: ("/login" not in d.current_url) or bool(d.find_elements(By.ID, "download-export-form"))
        )
        log.info("Authentification réussie.")
    except TimeoutException:
        raise RuntimeError("Échec d'authentification")

# ===================== MAIN =====================
def main_enhanced(driver=None):
    from dotenv import load_dotenv

    t0 = time.time()
    ensure_dir(DOWNLOAD_DIR)

    log.info("=== VÉRIFICATION INITIALE ===")
    log.info("Dossier: %s", DOWNLOAD_DIR)
    log.info("Fichiers attendus (bases): %d", len(EXPECTED_BASES))

    log.info("Nettoyage des fichiers dupliqués…")
    cleanup_duplicate_files(DOWNLOAD_DIR)

    missing_bases, present_map = check_existing_files(EXPECTED_BASES, DOWNLOAD_DIR)
    nb_present = sum(1 for v in present_map.values() if v)

    log.info("Présents (aujourd'hui): %d", nb_present)
    log.info("Manquants (aujourd'hui): %d", len(missing_bases))
    if missing_bases:
        to_dl_list = [expected_filename_for_today(b) for b in missing_bases]
        log.info("À télécharger: %s", human_list(to_dl_list))
    else:
        log.info("Tous les fichiers datés %s sont déjà présents. Rien à faire.", today_str())
        return

    own_driver = False
    if driver is None:
        driver = start_chrome(DOWNLOAD_DIR, headless=HEADLESS)
        own_driver = True

    try:
        # Login
        load_dotenv("id_cc.env")
        email = os.getenv("EMAIL")
        password = os.getenv("PASSWORD") or os.getenv("PASSWORD_CC")
        if not email or not password:
            raise RuntimeError("EMAIL / PASSWORD introuvables dans id_cc.env")

        first_url = EXPORT_URLS[missing_bases[0]]
        commcare_login(driver, email, password, first_url)

        # Passes globales
        total_success = 0
        files_to_download = missing_bases[:]
        current_pass = 1

        while files_to_download and current_pass <= MAX_GLOBAL_PASSES:
            log.info("=== PASSE %d ===", current_pass)
            successful_downloads = 0
            failed_files: List[str] = []

            for base in files_to_download:
                # Vérification stricte AVANT chaque tentative, même en cas de relance
                if any(file_matches_today(base, f) for f in list_xlsx(DOWNLOAD_DIR)):
                    log.info(f"⏩ Fichier déjà présent pour {base}. Aucun téléchargement lancé.")
                    successful_downloads += 1
                    continue

                log.info(f"📥 Début du téléchargement: {expected_filename_for_today(base)}")
                ok = download_with_verification(base, driver, max_retries=MAX_RETRIES_PER_FILE)
                if ok:
                    successful_downloads += 1
                    log.info(f"✅ Téléchargement réussi pour: {base}")
                    cleanup_duplicate_files(DOWNLOAD_DIR)
                else:
                    failed_files.append(base)
                    log.warning(f"❌ Téléchargement échoué pour: {base}")

            # Filtrer à nouveau les bases déjà téléchargées pour la prochaine passe
            files_to_download = [
                b for b in failed_files
                if not any(file_matches_today(b, f) for f in list_xlsx(DOWNLOAD_DIR))
            ]
            log.info("Résultats Passe %d:", current_pass)
            log.info("   Réussis: %d", successful_downloads)
            log.info("   Échoués: %d", len(files_to_download))
            if files_to_download:
                ff_disp = [expected_filename_for_today(b) for b in files_to_download]
                log.info("   Fichiers échoués: %s", human_list(ff_disp))

            total_success += successful_downloads
            current_pass += 1

        # Rapport final
        dt = time.time() - t0
        total_failed = len(files_to_download)

        log.info("=== RAPPORT FINAL ===")
        if total_failed == 0 and total_success > 0:
            log.info("🎉 Tous les téléchargements (date %s) terminés avec succès !", today_str())

            # Vérification finale
            log.info("=== VÉRIFICATION FINALE ===")
            final_missing, final_present = check_existing_files(EXPECTED_BASES, DOWNLOAD_DIR)
            if not final_missing:
                log.info("✅ Tous les fichiers attendus sont présents.")
                today_files = []
                for _, files in final_present.items():
                    today_files.extend(files)
                log.info(f"📁 Fichiers du jour ({len(today_files)}):")
                for i, filename in enumerate(sorted(today_files), 1):
                    file_path = os.path.join(DOWNLOAD_DIR, filename)
                    try:
                        size_mb = os.path.getsize(file_path) / (1024 * 1024)
                        log.info(f"   {i:2d}. {filename} ({size_mb:.1f} MB)")
                    except Exception:
                        log.info(f"   {i:2d}. {filename}")
            else:
                log.warning(f"⚠️ Encore manquants: {final_missing}")
        else:
            log.warning("⚠️ Téléchargements incomplets pour la date %s.", today_str())
            if total_failed > 0:
                failed_list = [expected_filename_for_today(b) for b in files_to_download]
                log.warning(f"❌ Non téléchargés: {human_list(failed_list)}")

        log.info("📊 STATISTIQUES:")
        log.info("   ✅ Total réussis: %d", total_success)
        log.info("   ❌ Total échoués: %d", total_failed)
        log.info("   ⏱️ Temps total: %dm %ds", int(dt // 60), int(dt % 60))
        if total_success > 0:
            log.info("   📈 Temps moyen par fichier: %.1fs", dt / total_success)

        log.info("🔚 Fermeture du navigateur et fin du processus…")
        time.sleep(2)

    finally:
        if own_driver and driver:
            try:
                log.info("🔒 Fermeture du navigateur Chrome…")
                driver.quit()
                log.info("✅ Navigateur fermé.")
            except Exception as e:
                log.warning(f"⚠️ Erreur lors de la fermeture du navigateur: {e}")

        log.info("=" * 60)
        log.info("🏁 PROCESSUS TERMINÉ")
        log.info("=" * 60)

if __name__ == "__main__":
    main_enhanced()
