# src/api/gpt_client.py
import os
from openai import OpenAI
from dotenv import load_dotenv
import base64 # Asegúrate de importar base64 si no estaba ya

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if OPENAI_API_KEY is None:
    raise EnvironmentError("La clave de API de OpenAI no se encontró en el archivo .env")

client = OpenAI(api_key=OPENAI_API_KEY)

# MODIFIED FUNCTION DEFINITION
def analyze_image_with_gpt(image_inputs: list, prompt: str = "Analyze the provided image(s).") -> str:
    """
    Analiza una o varias imágenes utilizando el modelo de visión de OpenAI.

    Args:
        image_inputs: Una lista de diccionarios. Cada diccionario debe tener:
                      {'position': str, 'source': str}
                      donde 'position' es una descripción (ej: 'center', 'left', 'right')
                      y 'source' es la URL o cadena base64 de la imagen (con prefijo data:).
        prompt: La pregunta o instrucción principal para el modelo.

    Returns:
        El texto de la respuesta del modelo.
    """
    try:
        # Start with the main text prompt
        content = [{"type": "text", "text": prompt}]

        # Add image inputs to the content list
        for img_input in image_inputs:
            position = img_input.get('position', 'image') # Default position label
            image_source = img_input.get('source')

            if not image_source:
                continue # Skip if source is missing

            # Add descriptive text before each image (optional but helpful)
            content.append({"type": "text", "text": f"Image from the {position} view:"})

            # Add the image data itself
            if image_source.startswith("http") or image_source.startswith("data:"):
                 content.append({
                     "type": "image_url",
                     "image_url": {"url": image_source, "detail": "auto"} # Use "auto" or "high" based on need
                 })
            else:
                # If it's a raw base64 string without the prefix, add it (less robust)
                # Consider enforcing the "data:" prefix in the calling code
                try:
                    # Basic check if it looks like base64
                    base64.b64decode(image_source)
                    data_url = f"data:image/jpeg;base64,{image_source}" # Assume JPEG, adjust if needed
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": data_url, "detail": "auto"}
                    })
                except Exception:
                     print(f"Warning: Skipping invalid image source format for position {position}.")
                     continue # Skip this invalid source


        if len(content) == 1: # Only the initial prompt, no valid images added
             return "Error: No valid images provided for analysis."

        response = client.chat.completions.create(
            model="gpt-4o",  # Make sure model supports vision and multiple images
            messages=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
            max_tokens=2000,  # Increased slightly for potentially more complex analysis
            # Ensure response_format is compatible if expecting JSON structure
            # If the prompt guides towards JSON, keep it. Otherwise, remove/adjust.
            response_format={"type": "json_object"},
            temperature=0.5,
        )
        return response.choices[0].message.content
    except Exception as e:
        # Provide more context in the error if possible
        return f"Error during API call: {e}. Check image formats and API key."


def generate_text_with_gpt(prompt: str, model: str = "gpt-4o") -> str:
    """
    Genera texto usando un modelo de OpenAI (sin análisis de imagen).

    Args:
        prompt: El prompt para el modelo.
        model: El modelo de OpenAI a utilizar (ej: "gpt-4o", "gpt-3.5-turbo").

    Returns:
        El texto de la respuesta del modelo.
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                # Puedes añadir un mensaje de sistema si quieres definir mejor el rol del AI
                # {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000, # Ajusta según necesites para el plan
            temperature=0.5, # Temperatura moderada para planes creativos pero consistentes
            # response_format={"type": "text"}, # Opcional, si no necesitas JSON
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error en la llamada a la API de texto de OpenAI: {e}")
        # Considera lanzar la excepción o devolver un mensaje de error específico
        # raise e # Opcional: relanzar para que el llamador lo maneje
        return f"Error al generar texto: {e}"


# Example usage (for testing within this file)
if __name__ == "__main__":
    # Example with multiple images (URLs)
    images_to_analyze = [
        {'position': 'left', 'source': 'URL_IMAGEN_IZQUIERDA'}, # Reemplaza con URLs reales
        {'position': 'center', 'source': 'URL_IMAGEN_CENTRAL'},
        {'position': 'right', 'source': 'URL_IMAGEN_DERECHA'}
    ]
    multi_image_prompt = (
        "Analyze the following three images representing a panoramic view (left, center, right). "
        "Describe the overall scene, identify key objects noting their position across views (e.g., 'door visible in center and right'), "
        "potential navigation paths, obstacles, landmarks, and suggest a node name and potential actions. "
        "Ensure the output is a single JSON object following the standard structure." # Adapt prompt for JSON structure if needed
    )
    # description_multi = analyze_image_with_gpt(images_to_analyze, multi_image_prompt)
    # print(f"Descripción multi-imagen: {description_multi}")

    # Example with single image (URL)
    single_image = [
        {'position': 'center', 'source': "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"}
    ]
    single_image_prompt = "Describe this scene in detail. Output as JSON." # Simplified prompt
    # description_single = analyze_image_with_gpt(single_image, single_image_prompt)
    # print(f"Descripción imagen única: {description_single}")