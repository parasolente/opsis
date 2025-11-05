import cv2
import torch
from ultralytics import YOLO
import uuid  # ### CAMBIO ### Importado para nombres de archivo únicos
import os    # ### CAMBIO ### Importado para manejar rutas de archivos

# -----------------------------------------------------------------
# ### CAMBIO ###: Carga de modelos (se hace UNA SOLA VEZ)
# -----------------------------------------------------------------
# Asegúrate de que las rutas sean correctas desde donde ejecutes el servidor

# Obten la ruta del directorio donde se encuentra este script (procesador.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Construye las rutas a los modelos usando BASE_DIR
MODELO_PLANTULA_PATH = os.path.join(BASE_DIR, 'model', 'best_n.pt')
MODELO_CELDA_PATH = os.path.join(BASE_DIR, 'model', 'best.pt')

print(f"--- [INFO] Buscando modelos en: {os.path.join(BASE_DIR, 'model')}")

print("--- [INFO] Cargando modelos en memoria... ---")
try:
    MODELO_PLANTULA = YOLO(MODELO_PLANTULA_PATH)
    MODELO_CELDA = YOLO(MODELO_CELDA_PATH)
    print("--- [INFO] Modelos cargados exitosamente. ---")
except Exception as e:
    print(f"Error CRÍTICO: No se pudieron cargar los modelos al inicio. Error: {e}")
    exit()

def get_class_id(model_names, target_name):
    """
    Función de ayuda para encontrar el ID de una clase
    buscando en el diccionario 'names' del modelo.
    """
    for class_id, name in model_names.items():
        if name == target_name:
            return class_id
    return None

def calcular_iou(boxA, boxB):
    """
    Calcula la Intersección sobre Unión (IoU) entre dos cajas.
    Las cajas deben estar en formato [x1, y1, x2, y2].
    """
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    iou = interArea / float(boxAArea + boxBArea - interArea)
    return iou

# ### CAMBIO ###: La función ahora solo necesita la ruta de la imagen DE ENTRADA
def procesar_imagen_fusionada(path_imagen_entrada):
    """
    Usa los modelos globales para procesar una imagen de entrada,
    guarda el resultado y devuelve las estadísticas.
    """
    
    print(f"--- Procesando imagen: {path_imagen_entrada} ---")
    
    names_plantula = MODELO_PLANTULA.names
    names_celda = MODELO_CELDA.names
    
    id_plantula_en_mod1 = get_class_id(names_plantula, 'plantula')
    id_celda_en_mod2 = get_class_id(names_celda, 'celda_vacia')

    if id_plantula_en_mod1 is None or id_celda_en_mod2 is None:
        print("Error: No se pudieron encontrar las clases 'plantula' o 'celda_vacia' en los modelos.")
        return None

    # --- [1/3] Predicción Modelo 1 (Plántulas) ---
    results_plantula = MODELO_PLANTULA.predict(
        path_imagen_entrada, save=False, show=False, 
        conf=0.8,
        classes=[id_plantula_en_mod1]
    )

    # --- [2/3] Predicción Modelo 2 (Celdas Vacías) ---
    results_celda = MODELO_CELDA.predict(
        path_imagen_entrada, save=False, show=False, 
        conf=0.6,
        classes=[id_celda_en_mod2]
    )

    r_plantula = results_plantula[0]
    r_celda = results_celda[0]

    # --- [3/3] Filtrado y Conteo ---
    plantula_boxes = r_plantula.boxes
    celda_boxes = r_celda.boxes
    celda_boxes_filtradas = []
    IOU_THRESHOLD = 0.1

    for celda_box in celda_boxes:
        es_superpuesta = False
        celda_xyxy = celda_box.xyxy[0]
        for plantula_box in plantula_boxes:
            plantula_xyxy = plantula_box.xyxy[0]
            iou = calcular_iou(celda_xyxy, plantula_xyxy)
            if iou > IOU_THRESHOLD:
                es_superpuesta = True
                break
        if not es_superpuesta:
            celda_boxes_filtradas.append(celda_box)

    # --- Conteo y Estadísticas ---
    plantula_count = len(plantula_boxes)
    celda_vacia_count = len(celda_boxes_filtradas)
    total_cavidades = plantula_count + celda_vacia_count

    # -----------------------------------------------------------------
    # ### ¡CAMBIO! Cálculo del Porcentaje de Germinación
    # -----------------------------------------------------------------
    if total_cavidades > 0:
        porcentaje_germinacion = (plantula_count / total_cavidades) * 100
    else:
        porcentaje_germinacion = 0.0 # Evitar división por cero

    print("--- Conteo Final Fusionado y Filtrado ---")
    print(f"Plántulas: {plantula_count}")
    print(f"Celdas Vacías: {celda_vacia_count}")
    print(f"Total Cavidades: {total_cavidades}")
    print(f"Porcentaje Germinación: {porcentaje_germinacion:.2f}%")

    # --- Dibujado ---
    img_con_cajas = r_plantula.orig_img.copy()
    COLOR_PLANTULA = (0, 255, 0)
    COLOR_CELDA = (255, 100, 0)

    for b in plantula_boxes:
        box = b.xyxy[0].cpu().numpy().astype(int)
        conf = b.conf[0].cpu().numpy()
        label = f"{names_plantula[int(b.cls[0])]} {conf:.2f}"
        cv2.rectangle(img_con_cajas, (box[0], box[1]), (box[2], box[3]), COLOR_PLANTULA, 2)
        cv2.putText(img_con_cajas, label, (box[0], box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_PLANTULA, 2)

    for b in celda_boxes_filtradas:
        box = b.xyxy[0].cpu().numpy().astype(int)
        conf = b.conf[0].cpu().numpy()
        label = f"{names_celda[int(b.cls[0])]} {conf:.2f}"
        cv2.rectangle(img_con_cajas, (box[0], box[1]), (box[2], box[3]), COLOR_CELDA, 2)
        cv2.putText(img_con_cajas, label, (box[0], box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_CELDA, 2)

    # -----------------------------------------------------------------
    # ### CAMBIO ###: Guardar con nombre único y devolver datos
    # -----------------------------------------------------------------
    
    # Crea un nombre de archivo único
    nombre_archivo_salida = f"resultado_{uuid.uuid4()}.jpg"
    
    # Define la ruta de salida (asumimos una carpeta 'static/results'
    # Esta carpeta debe existir)
    DIRECTORIO_SALIDA = "static/results"
    os.makedirs(DIRECTORIO_SALIDA, exist_ok=True) # Crea el directorio si no existe
    
    output_path = os.path.join(DIRECTORIO_SALIDA, nombre_archivo_salida)
    
    try:
        cv2.imwrite(output_path, img_con_cajas)
        print(f"¡Éxito! Imagen guardada en: {output_path}")
        
        # Devuelve un diccionario con toda la información
        return {
            "plantula_count": plantula_count,
            "celda_vacia_count": celda_vacia_count,
            "total_cavidades": total_cavidades,
            "porcentaje_germinacion": round(porcentaje_germinacion, 2),
            "output_image_filename": nombre_archivo_salida # Solo el nombre del archivo
        }
        
    except Exception as e:
        print(f"Error al guardar la imagen: {e}")
        return None

# --- Bloque de prueba (se puede quedar) ---
if __name__ == "__main__":
    IMAGEN_PATH = '/home/angel/Documentos/modelos/yolo/data/data/real/testing/imagen.png'
    datos = procesar_imagen_fusionada(IMAGEN_PATH)
    if datos:
        print("\n--- Resultados de la prueba ---")
        print(datos)
