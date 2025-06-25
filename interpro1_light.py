import streamlit as st
from datetime import datetime, date
import copy
import json
import requests

# --- PAGE CONFIGURATION (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(layout="wide", page_title="🛠️ Le laboratoire des Prompts IA", initial_sidebar_state="collapsed" )

# --- CUSTOM CSS FOR SIDEBAR TOGGLE TEXT ---
st.markdown("""
    <style>
        /* PADDING NORMAL POUR TOUTES LES PAGES (éviter empiètement header) */
        .main .block-container {
            padding-top: 3rem !important;
            margin-top: 0rem !important;
        }
        
        [data-testid="stMainBlockContainer"] {
            padding-top: 3rem !important;
        }
        
        .css-1d391kg, .css-18e3th9 {
            padding-top: 3rem !important;
        }
        
        /* REDUCTION SPECIFIQUE POUR LA PAGE D'ACCUEIL UNIQUEMENT */
        /* Cible spécifiquement le header de bienvenue sur la page d'accueil */
        h1[data-testid="stHeading"]:first-of-type {
            margin-top: -2rem !important;
            padding-top: 0rem !important;
        }
        
        /* Alternative: cible le texte spécifique de bienvenue */
        h1:contains("Bienvenue dans votre laboratoire") {
            margin-top: -2rem !important;
            padding-top: 0rem !important;
        }
        
        /* Cible le bouton spécifique que vous avez identifié */
        button[data-testid="stBaseButton-headerNoPadding"]::after {
            content: " Menu";      /* Le texte à ajouter */
            margin-left: 8px;     /* Espace entre la flèche et le texte (ajustez si besoin) */
            font-size: 0.9em;     /* Taille du texte (ajustez si besoin) */
            vertical-align: middle; /* Aide à l'alignement vertical avec l'icône */
            color: inherit;       /* Hérite de la couleur du thème (bon pour thèmes clair/sombre) */
            font-weight: normal;  /* Assure que le texte n'est pas en gras par défaut */
            display: inline-flex; /* Peut aider à un meilleur alignement et comportement */
            align-items: center;
        }
        div[data-testid="stCodeBlock"] pre,
        pre.st-emotion-cache-1nqbjoj /* Cible spécifique à votre HTML, attention à sa stabilité */
        {

            max-height: 520px !important;
            overflow-y: auto !important;
            font-size: 0.875em !important;
            /* Assurez-vous qu'il n'est pas caché par autre chose */
            display: block !important; 
            visibility: visible !important;
            opacity: 1 !important;
        }

        /* Cible le div conteneur direct à l'intérieur de stCodeBlock s'il existe et gère le scroll */
        div[data-testid="stCodeBlock"] > div:first-child {
            height: 120px !important; /* Doit correspondre à la valeur ci-dessus */
            max-height: 120px !important;
            overflow-y: auto !important;
             display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
        }
        
        /* Si le div interne au <pre> doit gérer le scroll */
        pre.st-emotion-cache-1nqbjoj > div[style*="background-color: transparent;"] {
            height: auto !important; 
            max-height: 100% !important; 
            overflow-y: auto !important;
        }
                /* === NOUVELLES RÈGLES POUR L'ICÔNE DE COPIE DE ST.CODE === */
        button[data-testid="stCodeCopyButton"] {
            opacity: 0.85 !important;
            visibility: visible !important;
            background-color: #f0f2f6 !important;
            border: 1px solid #cccccc !important;
            border-radius: 4px !important;
            padding: 3px 5px !important;
            transition: opacity 0.15s ease-in-out, background-color 0.15s ease-in-out;
            /* top: 2px !important; */
            /* right: 2px !important; */
        }

        button[data-testid="stCodeCopyButton"]:hover {
            opacity: 1 !important;
            background-color: #e6e8eb !important;
            border-color: #b0b0b0 !important;
        }

        button[data-testid="stCodeCopyButton"] svg {
            transform: scale(1.2); 
            vertical-align: middle;
        }
        
        /* === SOLUTION POUR COMPRESSION LATERALE DE LA SIDEBAR === */
        /* Force le contenu principal à se comprimer au lieu d'être décalé */
        section[data-testid="stSidebar"] {
            width: 21rem !important;
            min-width: 21rem !important;
            max-width: 21rem !important;
        }
        
        /* Ajustement du conteneur principal pour la compression */
        .main .block-container {
            max-width: calc(100vw - 21rem) !important;
            width: calc(100vw - 21rem) !important;
        }
        
        /* Quand la sidebar est fermée, reprendre toute la largeur */
        section[data-testid="stSidebar"][aria-expanded="false"] ~ .main .block-container,
        section[data-testid="stSidebar"]:not([aria-expanded="true"]) ~ .main .block-container {
            max-width: 100vw !important;
            width: 100vw !important;
        }
        
        /* Alternative pour cibler via l'état collapsed */
        .main .block-container {
            transition: width 0.3s ease, max-width 0.3s ease !important;
        }
        
        /* Responsive: sur petits écrans, garder le comportement normal */
        @media (max-width: 768px) {
            .main .block-container {
                max-width: 100vw !important;
                width: 100vw !important;
            }
        }
        
    <style>
""", unsafe_allow_html=True)

# --- Initial Data Structure & Constants ---
CURRENT_YEAR = datetime.now().year
GIST_DATA_FILENAME = "prompt_templates_data_v3.json"

# --- Function to load prompt templates from files ---
def load_prompt_template(filename):
    """Load prompt template from file, with fallback to basic template if file not found."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        st.warning(f"Fichier de template '{filename}' non trouvé. Utilisation d'un template de base.")
        return "# MISSION\nVous êtes un assistant IA. Veuillez traiter la demande suivante: {problematique}"
    except Exception as e:
        st.error(f"Erreur lors du chargement du template '{filename}': {e}")
        return "# MISSION\nVous êtes un assistant IA. Veuillez traiter la demande suivante: {problematique}"

# Load prompt templates from external files
META_PROMPT_FOR_EXTERNAL_LLM_TEMPLATE = load_prompt_template("prompt_creation_template.md")
META_PROMPT_FOR_LLM_AMELIORATION_TEMPLATE = load_prompt_template("prompt_improvement_template.md")

ASSISTANT_FORM_VARIABLES = [
    {"name": "problematique", "label": "Décrivez le besoin ou la tâche que le prompt cible doit résoudre :", "type": "text_area", "default": "", "height": 100},
    {"name": "doc_source", "label": "Quel(s) types de document(s) sont nécessaire pour la réalisation de votre besoin ? (e.g. PDF, e-mail, texte brut -laisser vide si non pertinent-) :", "type": "text_input", "default": ""},
    {"name": "elements_specifiques_a_extraire", "label": "Quelles sont les informations spécifiques que vous souhaitez identifier / générer ? (e.g. l'ensemble des ID clients, les clauses du contrat) :", "type": "text_area", "default": "", "height": 100},
    {"name": "format_sortie_desire", "label": "Optionnel : sous quel format voulez vous que le prompt produise une réponse ? (e.g. un texte de deux pages, une liste à puces) :", "type": "text_area", "default": "", "height": 75},
    {"name": "public_cible_reponse", "label": "Optionnel : pour quel public cible s'adressera le résultat du prompt ? (e.g. des profils techniques, le grand public) :", "type": "text_input", "default": ""},
]

def get_default_dates():
    now_iso = datetime.now().isoformat()
    return now_iso, now_iso

INITIAL_PROMPT_TEMPLATES = {
    "Achat": {}, "RH": {}, "Finance": {}, "Comptabilité": {}
}
for family, use_cases in INITIAL_PROMPT_TEMPLATES.items(): # Initial cleanup
    if isinstance(use_cases, dict):
        for uc_name, uc_config in use_cases.items():
            if "is_favorite" in uc_config: # pragma: no cover
                del uc_config["is_favorite"]

# --- Utility Functions (User's original versions, with height fix in _postprocess_after_loading) ---
def parse_default_value(value_str, var_type):
    if not value_str:
        if var_type == "number_input": return 0.0
        if var_type == "date_input": return datetime.now().date()
        return ""
    if var_type == "number_input":
        try: return float(value_str)
        except ValueError: return 0.0
    elif var_type == "date_input":
        try: return datetime.strptime(value_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return value_str if isinstance(value_str, date) else datetime.now().date()
    return value_str

def _preprocess_for_saving(data_to_save):
    processed_data = copy.deepcopy(data_to_save)
    for family_name in list(processed_data.keys()):
        use_cases_in_family = processed_data[family_name]
        if not isinstance(use_cases_in_family, dict): # pragma: no cover
            st.error(f"Données corrompues (famille non-dict): '{family_name}'. Suppression.")
            del processed_data[family_name]
            continue
        for use_case_name in list(use_cases_in_family.keys()):
            config = use_cases_in_family[use_case_name]
            if not isinstance(config, dict): # pragma: no cover
                st.error(f"Données corrompues (cas d'usage non-dict): '{use_case_name}' dans '{family_name}'. Suppression.")
                del processed_data[family_name][use_case_name]
                continue
            if not isinstance(config.get("variables"), list):
                config["variables"] = []
            for var_info in config.get("variables", []):
                if isinstance(var_info, dict):
                    if var_info.get("type") == "date_input" and isinstance(var_info.get("default"), date):
                        var_info["default"] = var_info["default"].strftime("%Y-%m-%d")
                    if var_info.get("type") == "number_input":
                        if "default" in var_info and var_info["default"] is not None:
                            var_info["default"] = float(var_info["default"])
                        if "min_value" in var_info and var_info["min_value"] is not None:
                            var_info["min_value"] = float(var_info["min_value"])
                        if "max_value" in var_info and var_info["max_value"] is not None:
                            var_info["max_value"] = float(var_info["max_value"])
                        if "step" in var_info and var_info["step"] is not None:
                            var_info["step"] = float(var_info["step"])
                        else: 
                            var_info["step"] = 1.0
                    # Ensure height for text_area is an int if it exists (it should be already from other functions)
                    if var_info.get("type") == "text_area":
                        if "height" in var_info and var_info["height"] is not None:
                            try:
                                var_info["height"] = int(var_info["height"])
                            except (ValueError, TypeError): # pragma: no cover
                                var_info["height"] = 100 # Should not happen if data is clean

            config.setdefault("tags", [])
            if "is_favorite" in config: # pragma: no cover
                del config["is_favorite"]
            config.setdefault("usage_count", 0)
            config.setdefault("created_at", datetime.now().isoformat())
            config.setdefault("updated_at", datetime.now().isoformat())
    return processed_data

def _postprocess_after_loading(loaded_data): # User's trusted version + height fix
    processed_data = copy.deepcopy(loaded_data)
    now_iso = datetime.now().isoformat()
    for family_name in list(processed_data.keys()):
        use_cases_in_family = processed_data[family_name]
        if not isinstance(use_cases_in_family, dict): # pragma: no cover
            st.warning(f"Données corrompues (famille non-dict): '{family_name}'. Ignorée.")
            del processed_data[family_name]
            continue
        for use_case_name in list(use_cases_in_family.keys()):
            config = use_cases_in_family[use_case_name]
            if not isinstance(config, dict): # pragma: no cover
                st.warning(f"Données corrompues (cas d'usage non-dict): '{use_case_name}' dans '{family_name}'. Ignoré.")
                del processed_data[family_name][use_case_name]
                continue
            if not isinstance(config.get("variables"), list):
                config["variables"] = []
            for var_info in config.get("variables", []):
                if isinstance(var_info, dict):
                    if var_info.get("type") == "date_input" and isinstance(var_info.get("default"), str):
                        try:
                            var_info["default"] = datetime.strptime(var_info["default"], "%Y-%m-%d").date()
                        except ValueError:
                            var_info["default"] = datetime.now().date()
                    if var_info.get("type") == "number_input":
                        if "default" in var_info and var_info["default"] is not None:
                            var_info["default"] = float(var_info["default"])
                        else: 
                            var_info["default"] = 0.0
                        if "min_value" in var_info and var_info["min_value"] is not None:
                            var_info["min_value"] = float(var_info["min_value"])
                        if "max_value" in var_info and var_info["max_value"] is not None:
                            var_info["max_value"] = float(var_info["max_value"])
                        if "step" in var_info and var_info["step"] is not None:
                            var_info["step"] = float(var_info["step"])
                        else: 
                            var_info["step"] = 1.0

                    # --- ADDED ROBUST HEIGHT VALIDATION ---
                    if var_info.get("type") == "text_area":
                        height_val = var_info.get("height")
                        if height_val is not None:
                            try:
                                h = int(height_val)
                                if h >= 68:
                                    var_info["height"] = h
                                else:
                                    var_info["height"] = 68 # Set to minimum if too small
                                    # st.warning(f"Hauteur pour '{var_info.get('name', 'N/A')}' ajustée à 68px (minimum).")
                            except (ValueError, TypeError):
                                var_info["height"] = 100 # Default if invalid
                        # If height_val was None, 'height' key might not be in var_info, or it's None.
                        # The st.text_area widget call will handle None by using its internal default.
                        # Or we can explicitly set a default:
                        # else:
                        #     var_info["height"] = 100 # Default if not present

            config.setdefault("tags", [])
            if "is_favorite" in config: # pragma: no cover
                del config["is_favorite"]
            config.setdefault("usage_count", 0)
            config.setdefault("created_at", now_iso)
            config.setdefault("updated_at", now_iso)
            if not isinstance(config.get("tags"), list): config["tags"] = []
    return processed_data

# --- NEW: Simplified function to prepare newly injected use case config ---
def _prepare_newly_injected_use_case_config(uc_config_from_json):
    prepared_config = copy.deepcopy(uc_config_from_json)
    now_iso_created, now_iso_updated = get_default_dates()

    prepared_config["created_at"] = now_iso_created
    prepared_config["updated_at"] = now_iso_updated
    prepared_config["usage_count"] = 0 

    if "template" not in prepared_config or not isinstance(prepared_config["template"], str): # pragma: no cover
        prepared_config["template"] = "" 
        st.warning(f"Cas d'usage injecté '{uc_config_from_json.get('name', 'INCONNU')}' sans template valide. Template initialisé à vide.")

    if not isinstance(prepared_config.get("variables"), list):
        prepared_config["variables"] = []

    for var_info in prepared_config.get("variables", []): # Ensure height is valid for text_area
        if isinstance(var_info, dict) and var_info.get("type") == "text_area":
            height_val = var_info.get("height")
            if height_val is not None:
                try:
                    h = int(height_val)
                    if h >= 68: var_info["height"] = h
                    else: var_info["height"] = 68 
                except (ValueError, TypeError):
                    var_info["height"] = 100 # Default if invalid type
            # If 'height' key is missing, it's fine; widget will use its default.

    if not isinstance(prepared_config.get("tags"), list):
        prepared_config["tags"] = []
    else:
        prepared_config["tags"] = sorted(list(set(str(tag).strip() for tag in prepared_config["tags"] if str(tag).strip())))

    if "is_favorite" in prepared_config: # pragma: no cover
        del prepared_config["is_favorite"]

    # Ajout pour la gestion des notes
    # if "ratings" not in prepared_config or not isinstance(prepared_config["ratings"], list):
    #     prepared_config["ratings"] = []
    # if "average_rating" not in prepared_config:
    #     prepared_config["average_rating"] = 0.0
    return prepared_config

# --- Gist Interaction Functions (User's original versions) ---
def get_gist_content(gist_id, github_pat):
    headers = {"Authorization": f"token {github_pat}", "Accept": "application/vnd.github.v3+json"}
    try:
        response = requests.get(f"https://api.github.com/gists/{gist_id}", headers=headers)
        response.raise_for_status()
        gist_data = response.json()
        if GIST_DATA_FILENAME in gist_data["files"]:
            return gist_data["files"][GIST_DATA_FILENAME]["content"]
        else:
            st.info(f"Fichier '{GIST_DATA_FILENAME}' non trouvé dans Gist. Initialisation.")
            return "{}" 
    except requests.exceptions.HTTPError as http_err: # pragma: no cover
        if response.status_code == 404: st.error(f"Erreur Gist (get): Gist avec ID '{gist_id}' non trouvé (404). Vérifiez l'ID.")
        elif response.status_code in [401, 403]: st.error(f"Erreur Gist (get): Problème d'authentification (PAT GitHub invalide ou permissions insuffisantes).")
        else: st.error(f"Erreur HTTP Gist (get): {http_err}")
        return None 
    except requests.exceptions.RequestException as e: # pragma: no cover
        st.error(f"Erreur de connexion Gist (get): {e}")
        return None
    except KeyError: # pragma: no cover
        st.error(f"Erreur Gist (get): Fichier '{GIST_DATA_FILENAME}' non trouvé ou structure Gist inattendue.")
        return None
    except json.JSONDecodeError: # pragma: no cover
         st.error(f"Erreur Gist (get): Réponse de l'API Gist n'est pas un JSON valide.") 
         return None 

def update_gist_content(gist_id, github_pat, new_content_json_string):
    headers = {"Authorization": f"token {github_pat}", "Accept": "application/vnd.github.v3+json"}
    data = {"files": {GIST_DATA_FILENAME: {"content": new_content_json_string}}}
    try:
        response = requests.patch(f"https://api.github.com/gists/{gist_id}", headers=headers, json=data)
        response.raise_for_status()
        return True
    except requests.exceptions.HTTPError as http_err: # pragma: no cover
        if response.status_code == 404: st.error(f"Erreur Gist (update): Gist avec ID '{gist_id}' non trouvé (404). Impossible de sauvegarder.")
        elif response.status_code in [401, 403]: st.error(f"Erreur Gist (update): Problème d'authentification (PAT GitHub invalide ou permissions insuffisantes pour écrire).")
        elif response.status_code == 422: st.error(f"Erreur Gist (update): Les données n'ont pas pu être traitées par GitHub (422). Vérifiez le format du JSON. Détails: {response.text}")
        else: st.error(f"Erreur HTTP Gist (update): {http_err}")
        return False
    except requests.exceptions.RequestException as e: # pragma: no cover
        st.error(f"Erreur de connexion Gist (update): {e}")
        return False

def save_editable_prompts_to_gist():
    GIST_ID = st.secrets.get("GIST_ID") 
    GITHUB_PAT = st.secrets.get("GITHUB_PAT") 
    if not GIST_ID or not GITHUB_PAT: # pragma: no cover
        st.sidebar.warning("Secrets Gist (GIST_ID/GITHUB_PAT) non configurés. Sauvegarde sur GitHub désactivée.")
        return
    if 'editable_prompts' in st.session_state:
        data_to_save = _preprocess_for_saving(st.session_state.editable_prompts)
        try:
            json_string = json.dumps(data_to_save, indent=4, ensure_ascii=False)
            if update_gist_content(GIST_ID, GITHUB_PAT, json_string):
                 st.toast("💾 Données sauvegardées sur Gist!", icon="☁️") # Feedback
            else: 
                st.warning("Sauvegarde Gist échouée.") 
        except Exception as e: # pragma: no cover
            st.error(f"Erreur préparation données pour Gist: {e}")

def load_editable_prompts_from_gist():
    GIST_ID = st.secrets.get("GIST_ID")
    GITHUB_PAT = st.secrets.get("GITHUB_PAT")
    if not GIST_ID or not GITHUB_PAT: # pragma: no cover
        st.sidebar.warning("Secrets Gist (GIST_ID/GITHUB_PAT) non configurés. Utilisation des modèles par défaut locaux.")
        return copy.deepcopy(INITIAL_PROMPT_TEMPLATES)
    raw_content = get_gist_content(GIST_ID, GITHUB_PAT) 
    if raw_content: 
        try:
            loaded_data = json.loads(raw_content)
            if not loaded_data or not isinstance(loaded_data, dict): 
                raise ValueError("Contenu Gist vide ou mal structuré.")
            return _postprocess_after_loading(loaded_data)
        except (json.JSONDecodeError, TypeError, ValueError) as e: 
            st.info(f"Erreur chargement Gist ('{str(e)[:50]}...'). Initialisation avec modèles par défaut.")
    else: 
        st.info("Gist vide ou inaccessible. Initialisation avec modèles par défaut.")
    initial_data = copy.deepcopy(INITIAL_PROMPT_TEMPLATES)
    if GIST_ID and GITHUB_PAT and (raw_content is None or raw_content == "{}"): # Try to save defaults if Gist was empty
        data_to_save_init = _preprocess_for_saving(initial_data) 
        try:
            json_string_init = json.dumps(data_to_save_init, indent=4, ensure_ascii=False)
            if update_gist_content(GIST_ID, GITHUB_PAT, json_string_init):
                st.info("Modèles par défaut sauvegardés sur Gist pour initialisation.")
        except Exception as e: # pragma: no cover
            st.error(f"Erreur sauvegarde initiale sur Gist: {e}")
    return initial_data

# --- Session State Initialization ---
if 'editable_prompts' not in st.session_state:
    st.session_state.editable_prompts = load_editable_prompts_from_gist()
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "accueil" # Nouvelle vue par défaut

if 'library_selected_family_for_display' not in st.session_state:
    available_families = list(st.session_state.editable_prompts.keys())
    st.session_state.library_selected_family_for_display = available_families[0] if available_families else None
    
if 'family_selector_edition' not in st.session_state:
    available_families = list(st.session_state.editable_prompts.keys())
    st.session_state.family_selector_edition = available_families[0] if available_families else None
if 'use_case_selector_edition' not in st.session_state:  st.session_state.use_case_selector_edition = None 
if 'editing_variable_info' not in st.session_state: st.session_state.editing_variable_info = None
if 'show_create_new_use_case_form' not in st.session_state: st.session_state.show_create_new_use_case_form = False
if 'force_select_family_name' not in st.session_state: st.session_state.force_select_family_name = None
if 'force_select_use_case_name' not in st.session_state: st.session_state.force_select_use_case_name = None
if 'confirming_delete_details' not in st.session_state: st.session_state.confirming_delete_details = None
if 'confirming_delete_family_name' not in st.session_state: st.session_state.confirming_delete_family_name = None
if 'library_search_term' not in st.session_state: st.session_state.library_search_term = ""
if 'library_selected_tags' not in st.session_state: st.session_state.library_selected_tags = []
if 'variable_type_to_create' not in st.session_state: st.session_state.variable_type_to_create = None
if 'active_generated_prompt' not in st.session_state: st.session_state.active_generated_prompt = ""
if 'duplicating_use_case_details' not in st.session_state: st.session_state.duplicating_use_case_details = None
if 'go_to_config_section' not in st.session_state: st.session_state.go_to_config_section = False

# Generator session state variables
if 'generator_selected_family' not in st.session_state: st.session_state.generator_selected_family = None
if 'generator_selected_use_case' not in st.session_state: st.session_state.generator_selected_use_case = None

if 'injection_selected_family' not in st.session_state:
    st.session_state.injection_selected_family = None
if 'injection_json_text' not in st.session_state:
    st.session_state.injection_json_text = ""

if 'assistant_form_values' not in st.session_state:
    st.session_state.assistant_form_values = {var['name']: var['default'] for var in ASSISTANT_FORM_VARIABLES}
if 'generated_meta_prompt_for_llm' not in st.session_state: 
    st.session_state.generated_meta_prompt_for_llm = ""

# NOUVELLES CLÉS POUR L'ASSISTANT UNIFIÉ
if 'assistant_mode' not in st.session_state:
    st.session_state.assistant_mode = "creation"  # Modes possibles: "creation", "amelioration"
if 'assistant_existing_prompt_value' not in st.session_state:
    st.session_state.assistant_existing_prompt_value = ""

# --- Sidebar Navigation with Tabs ---
st.sidebar.header("Menu Principal")
tab_bibliotheque, tab_injection = st.sidebar.tabs([
    "📚 Bibliothèque",
    "💡 Assistant" 
])


# --- Tab: Bibliothèque (Sidebar content) ---
with tab_bibliotheque:
    st.subheader("Explorer la Bibliothèque de Prompts")
    search_col, filter_tag_col = st.columns(2)
    with search_col:
        st.session_state.library_search_term = st.text_input(
            "🔍 Rechercher par mot-clé:",
            value=st.session_state.get("library_search_term", ""),
            placeholder="Nom, template, variable..."
        )

    all_tags_list = sorted(list(set(tag for family in st.session_state.editable_prompts.values() for uc in family.values() for tag in uc.get("tags", []))))
    with filter_tag_col:
        st.session_state.library_selected_tags = st.multiselect(
            "🏷️ Filtrer par Tags:",
            options=all_tags_list,
            default=st.session_state.get("library_selected_tags", [])
        )
    st.markdown("---")

    if not st.session_state.editable_prompts or not any(st.session_state.editable_prompts.values()):
        st.info("La bibliothèque est vide. Ajoutez des prompts via l'onglet 'Édition'.")
    else:
        sorted_families_bib = sorted(list(st.session_state.editable_prompts.keys()))

        if not st.session_state.get('library_selected_family_for_display') or \
           st.session_state.library_selected_family_for_display not in sorted_families_bib:
            st.session_state.library_selected_family_for_display = sorted_families_bib[0] if sorted_families_bib else None

        st.write("Sélectionner un métier à afficher :")
        for family_name_bib in sorted_families_bib:
            button_key = f"lib_family_btn_{family_name_bib.replace(' ', '_').replace('&', '_')}"
            is_selected_family = (st.session_state.library_selected_family_for_display == family_name_bib)
            if st.button(
                family_name_bib,
                key=button_key,
                use_container_width=True, 
                type="primary" if is_selected_family else "secondary"
            ):
                if st.session_state.library_selected_family_for_display != family_name_bib:
                    st.session_state.library_selected_family_for_display = family_name_bib
                    st.session_state.view_mode = "library" 
                    st.rerun() 
        st.markdown("---")

# --- Tab: Injection (Sidebar content) ---
with tab_injection:
    st.subheader("Assistant & Injection")
    st.markdown("Utilisez l'assistant pour préparer un prompt système ou injectez des cas d'usage en format JSON.")
    # MODIFICATION DU BOUTON EXISTANT
    if st.button("✨ Assistant Prompt Système", key="start_assistant_unified_btn", use_container_width=True): # Nom du bouton mis à jour
        st.session_state.view_mode = "assistant_creation" 
        # Réinitialiser au mode "creation" par défaut et vider les champs des deux modes potentiels
        st.session_state.assistant_mode = "creation" 
        st.session_state.assistant_form_values = {var['name']: var['default'] for var in ASSISTANT_FORM_VARIABLES}
        st.session_state.assistant_existing_prompt_value = "" 
        st.session_state.generated_meta_prompt_for_llm = "" # Le méta-prompt généré est commun
        st.rerun()
    
    if st.button("💉 Injecter JSON Manuellement", key="start_manual_injection_btn", use_container_width=True):
        st.session_state.view_mode = "inject_manual" 
        st.session_state.injection_selected_family = None 
        st.session_state.injection_json_text = "" 
        st.session_state.generated_meta_prompt_for_llm = "" # Aussi réinitialiser ici
        st.rerun()

# --- Main Display Area ---
final_selected_family_edition = st.session_state.get('family_selector_edition')
final_selected_use_case_edition = st.session_state.get('use_case_selector_edition')
library_family_to_display = st.session_state.get('library_selected_family_for_display')

# NOUVELLE SECTION POUR LA PAGE D'ACCUEIL
if st.session_state.view_mode == "accueil":
    st.header("Bienvenue dans votre laboratoire des prompts IA ! 💡")
    st.caption(f"Créé par le pôle Data / IA")
    st.markdown("""
        Vous êtes au bon endroit pour maîtriser l'art de "parler" aux Intelligences Artificielles (IA) et obtenir d'elles exactement ce dont vous avez besoin !

        **Qu'est-ce qu'un "prompt" ?**
        Imaginez donner des instructions à un assistant virtuel intelligent, mais qui a besoin de consignes claires. Un "prompt", c'est simplement cette instruction, cette question ou cette consigne que vous formulez à l'IA.
        Plus votre instruction est bien pensée, plus l'IA vous fournira une réponse utile et pertinente.

        **Que pouvez-vous faire avec cette application ?**

        Cet outil est conçu pour vous simplifier la vie, que vous soyez novice ou plus expérimenté :

        * **Découvrir et utiliser des modèles d'instructions prêts à l'emploi** : Explorez une collection de "prompts" déjà conçus pour diverses tâches (comme rédiger un email, résumer un document, analyser une situation, etc.). Vous pourrez les utiliser tels quels ou les adapter facilement.
        * **Créer vos propres instructions sur mesure** : Vous avez une idée précise en tête ? Notre assistant vous guide pas à pas pour construire le "prompt" parfait, même si vous n'avez aucune connaissance technique. L'objectif est de transformer votre besoin en une instruction claire pour l'IA.
        * **Organiser et améliorer vos instructions** : Conservez vos meilleurs "prompts", modifiez-les et perfectionnez-les au fil du temps.

        En bref, cet outil vous aide à formuler les meilleures demandes possibles aux IA pour qu'elles deviennent de véritables alliées dans votre travail ou vos projets.
    """)

    cols_accueil = st.columns(2)
    with cols_accueil[0]:
        if st.button("📚 Je souhaite utiliser / modifier un prompt existant", use_container_width=True, type="primary"):
            st.session_state.view_mode = "select_family_for_library"
            st.rerun()
    with cols_accueil[1]:
        if st.button("✨ Je souhaite créer un prompt à partir de mon besoin", use_container_width=True, type="primary"):
            st.session_state.view_mode = "assistant_creation"
            # Réinitialiser les valeurs du formulaire de l'assistant et le prompt généré
            st.session_state.assistant_form_values = {var['name']: var['default'] for var in ASSISTANT_FORM_VARIABLES}
            st.session_state.generated_meta_prompt_for_llm = ""
            st.rerun()

elif st.session_state.view_mode == "select_family_for_library":
    if st.button("⬅️ Retour à l'accueil", key="back_to_accueil_from_select_family"):
        st.session_state.view_mode = "accueil"
        st.rerun()
    st.header("📚 Explorer les prompts par métier")
    st.markdown("Cliquez sur le nom d'un métier pour afficher les prompts associés.")
    st.markdown("---")

    available_families = list(st.session_state.editable_prompts.keys())

    if not available_families:
        st.info("Aucun métier de prompts n'a été créé pour le moment.")
        st.markdown("Vous pouvez en créer via l'onglet **Édition** dans le menu latéral (accessible via l'icône Menu en haut à gauche).")
        st.markdown("---")

    else:
        sorted_families = sorted(available_families)
        
        # Vous pouvez ajuster le nombre de colonnes si vous avez beaucoup de familles
        num_cols = 3 
        cols = st.columns(num_cols)
        for i, family_name in enumerate(sorted_families):
            with cols[i % num_cols]:
                if st.button(f"{family_name}", key=f"select_family_for_lib_btn_{family_name}", use_container_width=True, help=f"Voir les prompts du métier '{family_name}'"):
                    st.session_state.library_selected_family_for_display = family_name
                    st.session_state.view_mode = "library" # Redirige vers la bibliothèque avec la famille sélectionnée
                    st.rerun()
        
        st.markdown("---")

elif st.session_state.view_mode == "library":
    if st.button("⬅️ Retour à la sélection des métiers", key="back_to_select_family_from_library"):
        st.session_state.view_mode = "select_family_for_library"
        st.rerun()
    if not library_family_to_display:
        st.info("Veuillez sélectionner un métier dans la barre latérale (onglet Bibliothèque) pour afficher les prompts.")
        available_families_main_display = list(st.session_state.editable_prompts.keys())
        if available_families_main_display:
            st.session_state.library_selected_family_for_display = available_families_main_display[0]
            st.rerun()
        elif not any(st.session_state.editable_prompts.values()): 
             st.warning("Aucun métier de cas d'usage n'est configurée. Créez-en via l'onglet 'Édition'.")
    elif library_family_to_display in st.session_state.editable_prompts:
        st.header(f"Bibliothèque - métier : {library_family_to_display}")
        use_cases_in_family_display = st.session_state.editable_prompts[library_family_to_display]
        filtered_use_cases = {}
        search_term_lib = st.session_state.get("library_search_term", "").strip().lower()
        selected_tags_lib = st.session_state.get("library_selected_tags", [])
        if use_cases_in_family_display:
            for uc_name, uc_config in use_cases_in_family_display.items():
                match_search = True
                if search_term_lib:
                    match_search = (search_term_lib in uc_name.lower() or
                                    search_term_lib in uc_config.get("template", "").lower() or
                                    any(search_term_lib in var.get("name","").lower() or search_term_lib in var.get("label","").lower() 
                                        for var in uc_config.get("variables", [])))
                match_tags = True
                if selected_tags_lib: match_tags = all(tag in uc_config.get("tags", []) for tag in selected_tags_lib)
                if match_search and match_tags: filtered_use_cases[uc_name] = uc_config
        if not filtered_use_cases:
            if not use_cases_in_family_display: st.info(f"Le métier '{library_family_to_display}' ne contient actuellement aucun prompt.")
            else: st.info("Aucun prompt ne correspond à vos critères de recherche/filtre dans cette métier.")
        else:
            # Gestion de la duplication de cas d'usage
            if st.session_state.duplicating_use_case_details and \
               st.session_state.duplicating_use_case_details["family"] == library_family_to_display:
                
                original_uc_name_for_dup = st.session_state.duplicating_use_case_details["use_case"]
                original_family_name_for_dup = st.session_state.duplicating_use_case_details["family"]
                
                st.markdown(f"### 📋 Dupliquer '{original_uc_name_for_dup}' (depuis: {original_family_name_for_dup})")
                
                form_key_duplicate = f"form_duplicate_lib_{original_family_name_for_dup.replace(' ','_')}_{original_uc_name_for_dup.replace(' ','_')}"
                with st.form(key=form_key_duplicate):
                    available_families_list = list(st.session_state.editable_prompts.keys())
                    try:
                        default_family_idx = available_families_list.index(original_family_name_for_dup)
                    except ValueError:
                        default_family_idx = 0
                    
                    selected_target_family_for_duplicate = st.selectbox(
                        "Choisir la famille de destination pour la copie :",
                        options=available_families_list,
                        index=default_family_idx,
                        key=f"target_family_dup_select_{form_key_duplicate}"
                    )
                    
                    suggested_new_name_base = f"{original_uc_name_for_dup} (copie)"
                    suggested_new_name = suggested_new_name_base
                    temp_copy_count = 1
                    while suggested_new_name in st.session_state.editable_prompts.get(selected_target_family_for_duplicate, {}):
                        suggested_new_name = f"{suggested_new_name_base} {temp_copy_count}"
                        temp_copy_count += 1
                    
                    new_duplicated_uc_name_input = st.text_input(
                        "Nouveau nom pour le cas d'usage dupliqué:",
                        value=suggested_new_name,
                        key=f"new_dup_name_input_{form_key_duplicate}"
                    )
                    
                    submitted_duplicate_form = st.form_submit_button("✅ Confirmer la Duplication", use_container_width=True)
                    
                    if submitted_duplicate_form:
                        new_uc_name_val_from_form = new_duplicated_uc_name_input.strip()
                        target_family_on_submit = selected_target_family_for_duplicate
                        
                        if not new_uc_name_val_from_form:
                            st.error("Le nom du nouveau cas d'usage ne peut pas être vide.")
                        elif new_uc_name_val_from_form in st.session_state.editable_prompts.get(target_family_on_submit, {}):
                            st.error(f"Un cas d'usage nommé '{new_uc_name_val_from_form}' existe déjà dans la famille '{target_family_on_submit}'.")
                        else:
                            current_prompt_config = st.session_state.editable_prompts[original_family_name_for_dup][original_uc_name_for_dup]
                            st.session_state.editable_prompts[target_family_on_submit][new_uc_name_val_from_form] = copy.deepcopy(current_prompt_config)
                            now_iso_dup_create, now_iso_dup_update = get_default_dates()
                            st.session_state.editable_prompts[target_family_on_submit][new_uc_name_val_from_form]["created_at"] = now_iso_dup_create
                            st.session_state.editable_prompts[target_family_on_submit][new_uc_name_val_from_form]["updated_at"] = now_iso_dup_update
                            st.session_state.editable_prompts[target_family_on_submit][new_uc_name_val_from_form]["usage_count"] = 0
                            save_editable_prompts_to_gist()
                            st.success(f"Cas d'usage '{original_uc_name_for_dup}' dupliqué en '{new_uc_name_val_from_form}' dans la famille '{target_family_on_submit}'.")
                            
                            st.session_state.duplicating_use_case_details = None
                            if target_family_on_submit != library_family_to_display:
                                st.session_state.library_selected_family_for_display = target_family_on_submit
                            st.rerun()
                
                cancel_key_duplicate = f"cancel_dup_process_lib_{original_family_name_for_dup.replace(' ','_')}_{original_uc_name_for_dup.replace(' ','_')}"
                if st.button("❌ Annuler la Duplication", key=cancel_key_duplicate, use_container_width=True):
                    st.session_state.duplicating_use_case_details = None
                    st.rerun()
                
                st.markdown("---")
            
            # Gestion de la suppression de cas d'usage
            if st.session_state.confirming_delete_details and \
               st.session_state.confirming_delete_details["family"] == library_family_to_display:
                
                details = st.session_state.confirming_delete_details
                st.warning(f"⚠️ Supprimer '{details['use_case']}' de '{details['family']}' ? Action irréversible.")
                
                c1_del_uc, c2_del_uc, _ = st.columns([1,1,3])
                if c1_del_uc.button(f"Oui, supprimer '{details['use_case']}'", key=f"del_yes_lib_{details['family']}_{details['use_case']}", type="primary"):
                    deleted_uc_name_for_msg = details['use_case']
                    deleted_uc_fam_for_msg = details['family']
                    del st.session_state.editable_prompts[details["family"]][details["use_case"]]
                    save_editable_prompts_to_gist()
                    st.success(f"'{deleted_uc_name_for_msg}' supprimé de '{deleted_uc_fam_for_msg}'.")
                    st.session_state.confirming_delete_details = None
                    st.rerun()
                
                if c2_del_uc.button("Non, annuler", key=f"del_no_lib_{details['family']}_{details['use_case']}"):
                    st.session_state.confirming_delete_details = None
                    st.rerun()
                
                st.markdown("---")
            
            sorted_use_cases_display = sorted(list(filtered_use_cases.keys()))
            for use_case_name_display in sorted_use_cases_display:
                prompt_config_display = filtered_use_cases[use_case_name_display]
                template_display = prompt_config_display.get("template", "_Template non défini._")
                exp_title = f"{use_case_name_display}"
                if prompt_config_display.get("usage_count", 0) > 0: exp_title += f" (Utilisé {prompt_config_display.get('usage_count')} fois)"
                with st.expander(exp_title, expanded=False):
                    
                    tags_display = prompt_config_display.get("tags", [])
                    if tags_display: st.markdown(f"**Tags :** {', '.join([f'`{tag}`' for tag in tags_display])}")
                    created_at_str = prompt_config_display.get('created_at', get_default_dates()[0])
                    updated_at_str = prompt_config_display.get('updated_at', get_default_dates()[1])
                    st.caption(f"Créé le: {datetime.fromisoformat(created_at_str).strftime('%d/%m/%Y %H:%M')} | Modifié le: {datetime.fromisoformat(updated_at_str).strftime('%d/%m/%Y %H:%M')}")

                    col_btn_lib1, col_btn_lib2, col_btn_lib3 = st.columns(3)
                    with col_btn_lib1:
                        if st.button(f"✍️ Utiliser ce prompt", key=f"main_lib_use_{library_family_to_display.replace(' ', '_')}_{use_case_name_display.replace(' ', '_')}", use_container_width=True):
                            st.session_state.view_mode = "generator"; st.session_state.generator_selected_family = library_family_to_display; st.session_state.generator_selected_use_case = use_case_name_display; st.session_state.active_generated_prompt = ""; st.rerun()
                    with col_btn_lib2:
                        if st.button(f"📋 Dupliquer ce prompt", key=f"main_lib_duplicate_{library_family_to_display.replace(' ', '_')}_{use_case_name_display.replace(' ', '_')}", use_container_width=True):
                            st.session_state.duplicating_use_case_details = {
                                "family": library_family_to_display,
                                "use_case": use_case_name_display
                            }
                            st.rerun()
                    with col_btn_lib3:
                        if st.button(f"🗑️ Supprimer ce prompt", key=f"main_lib_delete_{library_family_to_display.replace(' ', '_')}_{use_case_name_display.replace(' ', '_')}", use_container_width=True):
                            st.session_state.confirming_delete_details = {
                                "family": library_family_to_display,
                                "use_case": use_case_name_display
                            }
                            st.rerun()
    else: 
        st.info("Aucun métier n'est actuellement sélectionnée dans la bibliothèque ou le métier sélectionné n'existe plus.")
        available_families_check = list(st.session_state.editable_prompts.keys())
        if not available_families_check : st.warning("La bibliothèque est entièrement vide. Veuillez créer des métiers et des prompts.")

elif st.session_state.view_mode == "edit":
    current_family_of_edited_prompt = st.session_state.get('family_selector_edition') # ou 'métier_selector_edition' si vous avez renommé cette clé de session_state
    if st.button(f"⬅️ Retour à la bibliothèque ({current_family_of_edited_prompt or 'Métier'})", key="back_to_library_from_edit"):
        if current_family_of_edited_prompt:
            st.session_state.library_selected_family_for_display = current_family_of_edited_prompt
        st.session_state.view_mode = "library"
        st.rerun()
    if not final_selected_family_edition : st.info("Sélectionnez un métier dans la barre latérale (onglet Édition) ou créez-en un pour commencer.")
    elif not final_selected_use_case_edition: st.info(f"Sélectionnez un cas d'usage dans le métier '{final_selected_family_edition}' ou créez-en un nouveau pour commencer.")
    elif final_selected_family_edition in st.session_state.editable_prompts and final_selected_use_case_edition in st.session_state.editable_prompts[final_selected_family_edition]:
        current_prompt_config = st.session_state.editable_prompts[final_selected_family_edition][final_selected_use_case_edition]
        st.header(f"Cas d'usage: {final_selected_use_case_edition}")
        created_at_str_edit = current_prompt_config.get('created_at', get_default_dates()[0]); updated_at_str_edit = current_prompt_config.get('updated_at', get_default_dates()[1])
        st.caption(f"Métier : {final_selected_family_edition} | Utilisé {current_prompt_config.get('usage_count', 0)} fois. Créé: {datetime.fromisoformat(created_at_str_edit).strftime('%d/%m/%Y')}, Modifié: {datetime.fromisoformat(updated_at_str_edit).strftime('%d/%m/%Y')}")
        gen_form_values = {}
        with st.form(key=f"gen_form_{final_selected_family_edition}_{final_selected_use_case_edition}"):
            if not current_prompt_config.get("variables"): st.info("Ce cas d'usage n'a pas de variables configurées pour la génération.")
            variables_for_form = current_prompt_config.get("variables", [])
            if not isinstance(variables_for_form, list): variables_for_form = [] 
            cols_per_row = 2 if len(variables_for_form) > 1 else 1
            var_chunks = [variables_for_form[i:i + cols_per_row] for i in range(0, len(variables_for_form), cols_per_row)]
            for chunk in var_chunks:
                cols = st.columns(len(chunk))
                for i, var_info in enumerate(chunk):
                    with cols[i]:
                        widget_key = f"gen_input_{final_selected_family_edition}_{final_selected_use_case_edition}_{var_info['name']}"; field_default = var_info.get("default"); var_type = var_info.get("type")
                        if var_type == "text_input": gen_form_values[var_info["name"]] = st.text_input(var_info["label"], value=str(field_default or ""), key=widget_key)
                        elif var_type == "selectbox":
                            opts = var_info.get("options", []); idx = 0 
                            if opts: 
                                try: idx = opts.index(field_default) if field_default in opts else 0
                                except ValueError: idx = 0 # pragma: no cover
                            gen_form_values[var_info["name"]] = st.selectbox(var_info["label"], options=opts, index=idx, key=widget_key)
                        elif var_type == "date_input":
                            val_date = field_default if isinstance(field_default, date) else datetime.now().date()
                            gen_form_values[var_info["name"]] = st.date_input(var_info["label"], value=val_date, key=widget_key)
                        elif var_type == "number_input": 
                            current_value_default_gen = var_info.get("default"); min_val_config_gen = var_info.get("min_value"); max_val_config_gen = var_info.get("max_value"); step_config_gen = var_info.get("step")
                            val_num_gen = float(current_value_default_gen) if isinstance(current_value_default_gen, (int, float)) else 0.0
                            min_val_gen = float(min_val_config_gen) if min_val_config_gen is not None else None; max_val_gen = float(max_val_config_gen) if max_val_config_gen is not None else None; step_val_gen = float(step_config_gen) if step_config_gen is not None else 1.0
                            if min_val_gen is not None and val_num_gen < min_val_gen: val_num_gen = min_val_gen 
                            if max_val_gen is not None and val_num_gen > max_val_gen: val_num_gen = max_val_gen 
                            gen_form_values[var_info["name"]] = st.number_input(var_info["label"], value=val_num_gen, min_value=min_val_gen,max_value=max_val_gen, step=step_val_gen, key=widget_key, format="%.2f")
                        elif var_type == "text_area": 
                            height_val = var_info.get("height")
                            final_height = None 
                            if height_val is not None:
                                try:
                                    h = int(height_val)
                                    if h >= 68: final_height = h
                                    else: final_height = 68 
                                except (ValueError, TypeError): final_height = None 
                            else: final_height = None 
                            gen_form_values[var_info["name"]] = st.text_area(var_info["label"], value=str(field_default or ""), height=final_height, key=widget_key)
            if st.form_submit_button("🚀 Générer Prompt"):
                processed_values_for_template = {}
                for k, v_val in gen_form_values.items(): # gen_form_values vient de votre formulaire
                    if v_val is None:
                        # On ne met pas les valeurs None dans le dictionnaire,
                        # donc les placeholders correspondants ne seront pas remplacés (comportement original)
                        continue 
                    
                    if isinstance(v_val, date):
                        processed_values_for_template[k] = v_val.strftime("%d/%m/%Y")
                    elif isinstance(v_val, float): # On regroupe ici tous les traitements pour les floats
                        if v_val.is_integer(): # Si le float est un entier (ex: 50.0)
                            processed_values_for_template[k] = str(int(v_val)) # Convertir en "50"
                        else: # S'il s'agit d'un float avec des décimales (ex: 0.125000...)
                            processed_values_for_template[k] = f"{v_val:.2f}" # Formater avec 2 décimales
                    else: # Pour tous les autres types (str, bool, etc. qui ne sont ni date ni float)
                        processed_values_for_template[k] = str(v_val)
                
                final_vals_for_prompt = processed_values_for_template # final_vals_for_prompt contient maintenant des chaînes

                try:
                    prompt_template_content = current_prompt_config.get("template", "")
                    processed_template = prompt_template_content

                    # 1. Remplacer les variables connues par Streamlit (celles du formulaire)
                    # Trier par longueur de clé (descendant) pour éviter les substitutions partielles
                    # (ex: remplacer {jour_semaine} avant {jour})
                    sorted_vars_for_formatting = sorted(final_vals_for_prompt.items(), key=lambda item: len(item[0]), reverse=True)

                    for var_name, var_value in sorted_vars_for_formatting:
                        placeholder_streamlit = f"{{{var_name}}}"
                        # Remplacer uniquement les placeholders exacts et simples
                        processed_template = processed_template.replace(placeholder_streamlit, str(var_value))

                    # 2. Convertir les doubles accolades (pour le LLM final) en simples accolades
                    # Ceci suppose que le template original (venant du JSON) utilisait bien {{...}}
                    # pour les placeholders destinés au LLM final.
                    formatted_template_content = processed_template.replace("{{", "{").replace("}}", "}")

                    use_case_title = final_selected_use_case_edition 
                    generated_prompt = f"Sujet : {use_case_title}\n{formatted_template_content}"
                    st.session_state.active_generated_prompt = generated_prompt
                    st.success("Prompt généré avec succès!")
                    st.balloons()
                    current_prompt_config["usage_count"] = current_prompt_config.get("usage_count", 0) + 1
                    current_prompt_config["updated_at"] = datetime.now().isoformat()
                    save_editable_prompts_to_gist()

                except Exception as e: # Garder un catch-all pour les erreurs imprévues
                    st.error(f"Erreur inattendue lors de la génération du prompt : {e}") # pragma: no cover
                    st.session_state.active_generated_prompt = f"ERREUR INATTENDUE - TEMPLATE ORIGINAL :\n---\n{prompt_template_content}" # pragma: no cover
        st.markdown("---")
        if st.session_state.active_generated_prompt:
            st.subheader("✅ Prompt Généré (éditable):")
            edited_prompt_value = st.text_area("Prompt:", value=st.session_state.active_generated_prompt, height=200, key=f"editable_generated_prompt_output_{final_selected_family_edition}_{final_selected_use_case_edition}", label_visibility="collapsed")
            if edited_prompt_value != st.session_state.active_generated_prompt: 
                st.session_state.active_generated_prompt = edited_prompt_value # pragma: no cover
            col_caption, col_indicator = st.columns([1.8, 0.2]) # Ajustez les proportions si nécessaire
            with col_caption:
                st.caption("Prompt généré (pour relecture et copie manuelle) :")
            with col_indicator:
                st.markdown("<div style='color:red; text-align:right; font-size:0.9em; padding-right:0.9em;'>Copier ici : 👇</div>", unsafe_allow_html=True)
    

            if st.session_state.active_generated_prompt:
                st.code(st.session_state.active_generated_prompt, language='markdown', line_numbers=True)
            else:
                st.markdown("*Aucun prompt généré à afficher.*")
        
                st.markdown("---") # Un petit séparateur

                prompt_text_escaped_for_js = json.dumps(st.session_state.active_generated_prompt)

        
        if st.session_state.confirming_delete_details and st.session_state.confirming_delete_details["family"] == final_selected_family_edition and st.session_state.confirming_delete_details["use_case"] == final_selected_use_case_edition:
            details = st.session_state.confirming_delete_details; st.warning(f"Supprimer '{details['use_case']}' de '{details['family']}' ? Action irréversible.")
            c1_del_uc, c2_del_uc, _ = st.columns([1,1,3])
            if c1_del_uc.button(f"Oui, supprimer '{details['use_case']}'", key=f"del_yes_{details['family']}_{details['use_case']}", type="primary"):
                deleted_uc_name_for_msg = details['use_case']; deleted_uc_fam_for_msg = details['family']; del st.session_state.editable_prompts[details["family"]][details["use_case"]]; save_editable_prompts_to_gist(); st.success(f"'{deleted_uc_name_for_msg}' supprimé de '{deleted_uc_fam_for_msg}'.")
                st.session_state.confirming_delete_details = None; st.session_state.force_select_family_name = deleted_uc_fam_for_msg; st.session_state.force_select_use_case_name = None 
                if st.session_state.editing_variable_info and st.session_state.editing_variable_info.get("family") == deleted_uc_fam_for_msg and st.session_state.editing_variable_info.get("use_case") == deleted_uc_name_for_msg: st.session_state.editing_variable_info = None # pragma: no cover
                st.session_state.active_generated_prompt = ""; st.session_state.variable_type_to_create = None; st.session_state.view_mode = "edit"; st.rerun()
            if c2_del_uc.button("Non, annuler", key=f"del_no_{details['family']}_{details['use_case']}"): st.session_state.confirming_delete_details = None; st.rerun() 
            st.markdown("---") 
 
    else:
        if not final_selected_family_edition: 
            st.info("Veuillez sélectionner un métier dans la barre latérale (onglet Édition) pour commencer.")
        elif not final_selected_use_case_edition: 
            st.info(f"Veuillez sélectionner un cas d'usage pour le métier '{final_selected_family_edition}' ou en créer un.")
        else: 
            st.warning(f"Le cas d'usage '{final_selected_use_case_edition}' dans le métier '{final_selected_family_edition}' semble introuvable. Il a peut-être été supprimé. Veuillez vérifier vos sélections.")
            st.session_state.use_case_selector_edition = None # pragma: no cover

elif st.session_state.view_mode == "generator":
    generator_family = st.session_state.get('generator_selected_family')
    generator_use_case = st.session_state.get('generator_selected_use_case')
    
    if st.button(f"⬅️ Retour à la bibliothèque ({generator_family or 'Métier'})", key="back_to_library_from_generator"):
        if generator_family:
            st.session_state.library_selected_family_for_display = generator_family
        st.session_state.view_mode = "library"
        st.rerun()
    
    if not generator_family or not generator_use_case:
        st.info("Sélection de prompt invalide. Retournez à la bibliothèque pour choisir un prompt.")
    elif generator_family not in st.session_state.editable_prompts or generator_use_case not in st.session_state.editable_prompts[generator_family]:
        st.warning("Le prompt sélectionné n'existe plus. Retournez à la bibliothèque pour en choisir un autre.")
    else:
        current_prompt_config = st.session_state.editable_prompts[generator_family][generator_use_case]
        st.header(f"Générateur de Prompt: {generator_use_case}")
        created_at_str_gen = current_prompt_config.get('created_at', get_default_dates()[0])
        updated_at_str_gen = current_prompt_config.get('updated_at', get_default_dates()[1])
        st.caption(f"Métier : {generator_family} | Utilisé {current_prompt_config.get('usage_count', 0)} fois. Créé: {datetime.fromisoformat(created_at_str_gen).strftime('%d/%m/%Y')}, Modifié: {datetime.fromisoformat(updated_at_str_gen).strftime('%d/%m/%Y')}")
        
        gen_form_values = {}
        with st.form(key=f"gen_form_{generator_family}_{generator_use_case}"):
            if not current_prompt_config.get("variables"):
                st.info("Ce cas d'usage n'a pas de variables configurées pour la génération.")
            
            variables_for_form = current_prompt_config.get("variables", [])
            if not isinstance(variables_for_form, list):
                variables_for_form = []
            
            cols_per_row = 2 if len(variables_for_form) > 1 else 1
            var_chunks = [variables_for_form[i:i + cols_per_row] for i in range(0, len(variables_for_form), cols_per_row)]
            
            for chunk in var_chunks:
                cols = st.columns(len(chunk))
                for i, var_info in enumerate(chunk):
                    with cols[i]:
                        widget_key = f"gen_input_{generator_family}_{generator_use_case}_{var_info['name']}"
                        field_default = var_info.get("default")
                        var_type = var_info.get("type")
                        
                        if var_type == "text_input":
                            gen_form_values[var_info["name"]] = st.text_input(
                                var_info["label"], 
                                value=str(field_default or ""), 
                                key=widget_key
                            )
                        elif var_type == "selectbox":
                            opts = var_info.get("options", [])
                            idx = 0
                            if opts:
                                try:
                                    idx = opts.index(field_default) if field_default in opts else 0
                                except ValueError:
                                    idx = 0
                            gen_form_values[var_info["name"]] = st.selectbox(
                                var_info["label"], 
                                options=opts, 
                                index=idx, 
                                key=widget_key
                            )
                        elif var_type == "date_input":
                            val_date = field_default if isinstance(field_default, date) else datetime.now().date()
                            gen_form_values[var_info["name"]] = st.date_input(
                                var_info["label"], 
                                value=val_date, 
                                key=widget_key
                            )
                        elif var_type == "number_input":
                            current_value_default_gen = var_info.get("default")
                            min_val_config_gen = var_info.get("min_value")
                            max_val_config_gen = var_info.get("max_value")
                            step_config_gen = var_info.get("step")
                            val_num_gen = float(current_value_default_gen) if isinstance(current_value_default_gen, (int, float)) else 0.0
                            min_val_gen = float(min_val_config_gen) if min_val_config_gen is not None else None
                            max_val_gen = float(max_val_config_gen) if max_val_config_gen is not None else None
                            step_val_gen = float(step_config_gen) if step_config_gen is not None else 1.0
                            if min_val_gen is not None and val_num_gen < min_val_gen:
                                val_num_gen = min_val_gen
                            if max_val_gen is not None and val_num_gen > max_val_gen:
                                val_num_gen = max_val_gen
                            gen_form_values[var_info["name"]] = st.number_input(
                                var_info["label"], 
                                value=val_num_gen, 
                                min_value=min_val_gen,
                                max_value=max_val_gen, 
                                step=step_val_gen, 
                                key=widget_key, 
                                format="%.2f"
                            )
                        elif var_type == "text_area":
                            height_val = var_info.get("height")
                            final_height = None
                            if height_val is not None:
                                try:
                                    h = int(height_val)
                                    if h >= 68:
                                        final_height = h
                                    else:
                                        final_height = 68
                                except (ValueError, TypeError):
                                    final_height = None
                            else:
                                final_height = None
                            gen_form_values[var_info["name"]] = st.text_area(
                                var_info["label"], 
                                value=str(field_default or ""), 
                                height=final_height, 
                                key=widget_key
                            )
            
            if st.form_submit_button("🚀 Générer Prompt"):
                processed_values_for_template = {}
                for k, v_val in gen_form_values.items():
                    if v_val is None:
                        continue
                    
                    if isinstance(v_val, date):
                        processed_values_for_template[k] = v_val.strftime("%d/%m/%Y")
                    elif isinstance(v_val, float):
                        if v_val.is_integer():
                            processed_values_for_template[k] = str(int(v_val))
                        else:
                            processed_values_for_template[k] = f"{v_val:.2f}"
                    else:
                        processed_values_for_template[k] = str(v_val)
                
                final_vals_for_prompt = processed_values_for_template
                
                try:
                    prompt_template_content = current_prompt_config.get("template", "")
                    processed_template = prompt_template_content
                    
                    sorted_vars_for_formatting = sorted(final_vals_for_prompt.items(), key=lambda item: len(item[0]), reverse=True)
                    
                    for var_name, var_value in sorted_vars_for_formatting:
                        placeholder_streamlit = f"{{{var_name}}}"
                        processed_template = processed_template.replace(placeholder_streamlit, str(var_value))
                    
                    formatted_template_content = processed_template.replace("{{", "{").replace("}}", "}")
                    
                    use_case_title = generator_use_case
                    generated_prompt = f"Sujet : {use_case_title}\n{formatted_template_content}"
                    st.session_state.active_generated_prompt = generated_prompt
                    st.success("Prompt généré avec succès!")
                    st.balloons()
                    current_prompt_config["usage_count"] = current_prompt_config.get("usage_count", 0) + 1
                    current_prompt_config["updated_at"] = datetime.now().isoformat()
                    save_editable_prompts_to_gist()
                    
                except Exception as e:
                    st.error(f"Erreur inattendue lors de la génération du prompt : {e}")
                    st.session_state.active_generated_prompt = f"ERREUR INATTENDUE - TEMPLATE ORIGINAL :\n---\n{prompt_template_content}"
        
        st.markdown("---")
        if st.session_state.active_generated_prompt:
            st.subheader("✅ Prompt Généré (éditable):")
            edited_prompt_value = st.text_area(
                "Prompt:", 
                value=st.session_state.active_generated_prompt, 
                height=200, 
                key=f"editable_generated_prompt_output_{generator_family}_{generator_use_case}", 
                label_visibility="collapsed"
            )
            if edited_prompt_value != st.session_state.active_generated_prompt:
                st.session_state.active_generated_prompt = edited_prompt_value
            
            col_caption, col_indicator = st.columns([1.8, 0.2])
            with col_caption:
                st.caption("Prompt généré (pour relecture et copie manuelle) :")
            with col_indicator:
                st.markdown("<div style='color:red; text-align:right; font-size:0.9em; padding-right:0.9em;'>Copier ici : 👇</div>", unsafe_allow_html=True)
            
            if st.session_state.active_generated_prompt:
                st.code(st.session_state.active_generated_prompt, language='markdown', line_numbers=True)
            else:
                st.markdown("*Aucun prompt généré à afficher.*")

elif st.session_state.view_mode == "inject_manual": 
    if st.button("⬅️ Retour à l'accueil", key="back_to_accueil_from_inject"):
        st.session_state.view_mode = "accueil"
        st.rerun()
    st.header("💉 Injection Manuelle de Cas d'Usage JSON")
    st.markdown("""Collez ici un ou plusieurs cas d'usage au format JSON. Le JSON doit être un dictionnaire où chaque clé est le nom du nouveau cas d'usage, et la valeur est sa configuration.""")
    st.caption("Exemple de structure pour un cas d'usage :")
    json_example_string = """{
  "Nom de Mon Nouveau Cas d'Usage": {
    "template": "Ceci est le {variable_exemple} pour mon prompt.",
    "variables": [
      {
        "name": "variable_exemple",
        "label": "Variable d'Exemple",
        "type": "text_input",
        "default": "texte par défaut"
      }
    ],
    "tags": ["nouveau", "exemple"]
  }
}"""
    st.code(json_example_string, language="json")
    available_families_for_injection = list(st.session_state.editable_prompts.keys())
    if not available_families_for_injection: 
        st.warning("Aucun métier n'existe. Veuillez d'abord créer un métier via l'onglet 'Édition'.")
    else:
        selected_family_for_injection = st.selectbox("Choisissez le métier de destination pour l'injection :", options=[""] + available_families_for_injection, index=0, key="injection_family_selector")
        st.session_state.injection_selected_family = selected_family_for_injection if selected_family_for_injection else None
        if st.session_state.injection_selected_family:
            st.subheader(f"Injecter dans le métier : {st.session_state.injection_selected_family}")
            st.session_state.injection_json_text = st.text_area("Collez le JSON des cas d'usage ici :", value=st.session_state.get("injection_json_text", ""), height=300, key="injection_json_input")
            if st.button("➕ Injecter les Cas d'Usage", key="submit_injection_btn"):
                if not st.session_state.injection_json_text.strip(): 
                    st.error("La zone de texte JSON est vide.")
                else:
                    try:
                        injected_data = json.loads(st.session_state.injection_json_text)
                        if not isinstance(injected_data, dict): 
                            st.error("Le JSON fourni doit être un dictionnaire (objet JSON).")
                        else:
                            target_family_name = st.session_state.injection_selected_family
                            if target_family_name not in st.session_state.editable_prompts: 
                                st.error(f"Le métier de destination '{target_family_name}' n'existe plus ou n'a pas été correctement sélectionnée.") 
                            else:
                                family_prompts = st.session_state.editable_prompts[target_family_name]
                                successful_injections = []
                                failed_injections = []
                                first_new_uc_name = None
                                for uc_name, uc_config_json in injected_data.items():
                                    uc_name_stripped = uc_name.strip()
                                    if not uc_name_stripped: 
                                        failed_injections.append(f"Nom de cas d'usage vide ignoré.")
                                        continue
                                    if not isinstance(uc_config_json, dict) or "template" not in uc_config_json: 
                                        failed_injections.append(f"'{uc_name_stripped}': Configuration invalide ou template manquant.")
                                        continue
                                    if uc_name_stripped in family_prompts: 
                                        st.warning(f"Le cas d'usage '{uc_name_stripped}' existe déjà dans le métier '{target_family_name}'. Il a été ignoré.")
                                        failed_injections.append(f"'{uc_name_stripped}': Existe déjà, ignoré.")
                                        continue

                                    prepared_uc_config = _prepare_newly_injected_use_case_config(uc_config_json)

                                    if not prepared_uc_config.get("template"): 
                                        failed_injections.append(f"'{uc_name_stripped}': Template invalide après traitement.")
                                        continue
                                    family_prompts[uc_name_stripped] = prepared_uc_config
                                    successful_injections.append(uc_name_stripped)
                                    if first_new_uc_name is None: 
                                        first_new_uc_name = uc_name_stripped
                                if successful_injections:
                                    save_editable_prompts_to_gist()
                                    st.success(f"{len(successful_injections)} cas d'usage injectés avec succès dans '{target_family_name}': {', '.join(successful_injections)}")
                                    st.session_state.injection_json_text = "" 
                                    if first_new_uc_name: 
                                        st.session_state.view_mode = "edit"
                                        st.session_state.force_select_family_name = target_family_name
                                        st.session_state.force_select_use_case_name = first_new_uc_name
                                        st.session_state.go_to_config_section = True
                                        st.session_state.active_generated_prompt = "" # <--- AJOUTEZ CETTE LIGNE ICI
                                        st.rerun()
                                if failed_injections:
                                    for fail_msg in failed_injections: 
                                        st.error(f"Échec d'injection : {fail_msg}")
                                if not successful_injections and not failed_injections: 
                                    st.info("Aucun cas d'usage n'a été trouvé dans le JSON fourni ou tous étaient vides/invalides.")
                    except json.JSONDecodeError as e: 
                        st.error(f"Erreur de parsing JSON : {e}")
                    except Exception as e: 
                        st.error(f"Une erreur inattendue est survenue lors de l'injection : {e}") # pragma: no cover
        else: 
            st.info("Veuillez sélectionner un métier de destination pour commencer l'injection.")

elif st.session_state.view_mode == "assistant_creation": # Cette vue gère maintenant les deux modes
    if st.button("⬅️ Retour à l'accueil", key="back_to_accueil_from_assistant_unified"):
        st.session_state.view_mode = "accueil"
        st.rerun()
    st.header("✨ Assistant Prompt Système")

    # S'assurer que assistant_mode a une valeur initiale valide si elle n'est pas déjà définie
    if 'assistant_mode' not in st.session_state:
        st.session_state.assistant_mode = "creation"

    mode_options_labels = {
        "creation": "🆕 Créer un nouveau prompt système",
        "amelioration": "🚀 Améliorer un prompt existant"
    }
    
    # Utiliser l'index pour que st.radio se souvienne de la sélection via st.session_state.assistant_mode
    current_mode_index = 0 if st.session_state.assistant_mode == "creation" else 1

    selected_mode_key = st.radio(
        "Que souhaitez-vous faire ?",
        options=list(mode_options_labels.keys()),
        format_func=lambda key: mode_options_labels[key],
        index=current_mode_index,
        key="assistant_mode_radio_selector" # Clé unique pour le widget radio
    )

    # Si le mode sélectionné via le radio a changé, mettre à jour st.session_state et rerun pour rafraîchir le formulaire
    if selected_mode_key != st.session_state.assistant_mode:
        st.session_state.assistant_mode = selected_mode_key
        st.session_state.generated_meta_prompt_for_llm = "" # Vider le prompt généré car le mode a changé
        # Optionnel: vider les valeurs des formulaires lors du changement de mode pour éviter confusion
        # st.session_state.assistant_form_values = {var['name']: var['default'] for var in ASSISTANT_FORM_VARIABLES}
        # st.session_state.assistant_existing_prompt_value = ""
        st.rerun()

    if st.session_state.assistant_mode == "creation":
        st.markdown("Décrivez votre besoin pour que l'assistant génère une instruction détaillée. Vous donnerez cette instruction à LaPoste GPT qui, en retour, produira les éléments de votre cas d'usage (prompt système, variables, etc.).")
        with st.form(key="assistant_creation_form_std"):
            # Initialiser current_form_input_values avec les valeurs de session_state ou les valeurs par défaut
            # pour que les champs du formulaire soient pré-remplis correctement.
            temp_form_values = {}
            for var_info in ASSISTANT_FORM_VARIABLES:
                field_key = f"assistant_form_{var_info['name']}"
                # Utilise la valeur de session_state pour ce champ ou la valeur par défaut si non trouvée
                value_for_widget = st.session_state.assistant_form_values.get(var_info['name'], var_info['default'])

                if var_info["type"] == "text_input":
                    temp_form_values[var_info["name"]] = st.text_input(
                        var_info["label"], value=value_for_widget, key=field_key
                    )
                elif var_info["type"] == "text_area":
                    temp_form_values[var_info["name"]] = st.text_area(
                        var_info["label"], value=value_for_widget, height=var_info.get("height", 100), key=field_key
                    )
                elif var_info["type"] == "number_input": # Assurez-vous que ce cas est géré si vous l'avez
                    try:
                        num_value_for_widget = float(value_for_widget if value_for_widget else var_info["default"])
                    except (ValueError, TypeError):
                        num_value_for_widget = float(var_info["default"])
                    temp_form_values[var_info["name"]] = st.number_input(
                         var_info["label"],
                         value=num_value_for_widget,
                         min_value=float(var_info.get("min_value")) if var_info.get("min_value") is not None else None,
                         max_value=float(var_info.get("max_value")) if var_info.get("max_value") is not None else None,
                         step=float(var_info.get("step", 1.0)),
                         key=field_key,
                         format="%g" # ou un autre format si nécessaire
                    )
            submitted_assistant_form = st.form_submit_button("📝 Générer l'instruction de création")

            if submitted_assistant_form:
                st.session_state.assistant_form_values = temp_form_values.copy() # Sauvegarde les valeurs actuelles du formulaire
                try:
                    # Vérifier si tous les champs requis pour ce template sont remplis (si nécessaire)
                    populated_meta_prompt = META_PROMPT_FOR_EXTERNAL_LLM_TEMPLATE.format(**st.session_state.assistant_form_values)
                    st.session_state.generated_meta_prompt_for_llm = populated_meta_prompt
                    st.success("Instruction de création générée !")
                except KeyError as e: 
                    st.error(f"Erreur lors de la construction de l'instruction. Clé de formatage manquante : {e}.")
                    st.session_state.generated_meta_prompt_for_llm = ""
                except Exception as e: 
                    st.error(f"Une erreur inattendue est survenue : {e}")
                    st.session_state.generated_meta_prompt_for_llm = ""

    elif st.session_state.assistant_mode == "amelioration":
        st.markdown("Collez votre prompt existant. L'assistant générera une instruction pour LaPoste GPT afin de transformer votre prompt en un cas d'usage structuré et améliorable pour cette application.")
        with st.form(key="assistant_amelioration_form_unified"):
            # Utilise la valeur de session_state pour ce champ
            prompt_existant_input_val = st.text_area(
                "Collez votre prompt existant ici :",
                value=st.session_state.assistant_existing_prompt_value, 
                height=300,
                key="assistant_form_prompt_existant_unified"
            )
            submitted_assistant_amelioration_form = st.form_submit_button("📝 Générer l'instruction d'amélioration")

            if submitted_assistant_amelioration_form:
                st.session_state.assistant_existing_prompt_value = prompt_existant_input_val # Sauvegarde la valeur soumise
                if not prompt_existant_input_val.strip():
                    st.error("Veuillez coller un prompt existant dans la zone de texte.")
                    st.session_state.generated_meta_prompt_for_llm = ""
                else:
                    try:
                        populated_meta_prompt_amelioration = META_PROMPT_FOR_LLM_AMELIORATION_TEMPLATE.format(
                            prompt_existant=prompt_existant_input_val # Utiliser la valeur actuelle du champ
                        )
                        st.session_state.generated_meta_prompt_for_llm = populated_meta_prompt_amelioration
                        st.success("Instruction d'amélioration générée !")
                    except KeyError as e: 
                        st.error(f"Erreur lors de la construction de l'instruction. Clé de formatage manquante : {e}.")
                        st.session_state.generated_meta_prompt_for_llm = ""
                    except Exception as e: 
                        st.error(f"Une erreur inattendue est survenue : {e}")
                        st.session_state.generated_meta_prompt_for_llm = ""

    # Affichage commun du méta-prompt généré (qu'il vienne de la création ou de l'amélioration)
    if st.session_state.generated_meta_prompt_for_llm:
        col_subheader_assist, col_indicator_assist = st.columns([0.85, 0.15])
        with col_subheader_assist:
            st.subheader("📋 Instruction Générée (à coller dans LaPosteGPT) :")
        with col_indicator_assist:
            st.markdown("<div style='color:red; text-align:right; font-size:0.9em; padding-top:1.9em;padding-right:0.9em;'>Copier ici : 👇</div>", unsafe_allow_html=True)

        st.code(st.session_state.generated_meta_prompt_for_llm, language='markdown', line_numbers=True)
        st.caption("<span style='color:gray; font-size:0.9em;'>Utilisez l'icône en haut à droite du bloc de code pour copier l'instruction.</span>", unsafe_allow_html=True)
        st.markdown("---")
        st.info("Une fois que LaPoste GPT (ou votre LLM externe) a généré le JSON basé sur cette instruction, copiez ce JSON et utilisez le bouton \"💉 Injecter JSON Manuellement\" (disponible aussi dans l'onglet Assistant du menu) pour l'ajouter à votre atelier.")
        if st.button("💉 Injecter JSON Manuellement", key="prepare_inject_from_assistant_unified_btn", use_container_width=True, type="primary"):
            st.session_state.view_mode = "inject_manual"
            st.session_state.injection_selected_family = None
            st.session_state.injection_json_text = ""
            st.toast("Collez le JSON généré par le LLM et sélectionnez un métier de destination.", icon="💡")
            st.rerun()   
    if not any(st.session_state.editable_prompts.values()): # pragma: no cover
        st.warning("Aucun groupement de cas d'usage métier n'est configurée. Veuillez en créer une via l'onglet 'Édition' ou vérifier votre Gist.")
    elif st.session_state.view_mode not in ["library", "edit", "inject_manual", "assistant_creation"]: # pragma: no cover
        st.session_state.view_mode = "library" if list(st.session_state.editable_prompts.keys()) else "edit"
        st.rerun()

# --- Sidebar Footer ---
st.sidebar.markdown("---")
st.sidebar.info(f"Générateur v3.3.6 - © {CURRENT_YEAR} La Poste (démo)")
