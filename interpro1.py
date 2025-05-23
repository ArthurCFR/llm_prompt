import streamlit as st
from datetime import datetime, date
import copy
import json
# import requests # Mis en commentaire car non utilisable directement dans cet environnement de démo.
                 # Pour une exécution locale avec sauvegarde Gist, décommentez et installez la librairie.

# --- PAGE CONFIGURATION (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(layout="wide", page_title="🛠️ L'atelier des prompts IA")

# --- Initial Data Structure & Constants ---
CURRENT_YEAR = datetime.now().year
GIST_DATA_FILENAME = "prompt_templates_data_v3.json" # Nom du fichier dans le Gist

# --- META PROMPT TEMPLATE for the Assistant (Backend) ---
# This is the template that will be filled by the user's answers
# and then given to the user to run in an external LLM.
META_PROMPT_FOR_EXTERNAL_LLM_TEMPLATE = """# MISSION
Tu es un expert en conception de prompts (Prompt Engineer) spécialisé dans la création de prompts systèmes pour des modèles de langage avancés. Ta mission est de générer un "Prompt Cible" hautement efficace, structuré et réutilisable, ainsi que sa configuration JSON pour une application de gestion de prompts. Ce "Prompt Cible" sera ensuite utilisé par un utilisateur final pour réaliser une tâche spécifique.

# CONTEXTE DE LA DEMANDE UTILISATEUR
L'utilisateur souhaite obtenir un "Prompt Cible" capable d'adresser la problématique suivante : `{problematique}`.
Par exemple, si la problématique est "résumer un texte de loi et lister les contraintes financières attenantes", le "Prompt Cible" généré devra guider un LLM pour effectuer cette tâche sur un document pertinent.

# EXIGENCES POUR LE "PROMPT CIBLE" ET SA CONFIGURATION JSON
Le "Prompt Cible" et sa configuration JSON que tu vas générer DOIVENT :

## Pour le "Prompt Cible" (le template textuel) :
1.  **Définir clairement le rôle** de l'IA qui exécutera le prompt (par exemple, "Tu es un analyste juridique et financier expert...").
2.  **Spécifier l'objectif principal** de manière concise, basé sur la `{problematique}`.
3.  **Si pertinent, indiquer explicitement que le type de document source** et que l'IA doit être capable de le traiter : `{doc_source}`. Si `{doc_source}` est vide ou non pertinent, n'en fais pas mention.
4.  **Guider l'IA sur les informations spécifiques à extraire.** Ces informations sont : `{elements_specifiques_a_extraire}`.
5.  **Indiquer le format de sortie désiré pour le résultat du prompt cible : `{format_sortie_desire}`.**
6.  **Inclure des instructions pour gérer les ambiguïtés** ou le manque d'information (par exemple, demander des clarifications ou indiquer les limites).
7.  **Être paramétrable via des variables claires et explicites.** Le nombre de variables doit être compris entre {min_var} et {max_var}. Chaque variable doit être encadrée par des accolades simples (ex: `{{variable_name}}`) dans le template du "Prompt Cible".
8.  **Spécifier le public cible du résultat de ce prompt : `{public_cible_reponse}`.**

## Pour la configuration JSON (qui encapsule le "Prompt Cible") :
1.  **Suggérer un nom pour le cas d'usage** (`suggested_use_case_name`) : descriptif et concis (max 5-7 mots).
2.  **Inclure le "Prompt Cible" textuel** dans le champ `"template"` du JSON.
3.  **Lister et décrire chaque variable** utilisée dans le champ `"variables"` du JSON. Chaque objet variable doit avoir :
    * `"name"`: (string) Le nom technique de la variable (ex: `nom_client`), sans espaces ni caractères spéciaux autres que underscore, correspondant exactement à la variable dans le template.
    * `"label"`: (string) Le label descriptif pour l'utilisateur (ex: "Nom du client").
    * `"type"`: (string) Choisis parmi : `"text_input"`, `"selectbox"`, `"date_input"`, `"number_input"`, `"text_area"`.
    * `"default"`: (string, number, ou boolean) La valeur par défaut. Pour les dates, utilise le format "AAAA-MM-JJ". Si le type est number, la valeur par défaut doit être un nombre.
    * `"options"`: (array of strings, optionnel) Uniquement si `type` est `"selectbox"`. Liste des options.
    * `"min_value"`, `"max_value"`, `"step"`: (number, optionnel) Uniquement si `type` est `"number_input"`. `step` doit être positif.
    * `"height"`: (number, optionnel) Uniquement si `type` est `"text_area"`.
4.  **Proposer une liste de 3 à 5 mots-clés pertinents** (`"tags"`) pour le "Prompt Cible".

# FORMAT DE SORTIE ATTENDU DE TA PART (CE MÉTA-PROMPT)
Tu dois fournir ta réponse sous la forme d'un unique objet JSON. Cet objet JSON DOIT être structuré comme suit, où la clé principale est le nom suggéré pour le cas d'usage, et la valeur est un objet contenant le template, les variables et les tags :

```json
{{
  "Nom Suggéré Pour Le Cas D'Usage": {{
    "template": "Le corps principal du 'Prompt Cible' que tu as conçu. Les variables comme {{ma_variable}} doivent être ici.",
    "variables": [
      {{
        "name": "ma_variable",
        "label": "Label descriptif pour ma_variable",
        "type": "text_input",
        "default": "valeur_par_defaut_pour_ma_variable"
      }}
      // ... autres variables si définies ...
    ],
    "tags": ["mot_cle1", "mot_cle2", "mot_cle3"]
  }}
}}
```
Assure-toi que le JSON que tu génères est valide. Les variables dans le template doivent correspondre exactement aux noms définis dans la section "variables". Le nom du cas d'usage (la clé principale du JSON) doit être le même que celui que tu as mis dans `suggested_use_case_name` à l'étape précédente (mais ici c'est la clé de l'objet).
"""

# --- Variables for the Meta Prompt Assistant Form ---
ASSISTANT_FORM_VARIABLES = [
    {"name": "problematique", "label": "Décrivez la problématique ou la tâche que le prompt cible doit résoudre :", "type": "text_area", "default": "Ex: Résumer un texte de loi et lister les contraintes financières attenantes.", "height": 100},
    {"name": "doc_source", "label": "Type de document source (ex: PDF, e-mail, texte brut) si applicable (laisser vide si non pertinent) :", "type": "text_input", "default": ""},
    {"name": "elements_specifiques_a_extraire", "label": "Informations spécifiques à extraire ou générer par le prompt cible :", "type": "text_area", "default": "Ex: - Points clés du texte\n- Acteurs concernés\n- Dates importantes", "height": 100},
    {"name": "format_sortie_desire", "label": "Format de sortie souhaité pour le résultat du prompt cible :", "type": "text_area", "default": "Ex: Liste à puces concise, suivi d'un résumé de 3 phrases.", "height": 75},
    {"name": "min_var", "label": "Nombre minimum de variables pour le prompt cible :", "type": "number_input", "default": 1, "min_value":0, "max_value":10, "step":1},
    {"name": "max_var", "label": "Nombre maximum de variables pour le prompt cible :", "type": "number_input", "default": 3, "min_value":1, "max_value":15, "step":1},
    {"name": "public_cible_reponse", "label": "Public cible de la réponse générée par le prompt cible :", "type": "text_input", "default": "Experts du domaine"},
]

def get_default_dates():
    now_iso = datetime.now().isoformat()
    return now_iso, now_iso

INITIAL_PROMPT_TEMPLATES = {
    "Achat": {}, "RH": {}, "Finance": {}, "Comptabilité": {}
}

# --- Utility Functions ---
def parse_default_value(value_str, var_type):
    if not value_str: # Handle empty string input
        if var_type == "number_input": return 0.0
        if var_type == "date_input": return datetime.now().date()
        return "" # Default for text_input, text_area, selectbox if empty
    if var_type == "number_input":
        try: return float(value_str)
        except ValueError: return 0.0 # Fallback for invalid number string
    elif var_type == "date_input":
        try: return datetime.strptime(value_str, "%Y-%m-%d").date()
        except (ValueError, TypeError): # Handle parsing errors or if already a date object
            return value_str if isinstance(value_str, date) else datetime.now().date()
    return value_str # For text_input, selectbox (already string), text_area

def _preprocess_for_saving(data_to_save):
    processed_data = copy.deepcopy(data_to_save)
    for family_name in list(processed_data.keys()):
        use_cases_in_family = processed_data[family_name]
        if not isinstance(use_cases_in_family, dict):
            st.error(f"Données corrompues (famille non-dict): '{family_name}'. Suppression.") # pragma: no cover
            del processed_data[family_name] # pragma: no cover
            continue # pragma: no cover
        for use_case_name in list(use_cases_in_family.keys()):
            config = use_cases_in_family[use_case_name]
            if not isinstance(config, dict):
                st.error(f"Données corrompues (cas d'usage non-dict): '{use_case_name}' dans '{family_name}'. Suppression.") # pragma: no cover
                del processed_data[family_name][use_case_name] # pragma: no cover
                continue # pragma: no cover
            
            # Ensure 'variables' is a list
            if not isinstance(config.get("variables"), list):
                config["variables"] = [] # Initialize if missing or wrong type
            
            for var_info in config.get("variables", []):
                if isinstance(var_info, dict):
                    # Convert date objects to string for JSON serialization
                    if var_info.get("type") == "date_input" and isinstance(var_info.get("default"), date):
                        var_info["default"] = var_info["default"].strftime("%Y-%m-%d")
                    
                    # Ensure number_input fields are floats
                    if var_info.get("type") == "number_input":
                        for field in ["default", "min_value", "max_value", "step"]:
                            if field in var_info and var_info[field] is not None:
                                try:
                                    var_info[field] = float(var_info[field])
                                except (ValueError, TypeError): # pragma: no cover
                                    # Handle cases where conversion might fail, set a sensible default
                                    if field == "default": var_info[field] = 0.0
                                    elif field == "step": var_info[field] = 1.0
                                    else: var_info[field] = None # min_value, max_value can be None
                        if "step" not in var_info or var_info.get("step") is None: # Ensure step has a value
                             var_info["step"] = 1.0


            config.setdefault("tags", [])
            if "is_favorite" in config: # pragma: no cover
                del config["is_favorite"] # Old field, remove if present
            config.setdefault("usage_count", 0)
            config.setdefault("created_at", datetime.now().isoformat())
            config.setdefault("updated_at", datetime.now().isoformat())
    return processed_data

def _postprocess_after_loading(loaded_data):
    processed_data = copy.deepcopy(loaded_data)
    now_iso = datetime.now().isoformat() # For new/missing timestamps
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
                    # Convert date strings back to date objects
                    if var_info.get("type") == "date_input" and isinstance(var_info.get("default"), str):
                        try:
                            var_info["default"] = datetime.strptime(var_info["default"], "%Y-%m-%d").date()
                        except ValueError: # If parsing fails, default to today
                            var_info["default"] = datetime.now().date()
                    
                    # Ensure number_input fields are floats
                    if var_info.get("type") == "number_input":
                        for field in ["default", "min_value", "max_value", "step"]:
                            if field in var_info and var_info[field] is not None:
                                try:
                                    var_info[field] = float(var_info[field])
                                except (ValueError, TypeError): # pragma: no cover
                                    if field == "default": var_info[field] = 0.0
                                    elif field == "step": var_info[field] = 1.0
                                    else: var_info[field] = None
                            elif field == "default" and (field not in var_info or var_info[field] is None):
                                var_info[field] = 0.0 # Default to 0.0 if not present
                            elif field == "step" and (field not in var_info or var_info[field] is None):
                                var_info[field] = 1.0 # Default step to 1.0


            config.setdefault("tags", [])
            if not isinstance(config.get("tags"), list): # Ensure tags is always a list
                config["tags"] = []
            if "is_favorite" in config: # pragma: no cover
                del config["is_favorite"]
            config.setdefault("usage_count", 0)
            config.setdefault("created_at", now_iso)
            config.setdefault("updated_at", now_iso)
    return processed_data

def _preprocess_injected_use_case_data(injected_config):
    processed_config = copy.deepcopy(injected_config)
    now_iso_created, now_iso_updated = get_default_dates()

    # Initialize/Overwrite specific fields for new injection
    processed_config["created_at"] = now_iso_created
    processed_config["updated_at"] = now_iso_updated
    processed_config["usage_count"] = 0 # New prompts start with 0 usage

    if "template" not in processed_config or not isinstance(processed_config["template"], str):
        processed_config["template"] = "" 
        st.warning("Cas d'usage injecté sans template valide. Template initialisé à vide.")

    if not isinstance(processed_config.get("variables"), list):
        processed_config["variables"] = []
    
    temp_variables = []
    for var_info in processed_config.get("variables", []):
        if isinstance(var_info, dict):
            if not all(k in var_info for k in ("name", "label", "type")): # Basic validation
                st.warning(f"Variable injectée malformée ignorée : {var_info.get('name', 'NOM_MANQUANT')}")
                continue

            if var_info.get("type") == "date_input":
                if "default" in var_info and isinstance(var_info["default"], str):
                    try: datetime.strptime(var_info["default"], "%Y-%m-%d") # Validate format
                    except ValueError:
                        st.warning(f"Format de date par défaut invalide pour la variable '{var_info['name']}'. Utilisation de la date actuelle.")
                        var_info["default"] = datetime.now().date().strftime("%Y-%m-%d")
                elif "default" in var_info and isinstance(var_info["default"], date): # Should not happen if JSON is pure
                     var_info["default"] = var_info["default"].strftime("%Y-%m-%d")
                else: 
                    var_info["default"] = datetime.now().date().strftime("%Y-%m-%d")

            if var_info.get("type") == "number_input":
                for num_field in ["default", "min_value", "max_value", "step"]:
                    if num_field in var_info and var_info[num_field] is not None:
                        try: var_info[num_field] = float(var_info[num_field])
                        except (ValueError, TypeError): # pragma: no cover
                            st.warning(f"Valeur invalide pour '{num_field}' dans la variable '{var_info['name']}'. Mise à défaut.")
                            if num_field == "default": var_info[num_field] = 0.0
                            elif num_field == "step": var_info[num_field] = 1.0
                            else: var_info[num_field] = None 
                    elif num_field == "default" and (num_field not in var_info or var_info[num_field] is None):
                        var_info[num_field] = 0.0 
                    elif num_field == "step" and (num_field not in var_info or var_info[num_field] is None):
                         var_info[num_field] = 1.0 
            
            if var_info.get("type") == "selectbox":
                if "options" not in var_info or not isinstance(var_info["options"], list):
                    var_info["options"] = []
                    st.warning(f"Options manquantes ou malformées pour la variable selectbox '{var_info['name']}'. Initialisées à vide.")
                else:
                    var_info["options"] = [str(opt) for opt in var_info["options"]] # Ensure strings
                
                # Ensure default is one of the options
                if "default" not in var_info or var_info["default"] not in var_info["options"]:
                    if var_info["options"]:
                        var_info["default"] = var_info["options"][0] # Default to first option
                        st.warning(f"Défaut de la variable selectbox '{var_info['name']}' non valide ou manquant. Premier option utilisée.")
                    else:
                         var_info["default"] = "" # No options, no valid default
            
            temp_variables.append(var_info)
    processed_config["variables"] = temp_variables

    if not isinstance(processed_config.get("tags"), list):
        processed_config["tags"] = []
    else:
        processed_config["tags"] = sorted(list(set(str(tag).strip() for tag in processed_config["tags"] if str(tag).strip())))
    
    if "is_favorite" in processed_config: # pragma: no cover
        del processed_config["is_favorite"]
        
    return processed_config

# --- Gist Interaction Functions (Simulated for environments without 'requests') ---
def get_gist_content(gist_id, github_pat): # pragma: no cover
    # This is a placeholder. In a real environment, you'd use the requests library.
    # For local testing without secrets, this prevents errors.
    if gist_id == "YOUR_GIST_ID_HERE" or github_pat == "YOUR_GITHUB_PAT_HERE":
        st.info("Simulation: Gist non configuré. Retour du contenu Gist vide.")
        return "{}" 
    
    # Simulating an actual API call structure if requests was available
    # headers = {"Authorization": f"token {github_pat}", "Accept": "application/vnd.github.v3+json"}
    # try:
    #     # response = requests.get(f"https://api.github.com/gists/{gist_id}", headers=headers)
    #     # response.raise_for_status() 
    #     # gist_data = response.json()
    #     # if GIST_DATA_FILENAME in gist_data["files"]:
    #     #     return gist_data["files"][GIST_DATA_FILENAME]["content"]
    #     # else:
    #     #     st.info(f"Fichier '{GIST_DATA_FILENAME}' non trouvé dans Gist. Initialisation.")
    #     #     return "{}"
    #     pass # Placeholder for actual request call
    # except Exception as e: # Placeholder for requests.exceptions.RequestException
    #     st.error(f"Erreur Gist (get - simulée): {e}")
    #     return None
    st.warning("Fonctionnalité Gist (get_gist_content) simulée. Impossible de charger depuis GitHub.")
    return "{}" # Return empty JSON string to allow app to initialize

def update_gist_content(gist_id, github_pat, new_content_json_string): # pragma: no cover
    if gist_id == "YOUR_GIST_ID_HERE" or github_pat == "YOUR_GITHUB_PAT_HERE":
        st.info(f"Simulation: Gist non configuré. Contenu à sauvegarder (non envoyé) : {new_content_json_string[:100]}...")
        return True # Simulate success for local testing

    # Simulating an actual API call structure
    # headers = {"Authorization": f"token {github_pat}", "Accept": "application/vnd.github.v3+json"}
    # data = {"files": {GIST_DATA_FILENAME: {"content": new_content_json_string}}}
    # try:
    #     # response = requests.patch(f"https://api.github.com/gists/{gist_id}", headers=headers, json=data)
    #     # response.raise_for_status()
    #     # return True
    #     pass # Placeholder
    # except Exception as e: # Placeholder for requests.exceptions.RequestException
    #     st.error(f"Erreur Gist (update - simulée): {e}")
    #     return False
    st.info(f"Fonctionnalité Gist (update_gist_content) simulée. Sauvegarde sur GitHub désactivée. Contenu : {new_content_json_string[:100]}...")
    return True # Simulate success

def save_editable_prompts_to_gist():
    GIST_ID = st.secrets.get("GIST_ID", "YOUR_GIST_ID_HERE") 
    GITHUB_PAT = st.secrets.get("GITHUB_PAT", "YOUR_GITHUB_PAT_HERE") 
    
    if GIST_ID == "YOUR_GIST_ID_HERE" or GITHUB_PAT == "YOUR_GITHUB_PAT_HERE": # pragma: no cover
        st.sidebar.warning("Secrets Gist non configurés. La sauvegarde sur GitHub est désactivée.")
        return

    if 'editable_prompts' in st.session_state:
        data_to_save = _preprocess_for_saving(st.session_state.editable_prompts)
        try:
            json_string = json.dumps(data_to_save, indent=4, ensure_ascii=False)
            if not update_gist_content(GIST_ID, GITHUB_PAT, json_string): # pragma: no cover
                st.warning("Sauvegarde Gist échouée.") 
        except Exception as e: # pragma: no cover
            st.error(f"Erreur préparation données pour Gist: {e}")

def load_editable_prompts_from_gist():
    GIST_ID = st.secrets.get("GIST_ID", "YOUR_GIST_ID_HERE")
    GITHUB_PAT = st.secrets.get("GITHUB_PAT", "YOUR_GITHUB_PAT_HERE")

    if GIST_ID == "YOUR_GIST_ID_HERE" or GITHUB_PAT == "YOUR_GITHUB_PAT_HERE": # pragma: no cover
        st.sidebar.warning("Secrets Gist non configurés. Utilisation des modèles par défaut locaux.")
        return copy.deepcopy(INITIAL_PROMPT_TEMPLATES)

    raw_content = get_gist_content(GIST_ID, GITHUB_PAT) # Will use simulated version if requests not available
    
    if raw_content and raw_content != "{}": # Avoid parsing empty string from simulation
        try:
            loaded_data = json.loads(raw_content)
            if not loaded_data or not isinstance(loaded_data, dict): 
                raise ValueError("Contenu Gist vide ou mal structuré.")
            return _postprocess_after_loading(loaded_data)
        except (json.JSONDecodeError, TypeError, ValueError) as e: 
            st.info(f"Erreur chargement Gist ({e}). Initialisation avec modèles par défaut.")
    else: 
        st.info("Gist vide ou inaccessible (ou simulation). Initialisation avec modèles par défaut.")
    
    # If loading failed or Gist was empty, initialize and try to save default if Gist seems configured.
    initial_data = copy.deepcopy(INITIAL_PROMPT_TEMPLATES)
    # No attempt to save initial data if Gist is effectively mocked/unavailable
    # This part was causing issues in mocked environments, so it's safer to just return initial_data.
    return initial_data

# --- Session State Initialization ---
if 'editable_prompts' not in st.session_state:
    st.session_state.editable_prompts = load_editable_prompts_from_gist()
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "library"

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
if 'go_to_config_section' not in st.session_state: st.session_state.go_to_config_section = False

if 'injection_selected_family' not in st.session_state:
    st.session_state.injection_selected_family = None
if 'injection_json_text' not in st.session_state:
    st.session_state.injection_json_text = ""

if 'assistant_form_values' not in st.session_state:
    # Initialize with defaults from ASSISTANT_FORM_VARIABLES
    st.session_state.assistant_form_values = {var['name']: var['default'] for var in ASSISTANT_FORM_VARIABLES}
if 'generated_meta_prompt_for_llm' not in st.session_state: 
    st.session_state.generated_meta_prompt_for_llm = ""

# --- Main App UI ---
st.title(f"🛠️ L'atelier des prompts IA")

# --- Sidebar Navigation with Tabs ---
st.sidebar.header("Menu Principal")
tab_bibliotheque, tab_edition_generation, tab_injection = st.sidebar.tabs([
    "📚 Bibliothèque",
    "✍️ Génération & Édition",
    "💉 Injection" 
])

# --- Tab: Génération & Édition (Sidebar content) ---
with tab_edition_generation:
    st.subheader("Explorateur de Prompts")
    available_families = list(st.session_state.editable_prompts.keys())
    default_family_idx_edit = 0
    current_family_for_edit = st.session_state.get('family_selector_edition')

    if st.session_state.force_select_family_name and st.session_state.force_select_family_name in available_families:
        current_family_for_edit = st.session_state.force_select_family_name
        st.session_state.family_selector_edition = current_family_for_edit 
    elif current_family_for_edit and current_family_for_edit in available_families:
        pass 
    elif available_families:
        current_family_for_edit = available_families[0]
        st.session_state.family_selector_edition = current_family_for_edit 
    else:
        current_family_for_edit = None
        st.session_state.family_selector_edition = None 
    
    if current_family_for_edit and current_family_for_edit in available_families:
        default_family_idx_edit = available_families.index(current_family_for_edit)
    elif available_families: 
        default_family_idx_edit = 0
        current_family_for_edit = available_families[0]
        st.session_state.family_selector_edition = current_family_for_edit
    else: 
        default_family_idx_edit = 0 

    if not available_families:
        st.info("Aucune famille de cas d'usage. Créez-en une via les options ci-dessous.")
    else:
        prev_family_selection_edit = st.session_state.get('family_selector_edition') 
        selected_family_ui_edit = st.selectbox(
            "Famille :",
            options=available_families,
            index=default_family_idx_edit, 
            key='family_selectbox_widget_edit',
            help="Sélectionnez une famille pour voir ses cas d'usage."
        )
        if st.session_state.family_selector_edition != selected_family_ui_edit :
             st.session_state.family_selector_edition = selected_family_ui_edit
        
        if prev_family_selection_edit != selected_family_ui_edit:
            st.session_state.use_case_selector_edition = None
            st.session_state.force_select_use_case_name = None 
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
        elif current_uc_for_edit and current_uc_for_edit in use_cases_in_current_family_edit_options:
            pass 
        else: 
            current_uc_for_edit = use_cases_in_current_family_edit_options[0]
        
        st.session_state.use_case_selector_edition = current_uc_for_edit 

        if current_uc_for_edit: 
            default_uc_idx_edit = use_cases_in_current_family_edit_options.index(current_uc_for_edit)
        
        prev_uc_selection_edit = st.session_state.get('use_case_selector_edition') 
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
            st.session_state.view_mode = "edit"
            st.session_state.active_generated_prompt = ""
            st.session_state.variable_type_to_create = None 
            st.session_state.editing_variable_info = None   
            st.rerun()

    elif current_selected_family_for_edit_logic: 
        st.info(f"Aucun cas d'usage dans '{current_selected_family_for_edit_logic}'. Créez-en un.")
        st.session_state.use_case_selector_edition = None 

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
                    st.session_state.force_select_family_name = new_family_name.strip() 
                    st.session_state.use_case_selector_edition = None 
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
                        st.session_state.force_select_family_name = renamed_family_name 
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
        else: 
            st.caption("Sélectionnez une famille (ci-dessus) pour la gérer.")

    st.markdown("---")

    with st.expander("➕ Créer un Cas d'Usage", expanded=st.session_state.get('show_create_new_use_case_form', False)):
        if not available_families:
            st.caption("Veuillez d'abord créer une famille pour y ajouter des cas d'usage.")
        else: 
            if st.button("Afficher/Masquer Formulaire de Création de Cas d'Usage", key="toggle_create_uc_form_in_exp"):
                st.session_state.show_create_new_use_case_form = not st.session_state.get('show_create_new_use_case_form', False)
                st.rerun() 

            if st.session_state.get('show_create_new_use_case_form', False): 
                with st.form("new_use_case_form_in_exp", clear_on_submit=True):
                    default_create_family_idx_tab = 0
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
                        parent_family_val = uc_parent_family 
                        uc_name_val = uc_name_input.strip()
                        uc_template_val = uc_template_input 

                        if not uc_name_val: 
                            st.error("Le nom du cas d'usage ne peut pas être vide.")
                        elif uc_name_val in st.session_state.editable_prompts.get(parent_family_val, {}):
                            st.error(f"Le cas d'usage '{uc_name_val}' existe déjà dans la famille '{parent_family_val}'.")
                        else:
                            now_iso_create, now_iso_update = get_default_dates()
                            st.session_state.editable_prompts[parent_family_val][uc_name_val] = {
                                "template": uc_template_val or "Nouveau prompt...",
                                "variables": [], "tags": [], 
                                "usage_count": 0, "created_at": now_iso_create, "updated_at": now_iso_update
                            }
                            save_editable_prompts_to_gist()
                            st.success(f"Cas d'usage '{uc_name_val}' créé avec succès dans '{parent_family_val}'.")
                            st.session_state.show_create_new_use_case_form = False 
                            st.session_state.force_select_family_name = parent_family_val
                            st.session_state.force_select_use_case_name = uc_name_val
                            st.session_state.view_mode = "edit"
                            st.session_state.active_generated_prompt = "" 
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
                if st.session_state.library_selected_family_for_display != family_name_bib:
                    st.session_state.library_selected_family_for_display = family_name_bib
                    st.session_state.view_mode = "library" 
                    st.rerun() 
        st.markdown("---")

# --- Tab: Injection (Sidebar content) ---
with tab_injection:
    st.subheader("Injection de Cas d'Usage")
    st.markdown("Injectez des cas d'usage en format JSON ou utilisez l'assistant.")
    
    if st.button("💉 Injecter JSON Manuellement", key="start_manual_injection_btn", use_container_width=True):
        st.session_state.view_mode = "inject_manual" 
        st.session_state.injection_selected_family = None 
        st.session_state.injection_json_text = "" 
        st.session_state.generated_meta_prompt_for_llm = "" 
        st.rerun()

    st.markdown("---") 

    if st.button("✨ Créer un usage avec l'assistant", key="start_assistant_creation_btn", use_container_width=True):
        st.session_state.view_mode = "assistant_creation" 
        st.session_state.assistant_form_values = {var['name']: var['default'] for var in ASSISTANT_FORM_VARIABLES} 
        st.session_state.generated_meta_prompt_for_llm = "" 
        st.rerun()

# --- Main Display Area ---
final_selected_family_edition = st.session_state.get('family_selector_edition')
final_selected_use_case_edition = st.session_state.get('use_case_selector_edition')
library_family_to_display = st.session_state.get('library_selected_family_for_display')

if st.session_state.view_mode == "library":
    if not library_family_to_display:
        st.info("Veuillez sélectionner une famille dans la barre latérale (onglet Bibliothèque) pour afficher les prompts.")
        available_families_main_display = list(st.session_state.editable_prompts.keys())
        if available_families_main_display:
            st.session_state.library_selected_family_for_display = available_families_main_display[0]
            st.rerun()
        elif not any(st.session_state.editable_prompts.values()): 
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
                if selected_tags_lib: match_tags = all(tag in uc_config.get("tags", []) for tag in selected_tags_lib)
                if match_search and match_tags: filtered_use_cases[uc_name] = uc_config
        if not filtered_use_cases:
            if not use_cases_in_family_display: st.info(f"La famille '{library_family_to_display}' ne contient actuellement aucun prompt.")
            else: st.info("Aucun prompt ne correspond à vos critères de recherche/filtre dans cette famille.")
        else:
            sorted_use_cases_display = sorted(list(filtered_use_cases.keys()))
            for use_case_name_display in sorted_use_cases_display:
                prompt_config_display = filtered_use_cases[use_case_name_display]
                template_display = prompt_config_display.get("template", "_Template non défini._")
                exp_title = f"{use_case_name_display}"
                if prompt_config_display.get("usage_count", 0) > 0: exp_title += f" (Utilisé {prompt_config_display.get('usage_count')} fois)"
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
                    if tags_display: st.markdown(f"**Tags :** {', '.join([f'`{tag}`' for tag in tags_display])}")
                    created_at_str = prompt_config_display.get('created_at', get_default_dates()[0])
                    updated_at_str = prompt_config_display.get('updated_at', get_default_dates()[1])
                    st.caption(f"Créé le: {datetime.fromisoformat(created_at_str).strftime('%d/%m/%Y %H:%M')} | Modifié le: {datetime.fromisoformat(updated_at_str).strftime('%d/%m/%Y %H:%M')}")
                    st.markdown("---")
                    col_btn_lib1, col_btn_lib2 = st.columns(2)
                    with col_btn_lib1:
                        if st.button(f"✍️ Utiliser ce modèle", key=f"main_lib_use_{library_family_to_display.replace(' ', '_')}_{use_case_name_display.replace(' ', '_')}", use_container_width=True):
                            st.session_state.view_mode = "edit"; st.session_state.force_select_family_name = library_family_to_display; st.session_state.force_select_use_case_name = use_case_name_display; st.session_state.go_to_config_section = False; st.session_state.active_generated_prompt = ""; st.session_state.variable_type_to_create = None; st.session_state.editing_variable_info = None; st.session_state.confirming_delete_details = None; st.rerun()
                    with col_btn_lib2:
                        if st.button(f"⚙️ Éditer ce prompt", key=f"main_lib_edit_{library_family_to_display.replace(' ', '_')}_{use_case_name_display.replace(' ', '_')}", use_container_width=True):
                            st.session_state.view_mode = "edit"; st.session_state.force_select_family_name = library_family_to_display; st.session_state.force_select_use_case_name = use_case_name_display; st.session_state.go_to_config_section = True; st.session_state.active_generated_prompt = ""; st.session_state.variable_type_to_create = None; st.session_state.editing_variable_info = None; st.session_state.confirming_delete_details = None; st.rerun()
    else: 
        st.info("Aucune famille n'est actuellement sélectionnée dans la bibliothèque ou la famille sélectionnée n'existe plus.")
        available_families_check = list(st.session_state.editable_prompts.keys())
        if not available_families_check : st.warning("La bibliothèque est entièrement vide. Veuillez créer des familles et des prompts.")

elif st.session_state.view_mode == "edit":
    if not final_selected_family_edition : st.info("Sélectionnez une famille dans la barre latérale (onglet Génération & Édition) ou créez-en une pour commencer.")
    elif not final_selected_use_case_edition: st.info(f"Sélectionnez un cas d'usage dans la famille '{final_selected_family_edition}' ou créez-en un nouveau pour commencer.")
    elif final_selected_family_edition in st.session_state.editable_prompts and final_selected_use_case_edition in st.session_state.editable_prompts[final_selected_family_edition]:
        current_prompt_config = st.session_state.editable_prompts[final_selected_family_edition][final_selected_use_case_edition]
        st.header(f"Cas d'usage: {final_selected_use_case_edition}")
        created_at_str_edit = current_prompt_config.get('created_at', get_default_dates()[0]); updated_at_str_edit = current_prompt_config.get('updated_at', get_default_dates()[1])
        st.caption(f"Famille: {final_selected_family_edition} | Utilisé {current_prompt_config.get('usage_count', 0)} fois. Créé: {datetime.fromisoformat(created_at_str_edit).strftime('%d/%m/%Y')}, Modifié: {datetime.fromisoformat(updated_at_str_edit).strftime('%d/%m/%Y')}")
        st.markdown("---")
        st.subheader(f"🚀 Générer le Prompt")
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
                                except ValueError: idx = 0 
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
                            gen_form_values[var_info["name"]] = st.number_input(var_info["label"], value=val_num_gen, min_value=min_val_gen,max_value=max_val_gen, step=step_val_gen, key=widget_key, format="%g")
                        elif var_type == "text_area": gen_form_values[var_info["name"]] = st.text_area(var_info["label"], value=str(field_default or ""), height=var_info.get("height",100), key=widget_key)
            if st.form_submit_button("🚀 Générer Prompt"):
                final_vals_for_prompt = { k: (v.strftime("%d/%m/%Y") if isinstance(v, date) else v) for k, v in gen_form_values.items() if v is not None }
                try:
                    class SafeFormatter(dict):
                        def __missing__(self, key):
                            return f"{{{key}}}"
                    prompt_template_content = current_prompt_config.get("template", ""); formatted_template_content = prompt_template_content.format_map(SafeFormatter(final_vals_for_prompt)); use_case_title = final_selected_use_case_edition 
                    generated_prompt = f"Sujet : {use_case_title}\n{formatted_template_content}"
                    st.session_state.active_generated_prompt = generated_prompt; st.success("Prompt généré avec succès!"); st.balloons()
                    current_prompt_config["usage_count"] = current_prompt_config.get("usage_count", 0) + 1; current_prompt_config["updated_at"] = datetime.now().isoformat(); save_editable_prompts_to_gist()
                except Exception as e: st.error(f"Erreur lors de la génération du prompt: {e}") # pragma: no cover
        st.markdown("---")
        if st.session_state.active_generated_prompt:
            st.subheader("✅ Prompt Généré (éditable):")
            edited_prompt_value = st.text_area("Prompt:", value=st.session_state.active_generated_prompt, height=200, key=f"editable_generated_prompt_output_{final_selected_family_edition}_{final_selected_use_case_edition}", label_visibility="collapsed")
            if edited_prompt_value != st.session_state.active_generated_prompt: st.session_state.active_generated_prompt = edited_prompt_value # pragma: no cover
            st.caption("Prompt généré (pour relecture et copie manuelle) :"); st.code(st.session_state.active_generated_prompt, language=None) 
        st.markdown("---")
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
        should_expand_config = st.session_state.get('go_to_config_section', False)
        with st.expander(f"⚙️ Paramétrage du Prompt: {final_selected_use_case_edition}", expanded=should_expand_config):
            st.subheader("Template du Prompt")
            safe_family_key_part = str(final_selected_family_edition).replace(' ', '_').replace('.', '_').replace('{', '_').replace('}', '_').replace('(', '_').replace(')', '_'); safe_uc_key_part = str(final_selected_use_case_edition).replace(' ', '_').replace('.', '_').replace('{', '_').replace('}', '_').replace('(', '_').replace(')', '_')
            template_text_area_key = f"template_text_area_{safe_family_key_part}_{safe_uc_key_part}"; new_tpl = st.text_area("Template:", value=current_prompt_config.get('template', ''), height=200, key=template_text_area_key)
            st.markdown("""<style> div[data-testid="stExpander"] div[data-testid="stCodeBlock"] { margin-top: 0.1rem !important; margin-bottom: 0.15rem !important; padding-top: 0.1rem !important; padding-bottom: 0.1rem !important; } div[data-testid="stExpander"] div[data-testid="stCodeBlock"] pre { padding-top: 0.2rem !important; padding-bottom: 0.2rem !important; line-height: 1.1 !important; font-size: 0.85em !important; margin: 0 !important; } </style>""", unsafe_allow_html=True)
            st.markdown("##### Variables disponibles à insérer :"); variables_config = current_prompt_config.get('variables', [])
            if not variables_config: st.caption("Aucune variable définie pour ce prompt. Ajoutez-en ci-dessous.")
            else:
                col1, col2 = st.columns(2)
                for i, var_info in enumerate(variables_config):
                    if 'name' in var_info:
                        variable_string_to_display = f"{{{var_info['name']}}}"; target_column = col1 if i % 2 == 0 else col2
                        with target_column: st.code(variable_string_to_display, language=None)
                st.caption("Survolez une variable ci-dessus et cliquez sur l'icône qui apparaît pour la copier.")
            save_template_button_key = f"save_template_button_{safe_family_key_part}_{safe_uc_key_part}"
            if st.button("Sauvegarder Template", key=save_template_button_key): current_prompt_config['template'] = new_tpl; current_prompt_config["updated_at"] = datetime.now().isoformat(); save_editable_prompts_to_gist(); st.success("Template sauvegardé!"); st.rerun()
            st.markdown("---"); st.subheader("🏷️ Tags"); current_tags_str = ", ".join(current_prompt_config.get("tags", []))
            new_tags_str_input = st.text_input("Tags (séparés par des virgules):", value=current_tags_str, key=f"tags_input_{final_selected_family_edition}_{final_selected_use_case_edition}")
            if st.button("Sauvegarder Tags", key=f"save_tags_btn_{final_selected_family_edition}_{final_selected_use_case_edition}"): current_prompt_config["tags"] = sorted(list(set(t.strip() for t in new_tags_str_input.split(',') if t.strip()))); current_prompt_config["updated_at"] = datetime.now().isoformat(); save_editable_prompts_to_gist(); st.success("Tags sauvegardés!"); st.rerun()
            st.markdown("---"); st.subheader("Variables du Prompt"); current_variables_list = current_prompt_config.get('variables', [])
            if not current_variables_list: st.info("Aucune variable définie.")
            else: pass 
            for idx, var_data in enumerate(list(current_variables_list)): 
                var_id_for_key = var_data.get('name', f"varidx{idx}").replace(" ", "_"); action_key_prefix = f"var_action_{final_selected_family_edition.replace(' ','_')}_{final_selected_use_case_edition.replace(' ','_')}_{var_id_for_key}"
                col_info, col_up, col_down, col_edit, col_delete = st.columns([3, 0.5, 0.5, 0.8, 0.8])
                with col_info: st.markdown(f"**{idx + 1}. {var_data.get('name', 'N/A')}** ({var_data.get('label', 'N/A')})\n*Type: `{var_data.get('type', 'N/A')}`*")
                with col_up:
                    disable_up_button = (idx == 0)
                    if st.button("↑", key=f"{action_key_prefix}_up", help="Monter cette variable", disabled=disable_up_button, use_container_width=True): current_variables_list[idx], current_variables_list[idx-1] = current_variables_list[idx-1], current_variables_list[idx]; current_prompt_config["variables"] = current_variables_list; current_prompt_config["updated_at"] = datetime.now().isoformat(); save_editable_prompts_to_gist(); st.session_state.editing_variable_info = None; st.session_state.variable_type_to_create = None; st.rerun()
                with col_down:
                    disable_down_button = (idx == len(current_variables_list) - 1)
                    if st.button("↓", key=f"{action_key_prefix}_down", help="Descendre cette variable", disabled=disable_down_button, use_container_width=True): current_variables_list[idx], current_variables_list[idx+1] = current_variables_list[idx+1], current_variables_list[idx]; current_prompt_config["variables"] = current_variables_list; current_prompt_config["updated_at"] = datetime.now().isoformat(); save_editable_prompts_to_gist(); st.session_state.editing_variable_info = None; st.session_state.variable_type_to_create = None; st.rerun()
                with col_edit:
                    if st.button("Modifier", key=f"{action_key_prefix}_edit", use_container_width=True): st.session_state.editing_variable_info = { "family": final_selected_family_edition, "use_case": final_selected_use_case_edition, "index": idx, "data": copy.deepcopy(var_data) }; st.session_state.variable_type_to_create = var_data.get('type'); st.rerun()
                with col_delete:
                    if st.button("Suppr.", key=f"{action_key_prefix}_delete", type="secondary", use_container_width=True): variable_name_to_delete = current_variables_list.pop(idx).get('name', 'Variable inconnue'); current_prompt_config["variables"] = current_variables_list; current_prompt_config["updated_at"] = datetime.now().isoformat(); save_editable_prompts_to_gist(); st.success(f"Variable '{variable_name_to_delete}' supprimée."); st.session_state.editing_variable_info = None; st.session_state.variable_type_to_create = None; st.rerun()
            st.markdown("---"); st.subheader("Ajouter ou Modifier une Variable"); is_editing_var = False; variable_data_for_form = {"name": "", "label": "", "type": "", "options": "", "default": ""} 
            if st.session_state.editing_variable_info and st.session_state.editing_variable_info.get("family") == final_selected_family_edition and st.session_state.editing_variable_info.get("use_case") == final_selected_use_case_edition:
                edit_var_idx = st.session_state.editing_variable_info["index"]
                if edit_var_idx < len(current_prompt_config.get('variables',[])):
                    is_editing_var = True; current_editing_data_snapshot = current_prompt_config['variables'][edit_var_idx]; variable_data_for_form.update(copy.deepcopy(current_editing_data_snapshot))
                    if isinstance(variable_data_for_form.get("options"), list): variable_data_for_form["options"] = ", ".join(map(str, variable_data_for_form["options"]))
                    raw_def_edit_form = variable_data_for_form.get("default")
                    if isinstance(raw_def_edit_form, date): variable_data_for_form["default"] = raw_def_edit_form.strftime("%Y-%m-%d")
                    elif raw_def_edit_form is not None: variable_data_for_form["default"] = str(raw_def_edit_form)
                    else: variable_data_for_form["default"] = "" 
                else: st.session_state.editing_variable_info = None; st.session_state.variable_type_to_create = None; st.warning("La variable que vous tentiez de modifier n'existe plus. Annulation de l'édition."); st.rerun() # pragma: no cover
            if not is_editing_var and st.session_state.variable_type_to_create is None:
                st.markdown("##### 1. Choisissez le type de variable à créer :"); variable_types_map = { "Zone de texte (courte)": "text_input", "Liste choix": "selectbox", "Date": "date_input", "Nombre": "number_input", "Zone de texte (longue)": "text_area" }; num_type_buttons = len(variable_types_map); cols_type_buttons = st.columns(min(num_type_buttons, 5)); button_idx = 0
                for btn_label, type_val in variable_types_map.items():
                    if cols_type_buttons[button_idx % len(cols_type_buttons)].button(btn_label, key=f"btn_type_{type_val}_{final_selected_use_case_edition.replace(' ','_')}", use_container_width=True): st.session_state.variable_type_to_create = type_val; st.rerun()
                    button_idx += 1
                st.markdown("---")
            if st.session_state.variable_type_to_create:
                current_type_for_form = st.session_state.variable_type_to_create; variable_types_map_display = { "text_input": "Zone de texte (courte)", "selectbox": "Liste choix", "date_input": "Date", "number_input": "Nombre", "text_area": "Zone de texte (longue)" }; readable_type = variable_types_map_display.get(current_type_for_form, "Type Inconnu"); form_title = f"Modifier Variable : {variable_data_for_form.get('name','N/A')} ({readable_type})" if is_editing_var else f"Nouvelle Variable : {readable_type}"; st.markdown(f"##### 2. Configurez la variable")
                form_key_suffix = f"_edit_{st.session_state.editing_variable_info['index']}" if is_editing_var and st.session_state.editing_variable_info else "_create"; form_var_specific_key = f"form_var_{current_type_for_form}_{final_selected_use_case_edition.replace(' ','_')}{form_key_suffix}"
                with st.form(key=form_var_specific_key, clear_on_submit=(not is_editing_var)): 
                    st.subheader(form_title); var_name_input_form = st.text_input("Nom technique (ex : nom_client. Ne pas utiliser de caractères spéciaux -espaces, crochets {},virgules, etc.-)", value=variable_data_for_form.get("name", ""), key=f"{form_var_specific_key}_name", disabled=is_editing_var); var_label_input_form = st.text_input("Label pour l'utilisateur (description affichée)", value=variable_data_for_form.get("label", ""), key=f"{form_var_specific_key}_label"); var_options_str_input_form = ""
                    if current_type_for_form == "selectbox": var_options_str_input_form = st.text_input("Options (séparées par une virgule)", value=variable_data_for_form.get("options", ""), key=f"{form_var_specific_key}_options")
                    date_hint = " (Format AAAA-MM-JJ)" if current_type_for_form == "date_input" else ""; var_default_val_str_input_form = st.text_input(f"Valeur par défaut{date_hint}", value=str(variable_data_for_form.get("default", "")), key=f"{form_var_specific_key}_default")
                    min_val_input_form, max_val_input_form, step_val_input_form, height_val_input_form = None, None, None, None
                    if current_type_for_form == "number_input": 
                        num_cols_var_form = st.columns(3); min_val_edit_default = variable_data_for_form.get("min_value"); max_val_edit_default = variable_data_for_form.get("max_value"); step_val_edit_default = variable_data_for_form.get("step", 1.0) 
                        min_val_input_form = num_cols_var_form[0].number_input("Valeur minimale (optionnel)", value=float(min_val_edit_default) if min_val_edit_default is not None else None, format="%g", key=f"{form_var_specific_key}_min")
                        max_val_input_form = num_cols_var_form[1].number_input("Valeur maximale (optionnel)", value=float(max_val_edit_default) if max_val_edit_default is not None else None, format="%g", key=f"{form_var_specific_key}_max")
                        step_val_input_form = num_cols_var_form[2].number_input("Pas (incrément)", value=float(step_val_edit_default), format="%g", min_value=1e-9, key=f"{form_var_specific_key}_step") 
                    if current_type_for_form == "text_area": height_val_input_form = st.number_input("Hauteur de la zone de texte (pixels)", value=int(variable_data_for_form.get("height", 100)), min_value=50, step=25, key=f"{form_var_specific_key}_height")
                    submit_button_label_form = "Sauvegarder Modifications" if is_editing_var else "Ajouter Variable"; submitted_specific_var_form = st.form_submit_button(submit_button_label_form)
                    if submitted_specific_var_form:
                        var_name_val_submit = var_name_input_form.strip()
                        if not var_name_val_submit or not var_label_input_form.strip(): st.error("Le nom technique et le label de la variable sont requis.")
                        elif not var_name_val_submit.isidentifier(): st.error("Nom technique invalide. Utilisez lettres, chiffres, underscores. Ne pas commencer par un chiffre. Ne pas utiliser de mot-clé Python.")
                        elif current_type_for_form == "selectbox" and not [opt.strip() for opt in var_options_str_input_form.split(',') if opt.strip()]: st.error("Pour une variable de type 'Liste choix', au moins une option est requise.")
                        else:
                            new_var_data_to_submit = { "name": var_name_val_submit, "label": var_label_input_form.strip(), "type": current_type_for_form }; parsed_def_val_submit = parse_default_value(var_default_val_str_input_form.strip(), current_type_for_form)
                            if current_type_for_form == "selectbox":
                                options_list_submit = [opt.strip() for opt in var_options_str_input_form.split(',') if opt.strip()]; new_var_data_to_submit["options"] = options_list_submit
                                if options_list_submit: 
                                    if parsed_def_val_submit not in options_list_submit: st.warning(f"La valeur par défaut '{parsed_def_val_submit}' n'est pas dans la liste d'options. La première option '{options_list_submit[0]}' sera utilisée comme défaut."); new_var_data_to_submit["default"] = options_list_submit[0]
                                    else: new_var_data_to_submit["default"] = parsed_def_val_submit
                                else: new_var_data_to_submit["default"] = "" # pragma: no cover
                            else: new_var_data_to_submit["default"] = parsed_def_val_submit
                            if current_type_for_form == "number_input": 
                                if min_val_input_form is not None: new_var_data_to_submit["min_value"] = float(min_val_input_form)
                                if max_val_input_form is not None: new_var_data_to_submit["max_value"] = float(max_val_input_form)
                                if step_val_input_form is not None: new_var_data_to_submit["step"] = float(step_val_input_form)
                                else: new_var_data_to_submit["step"] = 1.0 
                            if current_type_for_form == "text_area" and height_val_input_form is not None: new_var_data_to_submit["height"] = int(height_val_input_form)
                            can_proceed_with_save = True; target_vars_list = current_prompt_config.get('variables', [])
                            if is_editing_var:
                                idx_to_edit_submit_form = st.session_state.editing_variable_info["index"]; target_vars_list[idx_to_edit_submit_form] = new_var_data_to_submit; st.success(f"Variable '{var_name_val_submit}' mise à jour avec succès."); st.session_state.editing_variable_info = None; st.session_state.variable_type_to_create = None 
                            else: 
                                existing_var_names_in_uc = [v['name'] for v in target_vars_list]
                                if var_name_val_submit in existing_var_names_in_uc: st.error(f"Une variable avec le nom technique '{var_name_val_submit}' existe déjà pour ce cas d'usage."); can_proceed_with_save = False # pragma: no cover
                                else: target_vars_list.append(new_var_data_to_submit); st.success(f"Variable '{var_name_val_submit}' ajoutée avec succès.")
                            if can_proceed_with_save:
                                current_prompt_config["variables"] = target_vars_list; current_prompt_config["updated_at"] = datetime.now().isoformat(); save_editable_prompts_to_gist()
                                if not is_editing_var: st.session_state.variable_type_to_create = None
                                st.rerun()
                    cancel_btn_key = f"cancel_var_action_btn_{form_var_specific_key}"
                    if st.button(cancel_button_label_form, key=cancel_btn_key, help="Réinitialise le formulaire de variable."): st.session_state.variable_type_to_create = None; 
                        if is_editing_var: st.session_state.editing_variable_info = None 
                        st.rerun()
            st.markdown("---"); action_cols = st.columns(2)
            with action_cols[0]:
                dup_key = f"dup_uc_btn_{final_selected_family_edition.replace(' ','_')}_{final_selected_use_case_edition.replace(' ','_')}"
                if st.button("🔄 Dupliquer ce Cas d'Usage", key=dup_key): # pragma: no cover
                    original_uc_name_dup = final_selected_use_case_edition; new_uc_name_base_dup = f"{original_uc_name_dup} (copie)"; new_uc_name_dup = new_uc_name_base_dup; copy_count_dup = 1
                    while new_uc_name_dup in st.session_state.editable_prompts[final_selected_family_edition]: new_uc_name_dup = f"{new_uc_name_base_dup} {copy_count_dup}"; copy_count_dup += 1
                    st.session_state.editable_prompts[final_selected_family_edition][new_uc_name_dup] = copy.deepcopy(current_prompt_config)
                    now_iso_dup_create, now_iso_dup_update = get_default_dates()
                    st.session_state.editable_prompts[final_selected_family_edition][new_uc_name_dup]["created_at"] = now_iso_dup_create; st.session_state.editable_prompts[final_selected_family_edition][new_uc_name_dup]["updated_at"] = now_iso_dup_update; st.session_state.editable_prompts[final_selected_family_edition][new_uc_name_dup]["usage_count"] = 0; save_editable_prompts_to_gist(); st.success(f"Cas d'usage '{original_uc_name_dup}' dupliqué en '{new_uc_name_dup}'.")
                    st.session_state.force_select_family_name = final_selected_family_edition; st.session_state.force_select_use_case_name = new_uc_name_dup; st.session_state.active_generated_prompt = ""; st.session_state.variable_type_to_create = None; st.session_state.editing_variable_info = None; st.rerun()
            with action_cols[1]:
                del_uc_key_exp = f"del_uc_btn_exp_{final_selected_family_edition.replace(' ','_')}_{final_selected_use_case_edition.replace(' ','_')}"; is_confirming_this_uc_delete = bool(st.session_state.confirming_delete_details and st.session_state.confirming_delete_details.get("family") == final_selected_family_edition and st.session_state.confirming_delete_details.get("use_case") == final_selected_use_case_edition)
                if st.button("🗑️ Supprimer Cas d'Usage", key=del_uc_key_exp, type="secondary", disabled=is_confirming_this_uc_delete): st.session_state.confirming_delete_details = {"family": final_selected_family_edition, "use_case": final_selected_use_case_edition}; st.rerun() 
        if st.session_state.get('go_to_config_section'): st.session_state.go_to_config_section = False 
    else: 
        if not final_selected_family_edition: st.info("Veuillez sélectionner une famille dans la barre latérale (onglet Génération & Édition) pour commencer.")
        elif not final_selected_use_case_edition: st.info(f"Veuillez sélectionner un cas d'usage pour la famille '{final_selected_family_edition}' ou en créer un.")
        else: st.warning(f"Le cas d'usage '{final_selected_use_case_edition}' dans la famille '{final_selected_family_edition}' semble introuvable. Il a peut-être été supprimé. Veuillez vérifier vos sélections."); st.session_state.use_case_selector_edition = None # pragma: no cover

elif st.session_state.view_mode == "inject_manual": 
    st.header("💉 Injection Manuelle de Cas d'Usage JSON")
    st.markdown("""Collez ici un ou plusieurs cas d'usage au format JSON. Le JSON doit être un dictionnaire où chaque clé est le nom du nouveau cas d'usage, et la valeur est sa configuration.""")
    st.caption("Exemple de structure pour un cas d'usage :"); st.code("""{  "Nom de Mon Nouveau Cas d'Usage": {    "template": "Ceci est le {variable_exemple} pour mon prompt.",    "variables": [      {        "name": "variable_exemple",        "label": "Variable d'Exemple",        "type": "text_input",        "default": "texte par défaut"      }    ],    "tags": ["nouveau", "exemple"]  }}""", language="json")
    available_families_for_injection = list(st.session_state.editable_prompts.keys())
    if not available_families_for_injection: st.warning("Aucune famille n'existe. Veuillez d'abord créer une famille via l'onglet 'Génération & Édition'.")
    else:
        selected_family_for_injection = st.selectbox("Choisissez la famille de destination pour l'injection :", options=[""] + available_families_for_injection, index=0, key="injection_family_selector")
        st.session_state.injection_selected_family = selected_family_for_injection if selected_family_for_injection else None
        if st.session_state.injection_selected_family:
            st.subheader(f"Injecter dans la famille : {st.session_state.injection_selected_family}")
            st.session_state.injection_json_text = st.text_area("Collez le JSON des cas d'usage ici :", value=st.session_state.get("injection_json_text", ""), height=300, key="injection_json_input")
            if st.button("➕ Injecter les Cas d'Usage", key="submit_injection_btn"):
                if not st.session_state.injection_json_text.strip(): st.error("La zone de texte JSON est vide.")
                else:
                    try:
                        injected_data = json.loads(st.session_state.injection_json_text)
                        if not isinstance(injected_data, dict): st.error("Le JSON fourni doit être un dictionnaire (objet JSON).")
                        else:
                            target_family_name = st.session_state.injection_selected_family
                            if target_family_name not in st.session_state.editable_prompts: st.error(f"La famille de destination '{target_family_name}' n'existe plus ou n'a pas été correctement sélectionnée.") # Should not happen
                            else:
                                family_prompts = st.session_state.editable_prompts[target_family_name]; successful_injections = []; failed_injections = []; first_new_uc_name = None
                                for uc_name, uc_config in injected_data.items():
                                    uc_name_stripped = uc_name.strip()
                                    if not uc_name_stripped: failed_injections.append(f"Nom de cas d'usage vide ignoré."); continue
                                    if not isinstance(uc_config, dict) or "template" not in uc_config: failed_injections.append(f"'{uc_name_stripped}': Configuration invalide ou template manquant."); continue
                                    if uc_name_stripped in family_prompts: st.warning(f"Le cas d'usage '{uc_name_stripped}' existe déjà dans la famille '{target_family_name}'. Il a été ignoré."); failed_injections.append(f"'{uc_name_stripped}': Existe déjà, ignoré."); continue
                                    processed_uc_config = _preprocess_injected_use_case_data(uc_config)
                                    if not processed_uc_config.get("template"): failed_injections.append(f"'{uc_name_stripped}': Template invalide après traitement."); continue
                                    family_prompts[uc_name_stripped] = processed_uc_config; successful_injections.append(uc_name_stripped)
                                    if first_new_uc_name is None: first_new_uc_name = uc_name_stripped
                                if successful_injections:
                                    save_editable_prompts_to_gist(); st.success(f"{len(successful_injections)} cas d'usage injectés avec succès dans '{target_family_name}': {', '.join(successful_injections)}"); st.session_state.injection_json_text = "" 
                                    if first_new_uc_name: st.session_state.view_mode = "edit"; st.session_state.force_select_family_name = target_family_name; st.session_state.force_select_use_case_name = first_new_uc_name; st.session_state.go_to_config_section = True; st.rerun()
                                if failed_injections:
                                    for fail_msg in failed_injections: st.error(f"Échec d'injection : {fail_msg}")
                                if not successful_injections and not failed_injections: st.info("Aucun cas d'usage n'a été trouvé dans le JSON fourni ou tous étaient vides/invalides.")
                    except json.JSONDecodeError as e: st.error(f"Erreur de parsing JSON : {e}")
                    except Exception as e: st.error(f"Une erreur inattendue est survenue lors de l'injection : {e}") # pragma: no cover
        else: st.info("Veuillez sélectionner une famille de destination pour commencer l'injection.")

elif st.session_state.view_mode == "assistant_creation":
    st.header("✨ Assistant de Création de Cas d'Usage")
    st.markdown("Répondez aux questions suivantes pour générer un \"Méta Prompt\". Vous pourrez ensuite utiliser ce Méta Prompt avec un LLM externe (comme ChatGPT, Claude, Gemini, etc.) pour obtenir la structure JSON finale à injecter.")

    current_form_values = st.session_state.assistant_form_values # Load current/default values
    
    with st.form(key="assistant_creation_form"):
        form_inputs = {} # To store user's input from this form submission
        for var_info in ASSISTANT_FORM_VARIABLES:
            field_key = f"assistant_form_{var_info['name']}"
            # Use current value from session state for stickiness, fallback to default from definition
            current_value = current_form_values.get(var_info['name'], var_info['default'])

            if var_info["type"] == "text_input":
                form_inputs[var_info["name"]] = st.text_input(var_info["label"], value=current_value, key=field_key)
            elif var_info["type"] == "text_area":
                form_inputs[var_info["name"]] = st.text_area(var_info["label"], value=current_value, height=var_info.get("height", 100), key=field_key)
            elif var_info["type"] == "number_input":
                # Ensure value is float for number_input
                try:
                    num_value = float(current_value)
                except (ValueError, TypeError):
                    num_value = float(var_info["default"])

                form_inputs[var_info["name"]] = st.number_input(
                    var_info["label"], 
                    value=num_value,
                    min_value=float(var_info.get("min_value", 0.0)) if var_info.get("min_value") is not None else None,
                    max_value=float(var_info.get("max_value", 100.0)) if var_info.get("max_value") is not None else None,
                    step=float(var_info.get("step", 1.0)), 
                    key=field_key,
                    format="%g" 
                )
            # Add other input types here if ASSISTANT_FORM_VARIABLES uses them

        submitted_assistant_form = st.form_submit_button("📝 Générer le Méta Prompt pour LLM Externe")

        if submitted_assistant_form:
            st.session_state.assistant_form_values = form_inputs # Save current inputs for stickiness
            
            try:
                # Ensure all placeholders are correctly handled, even if a field was somehow empty
                # The .format_map(defaultdict(str, form_inputs)) could be an alternative for safety
                # but simple .format should work if ASSISTANT_FORM_VARIABLES covers all placeholders.
                populated_meta_prompt = META_PROMPT_FOR_EXTERNAL_LLM_TEMPLATE.format(**form_inputs)
                st.session_state.generated_meta_prompt_for_llm = populated_meta_prompt
                st.success("Méta Prompt généré ! Vous pouvez le copier ci-dessous.")
            except KeyError as e: # pragma: no cover
                st.error(f"Erreur lors de la construction du Méta Prompt. Clé de formatage manquante : {e}. Veuillez vérifier les définitions de ASSISTANT_FORM_VARIABLES et le META_PROMPT_FOR_EXTERNAL_LLM_TEMPLATE.")
            except Exception as e: # pragma: no cover
                 st.error(f"Une erreur inattendue est survenue lors de la génération du Méta Prompt : {e}")
            # No rerun here, let the generated prompt display below

    if st.session_state.generated_meta_prompt_for_llm:
        st.subheader("📋 Méta Prompt Généré (à copier dans votre LLM externe) :")
        st.text_area("Méta Prompt :", value=st.session_state.generated_meta_prompt_for_llm, height=400, key="meta_prompt_output_for_copy", help="Copiez ce texte intégralement et utilisez-le comme instruction pour un LLM (ChatGPT, Gemini, Claude, etc.). Le LLM devrait alors vous fournir la structure JSON à utiliser dans la section 'Injecter JSON Manuellement'.")
        st.markdown("---")
        st.info("Une fois que votre LLM externe a généré le JSON basé sur ce Méta Prompt, copiez ce JSON et utilisez le bouton \"💉 Injecter JSON Manuellement\" dans la barre latérale pour l'ajouter à votre atelier.")

else: 
    if not any(st.session_state.editable_prompts.values()): # pragma: no cover
        st.warning("Aucune famille de cas d'usage n'est configurée. Veuillez en créer une via l'onglet 'Génération & Édition' ou vérifier votre Gist.")
    elif st.session_state.view_mode not in ["library", "edit", "inject_manual", "assistant_creation"]: # pragma: no cover
        st.session_state.view_mode = "library" if list(st.session_state.editable_prompts.keys()) else "edit"
        st.rerun()

# --- Sidebar Footer ---
st.sidebar.markdown("---")
st.sidebar.info(f"Générateur v3.3.4 - © {CURRENT_YEAR} La Poste (démo)")
