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

    # Define node colors
    start_node_color = "#FFD700"  # Gold
    default_node_color = "#ADD8E6" # Light Blue

    # Define edge properties
    edge_color = "#808080"      # Gray
    edge_thickness = 2

    for i, (node_id, data) in enumerate(graph.nodes(data=True)):
        label = node_id  # Use node_id as default label
        color = default_node_color
        if i == 0:  # Style the first node differently (e.g., the start node)
            color = start_node_color
        if 'description' in data:
            label = data['description']
            if len(label) > 30:
                label = label[:27] + "..."
        agraph_nodes.append(Node(id=node_id, label=label, title=data.get('description', ''),
                                 color=color, size=25))  # Added color and size

    for u, v, data in graph.edges(data=True):
        edge_label = data.get('action', '')
        edge_style = "solid"
        if 'door' in edge_label.lower():
            door_key = tuple(sorted((u, v)))
            if door_key in st.session_state.get('door_states', {}) and st.session_state.door_states[door_key] == "cerrada":
                edge_style = "dashed" # Indicate closed doors with dashed lines
                edge_label += " (Cerrada)"
            elif door_key in st.session_state.get('door_states', {}) and st.session_state.door_states[door_key] == "abierta":
                edge_label += " (Abierta)"

        agraph_edges.append(Edge(source=u, target=v, label=edge_label,
                                 color=edge_color, width=edge_thickness, style=edge_style))  # Added color, width, and style

    return agraph_nodes, agraph_edges

def get_node_data(graph, node_id):
    return graph.nodes.get(node_id)

def update_node_data(graph, node_id, new_data):
    if node_id in graph:
        graph.nodes[node_id].update(new_data)
