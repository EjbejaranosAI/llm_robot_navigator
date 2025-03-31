# src/mapping/graph_manager.py
import networkx as nx
from streamlit_agraph import Node, Edge

def initialize_graph():
    return nx.DiGraph()

def add_node_to_graph(graph, node_id, data):
    graph.add_node(node_id, **data)

def add_edge_to_graph(graph, node_from, node_to, action):
    graph.add_edge(node_from, node_to, action=action)

def convert_nx_to_agraph(graph):
    agraph_nodes = []
    agraph_edges = []

    # Definir colores para nodos
    start_node_border = "#FFD700"   # Borde dorado para el nodo inicial
    default_node_border = "#ADD8E6"   # Borde azul claro para el resto

    # Definir propiedades de los bordes
    edge_color = "#808080"      # Gris
    edge_thickness = 2

    for i, (node_id, data) in enumerate(graph.nodes(data=True)):
        # Forzar que el nombre sea una sola palabra: reemplazar espacios por guiones bajos
        node_name = str(node_id).replace(" ", "_")
        
        # Construir el contenido interno del nodo con las características del viewpoint,
        # si se encuentra en el atributo "llm_json". Puedes personalizar qué campos mostrar.
        viewpoint_details = ""
        llm_json = data.get("llm_json", {})
        if llm_json:
            details = []
            for key, value in llm_json.items():
                details.append(f"{key}: {value}")
            viewpoint_details = "\n".join(details)
        else:
            # Si no hay llm_json, se puede usar la descripción por defecto
            viewpoint_details = data.get("description", "")
        
        # Utilizar el nombre (ya sin espacios) para el label
        label = node_name
        
        # Configurar el color: fondo blanco, borde según sea nodo inicial o no
        node_color = {"background": "#ffffff", "border": start_node_border} if i == 0 else {"background": "#ffffff", "border": default_node_border}
        
        # Crear el nodo con las propiedades actualizadas
        agraph_nodes.append(Node(
            id=node_id,
            label=label,
            title=viewpoint_details,  # Información detallada interna del nodo
            color=node_color,
            size=25
        ))
    
    for u, v, data in graph.edges(data=True):
        edge_label = data.get('action', '')
        edge_style = "solid"
        if 'door' in edge_label.lower():
            door_key = tuple(sorted((u, v)))
            if door_key in st.session_state.get('door_states', {}) and st.session_state.door_states[door_key] == "cerrada":
                edge_style = "dashed"  # Indica puertas cerradas con línea discontinua
                edge_label += " (Cerrada)"
            elif door_key in st.session_state.get('door_states', {}) and st.session_state.door_states[door_key] == "abierta":
                edge_label += " (Abierta)"
        agraph_edges.append(Edge(
            source=u,
            target=v,
            label=edge_label,
            color=edge_color,
            width=edge_thickness,
            style=edge_style
        ))
    
    return agraph_nodes, agraph_edges

def get_node_data(graph, node_id):
    return graph.nodes.get(node_id)

def update_node_data(graph, node_id, new_data):
    if node_id in graph:
        graph.nodes[node_id].update(new_data)
