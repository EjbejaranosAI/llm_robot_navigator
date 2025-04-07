# src/interfaces/streamlit_app.py

import streamlit as st
import time
import base64
from PIL import Image
import io # Needed for handling image bytes if PIL is used for validation/preview
import os
import sys
import json
import re
import networkx as nx
from networkx.readwrite import json_graph

# --- Path Setup ---
# Adjust path if necessary to find custom modules
try:
    src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    # --- Import Custom Modules ---
    from api.gpt_client import analyze_image_with_gpt # Expects the modified version
    from utils.prompts import navigation_prompt, formatting_prompt # Expects the modified navigation_prompt
    from utils.parsing_llm_response import parse_raw_text_to_json # Assumed function exists
    from navigation.planer import generate_navigation_plan # Assumed function exists
    from mapping.graph_manager import (
        initialize_graph, add_node_to_graph, add_edge_to_graph,
        convert_nx_to_agraph, get_node_data, update_node_data
    )
    from streamlit_agraph import agraph, Node, Edge, Config # Ensure streamlit_agraph is installed
except ImportError as e:
    st.error(f"Error importing required modules: {e}")
    st.error("Please ensure all custom modules (api, utils, navigation, mapping) are accessible and required libraries (streamlit, networkx, Pillow, streamlit-agraph, python-dotenv, openai) are installed.")
    st.stop() # Stop execution if imports fail

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Navegación Robótica con LLM")

# --- Utility Functions ---
def safe_rerun():
    """Attempts to rerun the Streamlit app."""
    try:
        st.rerun() # st.experimental_rerun is deprecated, use st.rerun
    except Exception as e:
        st.warning(f"No se pudo reiniciar la app automáticamente: {e}")

# --- Session State Initialization ---
if 'graph' not in st.session_state:
    st.session_state.graph = initialize_graph()
if 'current_description' not in st.session_state:
    st.session_state.current_description = ""
if 'navigation_goal' not in st.session_state:
    st.session_state.navigation_goal = ""
if 'current_node' not in st.session_state:
    st.session_state.current_node = None # ID of the node where the robot currently is
if 'all_descriptions' not in st.session_state:
    st.session_state.all_descriptions = {} # node_id -> description mapping (consider if still needed with LLM components in node)
if 'navigation_plan' not in st.session_state:
    st.session_state.navigation_plan = ""
if 'action_history' not in st.session_state:
    st.session_state.action_history = []
if 'llm_components' not in st.session_state:
    st.session_state.llm_components = {} # Parsed JSON from the last analysis
if 'suggested_action' not in st.session_state: # May be deprecated if actions are handled directly from llm_components
    st.session_state.suggested_action = ""
if 'use_formatter' not in st.session_state:
    st.session_state.use_formatter = False
if 'timer_start' not in st.session_state: # Used for auto-action selection timeout
    st.session_state.timer_start = None
if 'selected_action' not in st.session_state: # Action chosen by user or timer
    st.session_state.selected_action = None
if 'clicked_node_id' not in st.session_state: # Node ID selected from graph preview
    st.session_state.clicked_node_id = None
# --- New/Modified State Variables ---
if 'input_mode' not in st.session_state:
    st.session_state.input_mode = "Vista Única (Centro)" # Default mode: "Vista Única (Centro)" or "Vista Panorámica (Izq, Centro, Der)"
if 'current_images' not in st.session_state:
    # Stores the image data (URL/base64) currently loaded in the UI input widgets
    st.session_state.current_images = {'left': None, 'center': None, 'right': None}
if 'analyzed_images' not in st.session_state:
    # Stores history of analyses performed.
    # Structure: list of tuples: (node_id, {'left': img_data, 'center': img_data, 'right': img_data})
    st.session_state.analyzed_images = []

# --- State Save/Load Functions ---
def save_state():
    """Serializes the current session state for saving."""
    # Convert graph to serializable format
    graph_data = json_graph.node_link_data(st.session_state.graph)
    # Prepare images: optionally replace large base64 with placeholders if needed
    # For simplicity, we save them as is for now.
    serializable_analyzed_images = st.session_state.analyzed_images
    serializable_current_images = st.session_state.current_images

    state = {
         "graph": graph_data,
         "current_description": st.session_state.current_description,
         "current_images": serializable_current_images, # Save dict of current UI images
         "input_mode": st.session_state.input_mode, # Save input mode
         "navigation_goal": st.session_state.navigation_goal,
         "current_node": st.session_state.current_node,
         "all_descriptions": st.session_state.all_descriptions, # Consider deprecating if node['description'] is enough
         "navigation_plan": st.session_state.navigation_plan,
         "action_history": st.session_state.action_history,
         "llm_components": st.session_state.llm_components,
         "suggested_action": st.session_state.suggested_action, # Consider deprecating
         "analyzed_images": serializable_analyzed_images, # Save history with image dicts
         "use_formatter": st.session_state.use_formatter,
         "selected_action": st.session_state.selected_action,
         "clicked_node_id": st.session_state.clicked_node_id,
         # Note: timer_start is transient and usually not saved/loaded
    }
    return state

def load_state(state):
    """Loads the application state from a dictionary."""
    try:
        st.session_state.graph = json_graph.node_link_graph(state["graph"])
        st.session_state.current_description = state.get("current_description", "")
        st.session_state.current_images = state.get("current_images", {'left': None, 'center': None, 'right': None})
        st.session_state.input_mode = state.get("input_mode", "Vista Única (Centro)")
        st.session_state.navigation_goal = state.get("navigation_goal", "")
        st.session_state.current_node = state.get("current_node", None)
        st.session_state.all_descriptions = state.get("all_descriptions", {})
        st.session_state.navigation_plan = state.get("navigation_plan", "")
        st.session_state.action_history = state.get("action_history", [])
        st.session_state.llm_components = state.get("llm_components", {})
        st.session_state.suggested_action = state.get("suggested_action", "")
        st.session_state.analyzed_images = state.get("analyzed_images", [])
        st.session_state.use_formatter = state.get("use_formatter", False)
        st.session_state.selected_action = state.get("selected_action", None)
        st.session_state.clicked_node_id = state.get("clicked_node_id", None)
        # Reset transient states
        st.session_state.timer_start = None
        st.sidebar.success("Estado cargado exitosamente.")
    except Exception as e:
        st.sidebar.error(f"Error al cargar el estado: {e}")
        # Optionally reset to default state on load error
        # initialize_session_state() # Need to define this function if used

# --- Sidebar: Save/Load State ---
st.sidebar.header("Guardar / Cargar Estado")
if st.sidebar.button("Guardar Estado"):
    try:
        state_to_save = save_state()
        state_json = json.dumps(state_to_save, indent=2)
        st.sidebar.download_button(
            label="Descargar Estado (JSON)",
            data=state_json,
            file_name="estado_navegacion_robotica.json",
            mime="application/json"
        )
        st.sidebar.success("Estado listo para descargar.")
    except Exception as e:
        st.sidebar.error(f"Error al preparar el estado para guardar: {e}")

uploaded_state_file = st.sidebar.file_uploader("Cargar Estado Guardado (JSON)", type="json")
if uploaded_state_file is not None:
    try:
        state_data = json.load(uploaded_state_file)
        load_state(state_data)
        # Rerun after loading to reflect the new state in the UI
        safe_rerun()
    except json.JSONDecodeError:
        st.sidebar.error("Error: El archivo cargado no es un JSON válido.")
    except Exception as e:
        st.sidebar.error(f"Error al procesar el archivo de estado: {e}")

# --- LLM Response Handling Functions ---
# Assume these functions are correctly implemented or imported
def format_llm_response(raw_response):
    """ Placeholder: Uses secondary LLM call to fix broken JSON. """
    # Replace with your actual implementation, likely calling analyze_image_with_gpt or similar
    st.warning("`format_llm_response` needs implementation.")
    prompt = formatting_prompt.replace('{raw_llm_output}', raw_response)
    # This might need a specific API call that doesn't require images
    # return analyze_text_with_gpt(prompt) # Hypothetical function
    return None # Return None if not implemented

def extract_llm_components(llm_response):
    """ Attempts to parse the LLM response string into a JSON object. """
    try:
        # Try direct JSON parsing first (assuming LLM follows instructions)
        parsed = json.loads(llm_response)
        # Basic validation (check if it's a dictionary)
        if not isinstance(parsed, dict):
             raise ValueError("Response is not a JSON object.")
        # You could add checks for mandatory keys here if needed
        return parsed
    except json.JSONDecodeError as json_err:
        st.warning(f"Fallo el parseo JSON inicial: {json_err}")
        # Try regex to find JSON within potential markdown/text
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                st.info("JSON extraído de bloque de código markdown.")
                if not isinstance(parsed, dict):
                     raise ValueError("Extracted content is not a JSON object.")
                return parsed
            except json.JSONDecodeError as nested_err:
                 st.warning(f"Fallo el parseo JSON del bloque extraído: {nested_err}")

        # Fallback to raw text parsing if direct/regex fails (using provided function)
        st.info("Intentando parseo de texto crudo como último recurso.")
        try:
            # Ensure parse_raw_text_to_json is robust
            return parse_raw_text_to_json(llm_response)
        except Exception as parse_err:
             st.error(f"Error crítico durante el parseo de texto crudo: {parse_err}")
             st.error(f"Respuesta LLM recibida:\n```\n{llm_response[:1000]}...\n```")
             return None # Return None if all parsing fails
    except ValueError as val_err:
         st.error(f"Error de validación de JSON: {val_err}")
         st.error(f"Respuesta LLM recibida:\n```\n{llm_response[:1000]}...\n```")
         return None
    except Exception as e:
         st.error(f"Error inesperado durante la extracción de componentes LLM: {e}")
         st.error(f"Respuesta LLM recibida:\n```\n{llm_response[:1000]}...\n```")
         return None

# --- Graph Interaction Functions ---
def connect_nodes_by_common_objects(graph, new_node_name, new_llm_components):
    """Adds edges between nodes if they share common identified objects."""
    # Placeholder: Implement robust object comparison logic if needed.
    # Current implementation relies on LLM suggesting connections or user actions.
    # This function could be enhanced to automatically suggest connections based on object overlap.
    st.info("`connect_nodes_by_common_objects` - Lógica de conexión automática no implementada activamente.")
    pass # Add logic here if desired

def check_goal_reached(llm_response_text, current_node_id, navigation_goal):
    """Checks if the LLM response or current node indicates goal achievement."""
    if not navigation_goal: return # No goal set

    goal_reached = False
    # Check if current node IS the goal
    if current_node_id and current_node_id.lower() == navigation_goal.lower():
        goal_reached = True

    # Check LLM text for keywords (adjust keywords as needed)
    if not goal_reached and llm_response_text:
        response_lower = llm_response_text.lower()
        if "goal reached" in response_lower or "destino alcanzado" in response_lower or "llegado al objetivo" in response_lower:
             goal_reached = True
             # Optionally parse the JSON first and check a specific field if available
             # llm_json = extract_llm_components(llm_response_text)
             # if llm_json and llm_json.get("goal_status") == "reached": goal_reached = True

    if goal_reached:
        st.success(f"🎉 ¡Objetivo Alcanzado: {navigation_goal}! 🎉")
        # Potentially stop further actions or offer new goal input
        return True
    return False

# --- Image Input Helper ---
def get_image_input(label, key_suffix):
    """Helper function to get image data from URL or upload using unique keys."""
    image_data = None
    st.markdown(f"**{label}:**")
    # Use horizontal radio buttons for space efficiency
    image_input_option = st.radio(
        f"Fuente ({label}):", ["URL", "Subir Archivo"],
        key=f"input_opt_{key_suffix}", horizontal=True, label_visibility="collapsed"
    )

    if image_input_option == "URL":
        image_url = st.text_input("URL:", key=f"url_{key_suffix}", placeholder="http://... o data:image/...")
        if image_url:
            # Basic validation for URL or data URI
            if image_url.startswith("http") or image_url.startswith("data:image"):
                image_data = image_url
            else:
                st.warning("URL inválida. Debe empezar con http, https o data:image", icon="⚠️")
                image_data = None
    else: # Subir Archivo
        uploaded_file = st.file_uploader(
            "Archivo:", type=["jpg", "jpeg", "png", "webp"], # Added webp
            key=f"upload_{key_suffix}", label_visibility="collapsed"
        )
        if uploaded_file is not None:
            try:
                # Check file size (optional)
                if uploaded_file.size > 15 * 1024 * 1024: # Limit to 15MB
                    st.warning("Archivo demasiado grande (> 15MB).", icon="⚠️")
                    return None

                image_bytes = uploaded_file.getvalue()
                # Determine mime type
                mime_type = uploaded_file.type
                base64_image = base64.b64encode(image_bytes).decode('utf-8')
                image_data = f"data:{mime_type};base64,{base64_image}"
            except Exception as e:
                st.error(f"Error procesando archivo subido: {e}")
                image_data = None
    return image_data

# --- ==================== Main Application Layout ==================== ---
st.title("🤖 Interfaz de Navegación Robótica con LLM")

# --- Button to Start Fresh ---
if st.sidebar.button("⚠️ Iniciar Nueva Navegación (Reset)", type="primary"):
    # Reset relevant state variables
    st.session_state.graph = initialize_graph()
    st.session_state.current_description = ""
    # st.session_state.navigation_goal = "" # Keep goal or reset? User decision.
    st.session_state.current_node = None
    st.session_state.all_descriptions = {}
    st.session_state.navigation_plan = ""
    st.session_state.action_history = []
    st.session_state.llm_components = {}
    st.session_state.input_mode = "Vista Única (Centro)"
    st.session_state.current_images = {'left': None, 'center': None, 'right': None}
    st.session_state.analyzed_images = []
    st.session_state.clicked_node_id = None
    st.session_state.selected_action = None
    st.success("Nueva navegación iniciada. Estado reseteado.")
    time.sleep(1) # Allow user to see message
    safe_rerun()

# --- Top Section: Input Configuration ---
with st.container(border=True):
    st.subheader("🎯 Configuración de Entrada")
    st.session_state.navigation_goal = st.text_input(
        "Objetivo de Navegación:",
        st.session_state.navigation_goal,
        placeholder="Ej: 'Ir a la cocina', 'Encontrar la silla roja'"
    )

    # --- Vision Mode Selection ---
    st.session_state.input_mode = st.radio(
        "Modo de Visión:",
        ["Vista Única (Centro)", "Vista Panorámica (Izq, Centro, Der)"],
        key='vision_mode_selector',
        horizontal=True,
        index=["Vista Única (Centro)", "Vista Panorámica (Izq, Centro, Der)"].index(st.session_state.input_mode)
    )

    # --- Image Input Widgets ---
    st.markdown("---")
    st.markdown("**Cargar Imagen(es) de la Vista Actual:**")
    images_data_ui = {'left': None, 'center': None, 'right': None}
    cols_img_input = st.columns(3)

    if st.session_state.input_mode == "Vista Única (Centro)":
        with cols_img_input[0]: st.empty() # Placeholder for layout consistency
        with cols_img_input[1]:
             images_data_ui['center'] = get_image_input("Imagen Central", "center_single")
        with cols_img_input[2]: st.empty() # Placeholder
    else: # Modo Vista Panorámica
        with cols_img_input[0]:
            images_data_ui['left'] = get_image_input("Imagen Izquierda", "left_pano")
        with cols_img_input[1]:
            images_data_ui['center'] = get_image_input("Imagen Centro", "center_pano")
        with cols_img_input[2]:
            images_data_ui['right'] = get_image_input("Imagen Derecha", "right_pano")

    # Update session state with images currently in the UI
    st.session_state.current_images = images_data_ui

    # --- Preview Loaded Images ---
    st.markdown("---")
    st.markdown("**Imágenes Cargadas para Análisis:**")
    preview_cols = st.columns(3)
    valid_images_count = 0
    images_to_preview = st.session_state.current_images
    with preview_cols[0]:
        if images_to_preview.get('left'):
            st.image(images_to_preview['left'], caption='Izquierda', use_container_width=True)
            valid_images_count += 1
        else: st.caption("Izquierda: N/A")
    with preview_cols[1]:
        if images_to_preview.get('center'):
            st.image(images_to_preview['center'], caption='Centro', use_container_width=True)
            valid_images_count += 1
        else: st.caption("Centro: N/A")
    with preview_cols[2]:
         if images_to_preview.get('right'):
            st.image(images_to_preview['right'], caption='Derecha', use_container_width=True)
            valid_images_count += 1
         else: st.caption("Derecha: N/A")

    # Display warnings if images are missing based on mode
    if st.session_state.input_mode == "Vista Única (Centro)" and not images_to_preview['center']:
        st.warning("Modo Vista Única: Falta la imagen central.", icon="⚠️")
    elif st.session_state.input_mode == "Vista Panorámica (Izq, Centro, Der)" and valid_images_count == 0:
        st.warning("Modo Vista Panorámica: Debes proporcionar al menos una imagen.", icon="⚠️")

    # --- Analysis Prompt & Trigger ---
    st.markdown("---")
    st.subheader("🧠 Análisis de la Vista")
    # Display the base prompt (consider making it non-editable or collapsible)
    with st.expander("Ver/Editar Prompt Base"):
        # Use the prompt loaded from utils.prompts
        prompt_text_from_file = navigation_prompt
        st.text_area("Prompt Base para LLM:", prompt_text_from_file, height=250, key="prompt_display_readonly", disabled=True) # Make read-only

    # Option to use secondary formatting prompt
    st.session_state.use_formatter = st.checkbox("Usar formateo LLM secundario si falla el parseo JSON", st.session_state.use_formatter)

    # --- Analyze Button ---
    if st.button("Analizar Vista Actual", type="primary", disabled=(valid_images_count == 0)):
        if not st.session_state.navigation_goal:
            st.warning("Por favor, define un objetivo de navegación antes de analizar.", icon="🎯")
        else:
            # 1. Prepare image inputs for the API
            image_inputs_for_api = []
            final_images_to_store = {} # Images associated with the analysis result (node)

            if st.session_state.input_mode == "Vista Única (Centro)":
                if st.session_state.current_images['center']:
                    img_src = st.session_state.current_images['center']
                    image_inputs_for_api.append({'position': 'center', 'source': img_src})
                    final_images_to_store['center'] = img_src
                # Error handled by button disabled state / warning above
            else: # Modo Panorámico
                for pos in ['left', 'center', 'right']:
                    img_src = st.session_state.current_images.get(pos)
                    if img_src:
                        image_inputs_for_api.append({'position': pos, 'source': img_src})
                        final_images_to_store[pos] = img_src
                # Error handled by button disabled state / warning above

            # 2. Prepare the prompt
            # Use the prompt loaded from file/variable
            analysis_prompt_base = navigation_prompt
            # Inject dynamic elements (Goal, History)
            action_history_str = ", ".join(st.session_state.action_history[-5:]) # Last 5 actions
            analysis_prompt_filled = analysis_prompt_base.replace(
                "{navigation_goal}", st.session_state.navigation_goal or "No definido"
            ).replace(
                "{action_history}", action_history_str or "Ninguna"
            )

            # 3. Call the API
            with st.spinner(f"🧠 Analizando vista ({st.session_state.input_mode})..."):
                try:
                    llm_response_raw = analyze_image_with_gpt(image_inputs_for_api, analysis_prompt_filled)
                    st.session_state.current_description = llm_response_raw # Store raw response
                except Exception as api_err:
                    st.error(f"Error durante la llamada a la API: {api_err}")
                    llm_response_raw = None

            # 4. Process the response
            if llm_response_raw:
                st.session_state.llm_components = extract_llm_components(llm_response_raw)

                # Optional: Use formatter if parsing failed
                if not st.session_state.llm_components and st.session_state.use_formatter:
                    st.info("Parseo inicial falló. Intentando formateo con LLM secundario...")
                    with st.spinner("🛠️ Formateando respuesta..."):
                        formatted_response = format_llm_response(llm_response_raw) # Needs implementation
                        if formatted_response:
                            st.session_state.llm_components = extract_llm_components(formatted_response)
                            if st.session_state.llm_components:
                                st.info("Formateo y parseo exitosos.")
                                st.session_state.current_description = formatted_response # Store formatted response
                        else:
                             st.error("Formateo secundario falló o no está implementado.")

                # 5. Update Graph and State if components were successfully extracted
                if st.session_state.llm_components:
                    st.success("Análisis completado y JSON parseado.")

                    # Extract suggested node name (provide a default)
                    suggested_node_name = st.session_state.llm_components.get(
                        "landmarks_and_suggested_node_name", {}
                    ).get("suggested_node_name", "").strip()
                    # Sanitize node name (replace spaces, ensure uniqueness maybe?)
                    suggested_node_name = re.sub(r'\s+', '_', suggested_node_name)
                    if not suggested_node_name: # Generate default if empty
                         suggested_node_name = f"Nodo_{st.session_state.graph.number_of_nodes() + 1}"
                         st.info(f"LLM no sugirió nombre, usando nombre por defecto: {suggested_node_name}")

                    # Extract scene description for node
                    node_description = st.session_state.llm_components.get("overall_scene_description", "Descripción no proporcionada.")

                    # Prepare node data
                    node_data = {
                        "description": node_description,
                        "images": final_images_to_store, # Dict of images used for this node's analysis
                        "llm_json": st.session_state.llm_components, # Full parsed JSON
                        "input_mode": st.session_state.input_mode, # Mode used for analysis
                        "timestamp": time.time() # Record analysis time
                    }

                    # Add or Update Node in Graph
                    previous_node = st.session_state.current_node # Node before analysis
                    node_existed = suggested_node_name in st.session_state.graph

                    if not node_existed:
                        add_node_to_graph(st.session_state.graph, suggested_node_name, node_data)
                        st.info(f"Nuevo nodo '{suggested_node_name}' añadido al grafo.")
                        # Add to history only if it's a genuinely new node analysis
                        st.session_state.analyzed_images.append((suggested_node_name, final_images_to_store))
                    else:
                        update_node_data(st.session_state.graph, suggested_node_name, node_data)
                        st.info(f"Nodo existente '{suggested_node_name}' actualizado con nueva información.")
                        # Update history entry? Or keep only first analysis? Decision: Update existing.
                        for i, (nid, _) in enumerate(st.session_state.analyzed_images):
                             if nid == suggested_node_name:
                                 st.session_state.analyzed_images[i] = (suggested_node_name, final_images_to_store)
                                 break
                        else: # Append if somehow it existed but wasn't in history
                            st.session_state.analyzed_images.append((suggested_node_name, final_images_to_store))


                    # Connect nodes automatically? (Using placeholder function)
                    # connect_nodes_by_common_objects(st.session_state.graph, suggested_node_name, st.session_state.llm_components)

                    # Logic to connect previous node to this new/updated node
                    # This requires an action. If LLM suggests a specific move to this node, use it.
                    # Otherwise, might need user input. For now, assume direct connection with placeholder action.
                    if previous_node and previous_node != suggested_node_name:
                         # Check if an edge already exists
                         if not st.session_state.graph.has_edge(previous_node, suggested_node_name):
                             # How to get the action? Look in llm_components? Ask user?
                             # Simplification: Add edge with generic action if none provided by LLM/user.
                             # TODO: Improve action determination logic.
                             connection_action = "move_to_analyzed" # Placeholder action
                             add_edge_to_graph(st.session_state.graph, previous_node, suggested_node_name, connection_action)
                             st.info(f"Conexión añadida: '{previous_node}' -> '{suggested_node_name}' (Acción: {connection_action})")
                             # Add reverse edge? Only if movement is reversible. Assumed directed graph.

                    # Update robot's current location
                    st.session_state.current_node = suggested_node_name
                    st.session_state.clicked_node_id = None # Reset clicked node after analysis moves position

                    # Check if goal reached
                    goal_status = check_goal_reached(st.session_state.current_description, st.session_state.current_node, st.session_state.navigation_goal)

                    # Rerun to update UI
                    safe_rerun()

                else: # LLM components extraction failed even after potential formatting
                    st.error("Fallo la extracción de componentes JSON de la respuesta LLM.")
                    st.subheader("Respuesta Cruda del LLM:")
                    st.text(llm_response_raw or "No se recibió respuesta.")


# --- Middle Section: Preview & History ---
with st.container(border=True):
    st.subheader(" G Vistas Rápidas")
    col_preview_graph, col_preview_node = st.columns([2, 3]) # Adjust proportions as needed

    # --- Graph Preview ---
    with col_preview_graph:
        st.markdown("**Grafo (Vista Rápida)**")
        if st.session_state.graph.number_of_nodes() > 0:
            # Highlight current node
            agraph_nodes_preview, agraph_edges_preview = convert_nx_to_agraph(st.session_state.graph) # Pass door_states if used
            for node in agraph_nodes_preview:
                if node.id == st.session_state.current_node:
                    node.color = "#FF0000" # Highlight current node in red (example)
                    node.borderWidth = 3
                if node.id == st.session_state.clicked_node_id:
                     node.color = "#00FF00" # Highlight clicked node in green (example)
                     node.borderWidth = 3


            config_preview = Config(
                width='100%',
                height=400, # Adjust height as needed
                directed=True,
                physics=False, # Faster rendering for preview
                hierarchical=False, # Try False for better layout sometimes
                # highlight_active=True # Doesn't work as expected directly with clicks
            )
            if agraph_nodes_preview:
                # Justo antes de la línea 571
                st.write("--- DEBUG INFO ---")
                st.write("Nodes para agraph:")
                # Convertir a diccionarios para mejor visualización en Streamlit
                try:
                    nodes_list_dict = [vars(n) for n in agraph_nodes_preview]
                    st.json(nodes_list_dict)
                except Exception as e:
                    st.error(f"Error convirtiendo nodos a dict: {e}")
                    st.write(agraph_nodes_preview) # Mostrar como lista si falla

                st.write("Edges para agraph:")
                try:
                    edges_list_dict = [vars(e) for e in agraph_edges_preview]
                    st.json(edges_list_dict)
                except Exception as e:
                    st.error(f"Error convirtiendo edges a dict: {e}")
                    st.write(agraph_edges_preview) # Mostrar como lista si falla

                st.write("Config para agraph:")
                st.json(vars(config_preview))
                st.write("--- FIN DEBUG INFO ---")


                # Capture clicks on this graph instance
                clicked_node_data = agraph(
                    nodes=agraph_nodes_preview,
                    edges=agraph_edges_preview,
                    config=config_preview
                 )
                if clicked_node_data: # If a node was clicked
                    st.session_state.clicked_node_id = clicked_node_data
                    # Rerun to update the node preview section immediately
                    safe_rerun()
            else:
                 st.info("Calculando grafo...")
        else:
            st.info("El grafo está vacío. Analiza una vista para empezar.")

    # --- Selected Node Preview ---
    with col_preview_node:
        st.markdown("**Nodo Seleccionado/Actual**")
        # Determine which node to display details for
        node_id_to_display = st.session_state.clicked_node_id or st.session_state.current_node

        if node_id_to_display and node_id_to_display in st.session_state.graph:
            st.markdown(f"**ID:** `{node_id_to_display}`")
            if node_id_to_display == st.session_state.current_node:
                 st.markdown("📍 **(Ubicación Actual)**")

            node_info = get_node_data(st.session_state.graph, node_id_to_display)
            if node_info:
                # --- Display Images associated with the node ---
                node_images = node_info.get("images", {}) # Get the dict of images
                st.markdown("**Vista(s) del Nodo:**")
                img_cols = st.columns(3)
                with img_cols[0]:
                    if node_images.get('left'): st.image(node_images['left'], caption='Izquierda', use_container_width=True)
                    else: st.caption("Izq: N/A")
                with img_cols[1]:
                    if node_images.get('center'): st.image(node_images['center'], caption='Centro', use_container_width=True)
                    else: st.caption("Centro: N/A")
                with img_cols[2]:
                     if node_images.get('right'): st.image(node_images['right'], caption='Derecha', use_container_width=True)
                     else: st.caption("Der: N/A")

                # --- Display Node Info ---
                st.markdown(f"**Modo Análisis:** {node_info.get('input_mode', 'N/A')}")
                st.markdown(f"**Descripción:** {node_info.get('description', 'N/A')}")
                with st.expander("Ver Detalles del Análisis (JSON)"):
                    st.json(node_info.get("llm_json", {}))
            else:
                st.warning(f"No se encontraron datos para el nodo {node_id_to_display}. Puede que el grafo esté corrupto.")
                # Consider resetting clicked_node_id if data is missing
                # if st.session_state.clicked_node_id == node_id_to_display: st.session_state.clicked_node_id = None

        elif st.session_state.clicked_node_id:
             st.warning(f"Nodo '{st.session_state.clicked_node_id}' seleccionado pero no encontrado en el grafo. Refrescando...")
             st.session_state.clicked_node_id = None # Reset invalid click
             time.sleep(1)
             safe_rerun()
        else:
            st.info("Analiza una vista o haz clic en un nodo del grafo para ver detalles.")

    # --- History of Analyzed Images/Views ---
    st.markdown("---")
    st.subheader("📜 Historial de Vistas Analizadas")
    if st.session_state.analyzed_images:
         # Display in rows (e.g., 5 columns per row)
         max_cols = 6
         num_images = len(st.session_state.analyzed_images)
         num_rows = (num_images + max_cols - 1) // max_cols

         image_idx = 0
         for r in range(num_rows):
             cols_hist = st.columns(max_cols)
             for c in range(max_cols):
                 if image_idx < num_images:
                     node_id, img_dict = st.session_state.analyzed_images[image_idx]
                     # Get thumbnail (prefer center, then left, then right)
                     thumb_img = img_dict.get('center') or img_dict.get('left') or img_dict.get('right')
                     with cols_hist[c]:
                         if thumb_img:
                             st.image(thumb_img, caption=f"#{image_idx+1}: {node_id[:15]}..", width=100) # Shorten name if long
                         else:
                             st.caption(f"#{image_idx+1}: {node_id[:15]}..\n(Sin img)")
                         # Button to select this node in the preview
                         if st.button(f"Ver #{image_idx+1}", key=f"view_hist_{image_idx}", help=f"Ver detalles del nodo {node_id}"):
                             st.session_state.clicked_node_id = node_id
                             safe_rerun()
                     image_idx += 1
                 else:
                     cols_hist[c].empty() # Fill remaining columns in the last row
    else:
        st.info("No se han analizado vistas aún.")


# --- Bottom Section: Full Graph, Plan & Actions ---
with st.container(border=True):
    st.subheader("🗺️ Grafo Completo, Plan y Acciones")
    col_graph_full, col_plan_full = st.columns([3, 2]) # Adjust proportions

    # --- Full Graph Display ---
    with col_graph_full:
        st.markdown("**Grafo de Navegación Completo**")
        if st.session_state.graph.number_of_nodes() > 0:
            # Use similar highlighting as preview graph
            agraph_nodes_full, agraph_edges_full = convert_nx_to_agraph(st.session_state.graph) # Pass door_states if used
            for node in agraph_nodes_full:
                 if node.id == st.session_state.current_node:
                     node.color = "#FF0000"
                     node.borderWidth = 3
                 if node.id == st.session_state.clicked_node_id:
                      node.color = "#00FF00"
                      node.borderWidth = 3

            config_full = Config(
                width='100%',
                height=600, # Larger height for full graph
                directed=True,
                physics=True, # Enable physics for potentially better layout
                hierarchical=False, # Usually better for exploration graphs
                nodes={'shape': 'dot', 'size': 16}, # Customize node appearance
                edges={'smooth': True}, # Customize edge appearance
                interaction={'navigationButtons': True, 'keyboard': True}, # Add controls
                # layout={'improvedLayout': True} # Experiment with layout options
                 )
            if agraph_nodes_full:
                 # No need to capture clicks here unless desired for other interactions
                 agraph(nodes=agraph_nodes_full, edges=agraph_edges_full, config=config_full)
            else:
                st.info("El grafo está vacío o no se pudo renderizar.")
        else:
            st.info("Grafo vacío. Analiza vistas para construir el mapa.")

    # --- Plan & Actions Section ---
    with col_plan_full:
        st.markdown("**Plan y Acciones Sugeridas**")

        # Display actions suggested by the last LLM analysis
        suggested_actions = st.session_state.llm_components.get('robot_perspective_and_potential_actions', [])
        if suggested_actions and isinstance(suggested_actions, list) and len(suggested_actions) > 0:
            st.markdown("**Acciones Sugeridas por LLM:**")
            # Using radio buttons for selection
            chosen_action = st.radio(
                "Selecciona la próxima acción:",
                options=suggested_actions,
                key="action_selector_radio",
                index=None, # Default to no selection
                help="Elige la acción que debe ejecutar el robot."
            )
            if chosen_action and st.button(f"Confirmar Acción: '{chosen_action}'"):
                st.session_state.selected_action = chosen_action
                st.session_state.action_history.append(chosen_action)
                st.success(f"Acción '{chosen_action}' añadida al historial. (Simulado - el robot debería ejecutarla ahora)")
                # TODO: Trigger robot execution here if applicable
                # Reset selection and potentially rerun
                st.session_state.selected_action = None # Reset after confirmation
                st.session_state.timer_start = None
                safe_rerun()


        elif st.session_state.llm_components: # Analysis happened, but no actions suggested
            st.info("El último análisis no sugirió acciones específicas.")
        else: # No analysis done yet
            st.info("Analiza una vista para obtener acciones sugeridas.")

        st.markdown("---")

        # --- Navigation Plan Generation ---
        st.markdown("**Plan de Navegación**")
        can_generate_plan = (
            st.session_state.graph.number_of_edges() > 0 and
            st.session_state.current_node and
            st.session_state.navigation_goal and
            nx.has_path(st.session_state.graph, st.session_state.current_node, st.session_state.navigation_goal) # Check path exists
        )

        # Check if goal node exists in graph
# Check if goal node exists in graph
        goal_node_exists = st.session_state.navigation_goal in st.session_state.graph if st.session_state.navigation_goal else False

        if st.session_state.current_node and st.session_state.navigation_goal:
             if not goal_node_exists:
                 st.warning(f"El nodo objetivo '{st.session_state.navigation_goal}' no existe actualmente en el grafo.", icon="⚠️")
             # --->>> CORRECCIÓN <<<---
             # Solo verifica el camino si el nodo objetivo existe
             elif goal_node_exists and not nx.has_path(st.session_state.graph, st.session_state.current_node, st.session_state.navigation_goal):
                 st.warning(f"No se encontró una ruta desde '{st.session_state.current_node}' hasta '{st.session_state.navigation_goal}' en el grafo actual.", icon="⚠️")


        if st.button("Generar/Actualizar Plan", disabled=not (st.session_state.current_node and st.session_state.navigation_goal and goal_node_exists)):
                    # --->>> CORRECCIÓN (Añadir esta comprobación interna) <<<---
                    if goal_node_exists and nx.has_path(st.session_state.graph, st.session_state.current_node, st.session_state.navigation_goal):
                        with st.spinner("Generando plan de navegación..."):
                            try:
                                st.session_state.navigation_plan = generate_navigation_plan(
                                    graph=st.session_state.graph,
                                    start_node=st.session_state.current_node,
                                    goal_node=st.session_state.navigation_goal,
                                    # Pass other required info like descriptions or history if needed by the planner
                                    # all_descriptions=st.session_state.all_descriptions,
                                    # action_history=st.session_state.action_history
                                )
                                st.success("Plan de navegación generado/actualizado.")
                                safe_rerun() # Rerun to display the new plan
                            except nx.NetworkXNoPath:
                                st.error(f"Error: No existe ruta de '{st.session_state.current_node}' a '{st.session_state.navigation_goal}'.")
                            except Exception as e:
                                st.error(f"Error al generar el plan: {e}")
                    # Manejar caso donde el nodo existe pero no hay path, o el nodo no existe (aunque el botón estaba deshabilitado)
                    elif goal_node_exists: # Sabemos que existe pero no hay path
                        st.error("No se puede generar plan: No existe ruta conectando los nodos.")
                    else: # El nodo objetivo no existe (el botón no debería haber sido clickeable, pero por si acaso)
                        st.error(f"No se puede generar plan: El nodo objetivo '{st.session_state.navigation_goal}' no existe.")


        # Display the generated plan
        if st.session_state.navigation_plan:
            st.markdown("---")
            st.markdown("#### Plan Actual:")
            st.markdown(st.session_state.navigation_plan) # Display plan (assuming it's markdown or text)
        else:
             # Provide guidance if plan cannot be generated
             required = []
             if not st.session_state.current_node: required.append("ubicación actual definida")
             if not st.session_state.navigation_goal: required.append("objetivo de navegación")
             if st.session_state.graph.number_of_nodes() == 0: required.append("grafo no vacío")
             elif st.session_state.navigation_goal and st.session_state.current_node and not goal_node_exists: required.append(f"que el nodo '{st.session_state.navigation_goal}' exista en el grafo")
             elif st.session_state.navigation_goal and st.session_state.current_node and goal_node_exists and not nx.has_path(st.session_state.graph, st.session_state.current_node, st.session_state.navigation_goal) : required.append("una ruta válida al objetivo")

             if required:
                 st.info(f"Se necesita {', '.join(required)} para generar un plan.")


        # --- Action History ---
        with st.expander("Ver Historial de Acciones"):
            if st.session_state.action_history:
                # Display actions in reverse order (most recent first)
                for i, action in enumerate(reversed(st.session_state.action_history), 1):
                    st.markdown(f"{len(st.session_state.action_history) - i + 1}. `{action}`")
            else:
                st.info("No se han registrado acciones.")

# --- Footer (Optional) ---
st.markdown("---")
st.caption("Navegación Robótica Asistida por LLM - v2.0 (Panorámica)")