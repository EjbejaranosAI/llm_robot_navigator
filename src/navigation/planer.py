# src/navigation/planner.py

import streamlit as st
from api.gpt_client import analyze_image_with_gpt

def generate_navigation_plan(graph, current_node, goal_description, all_descriptions, action_history):
    """
    Genera instrucciones de navegación usando el LLM, considerando el historial de acciones.
    """
    # Obtener conexiones del grafo
    edges = list(graph.edges(data=True))
    
    prompt = f"""Generate a detailed navigation plan using this structure:
    
Current Position: {current_node}
Navigation Goal: {goal_description}

Graph Structure:
Nodes: {list(graph.nodes())}
Connections: {edges}

Action History (last 5):
{action_history[-5:] if action_history else "None"}

Required Output Format:
1. Next Immediate Action: [Concrete action]
2. Suggested Path: [Node sequence]
3. Expected Challenges: [Potential obstacles]
4. Recommended Strategy: [Avoidance methods]
5. Confidence Level: [High/Medium/Low]

Reasoning Process:
[Step-by-step explanation using graph structure]

Generate the response in SPANISH."""
    
    try:
        plan = analyze_image_with_gpt(None, prompt)
        return f"## Plan de Navegación\n\n{plan}"
    except Exception as e:
        return f"Error generando plan: {str(e)}"