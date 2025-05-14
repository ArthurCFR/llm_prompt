import streamlit as st
from datetime import datetime, date
import copy # Nécessaire pour deepcopy
from collections import defaultdict # Importation de defaultdict
import json
import requests # For GitHub Gist API

# --- PAGE CONFIGURATION (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(layout="wide", page_title="Générateur de Prompts IA")

# --- Définition des Modèles de Prompts Initiaux ---
CURRENT_YEAR = datetime.now().year
INITIAL_PROMPT_TEMPLATES = {
    "Recherche de Fournisseurs": {
        "template": "Recherche dans la base de données quels sont les fournisseurs de {legume} les {critere_prix} entre l'année {annee_debut} et l'année {annee_fin}.",
        "variables": [
            {"name": "legume", "label": "Quel légume/produit recherchez-vous ?", "type": "text_input", "default": "tomates"},
            {"name": "critere_prix", "label": "Quel critère de prix ?", "type": "selectbox", "options": ["moins chers", "plus chers", "mieux notés"], "default": "moins chers"},
            {"name": "annee_debut", "label": "Année de début de la recherche", "type": "selectbox", "options": list(range(CURRENT_YEAR - 5, CURRENT_YEAR + 1)), "default": CURRENT_YEAR -1 },
            {"name": "annee_fin", "label": "Année de fin de la recherche", "type": "selectbox", "options": list(range(CURRENT_YEAR - 5, CURRENT_YEAR + 2)), "default": CURRENT_YEAR},
        ]
    },
    "Génération d'Email de Suivi Client": {
        "template": "Rédige un email de suivi pour {nom_client} concernant sa commande {num_commande} passée le {date_commande}. L'email doit avoir un ton {ton_email} et mentionner que nous attendons son retour sur {point_feedback}.",
        "variables": [
            {"name": "nom_client", "label": "Nom du client (ex: M. Martin)", "type": "text_input", "default": "M. Dupont"},
            {"name": "num_commande", "label": "Numéro de commande", "type": "text_input", "default": "CMD202400123"},
            {"name": "date_commande", "label": "Date de la commande", "type": "date_input", "default": date(CURRENT_YEAR, 1, 15)},
            {"name": "ton_email", "label": "Ton de l'email", "type": "selectbox", "options": ["professionnel", "amical", "formel", "enthousiaste"], "default": "professionnel"},
            {"name": "point_feedback", "label": "Point spécifique pour feedback (ex: son expérience avec le produit X)", "type": "text_input", "default": "son expérience avec notre nouveau service"},
        ]
    },
    "Résumé de Document": {
        "template": "Résume le document suivant en {nombre_points} points clés pour un public de {public_cible}. Le résumé doit se concentrer sur les aspects de {focus_resume}. Le style de résumé doit être {style_resume}. Voici le texte à résumer : \n\n{texte_document}",
        "variables": [
            {"name": "nombre_points", "label": "Nombre de points clés souhaités", "type": "number_input", "default": 3, "min_value":1, "max_value":10, "step":1},
            {"name": "public_cible", "label": "Public cible du résumé", "type": "selectbox", "options": ["direction", "équipe technique", "clients", "partenaires", "grand public"], "default": "direction"},
            {"name": "focus_resume", "label": "Focus principal du résumé", "type": "selectbox", "options": ["aspects techniques", "impacts financiers", "prochaines étapes", "conclusions principales", "avantages concurrentiels"], "default": "conclusions principales"},
            {"name": "style_resume", "label": "Style du résumé", "type": "selectbox", "options": ["concis et direct", "détaillé", "orienté action", "informatif neutre"], "default": "concis et direct"},
            {"name": "texte_document", "label": "Collez ici le texte à résumer", "type": "text_area", "height": 200, "default": "Veuillez coller le texte du document ici..."},
        ]
    }
}
GIST_DATA_FILENAME = "prompt_templates_data.json"

# --- Fonctions Utilitaires (pour la gestion des données et dates) ---
def parse_default_value(value_str, var_type):
    """Tente de convertir la valeur par défaut string au type approprié."""
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
            if isinstance(value_str, date): return value_str
            return datetime.now().date()
    return value_str

def _preprocess_for_saving(data_to_save):
    """Converts date objects to strings for JSON serialization."""
    processed_data = copy.deepcopy(data_to_save)
    for _, config in processed_data.items():
        for var_info in config.get("variables", []):
            if var_info.get("type") == "date_input" and isinstance(var_info.get("default"), date):
                var_info["default"] = var_info["default"].strftime("%Y-%m-%d")
    return processed_data

def _postprocess_after_loading(loaded_data):
    """Converts date strings back to date objects after JSON loading."""
    processed_data = copy.deepcopy(loaded_data)
    for _, config in processed_data.items():
        for var_info in config.get("variables", []):
            if var_info.get("type") == "date_input" and isinstance(var_info.get("default"), str):
                try:
                    var_info["default"] = datetime.strptime(var_info["default"], "%Y-%m-%d").date()
                except ValueError:
                    var_info["default"] = datetime.now().date() # Fallback if string is not a valid date
    return processed_data

# --- Fonctions pour l'interaction avec GitHub Gist ---
def get_gist_content(gist_id, github_pat):
    """Fetches the content of the specified file in a Gist."""
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
        st.error(f"Erreur Gist (get): Impossible de récupérer les données du Gist: {e}")
        return None
    except KeyError: 
        st.error(f"Erreur Gist (get): Structure de Gist inattendue ou fichier '{GIST_DATA_FILENAME}' non trouvé.")
        return None

def update_gist_content(gist_id, github_pat, new_content_json_string):
    """Updates the content of a file in a Gist."""
    headers = {"Authorization": f"token {github_pat}", "Accept": "application/vnd.github.v3+json"}
    data = {
        "files": {
            GIST_DATA_FILENAME: {
                "content": new_content_json_string
            }
        }
    }
    try:
        response = requests.patch(f"https://api.github.com/gists/{gist_id}", headers=headers, json=data)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur Gist (update): Impossible de mettre à jour les données du Gist: {e}")
        return False

def save_editable_prompts_to_gist():
    """Saves the current editable_prompts to GitHub Gist."""
    GIST_ID = st.secrets.get("GIST_ID")
    GITHUB_PAT = st.secrets.get("GITHUB_PAT")

    if not GIST_ID or not GITHUB_PAT:
        st.error("Configuration Gist manquante (GIST_ID ou GITHUB_PAT dans les secrets Streamlit). Sauvegarde impossible.")
        return

    if 'editable_prompts' in st.session_state:
        data_to_save_processed = _preprocess_for_saving(st.session_state.editable_prompts)
        try:
            json_string_to_save = json.dumps(data_to_save_processed, indent=4, ensure_ascii=False)
            if not update_gist_content(GIST_ID, GITHUB_PAT, json_string_to_save):
                st.warning("La sauvegarde vers Gist a échoué (voir erreurs ci-dessus), mais les données de session sont intactes.")
        except Exception as e:
            st.error(f"Erreur lors de la préparation des données pour Gist : {e}")

def load_editable_prompts_from_gist():
    """Loads editable_prompts from GitHub Gist, or returns initial templates and tries to save them if Gist is empty/new."""
    GIST_ID = st.secrets.get("GIST_ID")
    GITHUB_PAT = st.secrets.get("GITHUB_PAT")

    if not GIST_ID or not GITHUB_PAT:
        st.warning("Configuration Gist manquante (GIST_ID ou GITHUB_PAT dans les secrets Streamlit). Utilisation des modèles par défaut.")
        return copy.deepcopy(INITIAL_PROMPT_TEMPLATES)

    raw_content = get_gist_content(GIST_ID, GITHUB_PAT)

    if raw_content is not None:
        try:
            loaded_data = json.loads(raw_content)
            if not loaded_data: 
                raise ValueError("Contenu du Gist vide ou non structuré. Initialisation.")
            # st.success("Modèles chargés depuis Gist.") # Peut-être un peu verbeux à chaque chargement
            return _postprocess_after_loading(loaded_data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            st.info(f"Erreur/non-conformité lors du chargement depuis Gist ({e}). Utilisation des modèles par défaut et tentative d'initialisation du Gist.")
            initial_prompts_copy = copy.deepcopy(INITIAL_PROMPT_TEMPLATES)
            data_to_save_processed = _preprocess_for_saving(initial_prompts_copy)
            try:
                json_string_to_save = json.dumps(data_to_save_processed, indent=4, ensure_ascii=False)
                if update_gist_content(GIST_ID, GITHUB_PAT, json_string_to_save):
                    st.info("Modèles par défaut sauvegardés sur Gist pour initialisation.")
                else:
                    st.error("Échec de la sauvegarde des modèles par défaut sur Gist lors de l'initialisation.")
            except Exception as save_e:
                 st.error(f"Erreur lors de la sauvegarde initiale sur Gist: {save_e}")
            return initial_prompts_copy
    else:
        st.error("Impossible de récupérer les données du Gist. Utilisation des modèles par défaut.")
        return copy.deepcopy(INITIAL_PROMPT_TEMPLATES)

# --- Initialisation de l'état de session ---
if 'editable_prompts' not in st.session_state:
    st.session_state.editable_prompts = load_editable_prompts_from_gist()
if 'editing_variable_info' not in st.session_state:
    st.session_state.editing_variable_info = None
if 'show_create_new_use_case_form' not in st.session_state:
    st.session_state.show_create_new_use_case_form = False
if 'force_select_use_case_name' not in st.session_state:
    st.session_state.force_select_use_case_name = None
if 'confirming_delete_use_case_name' not in st.session_state: # NOUVELLE VARIABLE D'ÉTAT
    st.session_state.confirming_delete_use_case_name = None


# --- Interface Streamlit (Main app layout starts here) ---
st.title("📧 Générateur de Prompts pour LLM Interne")
st.markdown("Bienvenue ! Sélectionnez un cas d'usage, remplissez les informations, générez votre prompt, ou créez/modifiez des modèles.")

# --- Barre Latérale ---
st.sidebar.header("Navigation")
use_case_options = list(st.session_state.editable_prompts.keys()) 

current_selection_index = 0
if use_case_options: # S'assurer qu'il y a des options avant de calculer l'index
    if st.session_state.force_select_use_case_name and st.session_state.force_select_use_case_name in use_case_options:
        current_selection_index = use_case_options.index(st.session_state.force_select_use_case_name)
        st.session_state.force_select_use_case_name = None
    elif 'main_use_case_selector' in st.session_state and st.session_state.main_use_case_selector in use_case_options:
        current_selection_index = use_case_options.index(st.session_state.main_use_case_selector)
    else: # Défaut au premier si la sélection précédente n'est plus valide ou non définie
        st.session_state.main_use_case_selector = use_case_options[0]
        current_selection_index = 0


if not use_case_options and not st.session_state.show_create_new_use_case_form :
    st.sidebar.warning("Aucun modèle de prompt disponible. Créez-en un !")
    if not st.session_state.show_create_new_use_case_form: 
        st.session_state.show_create_new_use_case_form = True
        st.rerun() 
elif use_case_options:
    selected_use_case_name = st.sidebar.radio(
        "Choisissez un cas d'usage existant :",
        options=use_case_options,
        index=current_selection_index,
        key="main_use_case_selector"
    )

st.sidebar.markdown("---")

if st.sidebar.button("➕ Créer un nouveau cas d'usage", key="toggle_create_form_btn"):
    st.session_state.show_create_new_use_case_form = not st.session_state.show_create_new_use_case_form
    if not st.session_state.show_create_new_use_case_form: 
        st.rerun()


if st.session_state.show_create_new_use_case_form:
    with st.sidebar.expander("Définir un nouveau cas d'usage", expanded=True):
        with st.form("new_use_case_form", clear_on_submit=True):
            new_uc_name = st.text_input("Nom du nouveau cas d'usage (unique)", key="new_uc_name_input")
            new_uc_template = st.text_area("Template initial du prompt (ex: 'Analyse ce {document} pour en extraire les {elements_cles}.')", height=100, key="new_uc_template_input")
            submitted_new_uc = st.form_submit_button("Créer le cas d'usage")

            if submitted_new_uc:
                if not new_uc_name.strip():
                    st.error("Le nom du cas d'usage ne peut pas être vide.")
                elif new_uc_name in st.session_state.editable_prompts:
                    st.error(f"Le cas d'usage '{new_uc_name}' existe déjà. Veuillez choisir un autre nom.")
                else:
                    st.session_state.editable_prompts[new_uc_name] = {
                        "template": new_uc_template if new_uc_template.strip() else "Nouveau prompt pour {variable_exemple}.",
                        "variables": []
                    }
                    save_editable_prompts_to_gist()
                    st.success(f"Cas d'usage '{new_uc_name}' créé avec succès ! Vous pouvez maintenant l'éditer pour ajouter des variables.")
                    st.session_state.show_create_new_use_case_form = False 
                    st.session_state.force_select_use_case_name = new_uc_name 
                    st.rerun()

# --- Affichage Principal ---
if use_case_options and 'selected_use_case_name' in locals() and selected_use_case_name in st.session_state.editable_prompts:
    current_prompt_config = st.session_state.editable_prompts[selected_use_case_name]

    st.header(f"Cas d'usage : {selected_use_case_name}")

    # --- LOGIQUE DE CONFIRMATION DE SUPPRESSION ---
    if st.session_state.confirming_delete_use_case_name == selected_use_case_name:
        st.warning(f"Êtes-vous sûr de vouloir supprimer définitivement le cas d'usage '{selected_use_case_name}' ? Cette action est irréversible et toutes les variables associées seront perdues.")
        col_confirm, col_cancel, _ = st.columns([1,1,3]) 
        with col_confirm:
            if st.button("Oui, supprimer définitivement", key=f"confirm_delete_yes_{selected_use_case_name}", type="primary"):
                deleted_uc_name = st.session_state.confirming_delete_use_case_name
                del st.session_state.editable_prompts[deleted_uc_name]
                save_editable_prompts_to_gist()
                st.success(f"Le cas d'usage '{deleted_uc_name}' a été supprimé.")
                
                st.session_state.confirming_delete_use_case_name = None
                if st.session_state.main_use_case_selector == deleted_uc_name:
                    st.session_state.main_use_case_selector = None 
                
                if st.session_state.editing_variable_info and st.session_state.editing_variable_info.get('use_case') == deleted_uc_name:
                    st.session_state.editing_variable_info = None
                st.rerun()
        with col_cancel:
            if st.button("Non, annuler", key=f"confirm_delete_no_{selected_use_case_name}"):
                st.session_state.confirming_delete_use_case_name = None
                st.rerun()
        st.markdown("---") 
    # --- FIN DE LA LOGIQUE DE CONFIRMATION DE SUPPRESSION ---

    with st.expander("⚙️ Modifier ce modèle de prompt", expanded=False):
        st.subheader("Template du Prompt Actuel")
        template_editor_key = f"template_edit_{selected_use_case_name.replace(' ', '_').replace('{', '').replace('}', '')}"
        new_template_str = st.text_area(
            "Éditez le template (utilisez {nom_variable} pour les placeholders) :",
            value=current_prompt_config['template'], 
            height=150,
            key=template_editor_key
        )
        save_template_button_key = f"save_template_btn_{selected_use_case_name.replace(' ', '_').replace('{', '').replace('}', '')}"
        if st.button("Sauvegarder le Template", key=save_template_button_key):
            st.session_state.editable_prompts[selected_use_case_name]['template'] = new_template_str
            save_editable_prompts_to_gist()
            st.success("Template du prompt mis à jour !")
            st.rerun() 

        st.markdown("---")
        st.subheader("Variables du Prompt")
        if not current_prompt_config['variables']:
            st.info("Aucune variable définie pour ce modèle. Ajoutez-en ci-dessous.")

        for idx, var_data in enumerate(list(current_prompt_config['variables'])): 
            var_key_suffix = f"var_{selected_use_case_name.replace(' ', '_').replace('{', '').replace('}', '')}_{idx}"
            col1, col2, col3 = st.columns([4,1,1])
            with col1:
                st.markdown(f"**{var_data['name']}** ({var_data['label']}) - Type: `{var_data['type']}`")
            with col2:
                if st.button("Modifier", key=f"edit_btn_{var_key_suffix}"):
                    st.session_state.editing_variable_info = {
                        "use_case": selected_use_case_name, "index": idx, "data": copy.deepcopy(var_data)
                    }
                    st.rerun() 
            with col3:
                if st.button("Suppr.", key=f"remove_btn_{var_key_suffix}"):
                    if idx < len(st.session_state.editable_prompts[selected_use_case_name]['variables']):
                        st.session_state.editable_prompts[selected_use_case_name]['variables'].pop(idx)
                        if st.session_state.editing_variable_info and \
                           st.session_state.editing_variable_info['use_case'] == selected_use_case_name and \
                           st.session_state.editing_variable_info['index'] == idx:
                            st.session_state.editing_variable_info = None
                        save_editable_prompts_to_gist()
                        st.rerun() 
        
        st.markdown("---")
        is_editing_mode = False
        form_key_base = f"var_form_{selected_use_case_name.replace(' ', '_').replace('{', '').replace('}', '')}"
        submit_label = "Ajouter la Variable"
        form_header = "Ajouter une Nouvelle Variable"
        default_form_values = {"name": "", "label": "", "type": "text_input", "options": "", "default": ""}

        if st.session_state.editing_variable_info and st.session_state.editing_variable_info['use_case'] == selected_use_case_name:
            edit_idx = st.session_state.editing_variable_info['index']
            if edit_idx < len(st.session_state.editable_prompts[selected_use_case_name]['variables']):
                is_editing_mode = True
                form_key = f"edit_{form_key_base}_{edit_idx}" 
                submit_label = "Sauvegarder les Modifications"
                editing_data = st.session_state.editing_variable_info['data']
                form_header = f"Modifier la Variable : {editing_data.get('name', '')}"
                default_form_values.update(editing_data)
                default_form_values["options"] = ", ".join(editing_data.get("options", []))
                raw_default = editing_data.get("default")
                if isinstance(raw_default, date): default_form_values["default"] = raw_default.strftime("%Y-%m-%d")
                else: default_form_values["default"] = str(raw_default) if raw_default is not None else ""
            else: 
                st.session_state.editing_variable_info = None
                form_key = f"add_{form_key_base}" 
        else:
            form_key = f"add_{form_key_base}" 

        with st.form(key=form_key, clear_on_submit=not is_editing_mode): 
            st.subheader(form_header)
            var_name = st.text_input("Nom de la variable (unique, ex: `nom_produit`)", value=default_form_values["name"], key=f"{form_key}_name")
            var_label = st.text_input("Label pour l'utilisateur (ex: 'Quel produit ?')", value=default_form_values["label"], key=f"{form_key}_label")
            var_type_options = ["text_input", "selectbox", "date_input", "number_input", "text_area"]
            var_type_default_index = var_type_options.index(default_form_values["type"]) if default_form_values["type"] in var_type_options else 0
            var_type = st.selectbox("Type de variable", var_type_options, index=var_type_default_index, key=f"{form_key}_type")
            
            var_options_str = "" 
            if var_type == "selectbox":
                var_options_str = st.text_input("Options (pour selectbox, séparées par virgule)", value=default_form_values["options"], key=f"{form_key}_options")
            
            var_default_str = st.text_input("Valeur par défaut (optionnel)", value=default_form_values["default"], help="Pour les dates, utilisez YYYY-MM-DD.", key=f"{form_key}_default")
            
            submitted_var_form = st.form_submit_button(submit_label)

            if submitted_var_form:
                if not var_name or not var_label:
                    st.error("Le nom et le label de la variable sont requis.")
                else:
                    new_var_data = {"name": var_name, "label": var_label, "type": var_type}
                    if var_type == "selectbox":
                        new_var_data["options"] = [opt.strip() for opt in var_options_str.split(',') if opt.strip()]
                    
                    actual_default_value = parse_default_value(var_default_str, var_type)
                    if var_type == "selectbox" and new_var_data.get("options"):
                        if actual_default_value not in new_var_data["options"]:
                            st.warning(f"La valeur par défaut '{actual_default_value}' n'est pas dans les options. La première option ('{new_var_data['options'][0]}') sera utilisée.")
                            new_var_data["default"] = new_var_data["options"][0]
                        else:
                            new_var_data["default"] = actual_default_value
                    elif var_type == "selectbox": 
                         new_var_data["default"] = None
                    else: 
                        new_var_data["default"] = actual_default_value

                    if is_editing_mode and st.session_state.editing_variable_info:
                        edit_idx_val = st.session_state.editing_variable_info['index']
                        if edit_idx_val < len(st.session_state.editable_prompts[selected_use_case_name]['variables']):
                            st.session_state.editable_prompts[selected_use_case_name]['variables'][edit_idx_val] = new_var_data
                            st.success(f"Variable '{var_name}' mise à jour !")
                        else:
                             st.error("Erreur: La variable à modifier n'a pas été trouvée (peut-être supprimée).")
                        st.session_state.editing_variable_info = None 
                    else: 
                        st.session_state.editable_prompts[selected_use_case_name]['variables'].append(new_var_data)
                        st.success(f"Variable '{var_name}' ajoutée !")
                    
                    save_editable_prompts_to_gist()
                    st.rerun() 
        
        if is_editing_mode and st.session_state.editing_variable_info : 
            if st.button("Annuler la Modification", key=f"cancel_edit_var_{form_key_base}"):
                st.session_state.editing_variable_info = None
                st.rerun() 

        st.markdown("---") # AJOUT DU BOUTON DE SUPPRESSION DU CAS D'USAGE
        st.subheader("Supprimer ce cas d'usage")
        delete_button_key = f"delete_uc_btn_{selected_use_case_name.replace(' ', '_').replace('{', '').replace('}', '')}"
        disable_delete_button = (st.session_state.confirming_delete_use_case_name == selected_use_case_name)
        
        if st.button("🗑️ Supprimer ce cas d'usage", key=delete_button_key, type="secondary", disabled=disable_delete_button, help="Supprime définitivement ce cas d'usage."):
            st.session_state.confirming_delete_use_case_name = selected_use_case_name
            st.rerun()
    # FIN DE L'EXPANDER "Modifier ce modèle de prompt"

    st.markdown("---")
    st.header(f"Paramètres pour générer le prompt : {selected_use_case_name}")
    st.markdown("Veuillez remplir les champs ci-dessous.")
    
    form_values = {} 
    main_form_key = f"prompt_fill_form_{selected_use_case_name.replace(' ', '_').replace('{', '').replace('}', '')}"
    with st.form(key=main_form_key):
        num_variables = len(current_prompt_config["variables"])
        if not num_variables:
            st.info("Ce cas d'usage n'a pas encore de variables définies.")
        
        cols_per_row = 2 if num_variables > 1 else 1
        variable_chunks = [current_prompt_config["variables"][i:i + cols_per_row] for i in range(0, num_variables, cols_per_row)]

        for chunk in variable_chunks:
            cols = st.columns(len(chunk))
            for i, var_info in enumerate(chunk):
                with cols[i]:
                    widget_key = f"form_input_{selected_use_case_name.replace(' ', '_').replace('{', '').replace('}', '')}_{var_info['name']}"
                    default_val_for_field = var_info.get("default") 
                    label = var_info["label"]

                    if var_info["type"] == "text_input":
                        form_values[var_info["name"]] = st.text_input(label, value=str(default_val_for_field) if default_val_for_field is not None else "", key=widget_key)
                    elif var_info["type"] == "selectbox":
                        options = var_info.get("options", [])
                        idx = 0
                        if default_val_for_field is not None and default_val_for_field in options:
                            idx = options.index(default_val_for_field)
                        elif options: 
                            idx = 0
                        form_values[var_info["name"]] = st.selectbox(label, options=options, index=idx, key=widget_key)
                    elif var_info["type"] == "date_input":
                        val_date = default_val_for_field if isinstance(default_val_for_field, date) else datetime.now().date()
                        form_values[var_info["name"]] = st.date_input(label, value=val_date, key=widget_key)
                    elif var_info["type"] == "number_input":
                        val_num = default_val_for_field if isinstance(default_val_for_field, (int, float)) else 0
                        form_values[var_info["name"]] = st.number_input(label, value=val_num, 
                                                                        min_value=var_info.get("min_value"), 
                                                                        max_value=var_info.get("max_value"), 
                                                                        step=var_info.get("step", 1), 
                                                                        key=widget_key)
                    elif var_info["type"] == "text_area":
                        form_values[var_info["name"]] = st.text_area(label, value=str(default_val_for_field) if default_val_for_field is not None else "", 
                                                                     height=var_info.get("height", 100), 
                                                                     key=widget_key)
        
        submit_button_main_form = st.form_submit_button("Générer le Prompt")

    if submit_button_main_form:
        final_form_values = {} 
        for name, value in form_values.items():
            if isinstance(value, date): 
                final_form_values[name] = value.strftime("%d/%m/%Y") 
            else: 
                final_form_values[name] = value
        
        try:
            template_to_format = current_prompt_config["template"]
            class SafeFormatter(dict): 
                def __missing__(self, key):
                    return f"{{{key}}}" 

            final_prompt = template_to_format.format_map(SafeFormatter(final_form_values))

            st.subheader("✅ Prompt Généré :")
            st.code(final_prompt, language=None) 
            st.success("Prompt généré avec succès ! Utilisez l'icône de copie ci-dessus.")
            st.balloons()

        except KeyError as e:
            st.error(f"Erreur de formatage: La variable {{{e}}} est dans le template mais pas définie pour ce cas d'usage.")
        except Exception as e:
            st.error(f"Une erreur inattendue est survenue lors de la génération du prompt : {e}")
            st.error("Vérifiez que toutes les variables de votre template (ex: {ma_variable}) correspondent bien aux variables définies et remplies dans les formulaires.")

elif not use_case_options and st.session_state.show_create_new_use_case_form:
    st.info("Veuillez créer votre premier cas d'usage en utilisant le formulaire dans la barre latérale.")
elif not use_case_options:
    st.info("Commencez par créer un nouveau cas d'usage en utilisant le bouton '➕ Créer un nouveau cas d'usage' dans la barre latérale.")
else: 
    st.info("Veuillez sélectionner un cas d'usage dans la barre latérale pour commencer.")

st.sidebar.markdown("---")
st.sidebar.info(
    "Cette application aide à générer des prompts pour le LLM interne, "
    "en simplifiant la personnalisation et la gestion des modèles."
)
st.sidebar.markdown(f"© {CURRENT_YEAR} Votre Organisation")
