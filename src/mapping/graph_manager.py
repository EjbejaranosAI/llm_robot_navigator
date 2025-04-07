# src/mapping/graph_manager.py
import networkx as nx
from streamlit_agraph import Node, Edge

def initialize_graph():
    return nx.DiGraph()

def add_node_to_graph(graph, node_id, data):
    graph.add_node(node_id, **data)

def add_edge_to_graph(graph, node_from, node_to, action):
    graph.add_edge(node_from, node_to, action=action)

# MODIFIED FUNCTION DEFINITION: Added 'door_states=None' parameter
def convert_nx_to_agraph(graph, door_states=None):
    if door_states is None:
        door_states = {} # Default to an empty dictionary if not provided

    agraph_nodes = []
    agraph_edges = []

    # Definir colores para nodos
    start_node_border = "#FFD700"
    default_node_border = "#ADD8E6"

    # Definir propiedades de los bordes
    edge_color = "#808080"
    edge_thickness = 2

    for i, (node_id, data) in enumerate(graph.nodes(data=True)):
        node_name = str(node_id).replace(" ", "_")
        viewpoint_details = ""
        llm_json = data.get("llm_json", {})
        if llm_json:
            details = []
            for key, value in llm_json.items():
                details.append(f"{key}: {value}")
            viewpoint_details = "\n".join(details)
        else:
            viewpoint_details = data.get("description", "")
        label = node_name
        node_color = {"background": "#ffffff", "border": start_node_border} if i == 0 else {"background": "#ffffff", "border": default_node_border}
        agraph_nodes.append(Node(
            id=node_id,
            label=label,
            title=viewpoint_details,
            color=node_color,
            size=25
        ))

    for u, v, data in graph.edges(data=True):
        edge_label = data.get('action', '')
        edge_style = "solid"
        if 'door' in edge_label.lower():
            door_key = tuple(sorted((u, v)))
            # MODIFIED LINE: Use the 'door_states' argument instead of st.session_state
            if door_key in door_states and door_states[door_key] == "cerrada":
                edge_style = "dashed"
                edge_label += " (Cerrada)"
            # MODIFIED LINE: Use the 'door_states' argument instead of st.session_state
            elif door_key in door_states and door_states[door_key] == "abierta":
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
    # Use .get() for safer access in case node_id doesn't exist
    return graph.nodes.get(node_id)

def update_node_data(graph, node_id, new_data):
    if node_id in graph:
        graph.nodes[node_id].update(new_data)