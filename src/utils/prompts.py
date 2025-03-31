# src/utils/prompts.py
navigation_prompt = """You are a navigation AI. Generate STRICTLY a JSON response with this EXACT structure:

{
  "overall_scene_description": "[1-2 sentences]",
  "identified_objects": [
    {"name": "object1", "characteristics": "[key features]"},
    {"name": "object2", "characteristics": "[key features]"}
  ],
  "potential_navigation_paths": [
    {"description": "...", "direction": "[cardinal]", "features": "[notable aspects]"}
  ],
  "obstacles": [
    {"type": "...", "size": "[small/medium/large]", "location": "[relative position]"}
  ],
  "landmarks_and_suggested_node_name": {
    "suggested_node_name": "[2-4 word unique name]",
    "suggested_node_name_detailed": "[Detailed description of landmarks to identify this location]"
  },
  "robot_perspective_and_potential_actions": [
    "[Action 1]", "[Action 2]"
  ],
  "navigation_graph_elements": [
    {"target_node": "node_name", "action": "[specific movement]"}
  ],
  "reasoning": "[2-3 sentence logical chain]",
  "obstacle_avoidance_strategy": "[concrete steps]",
  "process_step": "[e.g., step 1, step 2, step 3]"
}

RULES:
1. Output ONLY valid JSON
2. Use double quotes ONLY
3. Ensure ALL brackets are properly closed
4. No markdown or additional text
5. Validate syntax with JSONLint
6. If uncertain about a field, use empty array []

Current Navigation Goal: {navigation_goal}
Action History (last 5): {action_history}

Image Analysis:

If a wall is detected directly in front of the robot, and there is no clear path forward, suggest the action "girar 180 grados" to analyze the area behind. The robot should remain in its current location while performing this turn.

If the robot has been in a state where the last action was "stop" or if no movement has occurred for a while (consider the action history), analyze the current image in the context of the previous actions and suggest the next logical step to progress towards the navigation goal. Avoid suggesting "stop" repeatedly if the goal has not been reached.
"""

formatting_prompt = """Repair and validate this JSON. Apply:

1. Add missing brackets/quotes
2. Escape special characters
3. Fix incorrect delimiters
4. Remove non-JSON text
5. Maintain original structure

Return ONLY valid JSON:

ERROR EXAMPLES TO AVOID:
BAD: "direction: North" → GOOD: "direction": "North"
BAD: ['item'] → GOOD: ["item"]
BAD: Unclosed array → GOOD: Close all []

Input JSON with errors:
{raw_llm_output}

Corrected JSON:"""