import streamlit as st
import time
import base64
from PIL import Image
import os
import sys
import json
import re
import networkx as nx
from networkx.readwrite import json_graph

# Ajustar path si fuera necesario
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Importar funciones y módulos
from api.gpt_client import analyze_image_with_gpt
from utils.prompts import navigation_prompt, formatting_prompt
from utils.parsing_llm_response import parse_raw_text_to_json
from navigation.planer import generate_navigation_plan
from mapping.graph_manager import (
    initialize_graph, add_node_to_graph, add_edge_to_graph,
    convert_nx_to_agraph, get_node_data, update_node_data
)
from streamlit_agraph import agraph, Config

st.set_page_config(layout="wide", page_title="Navegación Robótica con LLM")

# --- Función auxiliar para reiniciar la app de forma segura ---
def safe_rerun():
    try:
        st.experimental_rerun()
    except Exception as e:
        st.warning("No se pudo reiniciar la app automáticamente.")

# --- Estado de sesión ---
if 'graph' not in st.session_state:
    st.session_state.graph = initialize_graph()
if 'current_description' not in st.session_state:
    st.session_state.current_description = ""
if 'current_image' not in st.session_state:
    st.session_state.current_image = None
if 'navigation_goal' not in st.session_state:
    st.session_state.navigation_goal = ""
if 'current_node' not in st.session_state:
    st.session_state.current_node = None
if 'all_descriptions' not in st.session_state:
    st.session_state.all_descriptions = {}
if 'navigation_plan' not in st.session_state:
    st.session_state.navigation_plan = ""
if 'action_history' not in st.session_state:
    st.session_state.action_history = []
if 'llm_components' not in st.session_state:
    st.session_state.llm_components = {}
if 'suggested_action' not in st.session_state:
    st.session_state.suggested_action = ""
if 'use_formatter' not in st.session_state:
    st.session_state.use_formatter = False
if 'timer_start' not in st.session_state:
    st.session_state.timer_start = None
if 'selected_action' not in st.session_state:
    st.session_state.selected_action = None
if 'clicked_node_id' not in st.session_state:
    st.session_state.clicked_node_id = None
if 'analyzed_images' not in st.session_state:
    st.session_state.analyzed_images = []  # List of tuples: (node_id, image_data)

# --- Funciones para guardar/cargar estado ---
def save_state():
    graph_data = json_graph.node_link_data(st.session_state.graph)
    state = {
         "graph": graph_data,
         "current_description": st.session_state.current_description,
         "current_image": st.session_state.current_image,
         "navigation_goal": st.session_state.navigation_goal,
         "current_node": st.session_state.current_node,
         "all_descriptions": st.session_state.all_descriptions,
         "navigation_plan": st.session_state.navigation_plan,
         "action_history": st.session_state.action_history,
         "llm_components": st.session_state.llm_components,
         "suggested_action": st.session_state.suggested_action,
         "analyzed_images": st.session_state.analyzed_images
    }
    return state

def load_state(state):
    st.session_state.graph = json_graph.node_link_graph(state["graph"])
    st.session_state.current_description = state["current_description"]
    st.session_state.current_image = state["current_image"]
    st.session_state.navigation_goal = state["navigation_goal"]
    st.session_state.current_node = state["current_node"]
    st.session_state.all_descriptions = state["all_descriptions"]
    st.session_state.navigation_plan = state["navigation_plan"]
    st.session_state.action_history = state["action_history"]
    st.session_state.llm_components = state["llm_components"]
    st.session_state.suggested_action = state["suggested_action"]
    st.session_state.analyzed_images = state["analyzed_images"]

# --- Sección para guardar y cargar estado ---
st.sidebar.header("Guardar / Cargar Estado")
if st.sidebar.button("Guardar Estado"):
    state = save_state()
    state_json = json.dumps(state)
    st.sidebar.download_button(
        label="Descargar Estado",
        data=state_json,
        file_name="estado_navegacion.json",
        mime="application/json"
    )

uploaded_state_file = st.sidebar.file_uploader("Cargar Estado Guardado", type="json")
if uploaded_state_file is not None:
    try:
        state_data = json.load(uploaded_state_file)
        load_state(state_data)
        st.sidebar.success("Estado cargado exitosamente.")
        safe_rerun()
    except Exception as e:
        st.sidebar.error(f"Error al cargar el estado: {e}")

def format_llm_response(raw_response):
    prompt = formatting_prompt.replace('{raw_llm_output}', raw_response)
    return analyze_image_with_gpt(None, prompt)

def extract_llm_components(llm_response):
    try:
        json_str = re.search(r'^\s*\{.*\}\s*$', llm_response, re.DOTALL)
        if not json_str:
            raise ValueError("No JSON found")
        parsed = json.loads(json_str.group())
        required_keys = [
            "overall_scene_description",
            "identified_objects",
            "potential_navigation_paths",
            "obstacles",
            "landmarks_and_suggested_node_name",
            "robot_perspective_and_potential_actions"
        ]
        for key in required_keys:
            if key not in parsed:
                parsed[key] = [] if key.endswith('s') else {}
        node_name = parsed["landmarks_and_suggested_node_name"].get("suggested_node_name", "")
        if node_name:
            parsed["landmarks_and_suggested_node_name"]["suggested_node_name"] = (
                node_name.replace(" ", "_").replace(",", "").strip("_")
            )
        return parsed
    except Exception as e:
        st.error(f"JSON Decoding Error: {str(e)}")
        st.error(f"Raw Response: {llm_response[:500]}...")
        try:
            fixed_response = re.sub(r'(?<!\\)\'(?!\\))', '"', llm_response)
            fixed_response = re.sub(r"(\w+):", r'"\1":', fixed_response)
            return json.loads(fixed_response)
        except:
            return parse_raw_text_to_json(llm_response)

# --- Funciones adicionales ---
def connect_nodes_by_common_objects(graph, new_node_name, new_llm_components):
    """
    Revisa los objetos identificados en el nuevo nodo y los compara con los de los nodos existentes.
    Si hay objetos en común, se añade una conexión (arista) con un label que indique los objetos compartidos.
    """
    new_objs_raw = new_llm_components.get("identified_objects", [])
    new_objects = set()
    for obj in new_objs_raw:
        if isinstance(obj, dict):
            new_objects.add(obj.get("name", json.dumps(obj, sort_keys=True)))
        else:
            new_objects.add(obj)
    
    for existing_node, data in graph.nodes(data=True):
        if existing_node == new_node_name:
            continue
        existing_objs_raw = data.get("llm_json", {}).get("identified_objects", [])
        existing_objects = set()
        for obj in existing_objs_raw:
            if isinstance(obj, dict):
                existing_objects.add(obj.get("name", json.dumps(obj, sort_keys=True)))
            else:
                existing_objects.add(obj)
        common_objects = new_objects.intersection(existing_objects)
        if common_objects:
            action_label = f"Conexión por: {', '.join(common_objects)}"
            if not graph.has_edge(existing_node, new_node_name):
                add_edge_to_graph(graph, existing_node, new_node_name, action_label)
                st.info(f"Conectado '{existing_node}' a '{new_node_name}' por objetos: {', '.join(common_objects)}")

def check_goal_reached(llm_response, current_node, navigation_goal):
    """
    Si en la respuesta del LLM se detectan palabras clave que indiquen llegada al destino
    o si el nodo actual coincide con el goal, se muestra un mensaje de éxito.
    """
    llm_lower = llm_response.lower()
    if ("llegado" in llm_lower or "destino alcanzado" in llm_lower) or (current_node == navigation_goal and navigation_goal):
        st.success(f"¡Has llegado al destino: {navigation_goal}!")

# --- Layout Principal ---
st.title("Interfaz de Navegación Robótica con LLM")

# Botón para iniciar una nueva navegación
if st.button("Iniciar Nueva Navegación"):
    st.write("Iniciar Nueva Navegación button pressed")
    if 'graph' in st.session_state:
        st.write("Session state 'graph' exists. Performing reset and rerun.")
        st.session_state.current_node = None
        st.session_state.action_history = []
        st.session_state.graph = initialize_graph()
        st.session_state.analyzed_images = []
        st.session_state.clicked_node_id = None
        st.session_state.navigation_plan = ""
        safe_rerun()
    else:
        st.write("Session state 'graph' does not exist. Performing reset.")
        st.session_state.current_node = None
        st.session_state.action_history = []
        st.session_state.graph = initialize_graph()
        st.session_state.analyzed_images = []
        st.session_state.clicked_node_id = None
        st.session_state.navigation_plan = ""

# Sección superior: Entrada de imagen y análisis
with st.container():
    col_input, col_preview = st.columns([1, 1])
    with col_input:
        st.subheader("Objetivo y Entrada")
        st.session_state.navigation_goal = st.text_input("Objetivo de Navegación:", st.session_state.navigation_goal)
        image_input_option = st.radio("Método de entrada:", ["URL de la imagen", "Subir imagen"])
        image_data = None
        if image_input_option == "URL de la imagen":
            image_url = st.text_input("URL de la imagen:")
            if image_url:
                try:
                    st.image(image_url, caption='Imagen desde URL', width=250)
                    image_data = image_url
                except Exception as e:
                    st.error(f"Error al cargar imagen: {e}")
                    image_data = None
        else:
            uploaded_file = st.file_uploader("Subir imagen:", type=["jpg", "jpeg", "png"])
            if uploaded_file is not None:
                image = Image.open(uploaded_file)
                st.image(image, caption='Imagen Cargada', width=250)
                image_bytes = uploaded_file.getvalue()
                base64_image = base64.b64encode(image_bytes).decode('utf-8')
                image_data = f"data:image/jpeg;base64,{base64_image}"
        st.subheader("Prompt para Análisis")
        prompt = st.text_area("Descripción para la imagen:", navigation_prompt, height=120)
        st.session_state.use_formatter = st.checkbox("Usar formateo si falla JSON", st.session_state.use_formatter)
        if st.button("Analizar Imagen"):
            if not st.session_state.navigation_goal:
                st.warning("Define un objetivo de navegación.")
            elif image_data:
                full_prompt = navigation_prompt.replace(
                    "Current Navigation Goal: {navigation_goal}",
                    f"Current Navigation Goal: {st.session_state.navigation_goal}"
                )
                with st.spinner("Analizando imagen..."):
                    llm_response = analyze_image_with_gpt(image_data, full_prompt)
                    st.session_state.current_description = llm_response
                    st.session_state.llm_components = extract_llm_components(llm_response)
                    if not st.session_state.llm_components and st.session_state.use_formatter:
                        with st.spinner("Formateando respuesta..."):
                            formatted_response = format_llm_response(llm_response)
                            st.session_state.current_description = formatted_response
                            st.session_state.llm_components = extract_llm_components(formatted_response)
                    if st.session_state.llm_components:
                        suggested_node_name = st.session_state.llm_components.get(
                            "landmarks_and_suggested_node_name", {}
                        ).get("suggested_node_name", "Ubicación_Desconocida")
                        suggested_actions = st.session_state.llm_components.get(
                            "robot_perspective_and_potential_actions", []
                        )
                        if suggested_node_name == "Ubicación_Desconocida":
                            if st.session_state.graph.number_of_nodes() == 0:
                                suggested_node_name = "Inicio"
                            else:
                                suggested_node_name = f"Visitado_{st.session_state.graph.number_of_nodes() + 1}"
                        if st.session_state.current_node is None:
                            st.session_state.current_node = suggested_node_name
                        description = st.session_state.llm_components.get("overall_scene_description", "")
                        if suggested_node_name not in st.session_state.graph:
                            node_data = {
                                "description": description,
                                "image": image_data,
                                "llm_json": st.session_state.llm_components
                            }
                            add_node_to_graph(st.session_state.graph, suggested_node_name, node_data)
                            if suggested_node_name not in st.session_state.all_descriptions:
                                st.session_state.all_descriptions[suggested_node_name] = description
                            st.session_state.analyzed_images.append((suggested_node_name, image_data))
                            if st.session_state.current_node != suggested_node_name and st.session_state.current_node in st.session_state.graph:
                                st.info("Selecciona la acción para conectar nodos manualmente.")
                                if suggested_actions:
                                    chosen_action = st.selectbox("Acción sugerida:", suggested_actions)
                                else:
                                    chosen_action = st.text_input("Acción sugerida:")
                                user_action = st.text_input("O ingresa otra acción:")
                                action_to_add = user_action if user_action else chosen_action
                                if st.button("Confirmar y Conectar"):
                                    add_edge_to_graph(st.session_state.graph, st.session_state.current_node, suggested_node_name, action_to_add)
                                    st.session_state.action_history.append(action_to_add)
                                    st.session_state.current_node = suggested_node_name
                            connect_nodes_by_common_objects(st.session_state.graph, suggested_node_name, st.session_state.llm_components)
                        else:
                            node_data = {
                                "description": description,
                                "image": image_data,
                                "llm_json": st.session_state.llm_components
                            }
                            update_node_data(st.session_state.graph, suggested_node_name, node_data)
                            st.session_state.analyzed_images.append((suggested_node_name, image_data))
                            if st.session_state.current_node != suggested_node_name:
                                if suggested_actions:
                                    chosen_action = st.selectbox("Acción sugerida:", suggested_actions)
                                else:
                                    chosen_action = st.text_input("Acción sugerida:")
                                user_action = st.text_input("O ingresa otra acción:")
                                action_to_add = user_action if user_action else chosen_action
                                if st.button(f"Conectar '{st.session_state.current_node}' a '{suggested_node_name}'"):
                                    add_edge_to_graph(st.session_state.graph, st.session_state.current_node, suggested_node_name, action_to_add)
                                    st.session_state.action_history.append(action_to_add)
                                    st.session_state.current_node = suggested_node_name
                            connect_nodes_by_common_objects(st.session_state.graph, suggested_node_name, st.session_state.llm_components)
                        check_goal_reached(st.session_state.current_description, st.session_state.current_node, st.session_state.navigation_goal)
                    else:
                        st.warning("No se obtuvo respuesta parseable del LLM.")
            else:
                st.warning("Sube o ingresa una URL de imagen.")
    with col_preview:
        st.subheader("Vista Previa: Nodo y Grafo")
        if st.session_state.graph.number_of_nodes() > 0:
            config_preview = Config(width='100%', height=300, directed=True, physics=False, hierarchical=True)
            agraph_nodes_preview, agraph_edges_preview = convert_nx_to_agraph(st.session_state.graph)
            if agraph_nodes_preview:
                return_val = agraph(nodes=agraph_nodes_preview, edges=agraph_edges_preview, config=config_preview)
                if return_val and 'clicked_node_id' in return_val:
                    st.session_state.clicked_node_id = return_val['clicked_node_id']
        node_id_to_display = st.session_state.clicked_node_id if st.session_state.clicked_node_id else st.session_state.current_node
        if node_id_to_display:
            col_img_prev, col_info_prev = st.columns([1, 2])
            with col_img_prev:
                node_info = get_node_data(st.session_state.graph, node_id_to_display)
                if node_info:
                    st.write("**Nodo:**", node_id_to_display)
                    image_str = node_info.get("image", "")
                    if image_str:
                        st.image(image_str, width=200)
                    else:
                        st.write("Sin imagen disponible.")
            with col_info_prev:
                if node_info:
                    st.write("**Descripción:**", node_info.get("description", ""))
                    st.json(node_info.get("llm_json", {}))
        else:
            st.info("Selecciona un nodo del grafo o analiza una imagen.")
        st.subheader("Historial de Imágenes Analizadas")
        if st.session_state.analyzed_images:
            cols = st.columns(len(st.session_state.analyzed_images))
            for i, (node_id, img_data) in enumerate(st.session_state.analyzed_images):
                with cols[i]:
                    if img_data:
                        st.image(img_data, caption=f"#{i+1}: {node_id}", width=100, use_container_width=False)
                        if st.button(f"Ver #{i+1}", key=f"view_image_{i}"):
                            st.session_state.clicked_node_id = node_id
                            safe_rerun()
                    else:
                        st.write(f"Imagen #{i+1}: {node_id} (sin datos)")
        else:
            st.info("No se han analizado imágenes aún.")

# Sección inferior: Grafo, Plan y Acciones
with st.container():
    st.subheader("Grafo, Plan y Acciones")
    col_graph_full, col_plan_full = st.columns([1, 1])
    with col_graph_full:
        st.subheader("Grafo de Navegación Completo")
        if st.session_state.graph.number_of_nodes() > 0:
            config_full = Config(width='100%', height=600, directed=True, physics=True, hierarchical=False)
            agraph_nodes_full, agraph_edges_full = convert_nx_to_agraph(st.session_state.graph)
            if agraph_nodes_full:
                agraph(nodes=agraph_nodes_full, edges=agraph_edges_full, config=config_full)
            else:
                st.info("El grafo no tiene nodos/aristas.")
        else:
            st.info("Grafo vacío. Analiza imágenes para construir el mapa.")
    with col_plan_full:
        st.subheader("Plan & Acciones")
        actions = st.session_state.llm_components.get('robot_perspective_and_potential_actions', [])
        if actions:
            st.markdown("**Acciones Sugeridas:**")
            chosen_action = st.radio("Selecciona la acción:", actions, key="action_selector_full")
            if st.button("Confirmar Acción"):
                st.session_state.selected_action = chosen_action
                st.session_state.action_history.append(chosen_action)
                st.success(f"Acción '{chosen_action}' agregada al historial.")
            if st.session_state.selected_action is None:
                if st.session_state.timer_start is None:
                    st.session_state.timer_start = time.time()
                else:
                    elapsed = time.time() - st.session_state.timer_start
                    if elapsed >= 5:
                        auto_action = actions[0]
                        st.session_state.selected_action = auto_action
                        st.session_state.action_history.append(auto_action)
                        st.success(f"Acción '{auto_action}' seleccionada automáticamente.")
                        st.session_state.timer_start = None
                        safe_rerun()
            else:
                st.session_state.timer_start = None
        else:
            st.info("No hay acciones sugeridas. Analiza una imagen primero.")
        if st.session_state.graph.number_of_edges() > 0 and st.session_state.current_node and st.session_state.navigation_goal:
            if st.button("Generar/Actualizar Plan de Navegación"):
                with st.spinner("Generando plan..."):
                    try:
                        st.session_state.navigation_plan = generate_navigation_plan(
                            st.session_state.graph,
                            st.session_state.current_node,
                            st.session_state.navigation_goal,
                            st.session_state.all_descriptions,
                            st.session_state.action_history
                        )
                        safe_rerun()
                    except Exception as e:
                        st.error(f"Error generando plan: {str(e)}")
            if st.session_state.navigation_plan:
                st.markdown("---")
                st.markdown("#### Plan de Navegación:")
                st.markdown(st.session_state.navigation_plan)
        else:
            required_conditions = []
            if st.session_state.graph.number_of_edges() == 0:
                required_conditions.append("al menos una conexión entre nodos")
            if not st.session_state.current_node:
                required_conditions.append("nodo actual definido")
            if not st.session_state.navigation_goal:
                required_conditions.append("objetivo de navegación establecido")
            if required_conditions:
                st.info(f"Requerido para generar plan: {', '.join(required_conditions)}")
        with st.expander("Historial de Acciones"):
            if st.session_state.action_history:
                for i, action in enumerate(st.session_state.action_history, 1):
                    st.markdown(f"{i}. {action}")
            else:
                st.info("No se han registrado acciones.")
