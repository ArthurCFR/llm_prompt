import streamlit as st
from datetime import datetime, date
import copy 
from collections import defaultdict
import json
import requests

# --- PAGE CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Générateur de Prompts IA")

# --- Initial Data Structure ---
CURRENT_YEAR = datetime.now().year
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
                {"name": "num_commande", "label": "Numéro de commande", "type": "text_input", "default": "CMD202400123"},
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
def parse_default_value(value_str, var_type):
    if not value_str:
        if var_type == "number_input": return 0
        if var_type == "date_input": return datetime.now().date()
        return None
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
    for family_config in processed_data.values():
        for use_case_config in family_config.values():
            for var_info in use_case_config.get("variables", []):
                if var_info.get("type") == "date_input" and isinstance(var_info.get("default"), date):
                    var_info["default"] = var_info["default"].strftime("%Y-%m-%d")
    return processed_data

def _postprocess_after_loading(loaded_data):
    processed_data = copy.deepcopy(loaded_data)
    for family_config in processed_data.values():
        for use_case_config in family_config.values():
            for var_info in use_case_config.get("variables", []):
                if var_info.get("type") == "date_input" and isinstance(var_info.get("default"), str):
                    try:
                        var_info["default"] = datetime.strptime(var_info["default"], "%Y-%m-%d").date()
                    except ValueError:
                        var_info["default"] = datetime.now().date()
    return processed_data

# --- Gist Interaction Functions (no change in their core logic, only data structure they handle) ---
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
            if not loaded_data or not isinstance(loaded_data, dict): # Basic check for valid structure
                raise ValueError("Contenu Gist vide ou mal structuré.")
            return _postprocess_after_loading(loaded_data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            st.info(f"Erreur chargement Gist ({e}). Initialisation avec modèles par défaut.")
    else: # raw_content is None or empty string from get_gist_content
        st.info("Gist vide ou inaccessible. Initialisation avec modèles par défaut.")

    # Fallback: Initialize and try to save defaults to Gist
    initial_data = copy.deepcopy(INITIAL_PROMPT_TEMPLATES)
    data_to_save = _preprocess_for_saving(initial_data)
    try:
        json_string = json.dumps(data_to_save, indent=4, ensure_ascii=False)
        if update_gist_content(GIST_ID, GITHUB_PAT, json_string):
            st.info("Modèles par défaut sauvegardés sur Gist pour initialisation.")
        else:
            st.error("Échec sauvegarde modèles par défaut sur Gist.")
    except Exception as e:
        st.error(f"Erreur sauvegarde initiale sur Gist: {e}")
    return initial_data

# --- Session State Initialization ---
if 'editable_prompts' not in st.session_state:
    st.session_state.editable_prompts = load_editable_prompts_from_gist()

# Widget keys for selections
if 'family_selector' not in st.session_state:
    families_on_load = list(st.session_state.editable_prompts.keys())
    st.session_state.family_selector = families_on_load[0] if families_on_load else None
if 'use_case_selector' not in st.session_state:
    st.session_state.use_case_selector = None # Will be set based on family

if 'editing_variable_info' not in st.session_state:
    st.session_state.editing_variable_info = None # Structure: {"family": f, "use_case": uc, "index": i, "data": d}
if 'show_create_new_use_case_form' not in st.session_state:
    st.session_state.show_create_new_use_case_form = False
if 'force_select_family_name' not in st.session_state:
    st.session_state.force_select_family_name = None
if 'force_select_use_case_name' not in st.session_state:
    st.session_state.force_select_use_case_name = None
if 'confirming_delete_details' not in st.session_state:
    st.session_state.confirming_delete_details = None # Structure: {"family": f, "use_case": uc}


# --- Main App UI ---
st.title("Generateur Avancé de Prompts IA")

# --- Sidebar Navigation ---
st.sidebar.header("Navigation")
available_families = list(st.session_state.editable_prompts.keys())
selected_family_key = 'family_selector'
selected_use_case_key = 'use_case_selector'

# Family Selection
default_family_idx = 0
if st.session_state.force_select_family_name and st.session_state.force_select_family_name in available_families:
    default_family_idx = available_families.index(st.session_state.force_select_family_name)
    st.session_state[selected_family_key] = st.session_state.force_select_family_name # Update widget state for next run
elif st.session_state[selected_family_key] and st.session_state[selected_family_key] in available_families:
    default_family_idx = available_families.index(st.session_state[selected_family_key])
elif available_families:
    st.session_state[selected_family_key] = available_families[0] # Default to first
    default_family_idx = 0

if not available_families:
    st.sidebar.warning("Aucune famille de cas d'usage configurée.")
    st.session_state[selected_family_key] = None # Ensure it's None
else:
    current_family_selection_in_session = st.session_state[selected_family_key]
    
    ui_selected_family = st.sidebar.selectbox(
        "Famille d'usage:",
        options=available_families,
        index=default_family_idx,
        key=selected_family_key # This directly updates st.session_state.family_selector
    )

    # If family changed via UI, reset use case selection state and force_select flags
    if current_family_selection_in_session != ui_selected_family:
        st.session_state[selected_use_case_key] = None
        st.session_state.force_select_use_case_name = None
        st.session_state.force_select_family_name = None # Clear as family is now user-selected
        st.rerun() # Rerun to update use case options for the new family

# Use Case Selection (based on selected family)
current_selected_family_for_logic = st.session_state.get(selected_family_key)
use_cases_in_current_family_options = []
if current_selected_family_for_logic and current_selected_family_for_logic in st.session_state.editable_prompts:
    use_cases_in_current_family_options = list(st.session_state.editable_prompts[current_selected_family_for_logic].keys())

if use_cases_in_current_family_options:
    default_uc_idx = 0
    # Determine default index for use case radio
    if st.session_state.force_select_use_case_name and st.session_state.force_select_use_case_name in use_cases_in_current_family_options:
        default_uc_idx = use_cases_in_current_family_options.index(st.session_state.force_select_use_case_name)
        st.session_state[selected_use_case_key] = st.session_state.force_select_use_case_name # Update widget state
    elif st.session_state.get(selected_use_case_key) and st.session_state[selected_use_case_key] in use_cases_in_current_family_options:
        default_uc_idx = use_cases_in_current_family_options.index(st.session_state[selected_use_case_key])
    elif use_cases_in_current_family_options: # Default to first if no valid selection
        st.session_state[selected_use_case_key] = use_cases_in_current_family_options[0]
        default_uc_idx = 0
    
    current_uc_selection_in_session = st.session_state.get(selected_use_case_key)
    ui_selected_use_case = st.sidebar.radio(
        "Cas d'usage:",
        options=use_cases_in_current_family_options,
        index=default_uc_idx,
        key=selected_use_case_key # This updates st.session_state.use_case_selector
    )
    if current_uc_selection_in_session != ui_selected_use_case:
        st.rerun()

    # Consume force_select flags after they have been used to set indices
    if st.session_state.force_select_family_name: st.session_state.force_select_family_name = None
    if st.session_state.force_select_use_case_name: st.session_state.force_select_use_case_name = None
        
elif current_selected_family_for_logic:
    st.sidebar.info(f"Aucun cas d'usage dans '{current_selected_family_for_logic}'.")
    st.session_state[selected_use_case_key] = None # Ensure no use case is selected

# Get final selections for this run
# These are the values that the widgets have set in st.session_state
final_selected_family = st.session_state.get(selected_family_key)
final_selected_use_case = st.session_state.get(selected_use_case_key) if use_cases_in_current_family_options else None


st.sidebar.markdown("---")
if available_families: # Can only create use cases if families exist
    if st.sidebar.button("➕ Créer un Cas d'Usage", key="toggle_create_form_btn"):
        st.session_state.show_create_new_use_case_form = not st.session_state.show_create_new_use_case_form
        if not st.session_state.show_create_new_use_case_form: st.rerun()

if st.session_state.show_create_new_use_case_form and available_families:
    with st.sidebar.expander("Nouveau Cas d'Usage", expanded=True):
        with st.form("new_use_case_form", clear_on_submit=True):
            # Select family for the new use case
            default_creation_family_idx = available_families.index(final_selected_family) if final_selected_family and final_selected_family in available_families else 0
            uc_parent_family = st.selectbox("Famille Parente:", options=available_families, index=default_creation_family_idx, key="new_uc_parent_family")
            
            uc_name = st.text_input("Nom du Cas d'Usage (unique dans la famille):", key="new_uc_name")
            uc_template = st.text_area("Template Initial:", height=100, key="new_uc_template")
            submitted_new_uc = st.form_submit_button("Créer Cas d'Usage")

            if submitted_new_uc:
                parent_family_val = st.session_state.new_uc_parent_family # Get from key
                if not uc_name.strip():
                    st.error("Nom du cas d'usage requis.")
                elif uc_name in st.session_state.editable_prompts.get(parent_family_val, {}):
                    st.error(f"'{uc_name}' existe déjà dans la famille '{parent_family_val}'.")
                else:
                    if parent_family_val not in st.session_state.editable_prompts:
                         st.session_state.editable_prompts[parent_family_val] = {} # Should not happen if options are from keys
                    st.session_state.editable_prompts[parent_family_val][uc_name] = {"template": uc_template or "Nouveau prompt...", "variables": []}
                    save_editable_prompts_to_gist()
                    st.success(f"Cas d'usage '{uc_name}' créé dans '{parent_family_val}'.")
                    st.session_state.show_create_new_use_case_form = False
                    st.session_state.force_select_family_name = parent_family_val
                    st.session_state.force_select_use_case_name = uc_name
                    st.rerun()

# --- Main Display Area ---
if final_selected_family and final_selected_use_case and \
   final_selected_family in st.session_state.editable_prompts and \
   final_selected_use_case in st.session_state.editable_prompts[final_selected_family]:
    
    current_prompt_config = st.session_state.editable_prompts[final_selected_family][final_selected_use_case]
    st.header(f"Famille: {final_selected_family}  >  Cas d'usage: {final_selected_use_case}")

    # Delete Confirmation Logic
    if st.session_state.confirming_delete_details and \
       st.session_state.confirming_delete_details["family"] == final_selected_family and \
       st.session_state.confirming_delete_details["use_case"] == final_selected_use_case:
        
        details = st.session_state.confirming_delete_details
        st.warning(f"Supprimer '{details['use_case']}' de la famille '{details['family']}' ? Action irréversible.")
        c1, c2, _ = st.columns([1,1,3])
        if c1.button(f"Oui, supprimer '{details['use_case']}'", key=f"del_yes_{details['family']}_{details['use_case']}", type="primary"):
            del st.session_state.editable_prompts[details["family"]][details["use_case"]]
            save_editable_prompts_to_gist()
            st.success(f"'{details['use_case']}' supprimé de '{details['family']}'.")
            st.session_state.confirming_delete_details = None
            st.session_state.force_select_family_name = details["family"] # Reselect same family
            st.session_state.force_select_use_case_name = None # Let sidebar pick next/first or show none
            if st.session_state.editing_variable_info and \
               st.session_state.editing_variable_info.get("family") == details["family"] and \
               st.session_state.editing_variable_info.get("use_case") == details["use_case"]:
                st.session_state.editing_variable_info = None
            st.rerun()
        if c2.button("Non, annuler", key=f"del_no_{details['family']}_{details['use_case']}"):
            st.session_state.confirming_delete_details = None
            st.rerun()
        st.markdown("---")

    with st.expander("⚙️ Gérer le modèle de prompt", expanded=False):
        # Edit Template
        st.subheader("Template du Prompt")
        tpl_key = f"tpl_{final_selected_family}_{final_selected_use_case}"
        new_tpl = st.text_area("Template:", value=current_prompt_config['template'], height=200, key=tpl_key)
        if st.button("Sauvegarder Template", key=f"save_tpl_{tpl_key}"):
            st.session_state.editable_prompts[final_selected_family][final_selected_use_case]['template'] = new_tpl
            save_editable_prompts_to_gist()
            st.success("Template sauvegardé!")
            st.rerun()

        st.markdown("---")
        st.subheader("Variables du Prompt")
        if not current_prompt_config['variables']:
            st.info("Aucune variable définie.")

        for idx, var_data in enumerate(list(current_prompt_config['variables'])):
            var_disp_key = f"var_disp_{final_selected_family}_{final_selected_use_case}_{idx}"
            col1, col2, col3 = st.columns([4,1,1])
            col1.markdown(f"**{var_data['name']}** ({var_data['label']}) - Type: `{var_data['type']}`")
            if col2.button("Modifier", key=f"edit_var_{var_disp_key}"):
                st.session_state.editing_variable_info = {"family": final_selected_family, "use_case": final_selected_use_case, "index": idx, "data": copy.deepcopy(var_data)}
                st.rerun()
            if col3.button("Suppr.", key=f"del_var_{var_disp_key}"):
                st.session_state.editable_prompts[final_selected_family][final_selected_use_case]['variables'].pop(idx)
                if st.session_state.editing_variable_info and st.session_state.editing_variable_info.get("index") == idx and \
                   st.session_state.editing_variable_info.get("use_case") == final_selected_use_case and \
                   st.session_state.editing_variable_info.get("family") == final_selected_family:
                    st.session_state.editing_variable_info = None
                save_editable_prompts_to_gist()
                st.rerun()
        
        st.markdown("---")
        # Add/Edit Variable Form
        is_editing_var = False
        form_var_key_base = f"form_var_{final_selected_family}_{final_selected_use_case}"
        var_submit_label = "Ajouter Variable"
        var_form_header = "Ajouter Nouvelle Variable"
        var_defaults = {"name": "", "label": "", "type": "text_input", "options": "", "default": ""}

        if st.session_state.editing_variable_info and \
           st.session_state.editing_variable_info["family"] == final_selected_family and \
           st.session_state.editing_variable_info["use_case"] == final_selected_use_case:
            
            edit_var_idx = st.session_state.editing_variable_info["index"]
            # Check if index is still valid
            if edit_var_idx < len(st.session_state.editable_prompts[final_selected_family][final_selected_use_case]['variables']):
                is_editing_var = True
                var_form_header = f"Modifier Variable: {st.session_state.editing_variable_info['data'].get('name', '')}"
                var_submit_label = "Sauvegarder Modifications"
                var_defaults.update(st.session_state.editing_variable_info['data'])
                var_defaults["options"] = ", ".join(st.session_state.editing_variable_info['data'].get("options", []))
                raw_def = st.session_state.editing_variable_info['data'].get("default")
                var_defaults["default"] = raw_def.strftime("%Y-%m-%d") if isinstance(raw_def, date) else str(raw_def or "")
                form_var_key_base += f"_edit_{edit_var_idx}"
            else: # Index out of bounds, reset editing
                st.session_state.editing_variable_info = None


        with st.form(key=form_var_key_base, clear_on_submit=not is_editing_var):
            st.subheader(var_form_header)
            var_name = st.text_input("Nom variable (unique)", value=var_defaults["name"], key=f"{form_var_key_base}_name")
            # ... (rest of variable form fields: label, type, options, default) ...
            var_label = st.text_input("Label pour l'utilisateur", value=var_defaults["label"], key=f"{form_var_key_base}_label")
            var_type_opts = ["text_input", "selectbox", "date_input", "number_input", "text_area"]
            var_type_idx = var_type_opts.index(var_defaults["type"]) if var_defaults["type"] in var_type_opts else 0
            var_type = st.selectbox("Type de variable", var_type_opts, index=var_type_idx, key=f"{form_var_key_base}_type")
            
            var_options_val = ""
            if var_type == "selectbox":
                var_options_val = st.text_input("Options (séparées par virgule)", value=var_defaults["options"], key=f"{form_var_key_base}_options")
            
            var_default_val_str = st.text_input("Valeur par défaut (optionnel, YYYY-MM-DD pour dates)", value=var_defaults["default"], key=f"{form_var_key_base}_default")

            if st.form_submit_button(var_submit_label):
                if not var_name or not var_label:
                    st.error("Nom et label de variable requis.")
                else:
                    new_var_data = {"name": var_name, "label": var_label, "type": var_type}
                    if var_type == "selectbox":
                        new_var_data["options"] = [opt.strip() for opt in var_options_val.split(',') if opt.strip()]
                    
                    parsed_def = parse_default_value(var_default_val_str, var_type)
                    if var_type == "selectbox" and new_var_data.get("options"):
                        if parsed_def not in new_var_data["options"]:
                            st.warning(f"Défaut '{parsed_def}' non dans options. Premier sera utilisé.")
                            new_var_data["default"] = new_var_data["options"][0] if new_var_data["options"] else None
                        else: new_var_data["default"] = parsed_def
                    else: new_var_data["default"] = parsed_def

                    if is_editing_var:
                        idx_to_edit = st.session_state.editing_variable_info["index"]
                        st.session_state.editable_prompts[final_selected_family][final_selected_use_case]['variables'][idx_to_edit] = new_var_data
                        st.success("Variable mise à jour.")
                        st.session_state.editing_variable_info = None
                    else:
                        st.session_state.editable_prompts[final_selected_family][final_selected_use_case]['variables'].append(new_var_data)
                        st.success("Variable ajoutée.")
                    save_editable_prompts_to_gist()
                    st.rerun()
        
        if is_editing_var and st.session_state.editing_variable_info: # Cancel edit button
            if st.button("Annuler Modification Variable", key=f"cancel_edit_var_{form_var_key_base}"):
                st.session_state.editing_variable_info = None
                st.rerun()

        st.markdown("---")
        st.subheader("Supprimer ce Cas d'Usage")
        del_uc_key = f"del_uc_btn_{final_selected_family}_{final_selected_use_case}"
        disable_del_uc = bool(st.session_state.confirming_delete_details and \
                              st.session_state.confirming_delete_details["family"] == final_selected_family and \
                              st.session_state.confirming_delete_details["use_case"] == final_selected_use_case)
        if st.button("🗑️ Supprimer Cas d'Usage", key=del_uc_key, type="secondary", disabled=disable_del_uc):
            st.session_state.confirming_delete_details = {"family": final_selected_family, "use_case": final_selected_use_case}
            st.rerun()

    # Generate Prompt Section
    st.markdown("---")
    st.header(f"Générer Prompt: {final_selected_use_case}")
    # ... (Form for filling variables and generating prompt - adapt keys and access to current_prompt_config) ...
    # This part should be relatively similar, ensure current_prompt_config is correctly used.
    # Key for the form: f"gen_form_{final_selected_family}_{final_selected_use_case}"
    # Keys for widgets inside form: f"gen_input_{final_selected_family}_{final_selected_use_case}_{var_info['name']}"

    gen_form_values = {}
    with st.form(key=f"gen_form_{final_selected_family}_{final_selected_use_case}"):
        if not current_prompt_config["variables"]:
            st.info("Ce cas d'usage n'a pas de variables définies.")
        
        cols_per_row = 2 if len(current_prompt_config["variables"]) > 1 else 1
        var_chunks = [current_prompt_config["variables"][i:i + cols_per_row] for i in range(0, len(current_prompt_config["variables"]), cols_per_row)]

        for chunk in var_chunks:
            cols = st.columns(len(chunk))
            for i, var_info in enumerate(chunk):
                with cols[i]:
                    widget_key = f"gen_input_{final_selected_family}_{final_selected_use_case}_{var_info['name']}"
                    field_default = var_info.get("default")
                    # ... (logic for text_input, selectbox, date_input, number_input, text_area based on var_info["type"]) ...
                    # This logic can be largely reused, just ensure widget_key is unique
                    if var_info["type"] == "text_input":
                        gen_form_values[var_info["name"]] = st.text_input(var_info["label"], value=str(field_default or ""), key=widget_key)
                    elif var_info["type"] == "selectbox":
                        opts = var_info.get("options", [])
                        idx = opts.index(field_default) if field_default in opts else 0
                        gen_form_values[var_info["name"]] = st.selectbox(var_info["label"], options=opts, index=idx, key=widget_key)
                    elif var_info["type"] == "date_input":
                        val_date = field_default if isinstance(field_default, date) else datetime.now().date()
                        gen_form_values[var_info["name"]] = st.date_input(var_info["label"], value=val_date, key=widget_key)
                    elif var_info["type"] == "number_input":
                        val_num = field_default if isinstance(field_default, (int,float)) else 0
                        gen_form_values[var_info["name"]] = st.number_input(var_info["label"], value=val_num, min_value=var_info.get("min_value"), max_value=var_info.get("max_value"), step=var_info.get("step",1), key=widget_key)
                    elif var_info["type"] == "text_area":
                        gen_form_values[var_info["name"]] = st.text_area(var_info["label"], value=str(field_default or ""), height=var_info.get("height",100), key=widget_key)


        if st.form_submit_button("Générer Prompt"):
            final_vals_for_prompt = {k: (v.strftime("%d/%m/%Y") if isinstance(v, date) else v) for k, v in gen_form_values.items()}
            try:
                class SafeFormatter(dict):
                    def __missing__(self, key): return f"{{{key}}}"
                
                generated_prompt = current_prompt_config["template"].format_map(SafeFormatter(final_vals_for_prompt))
                st.subheader("✅ Prompt Généré:")
                st.code(generated_prompt, language=None)
                st.success("Prompt généré !")
                st.info("ATTENTION : copiez le prompt maintenant, il disparaîtra à la fermeture de cette session.")
                st.balloons()
            except Exception as e:
                st.error(f"Erreur génération prompt: {e}")

elif not available_families:
    st.info("Commencez par configurer des familles (via le code initial ou une future fonctionnalité de gestion).")
elif not final_selected_family:
    st.info("Sélectionnez une famille dans la barre latérale.")
else: # Family selected, but no use case or invalid use case
    st.info(f"Sélectionnez un cas d'usage pour la famille '{final_selected_family}' ou créez-en un.")

# --- Sidebar Footer ---
st.sidebar.markdown("---")
st.sidebar.info(f"Version avec Familles - © {CURRENT_YEAR} Votre Organisation")
