import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse # <-- Importamos ambos
from fastapi.middleware.cors import CORSMiddleware      # <-- Importamos CORS
from fastapi.staticfiles import StaticFiles  # <-- ¡AÑADE ESTA LÍNEA!
import shutil
import os
import uuid

# Importa la función principal de tu otro archivo
from procesador import procesar_imagen_fusionada

# --- Configuración de directorios ---
UPLOADS_DIR = "temp_uploads"
RESULTS_DIR = "static/results"

# Crear directorios si no existen
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# --- Inicializar la aplicación FastAPI ---
app = FastAPI(
    title="API de Conteo de Plántulas",
    description="Sube una imagen de una charola y recibe el conteo y porcentaje de germinación."
)

# --- Configuración de CORS ---
# (Esto permite que ngrok y navegadores se conecten)
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "null",
    "*" # <-- Añadimos "*" para permitir cualquier origen (como ngrok)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Servir archivos estáticos ---
# (Para poder ver las imágenes de resultado)
# ... (después de crear "app = FastAPI()")

# Sirve todos los archivos de la carpeta "static" (CSS, Imágenes)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Sirve los archivos de resultados de la IA (esto ya lo tenías)
app.mount("/resultados", StaticFiles(directory="static/results"), name="resultados")

# Endpoint para la API (esto ya lo tenías)
@app.post("/api/procesar-imagen/")
async def procesar_imagen_endpoint(file: UploadFile = File(...)):
    # 1. Generar un nombre de archivo de entrada único
    ext = file.filename.split('.')[-1]
    input_filename = f"input_{uuid.uuid4()}.{ext}"
    input_filepath = os.path.join(UPLOADS_DIR, input_filename)

    # 2. Guardar la imagen subida en el servidor
    try:
        with open(input_filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo guardar el archivo: {e}")
    finally:
        file.file.close()

    # 3. Llamar a tu script de procesamiento
    print(f"Enviando '{input_filepath}' al procesador...")
    try:
        # Aquí ocurre la magia: llamas a tu función importada
        datos_resultado = procesar_imagen_fusionada(input_filepath)

        if datos_resultado is None:
            raise HTTPException(status_code=500, detail="Error en el procesamiento de la imagen.")

        # 4. Añadir la URL completa de la imagen de resultado
        nombre_archivo_salida = datos_resultado["output_image_filename"]
        # La URL ya es relativa y correcta gracias a app.mount()
        url_resultado = f"/resultados/{nombre_archivo_salida}" 

        datos_resultado["output_image_url"] = url_resultado

        # 5. Limpiar el archivo de entrada
        os.remove(input_filepath)

        # 6. Devolver la respuesta en JSON
        return JSONResponse(content=datos_resultado)

    except Exception as e:
        # Limpiar en caso de error
        if os.path.exists(input_filepath):
            os.remove(input_filepath)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")

# --- RUTAS PARA CADA PÁGINA HTML ---

@app.get("/", response_class=FileResponse)
async def get_index():
    return "index.html"

@app.get("/demo.html", response_class=FileResponse)
async def get_demo():
    return "demo.html"

@app.get("/precios.html", response_class=FileResponse)
async def get_precios():
    return "precios.html"

@app.get("/guia-inicio.html", response_class=FileResponse)
async def get_guia():
    return "guia-inicio.html"

@app.get("/tecnologia-yolo.html", response_class=FileResponse)
async def get_yolo():
    return "tecnologia-yolo.html"

@app.get("/reduccion-de-tiempo.html", response_class=FileResponse)
async def get_reduccion():
    return "reduccion-de-tiempo.html"

# ... (El "if __name__ == '__main__':" va al final)


# --- Endpoint para servir el HTML ---
# (Esto es para que puedas entrar desde tu IP o ngrok)
@app.get("/", response_class=FileResponse)
async def read_index():
    """Sirve el archivo principal index.html"""
    return "index.html"


# --- ¡¡EL ENDPOINT QUE FALTABA!! ---
# (Esta es la función que recibe la foto)
@app.post("/api/procesar-imagen/")
async def procesar_imagen_endpoint(file: UploadFile = File(...)):
    """
    Endpoint para subir una imagen, procesarla y devolver los resultados.
    """
    
    # 1. Generar un nombre de archivo de entrada único
    ext = file.filename.split('.')[-1]
    input_filename = f"input_{uuid.uuid4()}.{ext}"
    input_filepath = os.path.join(UPLOADS_DIR, input_filename)

    # 2. Guardar la imagen subida en el servidor
    try:
        with open(input_filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo guardar el archivo: {e}")
    finally:
        file.file.close()

    # 3. Llamar a tu script de procesamiento
    print(f"Enviando '{input_filepath}' al procesador...")
    try:
        # Aquí ocurre la magia: llamas a tu función importada
        datos_resultado = procesar_imagen_fusionada(input_filepath)
        
        if datos_resultado is None:
            raise HTTPException(status_code=500, detail="Error en el procesamiento de la imagen.")

        # 4. Añadir la URL completa de la imagen de resultado
        nombre_archivo_salida = datos_resultado["output_image_filename"]
        # La URL ya es relativa y correcta gracias a app.mount()
        url_resultado = f"/resultados/{nombre_archivo_salida}" 
        
        datos_resultado["output_image_url"] = url_resultado

        # 5. Limpiar el archivo de entrada
        os.remove(input_filepath)

        # 6. Devolver la respuesta en JSON
        return JSONResponse(content=datos_resultado)

    except Exception as e:
        # Limpiar en caso de error
        if os.path.exists(input_filepath):
            os.remove(input_filepath)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")


# --- Para ejecutar el servidor ---
if __name__ == "__main__":
    # Recuerda ejecutar con: uvicorn main:app --reload --host 0.0.0.0
    uvicorn.run(app, host="127.0.0.1", port=8000)
