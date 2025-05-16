import streamlit as st
from datetime import datetime, date
import copy
import json
import requests

# --- PAGE CONFIGURATION (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(layout="wide", page_title="🦸🏻Générateur & Bibliothèque de Prompts IA v3.2") 

# --- Initial Data Structure & Constants ---
CURRENT_YEAR = datetime.now().year 
GIST_DATA_FILENAME = "prompt_templates_data_v3.json"

def get_default_dates():
    now_iso = datetime.now().isoformat()
    return now_iso, now_iso

created_at_initial, updated_at_initial = get_default_dates()
INITIAL_PROMPT_TEMPLATES = {
    "Achat": {
        "Recherche de Fournisseurs": {
            "template": "Recherche dans la base de données quels sont les fournisseurs de {legume} les {critere_prix} entre l'année {annee_debut} et l'année {annee_fin}.",
            "variables": [
                {"name": "legume", "label": "Quel légume/produit recherchez-vous ?", "type": "text_input", "default": "tomates"},
                {"name": "critere_prix", "label": "Quel critère de prix ?", "type": "selectbox", "options": ["moins chers", "plus chers", "mieux notés"], "default": "moins chers"},
                {"name": "annee_debut", "label": "Année de début", "type": "selectbox", "options": list(range(CURRENT_YEAR - 5, CURRENT_YEAR + 1)), "default": CURRENT_YEAR -1 },
                {"name": "annee_fin", "label": "Année de fin", "type": "selectbox", "options": list(range(CURRENT_YEAR - 5, CURRENT_YEAR + 2)), "default": CURRENT_YEAR},
            ],
            "tags": ["recherche", "fournisseur", "interne"],
            "previous_template": "",
            "usage_count": 0,
            "created_at": created_at_initial,
            "updated_at": updated_at_initial
        },
        "Génération d'Email de Suivi Client": {
            "template": "Rédige un email de suivi pour {nom_client} concernant sa commande {num_commande} passée le {date_commande}. L'email doit avoir un ton {ton_email} et mentionner que nous attendons son retour sur {point_feedback}.",
            "variables": [
                {"name": "nom_client", "label": "Nom du client", "type": "text_input", "default": "M. Dupont"},
                {"name": "num_commande", "label": "Numéro de commande", "type": "text_input", "default": f"CMD{CURRENT_YEAR}00123"},
                {"name": "date_commande", "label": "Date de la commande", "type": "date_input", "default": date(CURRENT_YEAR, 1, 15)},
                {"name": "ton_email", "label": "Ton de l'email", "type": "selectbox", "options": ["professionnel", "amical", "formel", "enthousiaste"], "default": "professionnel"},
                {"name": "point_feedback", "label": "Point pour feedback", "type": "text_input", "default": "son expérience avec notre nouveau service"},
            ],
            "tags": ["email", "client", "communication"],
            "previous_template": "",
            "usage_count": 0,
            "created_at": created_at_initial,
            "updated_at": updated_at_initial
        },
        "Résumé de Document": {
            "template": "Résume le document suivant en {nombre_points} points clés pour un public de {public_cible}. Le résumé doit se concentrer sur les aspects de {focus_resume}. Le style de résumé doit être {style_resume}. Voici le texte à résumer : \n\n{texte_document}",
            "variables": [
                {"name": "nombre_points", "label": "Nombre de points clés", "type": "number_input", "default": 3, "min_value":1, "max_value":10, "step":1},
                {"name": "public_cible", "label": "Public cible", "type": "selectbox", "options": ["direction", "équipe technique", "clients", "partenaires", "grand public"], "default": "direction"},
                {"name": "focus_resume", "label": "Focus principal", "type": "selectbox", "options": ["aspects techniques", "impacts financiers", "prochaines étapes", "conclusions principales", "avantages concurrentiels"], "default": "conclusions principales"},
                {"name": "style_resume", "label": "Style du résumé", "type": "selectbox", "options": ["concis et direct", "détaillé", "orienté action", "informatif neutre"], "default": "concis et direct"},
                {"name": "texte_document", "label": "Texte à résumer", "type": "text_area", "height": 200, "default": "Collez le texte ici..."},
            ],
            "tags": ["résumé", "analyse", "document"],
            "previous_template": "",
            "usage_count": 0,
            "created_at": created_at_initial,
            "updated_at": updated_at_initial
        }
    },
    "RH": {},
    "Finance": {},
    "Comptabilité": {}
}
# Ensure all initial templates are updated to remove "is_favorite" if it was missed
for family, use_cases in INITIAL_PROMPT_TEMPLATES.items():
    if isinstance(use_cases, dict):
        for uc_name, uc_config in use_cases.items():
            if "is_favorite" in uc_config: # Should not be there based on above, but defensive
                del uc_config["is_favorite"]


# --- Utility Functions ---
def parse_default_value(value_str, var_type):
    if not value_str: 
        if var_type == "number_input": return 0
        if var_type == "date_input": return datetime.now().date()
        return "" 
    if var_type == "number_input":
        try: return int(value_str)
        except ValueError: return 0
    elif var_type == "date_input":
        try: return datetime.strptime(value_str, "%Y-%m-%d").date()
        except (ValueError, TypeError): 
            return value_str if isinstance(value_str, date) else datetime.now().date()
    return value_str 

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
            for var_info in config.get("variables", []): # Iterate on potentially fixed list
                if isinstance(var_info, dict) and var_info.get("type") == "date_input" and isinstance(var_info.get("default"), date):
                    var_info["default"] = var_info["default"].strftime("%Y-%m-%d")
            
            config.setdefault("tags", [])
            config.setdefault("previous_template", "")
            if "is_favorite" in config: # Clean up old data if it exists
                del config["is_favorite"]
            config.setdefault("usage_count", 0)
            config.setdefault("created_at", datetime.now().isoformat())
            config.setdefault("updated_at", datetime.now().isoformat())
    return processed_data

def _postprocess_after_loading(loaded_data):
    processed_data = copy.deepcopy(loaded_data)
    now_iso = datetime.now().isoformat()
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

            for var_info in config.get("variables", []):
                if isinstance(var_info, dict) and var_info.get("type") == "date_input" and isinstance(var_info.get("default"), str):
                    try:
                        var_info["default"] = datetime.strptime(var_info["default"], "%Y-%m-%d").date()
                    except ValueError:
                        var_info["default"] = datetime.now().date() 
            
            config.setdefault("tags", [])
            config.setdefault("previous_template", "")
            if "is_favorite" in config: 
                del config["is_favorite"]
            config.setdefault("usage_count", 0)
            config.setdefault("created_at", now_iso) 
            config.setdefault("updated_at", now_iso) 
            if not isinstance(config.get("tags"), list): config["tags"] = [] 
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
            st.info(f"Fichier '{GIST_DATA_FILENAME}' non trouvé dans Gist. Initialisation.")
            return "{}"
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur Gist (get): {e}")
        return None
    except KeyError:
        st.error(f"Erreur Gist (get): Fichier '{GIST_DATA_FILENAME}' non trouvé ou structure Gist inattendue.")
        return None

def update_gist_content(gist_id, github_pat, new_content_json_string):
    headers = {"Authorization": f"token {github_pat}", "Accept": "application/vnd.github.v3+json"}
    data = {"files": {GIST_DATA_FILENAME: {"content": new_content_json_string}}}
    try:
        response = requests.patch(f"https://api.github.com/gists/{gist_id}", headers=headers, json=data)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur Gist (update): {e}")
        return False

def save_editable_prompts_to_gist():
    GIST_ID = st.secrets.get("GIST_ID")
    GITHUB_PAT = st.secrets.get("GITHUB_PAT")
    if not GIST_ID or not GITHUB_PAT:
        st.error("Secrets Gist manquants (GIST_ID/GITHUB_PAT). Sauvegarde impossible.")
        return
    if 'editable_prompts' in st.session_state:
        data_to_save = _preprocess_for_saving(st.session_state.editable_prompts)
        try:
            json_string = json.dumps(data_to_save, indent=4, ensure_ascii=False)
            if not update_gist_content(GIST_ID, GITHUB_PAT, json_string):
                st.warning("Sauvegarde Gist échouée.")
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
    data_to_save = _preprocess_for_saving(initial_data) 
    try:
        json_string = json.dumps(data_to_save, indent=4, ensure_ascii=False)
        if update_gist_content(GIST_ID, GITHUB_PAT, json_string):
            st.info("Modèles par défaut sauvegardés sur Gist pour initialisation.")
    except Exception as e:
        st.error(f"Erreur sauvegarde initiale sur Gist: {e}")
    return initial_data

# --- Session State Initialization ---
if 'editable_prompts' not in st.session_state:
    st.session_state.editable_prompts = load_editable_prompts_from_gist()

if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "library"
    default_library_family_on_start = "Achat"
    available_families_on_load = list(st.session_state.editable_prompts.keys())
    if default_library_family_on_start in available_families_on_load:
        st.session_state.library_selected_family_for_display = default_library_family_on_start
    elif available_families_on_load:
        st.session_state.library_selected_family_for_display = available_families_on_load[0]
    else:
        st.session_state.library_selected_family_for_display = None

if 'family_selector_edition' not in st.session_state:
    families_for_edit_init = list(st.session_state.editable_prompts.keys())
    st.session_state.family_selector_edition = families_for_edit_init[0] if families_for_edit_init else None

if 'use_case_selector_edition' not in st.session_state:
    st.session_state.use_case_selector_edition = None
    if st.session_state.family_selector_edition and \
       st.session_state.family_selector_edition in st.session_state.editable_prompts and \
       st.session_state.editable_prompts[st.session_state.family_selector_edition]:
        try:
            first_uc_in_family = list(st.session_state.editable_prompts[st.session_state.family_selector_edition].keys())[0]
            st.session_state.use_case_selector_edition = first_uc_in_family
        except IndexError:
            pass

if 'library_selected_family_for_display' not in st.session_state: 
    st.session_state.library_selected_family_for_display = None

if 'editing_variable_info' not in st.session_state:
    st.session_state.editing_variable_info = None
if 'show_create_new_use_case_form' not in st.session_state:
    st.session_state.show_create_new_use_case_form = False
if 'force_select_family_name' not in st.session_state:
    st.session_state.force_select_family_name = None
if 'force_select_use_case_name' not in st.session_state:
    st.session_state.force_select_use_case_name = None
if 'confirming_delete_details' not in st.session_state: 
    st.session_state.confirming_delete_details = None
if 'confirming_delete_family_name' not in st.session_state: 
    st.session_state.confirming_delete_family_name = None

if 'library_search_term' not in st.session_state:
    st.session_state.library_search_term = ""
if 'library_selected_tags' not in st.session_state:
    st.session_state.library_selected_tags = []

# --- Main App UI ---
st.title(f"🦸🏻Générateur & Bibliothèque de Prompts IA v3.2")

# --- Sidebar Navigation with Tabs ---
st.sidebar.header("Menu Principal")
tab_bibliotheque, tab_edition_generation = st.sidebar.tabs(["📚 Bibliothèque", "✍️ Génération & Édition"])

# --- Tab: Édition & Génération ---
with tab_edition_generation: 
    st.subheader("Explorateur et Création de Prompts")
    available_families = list(st.session_state.editable_prompts.keys())
    
    default_family_idx_edit = 0
    current_family_for_edit = st.session_state.get('family_selector_edition')

    if st.session_state.force_select_family_name and st.session_state.force_select_family_name in available_families:
        default_family_idx_edit = available_families.index(st.session_state.force_select_family_name)
        current_family_for_edit = st.session_state.force_select_family_name
    elif current_family_for_edit and current_family_for_edit in available_families:
        default_family_idx_edit = available_families.index(current_family_for_edit)
    elif available_families:
        default_family_idx_edit = 0
        current_family_for_edit = available_families[0]
    else: 
        current_family_for_edit = None

    st.session_state.family_selector_edition = current_family_for_edit

    if not available_families:
        st.info("Aucune famille de cas d'usage configurée. Vous pouvez en créer une ci-dessous.")
    else:
        prev_family_selection_edit = st.session_state.get('family_selector_edition')
        selected_family_ui_edit = st.selectbox(
            "Famille :",
            options=available_families,
            index=default_family_idx_edit if current_family_for_edit else 0, 
            key='family_selectbox_widget_edit',
            help="Sélectionnez une famille pour voir ses cas d'usage."
        )
        st.session_state.family_selector_edition = selected_family_ui_edit

        if prev_family_selection_edit != selected_family_ui_edit:
            st.session_state.use_case_selector_edition = None
            st.session_state.force_select_use_case_name = None
            st.session_state.force_select_family_name = None
            st.session_state.view_mode = "edit" 
            st.rerun()

    current_selected_family_for_edit_logic = st.session_state.get('family_selector_edition')
    use_cases_in_current_family_edit_options = []
    if current_selected_family_for_edit_logic and current_selected_family_for_edit_logic in st.session_state.editable_prompts:
        use_cases_in_current_family_edit_options = list(st.session_state.editable_prompts[current_selected_family_for_edit_logic].keys())

    if use_cases_in_current_family_edit_options:
        default_uc_idx_edit = 0
        current_uc_for_edit = st.session_state.get('use_case_selector_edition')

        if st.session_state.force_select_use_case_name and st.session_state.force_select_use_case_name in use_cases_in_current_family_edit_options:
            default_uc_idx_edit = use_cases_in_current_family_edit_options.index(st.session_state.force_select_use_case_name)
            current_uc_for_edit = st.session_state.force_select_use_case_name
        elif current_uc_for_edit and current_uc_for_edit in use_cases_in_current_family_edit_options:
            default_uc_idx_edit = use_cases_in_current_family_edit_options.index(current_uc_for_edit)
        elif use_cases_in_current_family_edit_options: 
            current_uc_for_edit = use_cases_in_current_family_edit_options[0]
            default_uc_idx_edit = 0
        
        st.session_state.use_case_selector_edition = current_uc_for_edit

        prev_uc_selection_edit = current_uc_for_edit 
        selected_use_case_ui_edit = st.radio(
            "Cas d'usage :",
            options=use_cases_in_current_family_edit_options,
            index=default_uc_idx_edit,
            key='use_case_radio_widget_edit',
            help="Sélectionnez un cas d'usage pour générer un prompt ou le paramétrer."
        )
        st.session_state.use_case_selector_edition = selected_use_case_ui_edit

        if prev_uc_selection_edit != selected_use_case_ui_edit:
            st.session_state.force_select_use_case_name = None
            st.session_state.view_mode = "edit" 
            st.rerun()
            
    elif current_selected_family_for_edit_logic: 
        st.info(f"Aucun cas d'usage dans '{current_selected_family_for_edit_logic}'.")
        st.session_state.use_case_selector_edition = None 

    if st.session_state.force_select_family_name: st.session_state.force_select_family_name = None
    if st.session_state.force_select_use_case_name: st.session_state.force_select_use_case_name = None
    st.markdown("---")
    
    with st.expander("🗂️ Gérer les Familles et Cas d'Usage", expanded=False):
        st.subheader("Gérer les Familles")
        with st.form("new_family_form", clear_on_submit=True):
            new_family_name = st.text_input("Nom de la nouvelle famille:")
            submitted_new_family = st.form_submit_button("➕ Créer Famille")
            if submitted_new_family and new_family_name.strip():
                if new_family_name.strip() in st.session_state.editable_prompts:
                    st.error(f"La famille '{new_family_name.strip()}' existe déjà.")
                else:
                    st.session_state.editable_prompts[new_family_name.strip()] = {}
                    save_editable_prompts_to_gist()
                    st.success(f"Famille '{new_family_name.strip()}' créée.")
                    st.session_state.force_select_family_name = new_family_name.strip() 
                    st.session_state.view_mode = "edit"
                    st.rerun()
            elif submitted_new_family:
                st.error("Le nom de la famille ne peut pas être vide.")

        if available_families and current_selected_family_for_edit_logic : 
            st.markdown("---")
            with st.form("rename_family_form"): 
                st.write(f"Renommer la famille actuelle : **{current_selected_family_for_edit_logic}**")
                renamed_family_name = st.text_input("Nouveau nom pour la famille:", value=current_selected_family_for_edit_logic)
                submitted_rename_family = st.form_submit_button("✏️ Renommer Famille")
                if submitted_rename_family and renamed_family_name.strip():
                    if renamed_family_name.strip() == current_selected_family_for_edit_logic:
                        st.info("Le nouveau nom est identique à l'ancien.")
                    elif renamed_family_name.strip() in st.session_state.editable_prompts:
                        st.error(f"Une famille nommée '{renamed_family_name.strip()}' existe déjà.")
                    else:
                        st.session_state.editable_prompts[renamed_family_name.strip()] = st.session_state.editable_prompts.pop(current_selected_family_for_edit_logic)
                        save_editable_prompts_to_gist()
                        st.success(f"Famille '{current_selected_family_for_edit_logic}' renommée en '{renamed_family_name.strip()}'.")
                        st.session_state.force_select_family_name = renamed_family_name.strip()
                        if st.session_state.library_selected_family_for_display == current_selected_family_for_edit_logic:
                           st.session_state.library_selected_family_for_display = renamed_family_name.strip()
                        st.session_state.view_mode = "edit"
                        st.rerun()
                elif submitted_rename_family:
                    st.error("Le nouveau nom de la famille ne peut pas être vide.")
            
            st.markdown("---")
            st.write(f"Supprimer la famille actuelle : **{current_selected_family_for_edit_logic}**")
            if st.session_state.confirming_delete_family_name == current_selected_family_for_edit_logic:
                st.warning(f"Êtes-vous sûr de vouloir supprimer la famille '{current_selected_family_for_edit_logic}' et tous ses cas d'usage ? Cette action est irréversible.")
                del_fam_col1, del_fam_col2, _ = st.columns([1,1,3])
                if del_fam_col1.button(f"Oui, supprimer '{current_selected_family_for_edit_logic}'", type="primary", key=f"confirm_del_fam_{current_selected_family_for_edit_logic}"):
                    del st.session_state.editable_prompts[current_selected_family_for_edit_logic]
                    save_editable_prompts_to_gist()
                    st.success(f"Famille '{current_selected_family_for_edit_logic}' supprimée.")
                    st.session_state.confirming_delete_family_name = None
                    st.session_state.family_selector_edition = None 
                    st.session_state.use_case_selector_edition = None
                    if st.session_state.library_selected_family_for_display == current_selected_family_for_edit_logic:
                        st.session_state.library_selected_family_for_display = None
                    st.session_state.view_mode = "edit"
                    st.rerun()
                if del_fam_col2.button("Non, annuler la suppression", key=f"cancel_del_fam_{current_selected_family_for_edit_logic}"):
                    st.session_state.confirming_delete_family_name = None
                    st.session_state.view_mode = "edit"
                    st.rerun()
            else:
                if st.button(f"🗑️ Supprimer Famille '{current_selected_family_for_edit_logic}'", key=f"del_fam_btn_{current_selected_family_for_edit_logic}"):
                    st.session_state.confirming_delete_family_name = current_selected_family_for_edit_logic
                    st.session_state.view_mode = "edit"
                    st.rerun()
        elif not available_families:
            st.caption("Créez une famille pour commencer à la gérer.")
        else: 
            st.caption("Sélectionnez une famille ci-dessus pour la gérer.")
        
        st.markdown("---")
        st.subheader("Créer un Cas d'Usage")
        if available_families:
            if st.button("➕ Afficher/Masquer Formulaire de Création de Cas d'Usage", key="toggle_create_form_btn_tab_edition_exp"):
                st.session_state.show_create_new_use_case_form = not st.session_state.show_create_new_use_case_form
                if not st.session_state.show_create_new_use_case_form: 
                    st.session_state.view_mode = "edit"
                    st.rerun()
        else: 
            st.markdown("*(Veuillez d'abord créer une famille pour pouvoir y ajouter des cas d'usage.)*")

        if st.session_state.show_create_new_use_case_form and available_families:
            with st.form("new_use_case_form_tab_edition_exp", clear_on_submit=True):
                default_create_family_idx_tab = 0
                if st.session_state.family_selector_edition and st.session_state.family_selector_edition in available_families:
                        default_create_family_idx_tab = available_families.index(st.session_state.family_selector_edition)
                
                uc_parent_family = st.selectbox(
                    "Famille Parente:", 
                    options=available_families, 
                    index=default_create_family_idx_tab, 
                    key="new_uc_parent_family_widget_exp"
                )
                uc_name = st.text_input("Nom du Cas d'Usage:", key="new_uc_name_widget_exp")
                uc_template = st.text_area("Template Initial:", height=100, key="new_uc_template_widget_exp", value="Nouveau prompt...")
                submitted_new_uc = st.form_submit_button("Créer Cas d'Usage")

                if submitted_new_uc:
                    parent_family_val = uc_parent_family 
                    uc_name_val = uc_name
                    uc_template_val = uc_template

                    if not uc_name_val.strip(): st.error("Nom du cas d'usage requis.")
                    elif uc_name_val in st.session_state.editable_prompts.get(parent_family_val, {}):
                        st.error(f"Le cas d'usage '{uc_name_val}' existe déjà dans la famille '{parent_family_val}'.")
                    else:
                        now_iso_create, now_iso_update = get_default_dates()
                        st.session_state.editable_prompts[parent_family_val][uc_name_val] = {
                            "template": uc_template_val or "Nouveau prompt...", 
                            "variables": [],
                            "tags": [],
                            "previous_template": "",
                            "usage_count": 0,
                            "created_at": now_iso_create,
                            "updated_at": now_iso_update
                        }
                        save_editable_prompts_to_gist()
                        st.success(f"Cas d'usage '{uc_name_val}' créé dans la famille '{parent_family_val}'.")
                        st.session_state.show_create_new_use_case_form = False
                        st.session_state.force_select_family_name = parent_family_val
                        st.session_state.force_select_use_case_name = uc_name_val
                        st.session_state.view_mode = "edit"
                        st.rerun()

# --- Tab: Bibliothèque ---
with tab_bibliotheque:
    st.subheader("Explorer la Bibliothèque de Prompts")
    search_col, filter_tag_col = st.columns(2)
    with search_col:
        st.session_state.library_search_term = st.text_input(
            "🔍 Rechercher par mot-clé:", 
            value=st.session_state.library_search_term,
            placeholder="Nom, template, variable..."
        )
    
    all_tags_list = sorted(list(set(tag for family in st.session_state.editable_prompts.values() for uc in family.values() for tag in uc.get("tags", []))))
    with filter_tag_col: 
        st.session_state.library_selected_tags = st.multiselect(
            "🏷️ Filtrer par Tags:",
            options=all_tags_list,
            default=st.session_state.library_selected_tags
        )
    st.markdown("---")

    if not st.session_state.editable_prompts or not any(st.session_state.editable_prompts.values()):
        st.info("La bibliothèque est vide. Ajoutez des prompts via l'onglet 'Génération & Édition'.")
    else:
        sorted_families_bib = sorted(list(st.session_state.editable_prompts.keys()))
        
        if not st.session_state.get('library_selected_family_for_display') or \
           st.session_state.library_selected_family_for_display not in sorted_families_bib:
            st.session_state.library_selected_family_for_display = sorted_families_bib[0] if sorted_families_bib else None

        st.write("Sélectionner une famille à afficher :")
        
        for family_name_bib in sorted_families_bib:
            button_key = f"lib_family_btn_{family_name_bib.replace(' ', '_').replace('&', '_')}"
            is_selected_family = (st.session_state.library_selected_family_for_display == family_name_bib)
            if st.button( 
                family_name_bib, 
                key=button_key, 
                use_container_width=True, 
                type="primary" if is_selected_family else "secondary"
            ):
                st.session_state.view_mode = "library" 
                st.session_state.library_selected_family_for_display = family_name_bib
                st.rerun()
        st.markdown("---") 

# --- Final selections from session state for main page logic ---
final_selected_family_edition = st.session_state.get('family_selector_edition')
final_selected_use_case_edition = st.session_state.get('use_case_selector_edition')
library_family_to_display = st.session_state.get('library_selected_family_for_display')

# --- Main Display Area ---
if 'view_mode' not in st.session_state: 
    st.session_state.view_mode = "library" if library_family_to_display else "edit"

if st.session_state.view_mode == "library" and library_family_to_display:
    st.header(f"Bibliothèque - Famille : {library_family_to_display}")
    
    use_cases_in_family_display = st.session_state.editable_prompts.get(library_family_to_display, {})
    
    filtered_use_cases = {}
    if use_cases_in_family_display:
        for uc_name, uc_config in use_cases_in_family_display.items():
            match_search = True
            if st.session_state.library_search_term.strip():
                term = st.session_state.library_search_term.strip().lower()
                match_search = (term in uc_name.lower() or
                                term in uc_config.get("template", "").lower() or
                                any(term in var.get("name","").lower() or term in var.get("label","").lower() for var in uc_config.get("variables", [])))

            match_tags = True
            if st.session_state.library_selected_tags:
                match_tags = all(tag in uc_config.get("tags", []) for tag in st.session_state.library_selected_tags)
            
            if match_search and match_tags: 
                filtered_use_cases[uc_name] = uc_config
    
    if not filtered_use_cases:
        if not use_cases_in_family_display:
             st.info(f"La famille '{library_family_to_display}' ne contient actuellement aucun prompt.")
        else:
            st.info("Aucun prompt ne correspond à vos critères de recherche/filtre dans cette famille.")
    else:
        sorted_use_cases_display = sorted(list(filtered_use_cases.keys()))
        for use_case_name_display in sorted_use_cases_display:
            prompt_config_display = filtered_use_cases[use_case_name_display]
            template_display = prompt_config_display.get("template", "_Template non défini._")
            
            exp_title = f"{use_case_name_display}"
            if prompt_config_display.get("usage_count", 0) > 0: 
                exp_title += f" (Utilisé {prompt_config_display.get('usage_count')} fois)"

            with st.expander(exp_title, expanded=False):
                st.markdown(f"##### Template pour : {use_case_name_display}")
                st.code(template_display, language=None)
                
                variables_display = prompt_config_display.get("variables", [])
                if variables_display:
                    st.markdown("**Variables associées:**")
                    var_details_list_display = [f"- `{v.get('name', 'N/A')}` ({v.get('label', 'N/A')})" for v in variables_display if isinstance(v, dict)]
                    if var_details_list_display: st.markdown("\n".join(var_details_list_display))
                    else: st.caption("_Aucune variable correctement définie._")
                else: st.caption("_Aucune variable spécifique définie._")

                tags_display = prompt_config_display.get("tags", [])
                if tags_display:
                    st.markdown(f"**Tags :** {', '.join([f'`{tag}`' for tag in tags_display])}")
                
                st.caption(f"Créé le: {datetime.fromisoformat(prompt_config_display.get('created_at', get_default_dates()[0])).strftime('%d/%m/%Y %H:%M')} | Modifié le: {datetime.fromisoformat(prompt_config_display.get('updated_at', get_default_dates()[1])).strftime('%d/%m/%Y %H:%M')}")

# --- Main Display for Génération & Édition View ---
elif st.session_state.view_mode == "edit" and \
     final_selected_family_edition and final_selected_use_case_edition and \
     final_selected_family_edition in st.session_state.editable_prompts and \
     final_selected_use_case_edition in st.session_state.editable_prompts[final_selected_family_edition]:
    
    current_prompt_config = st.session_state.editable_prompts[final_selected_family_edition][final_selected_use_case_edition]
    
    st.header(f"Cas d'usage: {final_selected_use_case_edition}") 
    st.caption(f"Famille: {final_selected_family_edition} | Utilisé {current_prompt_config.get('usage_count', 0)} fois. Créé: {datetime.fromisoformat(current_prompt_config.get('created_at', get_default_dates()[0])).strftime('%d/%m/%Y')}, Modifié: {datetime.fromisoformat(current_prompt_config.get('updated_at', get_default_dates()[1])).strftime('%d/%m/%Y')}")
    st.markdown("---")

    st.subheader(f"🚀 Générer Prompt") 
    gen_form_values = {} 
    with st.form(key=f"gen_form_{final_selected_family_edition}_{final_selected_use_case_edition}"):
        if not current_prompt_config["variables"]: st.info("Ce cas d'usage n'a pas de variables configurées pour la génération.")
        
        cols_per_row = 2 if len(current_prompt_config["variables"]) > 1 else 1
        var_chunks = [current_prompt_config["variables"][i:i + cols_per_row] for i in range(0, len(current_prompt_config["variables"]), cols_per_row)]
        
        for chunk in var_chunks:
            cols = st.columns(len(chunk))
            for i, var_info in enumerate(chunk):
                with cols[i]:
                    widget_key = f"gen_input_{final_selected_family_edition}_{final_selected_use_case_edition}_{var_info['name']}"
                    field_default = var_info.get("default") 

                    if var_info["type"] == "text_input":
                        gen_form_values[var_info["name"]] = st.text_input(var_info["label"], value=str(field_default or ""), key=widget_key)
                    elif var_info["type"] == "selectbox":
                        opts = var_info.get("options", [])
                        try: 
                            idx = opts.index(field_default) if field_default in opts else (0 if opts else -1)
                        except ValueError: 
                            idx = 0 if opts else -1
                        
                        if idx != -1: 
                            gen_form_values[var_info["name"]] = st.selectbox(var_info["label"], options=opts, index=idx, key=widget_key)
                        else: 
                            st.markdown(f"_{var_info['label']}: (Configuration Selectbox Invalide - Pas d'options)_")
                            gen_form_values[var_info["name"]] = None 
                    elif var_info["type"] == "date_input":
                        val_date = field_default if isinstance(field_default, date) else datetime.now().date() 
                        gen_form_values[var_info["name"]] = st.date_input(var_info["label"], value=val_date, key=widget_key)
                    elif var_info["type"] == "number_input":
                        val_num = field_default if isinstance(field_default, (int,float)) else 0 
                        gen_form_values[var_info["name"]] = st.number_input(var_info["label"], value=val_num, 
                                                                        min_value=var_info.get("min_value"), 
                                                                        max_value=var_info.get("max_value"), 
                                                                        step=var_info.get("step",1), key=widget_key)
                    elif var_info["type"] == "text_area":
                        gen_form_values[var_info["name"]] = st.text_area(var_info["label"], value=str(field_default or ""), 
                                                                     height=var_info.get("height",100), key=widget_key)
        
        if st.form_submit_button("🚀 Générer Prompt"):
            final_vals_for_prompt = {
                k: (v.strftime("%d/%m/%Y") if isinstance(v, date) else v) 
                for k, v in gen_form_values.items() if v is not None
            }
            try:
                class SafeFormatter(dict): 
                    def __missing__(self, key): return f"{{{key}}}" 
                
                generated_prompt = current_prompt_config["template"].format_map(SafeFormatter(final_vals_for_prompt))
                st.subheader("✅ Prompt Généré:") 
                st.code(generated_prompt, language=None) 
                st.success("Prompt généré avec succès!")
                st.balloons()
                
                current_prompt_config["usage_count"] = current_prompt_config.get("usage_count", 0) + 1
                current_prompt_config["updated_at"] = datetime.now().isoformat() 
                save_editable_prompts_to_gist()

            except Exception as e: st.error(f"Erreur lors de la génération du prompt: {e}")
    st.markdown("---") 

    if st.session_state.confirming_delete_details and \
       st.session_state.confirming_delete_details["family"] == final_selected_family_edition and \
       st.session_state.confirming_delete_details["use_case"] == final_selected_use_case_edition:
        details = st.session_state.confirming_delete_details
        st.warning(f"Supprimer '{details['use_case']}' de '{details['family']}' ? Action irréversible.")
        c1, c2, _ = st.columns([1,1,3])
        if c1.button(f"Oui, supprimer '{details['use_case']}'", key=f"del_yes_{details['family']}_{details['use_case']}", type="primary"):
            del st.session_state.editable_prompts[details["family"]][details["use_case"]]
            save_editable_prompts_to_gist()
            st.success(f"'{details['use_case']}' supprimé de '{details['family']}'.")
            st.session_state.confirming_delete_details = None
            st.session_state.force_select_family_name = details["family"] 
            st.session_state.force_select_use_case_name = None 
            if st.session_state.editing_variable_info and \
               st.session_state.editing_variable_info.get("family") == details["family"] and \
               st.session_state.editing_variable_info.get("use_case") == details["use_case"]:
                st.session_state.editing_variable_info = None
            st.session_state.view_mode = "edit"
            st.rerun()
        if c2.button("Non, annuler", key=f"del_no_{details['family']}_{details['use_case']}"):
            st.session_state.confirming_delete_details = None
            st.session_state.view_mode = "edit"
            st.rerun()
        st.markdown("---")

    with st.expander(f"⚙️ Paramétrage du Prompt: {final_selected_use_case_edition}", expanded=False): 
        st.subheader("Template du Prompt")
        tpl_key = f"tpl_{final_selected_family_edition}_{final_selected_use_case_edition}"
        new_tpl = st.text_area("Template:", value=current_prompt_config['template'], height=200, key=tpl_key) 
        
        defined_vars_for_template = [f"{{{var_info['name']}}}" for var_info in current_prompt_config.get('variables', [])]
        if defined_vars_for_template:
            st.caption(f"Variables disponibles à insérer: {', '.join(defined_vars_for_template)}")
        else:
            st.caption("Aucune variable définie pour ce prompt. Ajoutez-en ci-dessous.")

        if st.button("Sauvegarder Template", key=f"save_tpl_{tpl_key}"):
            if new_tpl != current_prompt_config['template']:
                current_prompt_config['previous_template'] = current_prompt_config['template']
            current_prompt_config['template'] = new_tpl
            current_prompt_config["updated_at"] = datetime.now().isoformat()
            save_editable_prompts_to_gist()
            st.success("Template sauvegardé!")
            st.session_state.view_mode = "edit" 
            st.rerun()

        if current_prompt_config.get('previous_template'):
            st.markdown("---")
            st.subheader("Version Précédente du Template")
            st.code(current_prompt_config['previous_template'], language=None)
            if st.button("Restaurer la version précédente", key=f"restore_prev_tpl_{tpl_key}"):
                current_prompt_config['template'] = current_prompt_config['previous_template']
                current_prompt_config["updated_at"] = datetime.now().isoformat()
                save_editable_prompts_to_gist()
                st.success("Version précédente restaurée!")
                st.session_state.view_mode = "edit"
                st.rerun()
        
        st.markdown("---")
        st.subheader("🏷️ Tags")
        current_tags_str = ", ".join(current_prompt_config.get("tags", []))
        new_tags_str = st.text_input(
            "Tags (séparés par des virgules):", 
            value=current_tags_str, 
            key=f"tags_{final_selected_family_edition}_{final_selected_use_case_edition}"
        )
        if st.button("Sauvegarder Tags", key=f"save_tags_{tpl_key}"):
            current_prompt_config["tags"] = sorted(list(set(t.strip() for t in new_tags_str.split(',') if t.strip())))
            current_prompt_config["updated_at"] = datetime.now().isoformat()
            save_editable_prompts_to_gist()
            st.success("Tags sauvegardés!")
            st.session_state.view_mode = "edit"
            st.rerun()

        st.markdown("---")
        st.subheader("Variables du Prompt")
        if not current_prompt_config['variables']: st.info("Aucune variable définie.")
        for idx, var_data in enumerate(list(current_prompt_config['variables'])): 
            var_disp_key = f"var_disp_{final_selected_family_edition}_{final_selected_use_case_edition}_{idx}"
            col1, col2, col3 = st.columns([4,1,1])
            col1.markdown(f"**{var_data['name']}** ({var_data['label']}) - Type: `{var_data['type']}`")
            if col2.button("Modifier", key=f"edit_var_{var_disp_key}"):
                st.session_state.editing_variable_info = {"family": final_selected_family_edition, "use_case": final_selected_use_case_edition, "index": idx, "data": copy.deepcopy(var_data)}
                st.session_state.view_mode = "edit"
                st.rerun()
            if col3.button("Suppr.", key=f"del_var_{var_disp_key}"):
                st.session_state.editable_prompts[final_selected_family_edition][final_selected_use_case_edition]['variables'].pop(idx)
                current_prompt_config["updated_at"] = datetime.now().isoformat() 
                if st.session_state.editing_variable_info and \
                   st.session_state.editing_variable_info.get("index") == idx and \
                   st.session_state.editing_variable_info.get("use_case") == final_selected_use_case_edition and \
                   st.session_state.editing_variable_info.get("family") == final_selected_family_edition:
                    st.session_state.editing_variable_info = None
                save_editable_prompts_to_gist()
                st.session_state.view_mode = "edit"
                st.rerun()
        
        st.markdown("---")
        is_editing_var = False
        form_var_key_base = f"form_var_{final_selected_family_edition}_{final_selected_use_case_edition}"
        var_submit_label = "Ajouter Variable"
        var_form_header = "Ajouter Nouvelle Variable"
        var_defaults = {"name": "", "label": "", "type": "text_input", "options": "", "default": ""}

        if st.session_state.editing_variable_info and \
           st.session_state.editing_variable_info.get("family") == final_selected_family_edition and \
           st.session_state.editing_variable_info.get("use_case") == final_selected_use_case_edition:
            edit_var_idx = st.session_state.editing_variable_info["index"]
            if edit_var_idx < len(st.session_state.editable_prompts[final_selected_family_edition][final_selected_use_case_edition].get('variables',[])):
                is_editing_var = True
                var_form_header = f"Modifier Variable: {st.session_state.editing_variable_info['data'].get('name', '')}"
                var_submit_label = "Sauvegarder Modifications"
                var_defaults.update(st.session_state.editing_variable_info['data']) 
                var_defaults["options"] = ", ".join(st.session_state.editing_variable_info['data'].get("options", []))
                raw_def = st.session_state.editing_variable_info['data'].get("default")
                var_defaults["default"] = raw_def.strftime("%Y-%m-%d") if isinstance(raw_def, date) else str(raw_def or "")
                form_var_key_base += f"_edit_{edit_var_idx}" 
            else: 
                st.session_state.editing_variable_info = None
                st.warning("La variable que vous éditiez a été supprimée ou modifiée. Veuillez réessayer.")
                st.rerun()

        with st.form(key=form_var_key_base, clear_on_submit=not is_editing_var): 
            st.subheader(var_form_header)
            var_name = st.text_input("Nom technique de la variable (unique, sans espaces ni caractères spéciaux)", value=var_defaults["name"], key=f"{form_var_key_base}_name")
            var_label = st.text_input("Label pour l'utilisateur (description)", value=var_defaults["label"], key=f"{form_var_key_base}_label")
            
            var_type_opts = ["text_input", "selectbox", "date_input", "number_input", "text_area"]
            var_type_idx = var_type_opts.index(var_defaults["type"]) if var_defaults["type"] in var_type_opts else 0
            var_type_key = f"{form_var_key_base}_type" # Key for the selectbox
            var_options_key = f"{form_var_key_base}_options" # Key for the options input

            var_type = st.selectbox(
                "Type de variable", 
                var_type_opts, 
                index=var_type_idx, 
                key=var_type_key
            )
            
            options_placeholder = st.empty() # Placeholder for conditional options input

            if var_type == "selectbox":
                with options_placeholder.container():
                    st.text_input( 
                        "Options (séparées par virgule)", 
                        value=var_defaults.get("options", ""), 
                        key=var_options_key
                    )
            # else: # Optionnel: vider explicitement si le type change
            #    options_placeholder.empty()

            var_default_val_str = st.text_input(
                "Valeur par défaut (optionnel, format finalList-MM-DD pour dates)", 
                value=var_defaults["default"], 
                key=f"{form_var_key_base}_default"
            )

            if st.form_submit_button(var_submit_label):
                actual_options_val_str = ""
                if var_type == "selectbox":
                    if var_options_key in st.session_state: # Get value using the specific key
                        actual_options_val_str = st.session_state[var_options_key]
                
                if not var_name.strip() or not var_label.strip(): 
                    st.error("Le nom technique et le label de la variable sont requis.")
                elif not var_name.strip().isidentifier(): 
                    st.error("Le nom technique de la variable ne doit contenir que des lettres, chiffres et underscores, et ne pas commencer par un chiffre.")
                elif var_type == "selectbox" and not [opt.strip() for opt in actual_options_val_str.split(',') if opt.strip()]:
                    st.error("Pour un type 'selectbox', veuillez fournir les options (séparées par des virgules). Le champ ne peut pas être vide.")
                else:
                    new_var_data = {"name": var_name.strip(), "label": var_label.strip(), "type": var_type}
                    if var_type == "selectbox":
                        new_var_data["options"] = [opt.strip() for opt in actual_options_val_str.split(',') if opt.strip()]
                    
                    parsed_def = parse_default_value(var_default_val_str.strip(), var_type)
                    
                    if var_type == "selectbox":
                        if new_var_data.get("options"): 
                            if parsed_def not in new_var_data["options"]:
                                st.warning(f"La valeur par défaut '{parsed_def}' n'est pas dans les options fournies. La première option ('{new_var_data['options'][0]}') sera utilisée comme défaut.")
                                new_var_data["default"] = new_var_data["options"][0]
                            else:
                                new_var_data["default"] = parsed_def
                    else: 
                        new_var_data["default"] = parsed_def

                    if is_editing_var:
                        idx_to_edit = st.session_state.editing_variable_info["index"]
                        st.session_state.editable_prompts[final_selected_family_edition][final_selected_use_case_edition]['variables'][idx_to_edit] = new_var_data
                        st.success("Variable mise à jour.")
                        st.session_state.editing_variable_info = None 
                    else: 
                        existing_var_names = [v['name'] for v in current_prompt_config.get('variables', [])]
                        if new_var_data['name'] in existing_var_names:
                            st.error(f"Une variable nommée '{new_var_data['name']}' existe déjà pour ce prompt.")
                            # Ne pas continuer si le nom existe déjà
                        else:
                            st.session_state.editable_prompts[final_selected_family_edition][final_selected_use_case_edition]['variables'].append(new_var_data)
                            st.success("Variable ajoutée.")
                            current_prompt_config["updated_at"] = datetime.now().isoformat() 
                            save_editable_prompts_to_gist()
                            st.session_state.view_mode = "edit" 
                            st.rerun()
                    
                    # Sauvegarder et rerun uniquement si pas d'erreur de nom dupliqué en mode ajout
                    if not (not is_editing_var and new_var_data['name'] in existing_var_names):
                        current_prompt_config["updated_at"] = datetime.now().isoformat() 
                        save_editable_prompts_to_gist()
                        st.session_state.view_mode = "edit" 
                        st.rerun()
        
        if is_editing_var and st.session_state.editing_variable_info: 
            if st.button("Annuler Modification Variable", key=f"cancel_edit_var_{form_var_key_base}"):
                st.session_state.editing_variable_info = None
                st.session_state.view_mode = "edit"
                st.rerun()

        st.markdown("---")
        action_cols = st.columns(2)
        with action_cols[0]:
            dup_key = f"dup_uc_btn_{final_selected_family_edition}_{final_selected_use_case_edition}"
            if st.button("🔄 Dupliquer ce Cas d'Usage", key=dup_key):
                original_uc_name = final_selected_use_case_edition
                new_uc_name_base = f"{original_uc_name} (copie)"
                new_uc_name = new_uc_name_base
                copy_count = 1
                while new_uc_name in st.session_state.editable_prompts[final_selected_family_edition]:
                    new_uc_name = f"{new_uc_name_base} {copy_count}"
                    copy_count += 1
                
                st.session_state.editable_prompts[final_selected_family_edition][new_uc_name] = copy.deepcopy(current_prompt_config)
                now_iso_dup_create, now_iso_dup_update = get_default_dates()
                st.session_state.editable_prompts[final_selected_family_edition][new_uc_name]["created_at"] = now_iso_dup_create
                st.session_state.editable_prompts[final_selected_family_edition][new_uc_name]["updated_at"] = now_iso_dup_update
                st.session_state.editable_prompts[final_selected_family_edition][new_uc_name]["usage_count"] = 0 

                save_editable_prompts_to_gist()
                st.success(f"Cas d'usage '{original_uc_name}' dupliqué en '{new_uc_name}'.")
                st.session_state.force_select_family_name = final_selected_family_edition
                st.session_state.force_select_use_case_name = new_uc_name
                st.session_state.view_mode = "edit"
                st.rerun()

        with action_cols[1]:
            del_uc_key = f"del_uc_btn_{final_selected_family_edition}_{final_selected_use_case_edition}"
            disable_del_uc_button = bool(st.session_state.confirming_delete_details and \
                                    st.session_state.confirming_delete_details["family"] == final_selected_family_edition and \
                                    st.session_state.confirming_delete_details["use_case"] == final_selected_use_case_edition)
            if st.button("🗑️ Supprimer Cas d'Usage", key=del_uc_key, type="secondary", disabled=disable_del_uc_button):
                st.session_state.confirming_delete_details = {"family": final_selected_family_edition, "use_case": final_selected_use_case_edition}
                st.session_state.view_mode = "edit"
                st.rerun()

elif st.session_state.view_mode == "edit" and final_selected_family_edition and not final_selected_use_case_edition:
    st.info(f"Sélectionnez un cas d'usage dans la famille '{final_selected_family_edition}' ou créez-en un nouveau pour commencer.")
elif st.session_state.view_mode == "edit" and not final_selected_family_edition:
     st.info("Sélectionnez une famille et un cas d'usage dans la barre latérale (onglet Génération & Édition) ou créez-les pour commencer.")
else: 
    available_families_main = list(st.session_state.editable_prompts.keys()) 
    if not available_families_main:
       st.warning("Aucune famille de cas d'usage n'est configurée. Veuillez en créer une via l'onglet 'Génération & Édition' ou vérifier votre Gist.")
    else:
       st.info("Bienvenue ! Sélectionnez une option dans la barre latérale pour commencer. Par défaut, la vue Bibliothèque est affichée si des prompts existent.")
    
    if st.session_state.view_mode != "library" and st.session_state.view_mode != "edit":
        st.session_state.view_mode = "library" if library_family_to_display else "edit"


# --- Sidebar Footer ---
st.sidebar.markdown("---")
st.sidebar.info(f"Générateur v3.2 - © {CURRENT_YEAR} La Poste (démo)")
