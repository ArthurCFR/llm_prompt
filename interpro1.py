import streamlit as st
from datetime import datetime, date
import copy
import json
import requests 

# --- PAGE CONFIGURATION (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(layout="wide", page_title="🛠️ L'atelier des prompts IA")

# --- Initial Data Structure & Constants ---
CURRENT_YEAR = datetime.now().year
GIST_DATA_FILENAME = "prompt_templates_data_v3.json"

META_PROMPT_FOR_EXTERNAL_LLM_TEMPLATE = """# MISSION
Tu es un expert en conception de prompts (Prompt Engineer) spécialisé dans la création de prompts systèmes pour des modèles de langage avancés. Ta mission est de générer un "Prompt Cible" hautement efficace, structuré et réutilisable, ainsi que sa configuration JSON pour une application de gestion de prompts. Ce "Prompt Cible" sera ensuite utilisé par un utilisateur final pour réaliser une tâche spécifique.

# CONTEXTE DE LA DEMANDE UTILISATEUR
L'utilisateur souhaite obtenir un "Prompt Cible" capable d'adresser la problématique suivante : `{problematique}`.
Par exemple, si la problématique est "résumer un texte de loi et lister les contraintes financières attenantes", le "Prompt Cible" généré devra guider un LLM pour effectuer cette tâche sur un document pertinent.

# EXIGENCES POUR LE "PROMPT CIBLE" ET SA CONFIGURATION JSON
Le "Prompt Cible" et sa configuration JSON que tu vas générer DOIVENT :

## Pour le "Prompt Cible" (le template textuel) :
1.  **Définir clairement le rôle** de l'IA qui exécutera le prompt (par exemple, "Tu es un analyste juridique et financier expert...").
2.  **Spécifier l'objectif principal** de manière concise, basé sur la problematique.
3.  **Si pertinent, indiquer explicitement que le type de document source** et que l'IA doit être capable de le traiter : `{doc_source}`. Si `{doc_source}` est vide ou non pertinent, n'en fais pas mention.
4.  **Guider l'IA sur les informations spécifiques à extraire.** Ces informations sont : `{elements_specifiques_a_extraire}`.
5.  **Indiquer le format de sortie désiré pour le résultat du prompt cible : `{format_sortie_desire}`. Le résultat obtenu après l'utilisation du prompt cible doit être pensé pour être agréable à lire, harmonieusement présenté, utilisant les styles de texte à bon escient (ex : gras, italique, souligné) "**
6.  **Inclure des instructions pour gérer les ambiguïtés** ou le manque d'information (par exemple, demander des clarifications ou indiquer les limites).
7.  **Être paramétrable via des variables claires et explicites.** Le nombre de variables doit être compris entre {min_var} et {max_var}. Toutes les variables (placeholders) DANS LE TEXTE du "Prompt Cible" que tu génères (celles qui seront remplies par l'utilisateur final du "Prompt Cible") DOIVENT être encadrées par des **DOUBLES ACCOLADES**, par exemple : `{{nom_du_client}}` ou `{{detail_du_produit}}`. N'utilise PAS d'accolades simples pour ces placeholders internes au "Prompt Cible".
8.  **Spécifier le public cible du résultat de ce prompt : `{public_cible_reponse}`.**
9.  **Ne pas rendre évident qu'il a été généré à partir d'un LLM en évitant des appartées contextuelles telles que des phrases : 'basée sur l'input', 'a partir des informations du prompt', etc..**
9.  **Faire en sorte que le résultat obtenu par le prompt cible n'ai pas l'air d'avoir été généré à partir d'un LLM, en évitant des appartées contextuelles telles que des phrases : 'basée sur l'input', 'a partir des informations du prompt', etc..**

## Pour la configuration JSON (qui encapsule le "Prompt Cible") :
1.  **Suggérer un nom pour le cas d'usage** (`suggested_use_case_name`) : descriptif et concis (max 5-7 mots).
2.  **Inclure le "Prompt Cible" textuel** dans le champ `"template"` du JSON.
3.  **Lister et décrire chaque variable** utilisée dans le champ `"variables"` du JSON. Chaque objet variable doit avoir :
    * `"name"`: (string) Le nom technique de la variable (ex: `nom_du_client` si le placeholder dans le template est `{{nom_du_client}}`), sans espaces ni caractères spéciaux autres que underscore.
    * `"label"`: (string) Le label descriptif pour l'utilisateur (ex: "Nom du client").
    * `"type"`: (string) Choisis parmi : `"text_input"`, `"selectbox"`, `"date_input"`, `"number_input"`, `"text_area"`.
    * `"default"`: (string, number, or boolean) La valeur par défaut. Pour les dates, utilise le format "AAAA-MM-JJ". Si le type est number, la valeur par défaut doit être un nombre.
    * `"options"`: (array of strings, optionnel) Uniquement si `type` est `"selectbox"`. Liste des options.
    * `"min_value"`, `"max_value"`, `"step"`: (number, optionnel) Uniquement si `type` est `"number_input"`. `step` doit être positif.
    * `"height"`: (number, optionnel) Uniquement si `type` est `"text_area"`. Assure-toi que c'est un entier >= 68.
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
if 'duplicating_use_case_details' not in st.session_state: st.session_state.duplicating_use_case_details = None
if 'go_to_config_section' not in st.session_state: st.session_state.go_to_config_section = False

if 'injection_selected_family' not in st.session_state:
    st.session_state.injection_selected_family = None
if 'injection_json_text' not in st.session_state:
    st.session_state.injection_json_text = ""

if 'assistant_form_values' not in st.session_state:
    st.session_state.assistant_form_values = {var['name']: var['default'] for var in ASSISTANT_FORM_VARIABLES}
if 'generated_meta_prompt_for_llm' not in st.session_state: 
    st.session_state.generated_meta_prompt_for_llm = ""

# --- Main App UI ---
st.title(f"🛠️ L'atelier des prompts IA")

# --- Sidebar Navigation with Tabs ---
st.sidebar.header("Menu Principal")
tab_bibliotheque, tab_edition_generation, tab_injection = st.sidebar.tabs([
    "📚 Bibliothèque",
    "✍️ Édition",
    "💡 Assistant" 
])

# --- Tab: Édition (Sidebar content) ---
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
        st.info("La bibliothèque est vide. Ajoutez des prompts via l'onglet 'Édition'.")
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
    st.subheader("Assistant & Injection")
    st.markdown("Utilisez l'assistant pour préparer un prompt système ou injectez des cas d'usage en format JSON.")
    if st.button("✨ Créer un prompt système (Assistant)", key="start_assistant_creation_btn", use_container_width=True):
        st.session_state.view_mode = "assistant_creation" 
        st.session_state.assistant_form_values = {var['name']: var['default'] for var in ASSISTANT_FORM_VARIABLES} 
        st.session_state.generated_meta_prompt_for_llm = "" 
        st.rerun()
    if st.button("💉 Injecter JSON Manuellement", key="start_manual_injection_btn", use_container_width=True):
        st.session_state.view_mode = "inject_manual" 
        st.session_state.injection_selected_family = None 
        st.session_state.injection_json_text = "" 
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
             st.warning("Aucune famille de cas d'usage n'est configurée. Créez-en via l'onglet 'Édition'.")
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
    if not final_selected_family_edition : st.info("Sélectionnez une famille dans la barre latérale (onglet Édition) ou créez-en une pour commencer.")
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
                            gen_form_values[var_info["name"]] = st.number_input(var_info["label"], value=val_num_gen, min_value=min_val_gen,max_value=max_val_gen, step=step_val_gen, key=widget_key, format="%g")
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
                final_vals_for_prompt = { k: (v.strftime("%d/%m/%Y") if isinstance(v, date) else v) for k, v in gen_form_values.items() if v is not None }
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
            if edited_prompt_value != st.session_state.active_generated_prompt: st.session_state.active_generated_prompt = edited_prompt_value # pragma: no cover
            st.caption("Prompt généré (pour relecture et copie manuelle) :"); st.code(st.session_state.active_generated_prompt, language=None)

        # --- '⚙️ Paramétrage du Prompt' Expander ---
        st.markdown("---")
        should_expand_config = st.session_state.get('go_to_config_section', False)
        with st.expander(f"⚙️ Paramétrage du Prompt: {final_selected_use_case_edition}", expanded=should_expand_config):
            # ... all prompt config code ...
            # REMOVE any 'Actions sur le Cas d'Usage' block from here
            pass
        st.markdown("---")
        # --- 'Actions sur le Cas d'Usage' Section (now only here, after expander) ---
        st.subheader("Actions sur le Cas d'Usage")
        action_cols_manage = st.columns(2)
        with action_cols_manage[0]:
            dup_key_init = f"initiate_dup_uc_btn_{final_selected_family_edition.replace(' ','_')}_{final_selected_use_case_edition.replace(' ','_')}_main"
            is_dup_form_active = (
                st.session_state.duplicating_use_case_details and
                st.session_state.duplicating_use_case_details["family"] == final_selected_family_edition and
                st.session_state.duplicating_use_case_details["use_case"] == final_selected_use_case_edition
            )
            if not is_dup_form_active:
                if st.button("🔄 Dupliquer ce Cas d'Usage", key=dup_key_init, use_container_width=True):
                    st.session_state.duplicating_use_case_details = {
                        "family": final_selected_family_edition,
                        "use_case": final_selected_use_case_edition
                    }
                    st.rerun()
        with action_cols_manage[1]:
            delete_button_key_main = f"del_uc_btn_exp_main_{final_selected_family_edition.replace(' ','_')}_{final_selected_use_case_edition.replace(' ','_')}"
            is_confirming_this_uc_delete_main = bool(st.session_state.confirming_delete_details and \
                st.session_state.confirming_delete_details.get("family") == final_selected_family_edition and \
                st.session_state.confirming_delete_details.get("use_case") == final_selected_use_case_edition)
            if st.button("🗑️ Supprimer Cas d'Usage", key=delete_button_key_main, type="secondary", disabled=is_confirming_this_uc_delete_main, use_container_width=True):
                st.session_state.confirming_delete_details = {"family": final_selected_family_edition, "use_case": final_selected_use_case_edition}
                st.rerun()
        if st.session_state.duplicating_use_case_details and \
           st.session_state.duplicating_use_case_details["family"] == final_selected_family_edition and \
           st.session_state.duplicating_use_case_details["use_case"] == final_selected_use_case_edition:
            original_uc_name_for_dup_form = st.session_state.duplicating_use_case_details["use_case"]
            st.markdown(f"#### Dupliquer '{original_uc_name_for_dup_form}'")
            form_key_duplicate = f"form_duplicate_name_{final_selected_family_edition.replace(' ','_')}_{original_uc_name_for_dup_form.replace(' ','_')}"
            input_key_dup_name = f"new_dup_name_input_{final_selected_family_edition.replace(' ','_')}_{original_uc_name_for_dup_form.replace(' ','_')}"
            submit_button_key_dup = f"submit_dup_form_{final_selected_family_edition.replace(' ','_')}_{original_uc_name_for_dup_form.replace(' ','_')}"
            cancel_button_key_dup = f"cancel_dup_process_{final_selected_family_edition.replace(' ','_')}_{original_uc_name_for_dup_form.replace(' ','_')}"
            with st.form(key=form_key_duplicate):
                suggested_new_name_base = f"{original_uc_name_for_dup_form} (copie)"
                suggested_new_name = suggested_new_name_base
                temp_copy_count = 1
                while suggested_new_name in st.session_state.editable_prompts.get(final_selected_family_edition, {}):
                    suggested_new_name = f"{suggested_new_name_base} {temp_copy_count}"
                    temp_copy_count += 1
                new_duplicated_uc_name_input = st.text_input(
                    "Nouveau nom pour le cas d'usage dupliqué:",
                    value=suggested_new_name,
                    key=input_key_dup_name
                )
                submitted_duplicate_form = st.form_submit_button("✅ Confirmer la Duplication", use_container_width=True, key=submit_button_key_dup)
                if submitted_duplicate_form:
                    new_uc_name_val_from_form = new_duplicated_uc_name_input.strip()
                    family_for_dup = st.session_state.duplicating_use_case_details["family"]
                    if not new_uc_name_val_from_form:
                        st.error("Le nom du nouveau cas d'usage ne peut pas être vide.")
                    elif new_uc_name_val_from_form in st.session_state.editable_prompts.get(family_for_dup, {}):
                        st.error(f"Un cas d'usage nommé '{new_uc_name_val_from_form}' existe déjà dans la famille '{family_for_dup}'.")
                    else:
                        st.session_state.editable_prompts[family_for_dup][new_uc_name_val_from_form] = copy.deepcopy(current_prompt_config)
                        now_iso_dup_create, now_iso_dup_update = get_default_dates()
                        st.session_state.editable_prompts[family_for_dup][new_uc_name_val_from_form]["created_at"] = now_iso_dup_create
                        st.session_state.editable_prompts[family_for_dup][new_uc_name_val_from_form]["updated_at"] = now_iso_dup_update
                        st.session_state.editable_prompts[family_for_dup][new_uc_name_val_from_form]["usage_count"] = 0
                        save_editable_prompts_to_gist()
                        st.success(f"Cas d'usage '{original_uc_name_for_dup_form}' dupliqué en '{new_uc_name_val_from_form}' dans la famille '{family_for_dup}'.")
                        st.session_state.duplicating_use_case_details = None
                        st.session_state.force_select_family_name = family_for_dup
                        st.session_state.force_select_use_case_name = new_uc_name_val_from_form
                        st.session_state.active_generated_prompt = ""
                        st.session_state.variable_type_to_create = None
                        st.session_state.editing_variable_info = None
                        st.session_state.go_to_config_section = True
                        st.rerun()
            if st.button("❌ Annuler la Duplication", key=cancel_button_key_dup, use_container_width=True):
                st.session_state.duplicating_use_case_details = None
                st.rerun()

elif st.session_state.view_mode == "inject_manual": 
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
        st.warning("Aucune famille n'existe. Veuillez d'abord créer une famille via l'onglet 'Édition'.")
    else:
        selected_family_for_injection = st.selectbox("Choisissez la famille de destination pour l'injection :", options=[""] + available_families_for_injection, index=0, key="injection_family_selector")
        st.session_state.injection_selected_family = selected_family_for_injection if selected_family_for_injection else None
        if st.session_state.injection_selected_family:
            st.subheader(f"Injecter dans la famille : {st.session_state.injection_selected_family}")
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
                                st.error(f"La famille de destination '{target_family_name}' n'existe plus ou n'a pas été correctement sélectionnée.") 
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
                                        st.warning(f"Le cas d'usage '{uc_name_stripped}' existe déjà dans la famille '{target_family_name}'. Il a été ignoré.")
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
            st.info("Veuillez sélectionner une famille de destination pour commencer l'injection.")

elif st.session_state.view_mode == "assistant_creation":
    st.header("✨ Assistant de Création de prompt système")
    st.markdown("Cet assistant vous aide à préparer une **instruction détaillée**. Vous donnerez cette instruction à LaPoste GPT qui, en retour, générera les éléments clés de votre cas d'usage (le prompt système, les variables, les tags, etc.). Vous pourrez ensuite l'importer ici via le bouton [💉 Injecter JSON Manuellement], puis l'améliorer à votre guise.")

    with st.form(key="assistant_creation_form"):
        current_form_input_values = {} 

        for var_info in ASSISTANT_FORM_VARIABLES:
            field_key = f"assistant_form_{var_info['name']}"
            value_for_widget = st.session_state.assistant_form_values.get(var_info['name'], var_info['default'])

            if var_info["type"] == "text_input":
                current_form_input_values[var_info["name"]] = st.text_input(
                    var_info["label"], 
                    value=value_for_widget,
                    key=field_key
                )
            elif var_info["type"] == "text_area":
                current_form_input_values[var_info["name"]] = st.text_area(
                    var_info["label"], 
                    value=value_for_widget,
                    height=var_info.get("height", 100), 
                    key=field_key
                )
            elif var_info["type"] == "number_input":
                try: 
                    num_value_for_widget = float(value_for_widget)
                except (ValueError, TypeError): 
                    num_value_for_widget = float(var_info["default"])

                current_form_input_values[var_info["name"]] = st.number_input(
                    var_info["label"], 
                    value=num_value_for_widget,
                    min_value=float(var_info.get("min_value", 0.0)) if var_info.get("min_value") is not None else None,
                    max_value=float(var_info.get("max_value", 100.0)) if var_info.get("max_value") is not None else None,
                    step=float(var_info.get("step", 1.0)), 
                    key=field_key, 
                    format="%g" 
                )

        submitted_assistant_form = st.form_submit_button("📝 Générer le prompt système")

        if submitted_assistant_form:
            st.session_state.assistant_form_values = current_form_input_values.copy()

            try:
                populated_meta_prompt = META_PROMPT_FOR_EXTERNAL_LLM_TEMPLATE.format(**st.session_state.assistant_form_values)
                st.session_state.generated_meta_prompt_for_llm = populated_meta_prompt
                st.success("Prompt système généré ! Vous pouvez le copier ci-dessous.")
            except KeyError as e: # pragma: no cover
                st.error(f"Erreur lors de la construction du prompt système. Clé de formatage manquante : {e}.")
            except Exception as e: # pragma: no cover
                st.error(f"Une erreur inattendue est survenue lors de la génération du prompt système : {e}")

    if st.session_state.generated_meta_prompt_for_llm:
        st.subheader("📋 Prompt système Généré (à copier dans votre LLM externe) :")
        st.code(st.session_state.generated_meta_prompt_for_llm, language='markdown', line_numbers=True)
        st.markdown("---")
        st.info("Une fois que votre LLM externe a généré le JSON basé sur ce prompt système, copiez ce JSON et utilisez le bouton \"💉 Injecter JSON Manuellement\" dans la barre latérale pour l'ajouter à votre atelier.")
else: 
    if not any(st.session_state.editable_prompts.values()): # pragma: no cover
        st.warning("Aucune famille de cas d'usage n'est configurée. Veuillez en créer une via l'onglet 'Édition', ou vérifier votre Gist.")
    elif st.session_state.view_mode not in ["library", "edit", "inject_manual", "assistant_creation"]: # pragma: no cover
        st.session_state.view_mode = "library" if list(st.session_state.editable_prompts.keys()) else "edit"
        st.rerun()

# --- Sidebar Footer ---
st.sidebar.markdown("---")
st.sidebar.info(f"Générateur v3.3.6 - © {CURRENT_YEAR} La Poste (démo)")
