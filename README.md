# LLM Robot Navigation

**🚧 EN DEVELOPMENT 🚧**

## Overview

This project aims to develop a robot navigation system guided by a Large Language Model (LLM). The application allows users to upload or provide an image, which is then analyzed by the LLM to understand the environment. Based on the analysis, the system builds a navigation graph, suggesting potential actions and paths. The ultimate goal is to enable a robot to autonomously navigate through an environment based on high-level instructions and visual input.

## Current Features

- **Image Input:** Users can provide images by uploading a file (JPG, JPEG, PNG) or by entering an image URL.
- **LLM-Powered Image Analysis:** Utilizes an LLM (currently based on OpenAI's GPT models) to:
  - Provide an overall scene description.
  - Identify objects.
  - Detect potential navigation paths.
  - Identify obstacles.
  - Recognize landmarks and suggest a node name.
  - Understand the robot's perspective and propose potential actions.
- **Navigation Graph Building:** Uses the `networkx` library to construct a directed graph:
  - **Nodes:** Represent locations or significant points, storing scene descriptions, associated images, and raw JSON responses from the LLM.
  - **Edges:** Represent actions taken between nodes (e.g., "walk through the door", "turn left") as labels.
- **Graph Visualization:** Displays the navigation graph with `streamlit-agraph` for clear visual connections.
- **Node Information Display:** Clickable nodes show detailed information including the captured image, textual description, and raw JSON response.
- **Navigation Goal Setting:** Allows users to input a navigation goal for future path planning.
- **Action History:** Tracks the actions taken during a navigation session.
- **Start New Navigation:** A reset button to clear the current session (graph and state).
- **History of Analyzed Images:** Displays a preview of analyzed images for session review.

## Project Structure
```
llm_robot_navigator/              <-- Directorio Raíz del Proyecto
├── .env                          <-- Archivo para claves API (¡NO SUBIR A GIT!)
├── .gitignore                    <-- Archivo para ignorar archivos/directorios en Git
├── requirements.txt              <-- Lista de dependencias Python (pip freeze > requirements.txt)
├── README.md                     <-- Descripción del proyecto, instrucciones de setup, etc.
│
├── src/                          <-- Directorio principal del código fuente Python
│   ├── __init__.py
│   ├── api/                      <-- Módulos relacionados con APIs externas (OpenAI)
│   │   ├── __init__.py
│   │   └── gpt_client.py
│   ├── mapping/                  <-- Lógica para crear y manejar el grafo/mapa
│   │   ├── __init__.py
│   │   └── graph_manager.py
│   ├── navigation/               <-- Lógica de planificación de rutas y replanificación
│   │   ├── __init__.py
│   │   └── planner.py
│   ├── interfaces/               <-- Código para interfaces de usuario (Streamlit)
│   │   ├── __init__.py
│   │   └── streamlit_app.py      <-- Tu aplicación Streamlit principal
│   ├── utils/                    <-- Funciones de utilidad compartidas (manejo de imágenes, etc.)
│   │   ├── __init__.py
│   │   └── prompts.py
│   └── main.py                   <-- Punto de entrada principal (si no es la app Streamlit)
│
├── ros_ws/                       <-- ROS Workspace (para la Fase 2)
│   ├── src/                      <-- Directorio 'src' del workspace de ROS
│   │   ├── llm_robot_pkg/        <-- Tu paquete ROS personalizado
│   │   │   ├── package.xml
│   │   │   ├── setup.py          <-- (Para ROS 2 Python)
│   │   │   ├── CMakeLists.txt    <-- (Si usas C++ o mixto)
│   │   │   ├── launch/           <-- Archivos de lanzamiento ROS
│   │   │   │   └── navigation_sim.launch.py
│   │   │   ├── nodes/            <-- Scripts ejecutables (nodos ROS)
│   │   │   │   ├── llm_service_node.py
│   │   │   │   ├── graph_manager_node.py
│   │   │   │   └── planner_node.py
│   │   │   └── llm_robot_pkg/    <-- Código Python del paquete (ROS 2)
│   │   │       ├── __init__.py
│   │   │       ├── llm_service.py
│   │   │       ├── graph_node.py
│   │   │       └── planner_logic.py
│   │   └── ... (otros paquetes si los usas)
│
├── simulation/                   <-- Archivos de configuración de la simulación
│   ├── worlds/                   <-- Archivos de mundo Gazebo (.world)
│   ├── models/                   <-- Modelos de robot/objetos (.sdf, .urdf)
│   └── config/                   <-- Archivos de configuración (Nav2 params, RViz config)
│
├── data/                         <-- Datos generados o necesarios (mapas guardados, logs - ¡cuidado con el tamaño en Git!)
│   └── graphs/                   <-- Grafos guardados
│
├── notebooks/                    <-- Jupyter notebooks para experimentación y análisis
│   └── 01_test_gpt_vision.ipynb
│
└── tests/                        <-- Pruebas unitarias e de integración
    ├── test_api.py
    └── test_mapping.py
```



## Project TODO: LLM Robot Navigation

### Phase 0: Setup 🛠️
- [x] **Define:** Project goals & success metrics. 🎯
- [x] **Select:** Tech stack (Python 🐍, LLM 🗣️, Streamlit 📊, ROS 🤖, Simulation ⚙️).
- [x] **Setup:** Development environment & Git 🌳.
- [x] **Configure:** Secure OpenAI API access 🔑.

### Phase 1: Core Logic & Web Interface 💻
- [x] **Connect:** Implement GPT API connection function. 🔗
- [x] **Describe:** Code function to get image descriptions via API. 🖼️📝
- [x] **Build UI:** Create basic Streamlit app (image upload/view). 🏗️📊
- [x] **Test:** Verify image description quality. ✅🧪
- [x] **Design Graph:** Define node/edge structure for the navigation graph. 🗺️✏️
- [x] **Build Graph:** Create graph-building functionality using `networkx`. ⚙️🌳
- [x] **Visualize Graph:** Display navigation graph with `streamlit-agraph`. 👁️📊

### Phase 2: ROS Integration & Simulation 🤖
- [ ] **Setup ROS Workspace:** Create ROS workspace and necessary packages. 🔧
- [ ] **ROS Node 1:** Develop `llm_service_node.py` to interface with GPT and image analysis. 🧠
- [ ] **ROS Node 2:** Create `graph_manager_node.py` to manage the navigation graph. 📍
- [ ] **ROS Node 3:** Implement `planner_node.py` for path planning and action execution. 🛣️
- [ ] **Integrate with Simulation:** Test integration with simulation tools (Gazebo, RViz). 🚗

## Getting Started 🚀

### Prerequisites
- Python 3.x 🐍
- pip (Python package installer)
- An OpenAI API key 🔑

### Installation ⬇️
1. Clone the repository to your local machine.
2. Navigate to the project's root directory.
3. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
