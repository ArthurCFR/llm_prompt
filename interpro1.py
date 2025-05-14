import streamlit as st
from datetime import datetime, date
import copy
# from collections import defaultdict # Plus utilisé directement
import json
import requests

# --- PAGE CONFIGURATION (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(layout="wide", page_title="Bibliothèque de Prompts IA")

# --- Initial Data Structure & Constants ---
CURRENT_YEAR = 2025 # Année actuelle pour les exemples
INITIAL_PROMPT_TEMPLATES = {
    "Achat": {
        "Recherche de Fournisseurs": {
            "template": "Recherche dans la base de données quels sont les fournisseurs de {legume} les {critere_prix} entre l'année {annee_debut} et l'année {annee_fin}.",
            "variables": [
                {"name": "legume", "label": "Quel légume/produit recherchez-vous ?", "type": "text_input", "default": "tomates"},
                {"name": "critere_prix", "label": "Quel critère de prix ?", "type": "selectbox", "options": ["moins chers", "plus chers", "mieux notés"], "default": "moins chers"},
                {"name": "annee_debut", "label": "Année de début", "type": "selectbox", "options": list(range(CURRENT_YEAR - 5, CURRENT_YEAR + 1)), "default": CURRENT_YEAR -1 },
                {"name": "annee_fin", "label": "Année de fin", "type": "selectbox", "options": list(range(CURRENT_YEAR - 5, CURRENT_YEAR + 2)), "default": CURRENT_YEAR},
            ]
        },
        "Génération d'Email de Suivi Client": {
            "template": "Rédige un email de suivi pour {nom_client} concernant sa commande {num_commande} passée le {date_commande}. L'email doit avoir un ton {ton_email} et mentionner que nous attendons son retour sur {point_feedback}.",
            "variables": [
                {"name": "nom_client", "label": "Nom du client", "type": "text_input", "default": "M. Dupont"},
                {"name": "num_commande", "label": "Numéro de commande", "type": "text_input", "default": "CMD202500123"}, # Adjusted year
                {"name": "date_commande", "label": "Date de la commande", "type": "date_input", "default": date(CURRENT_YEAR, 1, 15)},
                {"name": "ton_email", "label": "Ton de l'email", "type": "selectbox", "options": ["professionnel", "amical", "formel", "enthousiaste"], "default": "professionnel"},
                {"name": "point_feedback", "label": "Point pour feedback", "type": "text_input", "default": "son expérience avec notre nouveau service"},
            ]
        },
        "Résumé de Document": {
            "template": "Résume le document suivant en {nombre_points} points clés pour un public de {public_cible}. Le résumé doit se concentrer sur les aspects de {focus_resume}. Le style de résumé doit être {style_resume}. Voici le texte à résumer : \n\n{texte_document}",
            "variables": [
                {"name": "nombre_points", "label": "Nombre de points clés", "type": "number_input", "default": 3, "min_value":1, "max_value":10, "step":1},
                {"name": "public_cible", "label": "Public cible", "type": "selectbox", "options": ["direction", "équipe technique", "clients", "partenaires", "grand public"], "default": "direction"},
                {"name": "focus_resume", "label": "Focus principal", "type": "selectbox", "options": ["aspects techniques", "impacts financiers", "prochaines étapes", "conclusions principales", "avantages concurrentiels"], "default": "conclusions principales"},
                {"name": "style_resume", "label": "Style du résumé", "type": "selectbox", "options": ["concis et direct", "détaillé", "orienté action", "informatif neutre"], "default": "concis et direct"},
                {"name": "texte_document", "label": "Texte à résumer", "type": "text_area", "height": 200, "default": "Collez le texte ici..."},
            ]
        }
    },
    "RH": {},
    "Finance": {},
    "Comptabilité": {}
}
GIST_DATA_FILENAME = "prompt_templates_data.json"

# --- Utility Functions (Data Handling & Dates) ---
def _preprocess_for_saving(data_to_save):
    processed_data = copy.deepcopy(data_to_save)
    for family_name in list(processed_data.keys()): 
        use_cases_in_family = processed_data[family_name]
        if not isinstance(use_cases_in_family, dict):
            st.error(f"Données corrompues (famille non-dict): '{family_name}'. Suppression de la sauvegarde.")
            del processed_data[family_name]
            continue
        for use_case_name in list(use_cases_in_family.keys()):
            config = use_cases_in_family[use_case_name]
            if not isinstance(config, dict):
                st.error(f"Données corrompues (cas d'usage non-dict): '{use_case_name}' dans '{family_name}'. Suppression de la sauvegarde.")
                del processed_data[family_name][use_case_name]
                continue
            variables_list = config.get("variables")
            if not isinstance(variables_list, list):
                config["variables"] = []
                variables_list = config["variables"]
            for var_info in variables_list:
                if isinstance(var_info, dict) and var_info.get("type") == "date_input" and isinstance(var_info.get("default"), date):
                    var_info["default"] = var_info["default"].strftime("%Y-%m-%d")
    return processed_data

def _postprocess_after_loading(loaded_data):
    processed_data = copy.deepcopy(loaded_data)
    for family_name in list(processed_data.keys()):
        use_cases_in_family = processed_data[family_name]
        if not isinstance(use_cases_in_family, dict):
            st.warning(f"Données corrompues (famille non-dict): '{family_name}'. Ignorée lors du chargement.")
            del processed_data[family_name]
            continue
        for use_case_name in list(use_cases_in_family.keys()):
            config = use_cases_in_family[use_case_name]
            if not isinstance(config, dict):
                st.warning(f"Données corrompues (cas d'usage non-dict): '{use_case_name}' dans '{family_name}'. Ignoré lors du chargement.")
                del processed_data[family_name][use_case_name]
                continue
            variables_list = config.get("variables")
            if not isinstance(variables_list, list):
                config["variables"] = []
                variables_list = config["variables"]
            for var_info in variables_list:
                if isinstance(var_info, dict) and var_info.get("type") == "date_input" and isinstance(var_info.get("default"), str):
                    try:
                        var_info["default"] = datetime.strptime(var_info["default"], "%Y-%m-%d").date()
                    except ValueError:
                        var_info["default"] = datetime.now().date()
    return processed_data

# --- Gist Interaction Functions ---
def get_gist_content(gist_id, github_pat):
    headers = {"Authorization": f"token {github_pat}", "Accept": "application/vnd.github.v3+json"}
    try:
        response = requests.get(f"https://api.github.com/gists/{gist_id}", headers=headers)
        response.raise_for_status()
        gist_data = response.json()
        if GIST_DATA_FILENAME in gist_data["files"]:
            return gist_data["files"][GIST_DATA_FILENAME]["content"]
        else:
            st.info(f"Le fichier '{GIST_DATA_FILENAME}' n'existe pas dans le Gist. Il sera initialisé.")
            return "{}" 
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur Gist (get): {e}")
        return None
    except KeyError: 
        st.error(f"Erreur Gist (get): Fichier '{GIST_DATA_FILENAME}' non trouvé ou structure Gist inattendue.")
        return None

def update_gist_content(gist_id, github_pat, new_content_json_string):
    # Cette fonction n'est plus activement utilisée si l'UI ne permet plus de modifications,
    # mais elle est conservée pour l'intégrité de la logique de sauvegarde/chargement initiale.
    headers = {"Authorization": f"token {github_pat}", "Accept": "application/vnd.github.v3+json"}
    data = {"files": {GIST_DATA_FILENAME: {"content": new_content_json_string}}}
    try:
        response = requests.patch(f"https://api.github.com/gists/{gist_id}", headers=headers, json=data)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur Gist (update): {e}")
        return False

def save_editable_prompts_to_gist(): # Conservée pour une éventuelle utilisation future ou sauvegarde initiale
    GIST_ID = st.secrets.get("GIST_ID")
    GITHUB_PAT = st.secrets.get("GITHUB_PAT")
    if not GIST_ID or not GITHUB_PAT:
        # Pas d'erreur si l'UI ne sauvegarde pas, juste un log silencieux ou rien
        # st.error("Secrets Gist manquants (GIST_ID/GITHUB_PAT). Sauvegarde impossible.")
        return
    if 'editable_prompts' in st.session_state:
        data_to_save = _preprocess_for_saving(st.session_state.editable_prompts)
        try:
            json_string = json.dumps(data_to_save, indent=4, ensure_ascii=False)
            if not update_gist_content(GIST_ID, GITHUB_PAT, json_string):
                st.warning("Sauvegarde Gist échouée (si tentée).")
        except Exception as e:
            st.error(f"Erreur préparation données pour Gist: {e}")

def load_editable_prompts_from_gist():
    GIST_ID = st.secrets.get("GIST_ID")
    GITHUB_PAT = st.secrets.get("GITHUB_PAT")
    if not GIST_ID or not GITHUB_PAT:
        st.warning("Secrets Gist manquants. Utilisation des modèles par défaut.")
        return copy.deepcopy(INITIAL_PROMPT_TEMPLATES)
    
    raw_content = get_gist_content(GIST_ID, GITHUB_PAT)
    if raw_content:
        try:
            loaded_data = json.loads(raw_content)
            if not loaded_data or not isinstance(loaded_data, dict):
                raise ValueError("Contenu Gist vide ou mal structuré.")
            return _postprocess_after_loading(loaded_data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            st.info(f"Erreur chargement Gist ({e}). Initialisation avec modèles par défaut.")
    else: 
        st.info("Gist vide ou inaccessible. Initialisation avec modèles par défaut.")

    initial_data = copy.deepcopy(INITIAL_PROMPT_TEMPLATES)
    # Tenter de sauvegarder les données initiales si le Gist était vide/inaccessible
    # Ceci est utile si le Gist est fraîchement créé ou a été vidé.
    data_to_save = _preprocess_for_saving(initial_data)
    try:
        json_string = json.dumps(data_to_save, indent=4, ensure_ascii=False)
        if update_gist_content(GIST_ID, GITHUB_PAT, json_string):
            st.info("Modèles par défaut sauvegardés sur Gist pour initialisation.")
        # else:
            # Pas besoin d'erreur ici si la sauvegarde initiale échoue, l'app fonctionnera avec les données en mémoire.
            # st.error("Échec sauvegarde modèles par défaut sur Gist.") 
    except Exception as e:
        st.error(f"Erreur sauvegarde initiale sur Gist: {e}")
    return initial_data

# --- Session State Initialization ---
if 'editable_prompts' not in st.session_state:
    st.session_state.editable_prompts = load_editable_prompts_from_gist()

# Clé pour le widget de sélection de la famille dans la sidebar
if 'library_selected_family' not in st.session_state:
    available_families_on_load = list(st.session_state.editable_prompts.keys())
    st.session_state.library_selected_family = available_families_on_load[0] if available_families_on_load else None

# --- Main App UI ---
st.title("Bibliothèque de Prompts IA")

# --- Sidebar Navigation ---
st.sidebar.header("Navigation")
available_families_sidebar = sorted(list(st.session_state.editable_prompts.keys()))

if not available_families_sidebar:
    st.sidebar.warning("Aucune famille de prompts n'est configurée.")
    st.session_state.library_selected_family = None # Assurer qu'aucune famille n'est sélectionnée
else:
    # Si la famille précédemment sélectionnée n'existe plus, ou si aucune n'était sélectionnée,
    # choisir la première famille disponible comme défaut.
    if not st.session_state.library_selected_family or st.session_state.library_selected_family not in available_families_sidebar:
        st.session_state.library_selected_family = available_families_sidebar[0]
    
    # Le widget radio mettra à jour st.session_state.library_selected_family directement grâce à sa clé.
    st.sidebar.radio(
        "Choisissez une famille à afficher:",
        options=available_families_sidebar,
        key='library_selected_family' # La sélection est stockée et lue depuis st.session_state.library_selected_family
    )

st.sidebar.markdown("---")
st.sidebar.info(f"Bibliothèque v1 - © {CURRENT_YEAR} Votre Organisation")

# --- Main Display Area ---
selected_family_for_display = st.session_state.get('library_selected_family')

if not selected_family_for_display:
    if available_families_sidebar:
         st.info("Veuillez sélectionner une famille dans la barre latérale pour afficher ses prompts.")
    else:
         st.error("Aucune famille de prompts n'est disponible dans l'application.")
else:
    st.header(f"Prompts de la Famille : {selected_family_for_display}")
    st.markdown("---")

    # Récupérer les cas d'usage pour la famille sélectionnée
    use_cases_in_family = st.session_state.editable_prompts.get(selected_family_for_display, {})
    
    if not use_cases_in_family:
        st.info(f"La famille '{selected_family_for_display}' ne contient actuellement aucun prompt.")
    else:
        sorted_use_cases = sorted(list(use_cases_in_family.keys()))
        
        if not sorted_use_cases:
            st.info(f"La famille '{selected_family_for_display}' ne contient aucun prompt (liste vide).")
        else:
            for use_case_name in sorted_use_cases:
                prompt_config = use_cases_in_family[use_case_name]
                template = prompt_config.get("template", "_Template non défini pour ce cas d'usage._")
                
                with st.expander(f"{use_case_name}", expanded=False):
                    st.markdown(f"##### Template pour : {use_case_name}")
                    st.code(template, language=None)
                    
                    variables = prompt_config.get("variables", [])
                    if variables:
                        st.markdown("**Variables associées:**")
                        var_details_list = []
                        for var_info in variables:
                            if isinstance(var_info, dict): # S'assurer que var_info est un dictionnaire
                                var_name = var_info.get('name', 'Nom inconnu')
                                var_label = var_info.get('label', 'Label inconnu')
                                var_details_list.append(f"- `{var_name}` ({var_label})")
                        if var_details_list:
                            st.markdown("\n".join(var_details_list))
                        else:
                            st.caption("_Aucune variable correctement définie trouvée._")
                    else:
                        st.caption("_Aucune variable spécifique définie pour ce template._")
