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
    for node_id, data in graph.nodes(data=True):
        label = node_id  # Use node_id as default label
        if 'description' in data:
            label = data['description']
            if len(label) > 30:
                label = label[:27] + "..."
        agraph_nodes.append(Node(id=node_id, label=label, title=data.get('description', '')))
    for u, v, data in graph.edges(data=True):
        agraph_edges.append(Edge(source=u, target=v, label=data.get('action', '')))
    return agraph_nodes, agraph_edges

def get_node_data(graph, node_id):
    return graph.nodes.get(node_id)

def update_node_data(graph, node_id, new_data):
    if node_id in graph:
        graph.nodes[node_id].update(new_data)