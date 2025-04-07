# src/navigation/planner.py

import networkx as nx
import streamlit as st # Solo si necesitas mostrar errores/info directamente aquí
# Importar la NUEVA función de generación de texto
from api.gpt_client import generate_text_with_gpt # Asegúrate que esta función exista

def generate_navigation_plan(graph: nx.DiGraph, start_node: str, goal_node_id: str, action_history: list, door_states: dict):
    """
    Genera un plan de navegación utilizando NetworkX para pathfinding
    y un LLM para generar instrucciones detalladas.

    Args:
        graph: El grafo de navegación (NetworkX DiGraph).
        start_node: El ID del nodo de inicio.
        goal_node_id: El ID del nodo objetivo.
        action_history: Lista de acciones recientes.
        door_states: Diccionario con el estado de las puertas {('node1', 'node2'): 'abierta'/'cerrada'}.

    Returns:
        Un string formateado con el plan de navegación o un mensaje de error/sin ruta.
    """

    # --- Validación de Entrada ---
    if not start_node or start_node not in graph:
        return "Error: Nodo de inicio inválido o no encontrado en el grafo."
    if not goal_node_id or goal_node_id not in graph:
        return f"Error: Nodo objetivo '{goal_node_id}' inválido o no encontrado en el grafo."
    if start_node == goal_node_id:
        return "Información: Ya estás en el nodo objetivo."

    # --- Paso 1: Pathfinding Algorítmico ---
    path_nodes = None
    try:
        # Encuentra el camino más corto (ignora pesos por ahora, o añade lógica de peso si es necesario)
        # Considera si quieres manejar el estado de las puertas aquí creando un grafo temporal
        # o dejar que el LLM maneje la lógica de puertas cerradas en el paso 2.
        # Opción más simple: encontrar el camino geométrico y que el LLM avise de puertas.
        path_nodes = nx.shortest_path(graph, source=start_node, target=goal_node_id)
        st.info(f"Ruta encontrada por NetworkX: {' -> '.join(path_nodes)}") # Log/Info
    except nx.NetworkXNoPath:
        return f"No se encontró una ruta directa desde '{start_node}' hasta '{goal_node_id}' en el grafo actual."
    except Exception as e:
        return f"Error durante la búsqueda de ruta: {e}"

    # --- Paso 2: Preparar Prompt para el LLM ---
    if path_nodes and len(path_nodes) > 1:
        # Extraer información relevante para el prompt
        path_details = []
        for i in range(len(path_nodes) - 1):
            u, v = path_nodes[i], path_nodes[i+1]
            edge_data = graph.get_edge_data(u, v)
            action = edge_data.get('action', 'moverse') if edge_data else 'moverse (acción desconocida)'

            # Obtener descripción/landmarks del nodo de destino del paso
            node_v_data = graph.nodes.get(v, {})
            node_v_desc = node_v_data.get('description', '')
            node_v_landmarks = node_v_data.get('llm_json', {}).get('landmarks_and_suggested_node_name', {}).get('suggested_node_name_detailed', 'Sin landmarks específicos.')

            path_details.append({
                "from": u,
                "to": v,
                "action": action,
                "target_node_description": node_v_desc,
                "target_node_landmarks": node_v_landmarks
            })

        # Construir el prompt detallado
        prompt = f"""Eres un asistente de navegación robótica. Has calculado la siguiente secuencia de nodos como la ruta más corta desde {start_node} hasta {goal_node_id}:
{ ' -> '.join(path_nodes) }

Ahora, genera un plan paso a paso en lenguaje natural para el usuario (o robot).

Detalles de cada paso en la ruta:
{path_details}

Estado Actual de las Puertas Conocidas:
{door_states if door_states else "Ninguno conocido."}

Historial de Acciones Recientes (para contexto):
{action_history[-5:] if action_history else "Ninguno"}

Instrucciones para la generación del Plan:
1.  Describe cada paso claramente, indicando el nodo de inicio, la acción a tomar (usando la acción de la arista), y el nodo de destino.
2.  Incorpora landmarks o descripciones breves del nodo de destino para ayudar a la orientación (ej: "Ve hacia 'Cocina'. Deberías ver 'la nevera plateada'.").
3.  **MUY IMPORTANTE:** Revisa el estado de las puertas (`Door States`) para cada paso.
    * Si un paso implica pasar por una arista que representa una puerta y esa puerta está marcada como 'cerrada' en `Door States`, debes incluir una acción explícita como "Intentar abrir la puerta hacia [Nodo Destino]" ANTES del paso de movimiento. Advierte que el paso podría fallar si la puerta no se puede abrir.
    * Si una puerta está 'abierta' o no está en `Door States`, asume que se puede pasar (pero puedes mencionarlo si es una puerta).
4.  Usa el formato de salida requerido especificado abajo.
5.  Identifica posibles desafíos (puertas cerradas, pasos con acción desconocida).
6.  Sugiere un plan de contingencia breve si se encuentran obstáculos (intentar abrir puertas, buscar alternativas si están bloqueadas).

Formato de Salida Requerido:
## Plan de Navegación hacia {goal_node_id}
1. **Desde {path_nodes[0]}**: [Instrucción detallada para el paso 1, incluyendo acción y destino {path_nodes[1]}, y manejo de puertas si aplica]
2. **Desde {path_nodes[1]}**: [Instrucción detallada para el paso 2, ...]
... (continúa para todos los pasos)

### Posibles Desafíos
- [Listar desafíos como puertas cerradas en la ruta, acciones ambiguas, etc.]

### Plan de Contingencia
- [Sugerencias como intentar abrir puertas, buscar rutas alternativas si está bloqueado.]
"""

        # --- Paso 3: Llamar al LLM de Texto ---
        try:
            # Usa la función de generación de texto, no la de imagen
            plan_text = generate_text_with_gpt(prompt)
            return plan_text
        except Exception as e:
            # Podrías devolver un plan básico si el LLM falla
            basic_plan = f"## Plan Básico (Fallo LLM)\nSigue la ruta: {' -> '.join(path_nodes)}\nError LLM: {e}"
            return basic_plan
            # O simplemente el mensaje de error
            # return f"Error generando instrucciones detalladas con LLM: {str(e)}"

    elif path_nodes and len(path_nodes) == 1: # Caso start_node == goal_node_id (ya manejado antes, pero por si acaso)
         return "Información: Ya estás en el nodo objetivo."
    else: # Caso en que path_nodes es None o vacío por alguna razón inesperada
        return "Error inesperado: No se pudo determinar la ruta."