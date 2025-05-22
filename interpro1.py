import streamlit as st
from datetime import datetime, date
import copy
import json
import requests

# --- PAGE CONFIGURATION (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(layout="wide", page_title="🧬Générateur & Bibliothèque de Prompts LaPoste - Fonctions Support")

# --- Initial Data Structure & Constants ---
CURRENT_YEAR = datetime.now().year
GIST_DATA_FILENAME = "prompt_templates_data_v3.json"

def get_default_dates():
    now_iso = datetime.now().isoformat()
    return now_iso, now_iso

created_at_initial, updated_at_initial = get_default_dates()
INITIAL_PROMPT_TEMPLATES = {
    "Achat": {},
    "RH": {},
    "Finance": {},
    "Comptabilité": {}
}
for family, use_cases in INITIAL_PROMPT_TEMPLATES.items():
    if isinstance(use_cases, dict):
        for uc_name, uc_config in use_cases.items():
            if "is_favorite" in uc_config:
                del uc_config["is_favorite"]

# --- Utility Functions ---
def parse_default_value(value_str, var_type): # MODIFIÉ pour number_input
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
        if not isinstance(use_cases_in_family, dict):
            st.error(f"Données corrompues (famille non-dict): '{family_name}'. Suppression.")
            del processed_data[family_name]
            continue
        for use_case_name in list(use_cases_in_family.keys()):
            config = use_cases_in_family[use_case_name]
            if not isinstance(config, dict):
                st.error(f"Données corrompues (cas d'usage non-dict): '{use_case_name}' dans '{family_name}'. Suppression.")
                del processed_data[family_name][use_case_name]
                continue
            if not isinstance(config.get("variables"), list):
                config["variables"] = []
            for var_info in config.get("variables", []):
                if isinstance(var_info, dict):
                    if var_info.get("type") == "date_input" and isinstance(var_info.get("default"), date):
                        var_info["default"] = var_info["default"].strftime("%Y-%m-%d")
                    # Assurer la cohérence des types pour number_input lors de la sauvegarde
                    if var_info.get("type") == "number_input":
                        if "default" in var_info and var_info["default"] is not None:
                            var_info["default"] = float(var_info["default"])
                        if "min_value" in var_info and var_info["min_value"] is not None:
                            var_info["min_value"] = float(var_info["min_value"])
                        if "max_value" in var_info and var_info["max_value"] is not None:
                            var_info["max_value"] = float(var_info["max_value"])
                        if "step" in var_info and var_info["step"] is not None:
                            var_info["step"] = float(var_info["step"])
                        else: # Assurer un step par défaut si non présent
                            var_info["step"] = 1.0


            config.setdefault("tags", [])
            if "is_favorite" in config:
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
            st.warning(f"Données corrompues (famille non-dict): '{family_name}'. Ignorée.")
            del processed_data[family_name]
            continue
        for use_case_name in list(use_cases_in_family.keys()):
            config = use_cases_in_family[use_case_name]
            if not isinstance(config, dict):
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
                    # Assurer la cohérence des types pour number_input lors du chargement
                    if var_info.get("type") == "number_input":
                        if "default" in var_info and var_info["default"] is not None:
                            var_info["default"] = float(var_info["default"])
                        else: # S'assurer qu'il y a une valeur par défaut si absente ou None
                            var_info["default"] = 0.0
                        if "min_value" in var_info and var_info["min_value"] is not None:
                            var_info["min_value"] = float(var_info["min_value"])
                        if "max_value" in var_info and var_info["max_value"] is not None:
                            var_info["max_value"] = float(var_info["max_value"])
                        if "step" in var_info and var_info["step"] is not None:
                            var_info["step"] = float(var_info["step"])
                        else: # Assurer un step par défaut si non présent
                            var_info["step"] = 1.0


            config.setdefault("tags", [])
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
    except KeyError: # pragma: no cover
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
            if not loaded_data or not isinstance(loaded_data, dict): # Check if it's a non-empty dict
                raise ValueError("Contenu Gist vide ou mal structuré.")
            return _postprocess_after_loading(loaded_data)
        except (json.JSONDecodeError, TypeError, ValueError) as e: # Added TypeError
            st.info(f"Erreur chargement Gist ({e}). Initialisation avec modèles par défaut.")
    else: # raw_content is None or empty string
        st.info("Gist vide ou inaccessible. Initialisation avec modèles par défaut.")

    # If loading failed or Gist was empty, initialize and save default.
    initial_data = copy.deepcopy(INITIAL_PROMPT_TEMPLATES)
    # Only attempt to save to Gist if secrets are present
    if GIST_ID and GITHUB_PAT:
        data_to_save_init = _preprocess_for_saving(initial_data) # Preprocess before saving
        try:
            json_string_init = json.dumps(data_to_save_init, indent=4, ensure_ascii=False)
            if update_gist_content(GIST_ID, GITHUB_PAT, json_string_init):
                st.info("Modèles par défaut sauvegardés sur Gist pour initialisation.")
        except Exception as e: # pragma: no cover
            st.error(f"Erreur sauvegarde initiale sur Gist: {e}")
    return initial_data # Return initial_data whether save succeeded or not

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
        except IndexError: pass # pragma: no cover
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
if 'variable_type_to_create' not in st.session_state:
    st.session_state.variable_type_to_create = None
if 'active_generated_prompt' not in st.session_state: 
    st.session_state.active_generated_prompt = ""
if 'go_to_config_section' not in st.session_state:
    st.session_state.go_to_config_section = False


# --- Main App UI ---
st.title(f"🧬 Le laboratoire de prompt IA")

# --- Sidebar Navigation with Tabs ---
st.sidebar.header("Menu Principal")
tab_bibliotheque, tab_edition_generation = st.sidebar.tabs(["📚 Bibliothèque", "✍️ Génération & Édition"])

# --- Tab: Génération & Édition (Sidebar content) ---
with tab_edition_generation:
    st.subheader("Explorateur de Prompts")
    available_families = list(st.session_state.editable_prompts.keys())

    default_family_idx_edit = 0
    current_family_for_edit = st.session_state.get('family_selector_edition')

    # Logic to determine the selected family for editing
    if st.session_state.force_select_family_name and st.session_state.force_select_family_name in available_families:
        current_family_for_edit = st.session_state.force_select_family_name
        st.session_state.family_selector_edition = current_family_for_edit # Update session state
        # st.session_state.force_select_family_name = None # Consume the force flag
    elif current_family_for_edit and current_family_for_edit in available_families:
        pass # Already set and valid
    elif available_families:
        current_family_for_edit = available_families[0]
        st.session_state.family_selector_edition = current_family_for_edit # Update session state
    else:
        current_family_for_edit = None
        st.session_state.family_selector_edition = None # Update session state
    
    if current_family_for_edit and current_family_for_edit in available_families:
        default_family_idx_edit = available_families.index(current_family_for_edit)
    elif available_families: # Fallback if current_family_for_edit became invalid
        default_family_idx_edit = 0
        current_family_for_edit = available_families[0]
        st.session_state.family_selector_edition = current_family_for_edit
    else: # No families available
        default_family_idx_edit = 0 # Index won't be used if options are empty

    if not available_families:
        st.info("Aucune famille de cas d'usage. Créez-en une via les options ci-dessous.")
    else:
        prev_family_selection_edit = st.session_state.get('family_selector_edition') # Capture before widget
        selected_family_ui_edit = st.selectbox(
            "Famille :",
            options=available_families,
            index=default_family_idx_edit, # Ensure index is valid
            key='family_selectbox_widget_edit',
            help="Sélectionnez une famille pour voir ses cas d'usage."
        )
        # Update session state if different from widget's new value
        if st.session_state.family_selector_edition != selected_family_ui_edit :
             st.session_state.family_selector_edition = selected_family_ui_edit
        
        # Rerun logic if selection changed through UI
        if prev_family_selection_edit != selected_family_ui_edit:
            st.session_state.use_case_selector_edition = None
            st.session_state.force_select_use_case_name = None # Clear force for use case
            # st.session_state.force_select_family_name = None # Already handled or set by UI
            st.session_state.view_mode = "edit"
            st.session_state.active_generated_prompt = ""
            st.session_state.variable_type_to_create = None 
            st.session_state.editing_variable_info = None   
            st.rerun()

    current_selected_family_for_edit_logic = st.session_state.get('family_selector_edition')
    use_cases_in_current_family_edit_options = []
    if current_selected_family_for_edit_logic and current_selected_family_for_edit_logic in st.session_state.editable_prompts:
        use_cases_in_current_family_edit_options = list(st.session_state.editable_prompts[current_selected_family_for_edit_logic].keys())

    if use_cases_in_current_family_edit_options:
        default_uc_idx_edit = 0
        current_uc_for_edit = st.session_state.get('use_case_selector_edition')

        if st.session_state.force_select_use_case_name and st.session_state.force_select_use_case_name in use_cases_in_current_family_edit_options:
            current_uc_for_edit = st.session_state.force_select_use_case_name
            # st.session_state.force_select_use_case_name = None # Consume the flag
        elif current_uc_for_edit and current_uc_for_edit in use_cases_in_current_family_edit_options:
            pass # Already set and valid
        else: # Default to first if no valid selection or force
            current_uc_for_edit = use_cases_in_current_family_edit_options[0]
        
        st.session_state.use_case_selector_edition = current_uc_for_edit # Update session state

        if current_uc_for_edit: # Ensure it's not None
            default_uc_idx_edit = use_cases_in_current_family_edit_options.index(current_uc_for_edit)
        
        prev_uc_selection_edit = st.session_state.get('use_case_selector_edition') # Capture before widget
        selected_use_case_ui_edit = st.radio(
            "Cas d'usage :",
            options=use_cases_in_current_family_edit_options,
            index=default_uc_idx_edit,
            key='use_case_radio_widget_edit',
            help="Sélectionnez un cas d'usage pour générer un prompt ou le paramétrer."
        )
        if st.session_state.use_case_selector_edition != selected_use_case_ui_edit:
            st.session_state.use_case_selector_edition = selected_use_case_ui_edit

        if prev_uc_selection_edit != selected_use_case_ui_edit:
            # st.session_state.force_select_use_case_name = None # Already handled by UI
            st.session_state.view_mode = "edit"
            st.session_state.active_generated_prompt = ""
            st.session_state.variable_type_to_create = None 
            st.session_state.editing_variable_info = None   
            st.rerun()

    elif current_selected_family_for_edit_logic: # Family selected, but no use cases
        st.info(f"Aucun cas d'usage dans '{current_selected_family_for_edit_logic}'. Créez-en un.")
        st.session_state.use_case_selector_edition = None 

    # Consume force flags after they've been used to set initial selections
    if st.session_state.force_select_family_name: st.session_state.force_select_family_name = None
    if st.session_state.force_select_use_case_name: st.session_state.force_select_use_case_name = None
    st.markdown("---")

    with st.expander("🗂️ Gérer les Familles", expanded=False):
        with st.form("new_family_form_sidebar", clear_on_submit=True):
            new_family_name = st.text_input("Nom de la nouvelle famille:", key="new_fam_name_sidebar")
            submitted_new_family = st.form_submit_button("➕ Créer Famille")
            if submitted_new_family and new_family_name.strip():
                if new_family_name.strip() in st.session_state.editable_prompts:
                    st.error(f"La famille '{new_family_name.strip()}' existe déjà.")
                else:
                    st.session_state.editable_prompts[new_family_name.strip()] = {}
                    save_editable_prompts_to_gist()
                    st.success(f"Famille '{new_family_name.strip()}' créée.")
                    st.session_state.force_select_family_name = new_family_name.strip() # Force selection
                    st.session_state.use_case_selector_edition = None # No use case selected yet
                    st.session_state.view_mode = "edit"
                    st.rerun()
            elif submitted_new_family:
                st.error("Le nom de la famille ne peut pas être vide.")

        if available_families and current_selected_family_for_edit_logic :
            st.markdown("---")
            with st.form("rename_family_form_sidebar"):
                st.write(f"Renommer la famille : **{current_selected_family_for_edit_logic}**")
                renamed_family_name_input = st.text_input("Nouveau nom :", value=current_selected_family_for_edit_logic, key="ren_fam_name_sidebar")
                submitted_rename_family = st.form_submit_button("✏️ Renommer")
                if submitted_rename_family and renamed_family_name_input.strip():
                    renamed_family_name = renamed_family_name_input.strip()
                    if renamed_family_name == current_selected_family_for_edit_logic:
                        st.info("Le nouveau nom est identique à l'ancien.")
                    elif renamed_family_name in st.session_state.editable_prompts:
                        st.error(f"Une famille nommée '{renamed_family_name}' existe déjà.")
                    else:
                        st.session_state.editable_prompts[renamed_family_name] = st.session_state.editable_prompts.pop(current_selected_family_for_edit_logic)
                        save_editable_prompts_to_gist()
                        st.success(f"Famille '{current_selected_family_for_edit_logic}' renommée en '{renamed_family_name}'.")
                        st.session_state.force_select_family_name = renamed_family_name # Force selection
                        # Keep current use case if possible, or it will be reset if family changes
                        if st.session_state.library_selected_family_for_display == current_selected_family_for_edit_logic:
                           st.session_state.library_selected_family_for_display = renamed_family_name
                        st.session_state.view_mode = "edit"
                        st.rerun()
                elif submitted_rename_family:
                    st.error("Le nouveau nom de la famille ne peut pas être vide.")

            st.markdown("---")
            st.write(f"Supprimer la famille : **{current_selected_family_for_edit_logic}**")
            if st.session_state.confirming_delete_family_name == current_selected_family_for_edit_logic:
                st.warning(f"Supprimer '{current_selected_family_for_edit_logic}' et tous ses cas d'usage ? Action irréversible.")
                
                # --- MODIFICATION ICI : Affichage des boutons l'un au-dessus de l'autre ---
                button_text_confirm_delete = f"Oui, supprimer définitivement '{current_selected_family_for_edit_logic}'"
                if st.button(button_text_confirm_delete, type="primary", key=f"confirm_del_fam_sb_{current_selected_family_for_edit_logic}", use_container_width=True):
                    deleted_fam_name = current_selected_family_for_edit_logic 
                    del st.session_state.editable_prompts[current_selected_family_for_edit_logic]
                    save_editable_prompts_to_gist()
                    st.success(f"Famille '{deleted_fam_name}' supprimée.")
                    st.session_state.confirming_delete_family_name = None
                    st.session_state.family_selector_edition = None 
                    st.session_state.use_case_selector_edition = None
                    if st.session_state.library_selected_family_for_display == deleted_fam_name:
                        st.session_state.library_selected_family_for_display = None
                    st.session_state.view_mode = "edit"
                    st.rerun()
                
                if st.button("Non, annuler la suppression", key=f"cancel_del_fam_sb_{current_selected_family_for_edit_logic}", use_container_width=True):
                    st.session_state.confirming_delete_family_name = None
                    st.session_state.view_mode = "edit"
                    st.rerun()
            else:
                if st.button(f"🗑️ Supprimer Famille Sélectionnée", key=f"del_fam_btn_sb_{current_selected_family_for_edit_logic}"):
                    st.session_state.confirming_delete_family_name = current_selected_family_for_edit_logic
                    st.session_state.view_mode = "edit"
                    st.rerun()
        elif not available_families:
            st.caption("Créez une famille pour pouvoir la gérer.")
        else: # Families exist, but none selected for edit (should not happen if logic above is correct)
            st.caption("Sélectionnez une famille (ci-dessus) pour la gérer.")

    st.markdown("---")

    # Use 'expanded' argument of st.expander directly with session state
    with st.expander("➕ Créer un Cas d'Usage", expanded=st.session_state.get('show_create_new_use_case_form', False)):
        if not available_families:
            st.caption("Veuillez d'abord créer une famille pour y ajouter des cas d'usage.")
        else: # Families are available
            if st.button("Afficher/Masquer Formulaire de Création de Cas d'Usage", key="toggle_create_uc_form_in_exp"):
                st.session_state.show_create_new_use_case_form = not st.session_state.get('show_create_new_use_case_form', False)
                st.rerun() # Rerun to reflect expander state change

            if st.session_state.get('show_create_new_use_case_form', False): # Check again after button
                with st.form("new_use_case_form_in_exp", clear_on_submit=True):
                    default_create_family_idx_tab = 0
                    # Ensure current_selected_family_for_edit_logic is valid before using .index()
                    if current_selected_family_for_edit_logic and current_selected_family_for_edit_logic in available_families:
                        default_create_family_idx_tab = available_families.index(current_selected_family_for_edit_logic)
                    
                    uc_parent_family = st.selectbox(
                        "Famille Parente du nouveau cas d'usage:",
                        options=available_families,
                        index=default_create_family_idx_tab,
                        key="new_uc_parent_fam_in_exp"
                    )
                    uc_name_input = st.text_input("Nom du Nouveau Cas d'Usage:", key="new_uc_name_in_exp")
                    uc_template_input = st.text_area("Template Initial du Cas d'Usage:", height=100, key="new_uc_template_in_exp", value="Nouveau prompt...")
                    submitted_new_uc = st.form_submit_button("Créer Cas d'Usage")

                    if submitted_new_uc:
                        parent_family_val = uc_parent_family # Already selected, should be valid
                        uc_name_val = uc_name_input.strip()
                        uc_template_val = uc_template_input # No strip needed for text_area usually

                        if not uc_name_val: 
                            st.error("Le nom du cas d'usage ne peut pas être vide.")
                        elif uc_name_val in st.session_state.editable_prompts.get(parent_family_val, {}):
                            st.error(f"Le cas d'usage '{uc_name_val}' existe déjà dans la famille '{parent_family_val}'.")
                        else:
                            now_iso_create, now_iso_update = get_default_dates()
                            st.session_state.editable_prompts[parent_family_val][uc_name_val] = {
                                "template": uc_template_val or "Nouveau prompt...",
                                "variables": [], "tags": [], # "previous_template": "" a été supprimé de cette ligne
                                "usage_count": 0, "created_at": now_iso_create, "updated_at": now_iso_update
                            }
                            save_editable_prompts_to_gist()
                            st.success(f"Cas d'usage '{uc_name_val}' créé avec succès dans '{parent_family_val}'.")
                            st.session_state.show_create_new_use_case_form = False # Hide form
                            st.session_state.force_select_family_name = parent_family_val
                            st.session_state.force_select_use_case_name = uc_name_val
                            st.session_state.view_mode = "edit"
                            st.session_state.active_generated_prompt = "" # Réinitialiser le prompt affiché
                            st.rerun()


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
        st.info("La bibliothèque est vide. Ajoutez des prompts via l'onglet 'Génération & Édition'.")
    else:
        sorted_families_bib = sorted(list(st.session_state.editable_prompts.keys()))

        # Ensure a family is selected for display if possible
        if not st.session_state.get('library_selected_family_for_display') or \
           st.session_state.library_selected_family_for_display not in sorted_families_bib:
            st.session_state.library_selected_family_for_display = sorted_families_bib[0] if sorted_families_bib else None

        st.write("Sélectionner une famille à afficher :")
        # Buttons for family selection in the library view
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
                    st.session_state.view_mode = "library" # Ensure view mode
                    st.rerun() # Rerun if selection changes to update main display
        st.markdown("---")

# --- Main Display Area (Logic for both Library and Edit views) ---
final_selected_family_edition = st.session_state.get('family_selector_edition')
final_selected_use_case_edition = st.session_state.get('use_case_selector_edition')
library_family_to_display = st.session_state.get('library_selected_family_for_display')

# Default view mode logic
if 'view_mode' not in st.session_state:
    if library_family_to_display and any(st.session_state.editable_prompts.get(fam, {}) for fam in st.session_state.editable_prompts):
        st.session_state.view_mode = "library"
    else:
        st.session_state.view_mode = "edit" # Default to edit if library is empty or no family selected

if st.session_state.view_mode == "library":
    if not library_family_to_display:
        st.info("Veuillez sélectionner une famille dans la barre latérale (onglet Bibliothèque) pour afficher les prompts.")
        # Attempt to select a default family if none is selected and families exist
        available_families_main_display = list(st.session_state.editable_prompts.keys())
        if available_families_main_display:
            st.session_state.library_selected_family_for_display = available_families_main_display[0]
            st.rerun()
        elif not any(st.session_state.editable_prompts.values()): # No families or prompts at all
             st.warning("Aucune famille de cas d'usage n'est configurée. Créez-en via l'onglet 'Génération & Édition'.")


    elif library_family_to_display in st.session_state.editable_prompts:
        st.header(f"Bibliothèque - Famille : {library_family_to_display}")
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
                if selected_tags_lib:
                    match_tags = all(tag in uc_config.get("tags", []) for tag in selected_tags_lib)

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
                        else: st.caption("_Aucune variable correctement définie._") # pragma: no cover
                    else: st.caption("_Aucune variable spécifique définie._")
                    tags_display = prompt_config_display.get("tags", [])
                    if tags_display:
                        st.markdown(f"**Tags :** {', '.join([f'`{tag}`' for tag in tags_display])}")
                    created_at_str = prompt_config_display.get('created_at', get_default_dates()[0])
                    updated_at_str = prompt_config_display.get('updated_at', get_default_dates()[1])
                    st.caption(f"Créé le: {datetime.fromisoformat(created_at_str).strftime('%d/%m/%Y %H:%M')} | Modifié le: {datetime.fromisoformat(updated_at_str).strftime('%d/%m/%Y %H:%M')}")
                    st.markdown("---")
                    col_btn_lib1, col_btn_lib2 = st.columns(2)
                    with col_btn_lib1:
                        if st.button(f"✍️ Utiliser ce modèle", key=f"main_lib_use_{library_family_to_display.replace(' ', '_')}_{use_case_name_display.replace(' ', '_')}", use_container_width=True):
                            st.session_state.view_mode = "edit"
                            st.session_state.force_select_family_name = library_family_to_display
                            st.session_state.force_select_use_case_name = use_case_name_display
                            st.session_state.go_to_config_section = False
                            st.session_state.active_generated_prompt = ""
                            st.session_state.variable_type_to_create = None
                            st.session_state.editing_variable_info = None
                            st.session_state.confirming_delete_details = None
                            st.rerun()
                    with col_btn_lib2:
                        if st.button(f"⚙️ Éditer ce prompt", key=f"main_lib_edit_{library_family_to_display.replace(' ', '_')}_{use_case_name_display.replace(' ', '_')}", use_container_width=True):
                            st.session_state.view_mode = "edit"
                            st.session_state.force_select_family_name = library_family_to_display
                            st.session_state.force_select_use_case_name = use_case_name_display
                            st.session_state.go_to_config_section = True
                            st.session_state.active_generated_prompt = ""
                            st.session_state.variable_type_to_create = None
                            st.session_state.editing_variable_info = None
                            st.session_state.confirming_delete_details = None
                            st.rerun()
    else: # library_family_to_display is None or invalid, but view_mode is library
        st.info("Aucune famille n'est actuellement sélectionnée dans la bibliothèque ou la famille sélectionnée n'existe plus.")
        available_families_check = list(st.session_state.editable_prompts.keys())
        if not available_families_check :
             st.warning("La bibliothèque est entièrement vide. Veuillez créer des familles et des prompts.")


elif st.session_state.view_mode == "edit":
    if not final_selected_family_edition :
        st.info("Sélectionnez une famille dans la barre latérale (onglet Génération & Édition) ou créez-en une pour commencer.")
    elif not final_selected_use_case_edition:
        st.info(f"Sélectionnez un cas d'usage dans la famille '{final_selected_family_edition}' ou créez-en un nouveau pour commencer.")
    elif final_selected_family_edition in st.session_state.editable_prompts and \
         final_selected_use_case_edition in st.session_state.editable_prompts[final_selected_family_edition]:

        current_prompt_config = st.session_state.editable_prompts[final_selected_family_edition][final_selected_use_case_edition]

        st.header(f"Cas d'usage: {final_selected_use_case_edition}")
        created_at_str_edit = current_prompt_config.get('created_at', get_default_dates()[0])
        updated_at_str_edit = current_prompt_config.get('updated_at', get_default_dates()[1])
        st.caption(f"Famille: {final_selected_family_edition} | Utilisé {current_prompt_config.get('usage_count', 0)} fois. Créé: {datetime.fromisoformat(created_at_str_edit).strftime('%d/%m/%Y')}, Modifié: {datetime.fromisoformat(updated_at_str_edit).strftime('%d/%m/%Y')}")
        st.markdown("---")

        st.subheader(f"🚀 Générer Prompt")
        gen_form_values = {}
        with st.form(key=f"gen_form_{final_selected_family_edition}_{final_selected_use_case_edition}"):
            if not current_prompt_config.get("variables"): st.info("Ce cas d'usage n'a pas de variables configurées pour la génération.")
            
            # Ensure variables is a list
            variables_for_form = current_prompt_config.get("variables", [])
            if not isinstance(variables_for_form, list): # Should not happen with preprocessing
                variables_for_form = [] # pragma: no cover

            cols_per_row = 2 if len(variables_for_form) > 1 else 1
            var_chunks = [variables_for_form[i:i + cols_per_row] for i in range(0, len(variables_for_form), cols_per_row)]

            for chunk in var_chunks:
                cols = st.columns(len(chunk))
                for i, var_info in enumerate(chunk):
                    with cols[i]:
                        widget_key = f"gen_input_{final_selected_family_edition}_{final_selected_use_case_edition}_{var_info['name']}"
                        field_default = var_info.get("default")
                        var_type = var_info.get("type")

                        if var_type == "text_input":
                            gen_form_values[var_info["name"]] = st.text_input(var_info["label"], value=str(field_default or ""), key=widget_key)
                        elif var_type == "selectbox":
                            opts = var_info.get("options", [])
                            idx = 0 # Default index
                            if opts: # Ensure options exist
                                try: # Handle if default is not in options
                                    idx = opts.index(field_default) if field_default in opts else 0
                                except ValueError: # pragma: no cover
                                    idx = 0 
                            gen_form_values[var_info["name"]] = st.selectbox(var_info["label"], options=opts, index=idx, key=widget_key)
                        elif var_type == "date_input":
                            val_date = field_default if isinstance(field_default, date) else datetime.now().date()
                            gen_form_values[var_info["name"]] = st.date_input(var_info["label"], value=val_date, key=widget_key)
                        elif var_type == "number_input": # MODIFIÉ pour cohérence des types
                            current_value_default_gen = var_info.get("default")
                            min_val_config_gen = var_info.get("min_value")
                            max_val_config_gen = var_info.get("max_value")
                            step_config_gen = var_info.get("step")

                            val_num_gen = float(current_value_default_gen) if isinstance(current_value_default_gen, (int, float)) else 0.0
                            min_val_gen = float(min_val_config_gen) if min_val_config_gen is not None else None
                            max_val_gen = float(max_val_config_gen) if max_val_config_gen is not None else None
                            step_val_gen = float(step_config_gen) if step_config_gen is not None else 1.0

                            if min_val_gen is not None and val_num_gen < min_val_gen:
                                val_num_gen = min_val_gen # Ajuste la valeur pour qu'elle soit au moins min_value
                            if max_val_gen is not None and val_num_gen > max_val_gen:
                                val_num_gen = max_val_gen # Ajuste la valeur pour qu'elle ne dépasse pas max_value
                            
                            gen_form_values[var_info["name"]] = st.number_input(
                                var_info["label"], value=val_num_gen, min_value=min_val_gen,
                                max_value=max_val_gen, step=step_val_gen, key=widget_key, format="%g"
                            )
                        elif var_type == "text_area":
                            gen_form_values[var_info["name"]] = st.text_area(var_info["label"], value=str(field_default or ""),
                                                                        height=var_info.get("height",100), key=widget_key)

            if st.form_submit_button("🚀 Générer Prompt"):
                final_vals_for_prompt = {
                    k: (v.strftime("%d/%m/%Y") if isinstance(v, date) else v)
                    for k, v in gen_form_values.items() if v is not None
                }
                try:
                    class SafeFormatter(dict):
                        def __missing__(self, key): return f"{{{key}}}" # pragma: no cover
                    prompt_template_content = current_prompt_config.get("template", "")
                    formatted_template_content = prompt_template_content.format_map(SafeFormatter(final_vals_for_prompt))
                    use_case_title = final_selected_use_case_edition 
                    generated_prompt = f"Sujet : {use_case_title}\n{formatted_template_content}"
                    st.session_state.active_generated_prompt = generated_prompt
                    st.success("Prompt généré avec succès!")
                    st.balloons()
                    current_prompt_config["usage_count"] = current_prompt_config.get("usage_count", 0) + 1
                    current_prompt_config["updated_at"] = datetime.now().isoformat()
                    save_editable_prompts_to_gist()
                except Exception as e: # pragma: no cover
                    st.error(f"Erreur lors de la génération du prompt: {e}")
        st.markdown("---")
        
        if st.session_state.active_generated_prompt:
            st.subheader("✅ Prompt Généré (éditable):")
            edited_prompt_value = st.text_area(
                "Prompt:", value=st.session_state.active_generated_prompt, height=200,
                key=f"editable_generated_prompt_output_{final_selected_family_edition}_{final_selected_use_case_edition}",
                label_visibility="collapsed"
            )
            if edited_prompt_value != st.session_state.active_generated_prompt: # pragma: no cover
                st.session_state.active_generated_prompt = edited_prompt_value
            st.caption("Prompt généré (pour relecture et copie manuelle) :")
            st.code(st.session_state.active_generated_prompt, language=None) 
        st.markdown("---")

        if st.session_state.confirming_delete_details and \
           st.session_state.confirming_delete_details["family"] == final_selected_family_edition and \
           st.session_state.confirming_delete_details["use_case"] == final_selected_use_case_edition:
            details = st.session_state.confirming_delete_details
            st.warning(f"Supprimer '{details['use_case']}' de '{details['family']}' ? Action irréversible.")
            c1_del_uc, c2_del_uc, _ = st.columns([1,1,3])
            if c1_del_uc.button(f"Oui, supprimer '{details['use_case']}'", key=f"del_yes_{details['family']}_{details['use_case']}", type="primary"):
                deleted_uc_name_for_msg = details['use_case']
                deleted_uc_fam_for_msg = details['family']
                del st.session_state.editable_prompts[details["family"]][details["use_case"]]
                save_editable_prompts_to_gist()
                st.success(f"'{deleted_uc_name_for_msg}' supprimé de '{deleted_uc_fam_for_msg}'.")
                st.session_state.confirming_delete_details = None
                st.session_state.force_select_family_name = deleted_uc_fam_for_msg # Stay in the same family
                st.session_state.force_select_use_case_name = None # Will select first available or show "no use case"
                if st.session_state.editing_variable_info and \
                   st.session_state.editing_variable_info.get("family") == deleted_uc_fam_for_msg and \
                   st.session_state.editing_variable_info.get("use_case") == deleted_uc_name_for_msg:
                    st.session_state.editing_variable_info = None # pragma: no cover
                st.session_state.active_generated_prompt = ""
                st.session_state.variable_type_to_create = None
                st.session_state.view_mode = "edit"
                st.rerun()
            if c2_del_uc.button("Non, annuler", key=f"del_no_{details['family']}_{details['use_case']}"):
                st.session_state.confirming_delete_details = None
                # st.session_state.view_mode = "edit" # Already in edit mode
                st.rerun() # Rerun to clear confirmation widgets
            st.markdown("---") 

        should_expand_config = st.session_state.get('go_to_config_section', False)
        with st.expander(f"⚙️ Paramétrage du Prompt: {final_selected_use_case_edition}", expanded=should_expand_config):
            st.subheader("Template du Prompt")

            # Sanétiser les noms de famille et de cas d'usage pour les utiliser dans les clés
            # Remplacer les espaces et autres caractères qui pourraient causer des problèmes dans les clés
            safe_family_key_part = str(final_selected_family_edition).replace(' ', '_').replace('.', '_').replace('{', '_').replace('}', '_').replace('(', '_').replace(')', '_')
            safe_uc_key_part = str(final_selected_use_case_edition).replace(' ', '_').replace('.', '_').replace('{', '_').replace('}', '_').replace('(', '_').replace(')', '_')

            # Clé unique et sanétisée pour le st.text_area du template
            template_text_area_key = f"template_text_area_{safe_family_key_part}_{safe_uc_key_part}"
            new_tpl = st.text_area("Template:", value=current_prompt_config.get('template', ''), height=200, key=template_text_area_key)
            st.markdown("""
                <style>
                /* Cible les blocs de code à l'intérieur d'un expander */
                div[data-testid="stExpander"] div[data-testid="stCodeBlock"] {
                    margin-top: 0.1rem !important;    /* Petite marge en haut */
                    margin-bottom: 0.15rem !important; /* TRÈS PETITE marge en bas - C'est la clé pour réduire l'espace entre les lignes */
                    padding-top: 0.1rem !important;   /* Padding interne du bloc st.code */
                    padding-bottom: 0.1rem !important;
                }
                /* Cible le tag <pre> à l'intérieur de ces blocs de code */
                div[data-testid="stExpander"] div[data-testid="stCodeBlock"] pre {
                    padding-top: 0.2rem !important;   /* Padding pour le texte à l'intérieur de <pre> */
                    padding-bottom: 0.2rem !important;
                    line-height: 1.1 !important;      /* Hauteur de ligne pour le texte */
                    font-size: 0.85em !important;     /* Taille de police légèrement réduite */
                    margin: 0 !important;             /* S'assurer que <pre> n'a pas de marges propres */
                }
                </style>
            """, unsafe_allow_html=True)
        
            st.markdown("##### Variables disponibles à insérer :")
        
            variables_config = current_prompt_config.get('variables', [])
            if not variables_config:
                st.caption("Aucune variable définie pour ce prompt. Ajoutez-en ci-dessous.")
            else:
                # Définir deux colonnes
                col1, col2 = st.columns(2)
                
                for i, var_info in enumerate(variables_config):
                    if 'name' in var_info:
                        variable_string_to_display = f"{{{var_info['name']}}}"
                        
                        # Placer les variables alternativement dans les colonnes
                        target_column = col1 if i % 2 == 0 else col2
                        
                        with target_column:
                                st.code(variable_string_to_display, language=None)
                
                st.caption("Survolez une variable ci-dessus et cliquez sur l'icône qui apparaît pour la copier.")

            # Clé unique et sanétisée pour le bouton "Sauvegarder Template"
            save_template_button_key = f"save_template_button_{safe_family_key_part}_{safe_uc_key_part}"
            if st.button("Sauvegarder Template", key=save_template_button_key): # Cette ligne correspondra à la ligne 856 après modification
                current_prompt_config['template'] = new_tpl
                current_prompt_config["updated_at"] = datetime.now().isoformat()
                save_editable_prompts_to_gist()
                st.success("Template sauvegardé!")
                st.rerun()

            st.markdown("---")
            st.subheader("🏷️ Tags")
            current_tags_str = ", ".join(current_prompt_config.get("tags", []))
            new_tags_str_input = st.text_input(
                "Tags (séparés par des virgules):", value=current_tags_str,
                key=f"tags_input_{final_selected_family_edition}_{final_selected_use_case_edition}" # Unique key
            )
            if st.button("Sauvegarder Tags", key=f"save_tags_btn_{final_selected_family_edition}_{final_selected_use_case_edition}"): # Unique key
                current_prompt_config["tags"] = sorted(list(set(t.strip() for t in new_tags_str_input.split(',') if t.strip())))
                current_prompt_config["updated_at"] = datetime.now().isoformat()
                save_editable_prompts_to_gist()
                st.success("Tags sauvegardés!")
                st.rerun()

            st.markdown("---")
            st.subheader("Variables du Prompt")
            current_variables_list = current_prompt_config.get('variables', [])
            if not current_variables_list: 
                st.info("Aucune variable définie.")
            else:
                # Afficher les en-têtes pour les colonnes d'action pour plus de clarté si souhaité
                # _, col_actions_header = st.columns([6, 4]) # Exemple de ratio
                # col_actions_header.caption("Actions")
                pass # Ou pas d'en-tête spécifique, les icônes parlent d'elles-mêmes

            for idx, var_data in enumerate(list(current_variables_list)): 
                # Utiliser un identifiant unique pour les clés, basé sur le nom ou l'index
                var_id_for_key = var_data.get('name', f"varidx{idx}").replace(" ", "_")
                action_key_prefix = f"var_action_{final_selected_family_edition.replace(' ','_')}_{final_selected_use_case_edition.replace(' ','_')}_{var_id_for_key}"

                # Définition des colonnes: Info Variable | Monter | Descendre | Modifier | Supprimer
                col_info, col_up, col_down, col_edit, col_delete = st.columns([3, 0.5, 0.5, 0.8, 0.8])

                with col_info:
                    # Afficher l'index (ordre) de la variable
                    st.markdown(f"**{idx + 1}. {var_data.get('name', 'N/A')}** ({var_data.get('label', 'N/A')})\n* `{var_data.get('type', 'N/A')}`*")

                # Bouton Monter
                with col_up:
                    disable_up_button = (idx == 0)
                    if st.button("↑", key=f"{action_key_prefix}_up", help="Monter cette variable", disabled=disable_up_button, use_container_width=True):
                        # Échanger avec l'élément précédent
                        current_variables_list[idx], current_variables_list[idx-1] = current_variables_list[idx-1], current_variables_list[idx]
                        current_prompt_config["variables"] = current_variables_list # Mettre à jour la liste dans la config
                        current_prompt_config["updated_at"] = datetime.now().isoformat()
                        save_editable_prompts_to_gist()
                        # Réinitialiser l'état d'édition car les index ont changé
                        st.session_state.editing_variable_info = None
                        st.session_state.variable_type_to_create = None
                        st.rerun()

                # Bouton Descendre
                with col_down:
                    disable_down_button = (idx == len(current_variables_list) - 1)
                    if st.button("↓", key=f"{action_key_prefix}_down", help="Descendre cette variable", disabled=disable_down_button, use_container_width=True):
                        # Échanger avec l'élément suivant
                        current_variables_list[idx], current_variables_list[idx+1] = current_variables_list[idx+1], current_variables_list[idx]
                        current_prompt_config["variables"] = current_variables_list # Mettre à jour la liste
                        current_prompt_config["updated_at"] = datetime.now().isoformat()
                        save_editable_prompts_to_gist()
                        # Réinitialiser l'état d'édition car les index ont changé
                        st.session_state.editing_variable_info = None
                        st.session_state.variable_type_to_create = None
                        st.rerun()
                
                # Bouton Modifier
                with col_edit:
                    if st.button("Modifier", key=f"{action_key_prefix}_edit", use_container_width=True):
                        st.session_state.editing_variable_info = {
                            "family": final_selected_family_edition, 
                            "use_case": final_selected_use_case_edition, 
                            "index": idx, # L'index est correct au moment du clic
                            "data": copy.deepcopy(var_data)
                        }
                        st.session_state.variable_type_to_create = var_data.get('type')
                        st.rerun()
                
                # Bouton Supprimer
                with col_delete:
                    if st.button("Suppr.", key=f"{action_key_prefix}_delete", type="secondary", use_container_width=True):
                        variable_name_to_delete = current_variables_list.pop(idx).get('name', 'Variable inconnue')
                        current_prompt_config["variables"] = current_variables_list # Mettre à jour la liste
                        current_prompt_config["updated_at"] = datetime.now().isoformat()
                        save_editable_prompts_to_gist()
                        st.success(f"Variable '{variable_name_to_delete}' supprimée.")
                        # Réinitialiser l'état d'édition car la liste a changé
                        st.session_state.editing_variable_info = None
                        st.session_state.variable_type_to_create = None
                        st.rerun()
            
            st.markdown("---")
            st.subheader("Ajouter ou Modifier une Variable")

            is_editing_var = False
            variable_data_for_form = {"name": "", "label": "", "type": "", "options": "", "default": ""} # Default empty structure
            
            # Logic to load data if editing
            if st.session_state.editing_variable_info and \
               st.session_state.editing_variable_info.get("family") == final_selected_family_edition and \
               st.session_state.editing_variable_info.get("use_case") == final_selected_use_case_edition:
                edit_var_idx = st.session_state.editing_variable_info["index"]
                # Ensure index is still valid
                if edit_var_idx < len(current_prompt_config.get('variables',[])):
                    is_editing_var = True
                    # Pre-fill form data with existing variable, ensuring deep copy
                    current_editing_data_snapshot = current_prompt_config['variables'][edit_var_idx]
                    variable_data_for_form.update(copy.deepcopy(current_editing_data_snapshot))
                    # Convert options list to string for text_input
                    if isinstance(variable_data_for_form.get("options"), list):
                        variable_data_for_form["options"] = ", ".join(map(str, variable_data_for_form["options"]))
                    # Convert default date to string for text_input
                    raw_def_edit_form = variable_data_for_form.get("default")
                    if isinstance(raw_def_edit_form, date): # Date object
                        variable_data_for_form["default"] = raw_def_edit_form.strftime("%Y-%m-%d")
                    elif raw_def_edit_form is not None: # Other types (int, float, bool, str)
                        variable_data_for_form["default"] = str(raw_def_edit_form)
                    else: # Default is None
                        variable_data_for_form["default"] = "" # Empty string for text_input
                else: # Index out of bounds, likely variable was deleted externally or list changed
                    st.session_state.editing_variable_info = None # pragma: no cover
                    st.session_state.variable_type_to_create = None # pragma: no cover
                    st.warning("La variable que vous tentiez de modifier n'existe plus. Annulation de l'édition.") # pragma: no cover
                    st.rerun() # pragma: no cover

            # Step 1: Select variable type (only if not editing and no type selected yet)
            if not is_editing_var and st.session_state.variable_type_to_create is None:
                st.markdown("##### 1. Choisissez le type de variable à créer :")
                variable_types_map = {
                    "Zone de texte (courte)": "text_input", "Liste choix": "selectbox",
                    "Date": "date_input", "Nombre": "number_input", "Zone de texte (longue)": "text_area"
                }
                num_type_buttons = len(variable_types_map)
                # Adjust columns based on number of buttons for better responsiveness
                cols_type_buttons = st.columns(min(num_type_buttons, 5)) 
                button_idx = 0
                for btn_label, type_val in variable_types_map.items():
                    # Use modulo with the actual number of columns created
                    if cols_type_buttons[button_idx % len(cols_type_buttons)].button(btn_label, key=f"btn_type_{type_val}_{final_selected_use_case_edition.replace(' ','_')}", use_container_width=True):
                        st.session_state.variable_type_to_create = type_val
                        st.rerun()
                    button_idx += 1
                st.markdown("---")

            # Step 2: Display specific form if a type is selected or if editing
            if st.session_state.variable_type_to_create:
                current_type_for_form = st.session_state.variable_type_to_create
                variable_types_map_display = {
                    "text_input": "Zone de texte (courte)", "selectbox": "Liste choix", 
                    "date_input": "Date", "number_input": "Nombre", "text_area": "Zone de texte (longue)"
                }
                readable_type = variable_types_map_display.get(current_type_for_form, "Type Inconnu")
                form_title = f"Modifier Variable : {variable_data_for_form.get('name','N/A')} ({readable_type})" if is_editing_var else f"Nouvelle Variable : {readable_type}"
                st.markdown(f"##### 2. Configurez la variable")

                form_key_suffix = f"_edit_{st.session_state.editing_variable_info['index']}" if is_editing_var and st.session_state.editing_variable_info else "_create"
                form_var_specific_key = f"form_var_{current_type_for_form}_{final_selected_use_case_edition.replace(' ','_')}{form_key_suffix}"

                with st.form(key=form_var_specific_key, clear_on_submit=(not is_editing_var)): # Don't clear on submit when editing
                    st.subheader(form_title)
                    var_name_input_form = st.text_input(
                        "Nom technique (ex : nom_client. Ne pas utiliser de caractères spéciaux -espaces, crochets {},virgules, etc.-)", 
                        value=variable_data_for_form.get("name", ""), 
                        key=f"{form_var_specific_key}_name",
                        # Disable name editing for existing variables to simplify logic (renaming is complex)
                        disabled=is_editing_var 
                    )
                    var_label_input_form = st.text_input(
                        "Label pour l'utilisateur (description affichée)", 
                        value=variable_data_for_form.get("label", ""), 
                        key=f"{form_var_specific_key}_label"
                    )
                    var_options_str_input_form = ""
                    if current_type_for_form == "selectbox":
                        var_options_str_input_form = st.text_input(
                            "Options (séparées par une virgule)", 
                            value=variable_data_for_form.get("options", ""), 
                            key=f"{form_var_specific_key}_options"
                        )
                    # Default value input, hint for date format
                    date_hint = " (Format AAAA-MM-JJ)" if current_type_for_form == "date_input" else ""
                    var_default_val_str_input_form = st.text_input(
                        f"Valeur par défaut{date_hint}", 
                        value=str(variable_data_for_form.get("default", "")), # Ensure string for text_input
                        key=f"{form_var_specific_key}_default"
                    )

                    min_val_input_form, max_val_input_form, step_val_input_form, height_val_input_form = None, None, None, None
                    if current_type_for_form == "number_input": # MODIFIÉ pour cohérence des types
                        num_cols_var_form = st.columns(3)
                        min_val_edit_default = variable_data_for_form.get("min_value")
                        max_val_edit_default = variable_data_for_form.get("max_value")
                        step_val_edit_default = variable_data_for_form.get("step", 1.0) # Default to float

                        min_val_input_form = num_cols_var_form[0].number_input("Valeur minimale (optionnel)", 
                            value=float(min_val_edit_default) if min_val_edit_default is not None else None, 
                            format="%g", key=f"{form_var_specific_key}_min")
                        max_val_input_form = num_cols_var_form[1].number_input("Valeur maximale (optionnel)", 
                            value=float(max_val_edit_default) if max_val_edit_default is not None else None, 
                            format="%g", key=f"{form_var_specific_key}_max")
                        step_val_input_form = num_cols_var_form[2].number_input("Pas (incrément)", 
                            value=float(step_val_edit_default), # Step should always have a value
                            format="%g", min_value=1e-9, key=f"{form_var_specific_key}_step") # min_value to prevent zero step

                    if current_type_for_form == "text_area":
                        height_val_input_form = st.number_input("Hauteur de la zone de texte (pixels)", 
                            value=int(variable_data_for_form.get("height", 100)), # Height is int
                            min_value=50, step=25, key=f"{form_var_specific_key}_height")

                    submit_button_label_form = "Sauvegarder Modifications" if is_editing_var else "Ajouter Variable"
                    submitted_specific_var_form = st.form_submit_button(submit_button_label_form)

                    if submitted_specific_var_form:
                        var_name_val_submit = var_name_input_form.strip()
                        if not var_name_val_submit or not var_label_input_form.strip():
                            st.error("Le nom technique et le label de la variable sont requis.")
                        elif not var_name_val_submit.isidentifier():
                            st.error("Nom technique invalide. Utilisez lettres, chiffres, underscores. Ne pas commencer par un chiffre. Ne pas utiliser de mot-clé Python.")
                        elif current_type_for_form == "selectbox" and not [opt.strip() for opt in var_options_str_input_form.split(',') if opt.strip()]:
                            st.error("Pour une variable de type 'Liste choix', au moins une option est requise.")
                        else:
                            new_var_data_to_submit = {
                                "name": var_name_val_submit, 
                                "label": var_label_input_form.strip(), 
                                "type": current_type_for_form
                            }
                            parsed_def_val_submit = parse_default_value(var_default_val_str_input_form.strip(), current_type_for_form)

                            if current_type_for_form == "selectbox":
                                options_list_submit = [opt.strip() for opt in var_options_str_input_form.split(',') if opt.strip()]
                                new_var_data_to_submit["options"] = options_list_submit
                                if options_list_submit: # Ensure options are not empty
                                    if parsed_def_val_submit not in options_list_submit:
                                        st.warning(f"La valeur par défaut '{parsed_def_val_submit}' n'est pas dans la liste d'options. La première option '{options_list_submit[0]}' sera utilisée comme défaut.")
                                        new_var_data_to_submit["default"] = options_list_submit[0]
                                    else:
                                        new_var_data_to_submit["default"] = parsed_def_val_submit
                                else: # Should be caught by earlier check
                                    new_var_data_to_submit["default"] = ""  # pragma: no cover
                            else:
                                new_var_data_to_submit["default"] = parsed_def_val_submit

                            if current_type_for_form == "number_input": # MODIFIÉ pour cohérence des types
                                if min_val_input_form is not None: new_var_data_to_submit["min_value"] = float(min_val_input_form)
                                if max_val_input_form is not None: new_var_data_to_submit["max_value"] = float(max_val_input_form)
                                if step_val_input_form is not None: new_var_data_to_submit["step"] = float(step_val_input_form)
                                else: new_var_data_to_submit["step"] = 1.0 # Default step if somehow None
                            if current_type_for_form == "text_area" and height_val_input_form is not None:
                                new_var_data_to_submit["height"] = int(height_val_input_form)

                            can_proceed_with_save = True
                            target_vars_list = current_prompt_config.get('variables', [])

                            if is_editing_var:
                                idx_to_edit_submit_form = st.session_state.editing_variable_info["index"]
                                # Name is disabled for editing, so no collision check needed for name if it's the same var
                                target_vars_list[idx_to_edit_submit_form] = new_var_data_to_submit
                                st.success(f"Variable '{var_name_val_submit}' mise à jour avec succès.")
                                st.session_state.editing_variable_info = None 
                                st.session_state.variable_type_to_create = None 
                            else: # Creating new variable
                                existing_var_names_in_uc = [v['name'] for v in target_vars_list]
                                if var_name_val_submit in existing_var_names_in_uc:
                                    st.error(f"Une variable avec le nom technique '{var_name_val_submit}' existe déjà pour ce cas d'usage.")
                                    can_proceed_with_save = False # pragma: no cover
                                else:
                                    target_vars_list.append(new_var_data_to_submit)
                                    st.success(f"Variable '{var_name_val_submit}' ajoutée avec succès.")
                                    # Form cleared by clear_on_submit=True for creation

                            if can_proceed_with_save:
                                current_prompt_config["variables"] = target_vars_list # Ensure list is updated
                                current_prompt_config["updated_at"] = datetime.now().isoformat()
                                save_editable_prompts_to_gist()
                                # st.session_state.view_mode = "edit" # Already in edit mode
                                if not is_editing_var: # Reset type selection for next creation
                                    st.session_state.variable_type_to_create = None
                                st.rerun()
                # Fin du 'if submitted_specific_var_form:'

                # Bouton Annuler (MODIFIÉ : c'est un st.button, pas un st.form_submit_button)
                # Il est DANS le formulaire, mais n'est pas le bouton de soumission principal.
                cancel_button_label_form = "Annuler Modification" if is_editing_var else "Changer de Type / Annuler Création"
                # Utiliser une clé unique pour le bouton d'annulation
                cancel_btn_key = f"cancel_var_action_btn_{form_var_specific_key}"
                if st.button(cancel_button_label_form, key=cancel_btn_key, help="Réinitialise le formulaire de variable."):
                    st.session_state.variable_type_to_create = None # Retour à la sélection du type
                    if is_editing_var:
                        st.session_state.editing_variable_info = None # Annuler l'édition en cours
                    st.rerun()
            # Fin du 'with st.form(...)'
        # Fin du 'if st.session_state.variable_type_to_create:'

            st.markdown("---")
            action_cols = st.columns(2)
            with action_cols[0]:
                dup_key = f"dup_uc_btn_{final_selected_family_edition.replace(' ','_')}_{final_selected_use_case_edition.replace(' ','_')}"
                if st.button("🔄 Dupliquer ce Cas d'Usage", key=dup_key): # pragma: no cover
                    original_uc_name_dup = final_selected_use_case_edition
                    new_uc_name_base_dup = f"{original_uc_name_dup} (copie)"
                    new_uc_name_dup = new_uc_name_base_dup
                    copy_count_dup = 1
                    while new_uc_name_dup in st.session_state.editable_prompts[final_selected_family_edition]:
                        new_uc_name_dup = f"{new_uc_name_base_dup} {copy_count_dup}"
                        copy_count_dup += 1
                    st.session_state.editable_prompts[final_selected_family_edition][new_uc_name_dup] = copy.deepcopy(current_prompt_config)
                    now_iso_dup_create, now_iso_dup_update = get_default_dates()
                    st.session_state.editable_prompts[final_selected_family_edition][new_uc_name_dup]["created_at"] = now_iso_dup_create
                    st.session_state.editable_prompts[final_selected_family_edition][new_uc_name_dup]["updated_at"] = now_iso_dup_update
                    st.session_state.editable_prompts[final_selected_family_edition][new_uc_name_dup]["usage_count"] = 0
                    save_editable_prompts_to_gist()
                    st.success(f"Cas d'usage '{original_uc_name_dup}' dupliqué en '{new_uc_name_dup}'.")
                    st.session_state.force_select_family_name = final_selected_family_edition
                    st.session_state.force_select_use_case_name = new_uc_name_dup
                    st.session_state.active_generated_prompt = ""
                    st.session_state.variable_type_to_create = None 
                    st.session_state.editing_variable_info = None   
                    st.rerun()

            with action_cols[1]:
                del_uc_key_exp = f"del_uc_btn_exp_{final_selected_family_edition.replace(' ','_')}_{final_selected_use_case_edition.replace(' ','_')}"
                # Check if a delete confirmation is already for THIS use case
                is_confirming_this_uc_delete = bool(
                    st.session_state.confirming_delete_details and
                    st.session_state.confirming_delete_details.get("family") == final_selected_family_edition and
                    st.session_state.confirming_delete_details.get("use_case") == final_selected_use_case_edition
                )
                
                if st.button("🗑️ Supprimer Cas d'Usage", key=del_uc_key_exp, type="secondary", disabled=is_confirming_this_uc_delete):
                    st.session_state.confirming_delete_details = {"family": final_selected_family_edition, "use_case": final_selected_use_case_edition}
                    st.rerun() # Rerun to show confirmation dialog above the expander

        # Fin du 'with st.expander(...) pour Paramétrage'
        if st.session_state.get('go_to_config_section'): # Reset flag after expander is processed
            st.session_state.go_to_config_section = False 
    else: # Cas où final_selected_family_edition ou final_selected_use_case_edition est None ou invalide mais view_mode est "edit"
        if not final_selected_family_edition:
             st.info("Veuillez sélectionner une famille dans la barre latérale (onglet Génération & Édition) pour commencer.")
        elif not final_selected_use_case_edition:
             st.info(f"Veuillez sélectionner un cas d'usage pour la famille '{final_selected_family_edition}' ou en créer un.")
        else: # Les sélections sont là mais ne correspondent pas à des données valides (ex: supprimées)
            st.warning(f"Le cas d'usage '{final_selected_use_case_edition}' dans la famille '{final_selected_family_edition}' semble introuvable. Il a peut-être été supprimé. Veuillez vérifier vos sélections.") # pragma: no cover
            # Tentative de réinitialisation douce
            st.session_state.use_case_selector_edition = None
            # Ne pas faire de rerun automatique ici pour éviter les boucles si le problème persiste.

else: # Ni library ni edit, ou conditions non remplies
    if not any(st.session_state.editable_prompts.values()): # pragma: no cover
        st.warning("Aucune famille de cas d'usage n'est configurée. Veuillez en créer une via l'onglet 'Génération & Édition' ou vérifier votre Gist.")
    elif st.session_state.view_mode not in ["library", "edit"]: # pragma: no cover
        # Fallback si view_mode est invalide, default to library if possible
        st.session_state.view_mode = "library" if list(st.session_state.editable_prompts.keys()) else "edit"
        st.rerun()


# --- Sidebar Footer ---
st.sidebar.markdown("---")
st.sidebar.info(f"Générateur v3.3 - © {CURRENT_YEAR} La Poste (démo)")
