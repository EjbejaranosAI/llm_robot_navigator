# src/navigation/planner.py
# src/navigation/planner.py

import streamlit as st
from api.gpt_client import analyze_image_with_gpt

def generate_navigation_plan(graph, current_node, goal_description, all_descriptions, action_history, door_states):
    """
    Genera instrucciones de navegación usando el LLM, considerando el historial de acciones y el estado de las puertas.
    """
    # Obtener conexiones del grafo
    edges = list(graph.edges(data=True))

    prompt = f"""You are a navigation AI. Generate a detailed navigation plan to reach the goal.

Current Position: {current_node}
Navigation Goal: {goal_description}

Graph Structure:
Nodes: {list(graph.nodes())}
Connections: {edges}

Node Descriptions:
{all_descriptions}

Action History (last 5):
{action_history[-5:] if action_history else "None"}

Door States:
{door_states}

Consider the current location and the goal. Outline a sequence of steps (nodes to visit and actions to take) based on the graph and the descriptions of the nodes. Be specific about the actions required to move between connected nodes.

Take into account the current state of any doors. If a door is marked as 'cerrada', you should only suggest a path through it if the action 'abrir puerta' is possible and either has been successfully executed (marked as 'abierta') or is included as a step in your plan.

If the goal seems unreachable due to closed doors or other obstacles, indicate this in your response.

Required Output Format:
## Plan de Navegación
1. **Step 1**: [Action to take from current node] -> [Next Node]
2. **Step 2**: [Action to take] -> [Next Node]
... and so on, until the goal is reached.

Also include:
### Potential Challenges
[List any anticipated difficulties or obstacles, including closed doors]

### Contingency Plan
[Outline steps to take if challenges are encountered, including trying to open doors or finding alternative routes]."""

    try:
        plan = analyze_image_with_gpt(None, prompt)
        return plan
    except Exception as e:
        return f"Error generando plan: {str(e)}"
