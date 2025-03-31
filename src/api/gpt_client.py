# src/api/gpt_client.py
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if OPENAI_API_KEY is None:
    raise EnvironmentError("La clave de API de OpenAI no se encontró en el archivo .env")

client = OpenAI(api_key=OPENAI_API_KEY)

def analyze_image_with_gpt(image_source: str, prompt: str = "What's in this image?") -> str:
    """
    Analiza una imagen utilizando el modelo de visión de OpenAI.

    Args:
        image_source: La URL de la imagen o una cadena base64 de la imagen.
        prompt: La pregunta o instrucción para el modelo.

    Returns:
        El texto de la respuesta del modelo.
    """
    try:
        content = [{"type": "text", "text": prompt}]
        if image_source.startswith("http") or image_source.startswith("data:"):
            if image_source.startswith("http"):
                content.append({"type": "image_url", "image_url": {"url": image_source}})
            else:
                content.append({"type": "image_url", "image_url": {"url": image_source}}) # Data URL
        else:
            raise ValueError("Formato de imagen no válido. Debe ser una URL o una cadena base64 con encabezado de datos.")

        response = client.chat.completions.create(
            model="gpt-4o",  # Using gpt-4o as it supports vision
            messages=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
            max_tokens=1500,  # Adjust as needed
            response_format={"type": "json_object"}, 
            temperature=0.5,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error al analizar la imagen: {e}"

if __name__ == "__main__":
    # Ejemplo de uso con URL
    image_url_example = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
    description_url = analyze_image_with_gpt(image_url_example)
    print(f"Descripción de la imagen (URL): {description_url}")

    # Ejemplo de uso con base64 (puedes generar una cadena base64 a partir de un archivo local para probar)
    # with open("path/to/your/image.jpg", "rb") as image_file:
    #     base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    #     description_base64 = analyze_image_with_gpt(f"data:image/jpeg;base64,{base64_image}")
    #     print(f"Descripción de la imagen (Base64): {description_base64}")