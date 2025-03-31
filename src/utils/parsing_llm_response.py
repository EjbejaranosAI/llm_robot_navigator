import re
import json

def parse_raw_text_to_json(raw_text):
    """
    Parsea el raw text estructurado en secciones y bullets a un objeto JSON
    con la estructura esperada.
    """
    result = {
        "overall_scene_description": "",
        "identified_objects": [],
        "potential_navigation_paths": [],
        "obstacles": [],
        "landmarks_and_suggested_node_name": {
            "suggested_node_name": ""
        },
        "robot_perspective_and_potential_actions": [],
        "navigation_graph_elements": [],
        "reasoning": "",
        "obstacle_avoidance_strategy": ""
    }

    # Patrón para extraer secciones del raw text
    pattern = re.compile(r"\*\*(\d+\.\s+[^:]+):\*\*\s*\n(.+?)(?=\n\*\*\d+\.|$)", re.DOTALL)
    matches = pattern.findall(raw_text)
    for header, content in matches:
        header = header.strip()
        content = content.strip()
        if "Overall Scene Description" in header:
            result["overall_scene_description"] = content
        elif "Identified Objects" in header:
            # Divide por líneas que comienzan con guiones
            lines = re.split(r"\n- ", content)
            for line in lines:
                line = line.strip("- ").strip()
                if not line:
                    continue
                # Espera el formato: **Nombre:** descripción
                m = re.match(r"\*\*(.+?)\*\*:\s*(.*)", line)
                if m:
                    name = m.group(1).strip()
                    characteristics = m.group(2).strip()
                    result["identified_objects"].append({"name": name, "characteristics": characteristics})
                else:
                    # Si no hay coincidencia, se guarda la línea completa
                    result["identified_objects"].append({"name": line, "characteristics": ""})
        elif "Potential Navigation Paths" in header:
            lines = re.split(r"\n- ", content)
            for line in lines:
                line = line.strip("- ").strip()
                if not line:
                    continue
                # Intenta separar usando el formato: **Descripción:** detalles
                m = re.match(r"\*\*(.+?)\*\*:\s*(.*)", line)
                if m:
                    description = m.group(1).strip()
                    details = m.group(2).strip()
                    # Si no se especifica dirección, la dejamos vacía
                    result["potential_navigation_paths"].append({
                        "description": description, 
                        "direction": "", 
                        "features": details
                    })
                else:
                    result["potential_navigation_paths"].append({
                        "description": line, 
                        "direction": "", 
                        "features": ""
                    })
        elif "Obstacles" in header:
            lines = re.split(r"\n- ", content)
            for line in lines:
                line = line.strip("- ").strip()
                if not line:
                    continue
                m = re.match(r"\*\*(.+?)\*\*:\s*(.*)", line)
                if m:
                    typ = m.group(1).strip()
                    details = m.group(2).strip()
                    result["obstacles"].append({
                        "type": typ, 
                        "size": "",  # Si se requiere, se podría intentar extraer el tamaño
                        "location": details
                    })
                else:
                    result["obstacles"].append({
                        "type": line, 
                        "size": "", 
                        "location": ""
                    })
        elif "Landmarks and Suggested Node Name" in header:
            # Busca la línea que contenga "Suggested Node Name:"
            m = re.search(r"Suggested Node Name:\s*\"?([^\n\"]+)\"?", content)
            if m:
                result["landmarks_and_suggested_node_name"]["suggested_node_name"] = m.group(1).strip()
        elif "Robot's Perspective and Potential Actions" in header:
            lines = re.split(r"\n- ", content)
            for line in lines:
                line = line.strip("- ").strip()
                if line:
                    result["robot_perspective_and_potential_actions"].append(line)
        # Otras secciones (como navigation_graph_elements, reasoning, obstacle_avoidance_strategy)
        # se pueden agregar aquí según se requiera.
    return result
