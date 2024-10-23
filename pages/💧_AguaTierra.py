import streamlit as st
#import geemap
import geemap.foliumap as geemap
#import geemap.colormaps as cm
import ee
import os
import json
import datetime
#import leafmap.foliumap as leafmap

import fiona
import geopandas as gpd

import tempfile
import os
import uuid

import requests
import time
import pyogrio
import folium
import warnings
from shapely.geometry import Polygon

from google.oauth2 import service_account  # Importar la biblioteca adecuada


#################################### Lee las credenciales del archivo JSON 
# Obtener las credenciales desde las variables de entorno
gcp_service_account = os.getenv('GCP_SERVICE_ACCOUNT')

if gcp_service_account:
    try:
        # Cargar las credenciales con el alcance correcto
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(gcp_service_account),
            scopes=["https://www.googleapis.com/auth/earthengine"]
        )
        
        # Inicializar Google Earth Engine con las credenciales
        ee.Initialize(credentials)
        #st.success("GEE inicializado correctamente.")
    except json.JSONDecodeError as e:
        st.error(f"Error al decodificar el JSON: {e}")
    except AttributeError as e:
        st.error(f"Error de atributo: {e}")
    except Exception as e:
        st.error(f"Se produjo un error: {e}")
else:
    st.error("No se pudo encontrar la clave del servicio. Asegúrate de que esté configurada correctamente.")
    
    
######################################## INTERFAZ VISUAL
st.set_page_config(layout="wide")


st.sidebar.title("Detección Agua-Tierra")

texto1_side = """
Esta herramienta permite hacer una distinción entre el entorno marino-fluvial y terrestre a partir de seleccionar un área de interés y un período.
"""
texto_side_pasos = """
1- Seleccionar un área de estudio. 
    Opciones:
        - Dibujar en el mapa una geometría, exportarla mediante **Export** y luego subirla con la herramienta **Browse files**.
        - Directamente subir una geometría en formato geojson, kml o zip.
        
2- Seleccionar un rango de fechas para obtener las imágenes con el que se realizará el cálculo Agua-Tierra.

"""

st.sidebar.info(texto1_side)
st.sidebar.markdown("""---""")
# st.sidebar.subheader("Instrucciones:")
# st.sidebar.markdown("1- Seleccionar un área de estudio. ")
# st.sidebar.markdown("Opciones:")
# st.sidebar.markdown("- Dibujar en el mapa una geometría, exportarla mediante **Export** y luego subirla con la herramienta **Browse files**.")
# st.sidebar.markdown("- Directamente subir una geometría en formato geojson, kml o zip.")
# st.sidebar.markdown("2- Seleccionar un rango de fechas para obtener las imágenes con el que se realizará el cálculo Agua-Tierra.")
# st.sidebar.markdown("3- Calcular! 💧")
# st.sidebar.markdown("4- El resultado puede ser descargado. Tener en cuenta que la extención no sea demasiado grande!")

st.title("Aplicación Agua-Tierra")
st.markdown("Este algoritmo fue consruido en el entorno de Google Earth Engine a partir de imágenes **SENTINEL-2A/B MSI Nivel 1C** para el primer trimestre del 2023, el **Índice de Diferencia Normalizada de Agua** (NDWI), un DEM, **puntos de muestreo** y el algoritmo de **distancia mínima**.")

data = st.file_uploader(
            "Cargue un archivo **GeoJSON**, **kml** o **zip** para usarlo como ROI 👇",
            type=["geojson", "kml", "zip"],
        )

col1, col2 = st.columns([5,2]) 







################################## Mapa Basee
Map = geemap.Map(
            basemap="HYBRID",
            plugin_Draw=True,
            Draw_export=True,
            locate_control=True,
            plugin_LatLngPopup=False,
        )


#################################### VARIABLES GLOBALES
global classified_b
global extencion

classified_b = None
extencion = None

global geometria_seleccionada
geometria_seleccionada = None

global fecha_inicial
global fecha_final

global resultado_funcion
resultado_funcion = None #Inicializar la variable para el resultado


#################################### RECURSOS
#cartas = ee.FeatureCollection("projects/ee-dig-aplicaciones/assets/AguaTierra/Cartas_50000")
#valoresCarac_ = cartas.aggregate_array("carac").distinct().getInfo()# Obtener los valores únicos de la columna "carac"
#valoresCarac = [None] + valoresCarac_  # Crear una lista de valores, incluyendo una opción nula

# Color de categorías Agua/NoAgua
N1Color = [
    '#0000ff',  # Corriente de agua - clase 1
    '#764C04'  # Tierra/NoAgua - clase 2
]

muestras = ee.FeatureCollection("projects/ee-dig-aplicaciones/assets/AguaTierra/Muestras_Argentina_Borrador") # MUESTRAS
zona_muestreo = ee.FeatureCollection("projects/ee-dig-aplicaciones/assets/AguaTierra/AREA_A-T")# ZONA DE ENTRENAMIENTO


#################################### Entrenamiento
# Colección de imágenes Sentinel 2
s2 = ee.ImageCollection("COPERNICUS/S2_HARMONIZED") \
    .filterDate('2023-01-01', '2023-03-31') \
    .filterBounds(zona_muestreo) \
    .filterMetadata('CLOUDY_PIXEL_PERCENTAGE', 'less_than', 0.2)

s2c_ = s2.reduce(ee.Reducer.median())
s2c = s2c_.clip(zona_muestreo)

# NDWI
NDWI = s2c.normalizedDifference(['B3_median', 'B8_median']).rename('NDWImedian')

# Stack
stackIslas_a = NDWI
muestras_1 = muestras.randomColumn('random')

# División de muestras
entrenamiento = muestras_1.filter(ee.Filter.lt('random', 0.7))
validacion = muestras_1.filter(ee.Filter.gt('random', 0.7))

# Entrenar el clasificador utilizando datos de muestras
training = stackIslas_a.sampleRegions(
  collection=entrenamiento,
  properties=['class', 'random'],
  scale=30
)

# Bandas a utilizar en la clasificación
bandas_sel = ['NDWImedian']

# Entrenar clasificador RF
classifier = ee.Classifier.minimumDistance().train(
    features = training,
    classProperty = 'class',
    inputProperties = bandas_sel
)


#################################### FUNCIONES
def obtenerFecha():
    global fecha_inicial
    global fecha_final
    
    # Obtener las fechas seleccionadas
    fecha_inicio = fecha_inicial
    fecha_fin = fecha_final

    # Convertir las fechas al formato deseado ('YYYY-MM-DD')
    fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
    fecha_fin_str = fecha_fin.strftime('%Y-%m-%d')

    # Convertir las fechas en objetos ee.Date
    fecha_inicio_ee = ee.Date(fecha_inicio_str)
    fecha_fin_ee = ee.Date(fecha_fin_str)

    # Calcular la diferencia en milisegundos
    diferencia = fecha_inicio_ee.difference(fecha_fin_ee, 'days')

    # Verificar si la diferencia es negativa
    if diferencia.getInfo() >= 0:
        st.warning('La fecha final no puede ser mayor o igual que la fecha inicial')
        return None  # Devuelve None si hay un error
    else:
        return (fecha_inicio_ee, fecha_fin_ee)  # Devuelve fechas como objetos ee.Date


def gdf_to_ee_geometry(gdf):
    # Convierte el GeoDataFrame a un GeoJSON
    geojson = gdf.to_json()
    # Extrae la geometría en formato GeoJSON
    geometry = gdf.geometry.iloc[0]  # Toma la primera geometría del gdf
    # Convierte la geometría GeoJSON a una geometría compatible con Earth Engine
    ee_geometry = ee.Geometry(geometry.__geo_interface__)
    return ee_geometry


@st.cache_data
def uploaded_file_to_gdf(data):
    _, file_extension = os.path.splitext(data.name)
    file_id = str(uuid.uuid4())
    file_path = os.path.join(tempfile.gettempdir(), f"{file_id}{file_extension}")

    with open(file_path, "wb") as file:
        file.write(data.getbuffer())

    if file_path.lower().endswith(".kml"):
        fiona.drvsupport.supported_drivers["KML"] = "rw"
        gdf = gpd.read_file(file_path, driver="KML")
    else:
        gdf = gpd.read_file(file_path)

    return gdf


def descargarRaster():
    pass


def export_image(image):
    try:
        # Obtener la geometría de la imagen o de la región seleccionada
        region = image.geometry().getInfo() if st.session_state['roi'] is None else st.session_state['roi'].geometry().getInfo()

        # Generar la URL de descarga
        url = image.getDownloadURL({
            'name': 'imagen_exportada',  # Cambia esto a un nombre de archivo válido
            'scale': 10,  # Ajusta la escala según tus necesidades
            'crs': 'EPSG:4674',  # Asegúrate de que este CRS sea el que deseas
            'region': region,  # Obtener la geometría como un GeoJSON
            'format': 'GEO_TIFF'  # Asegúrate de que este formato sea válido
        })
        
        # Mostrar el enlace de descarga
        st.success("Imagen lista para descargar.")
        st.markdown(f"[Descargar imagen en formato GeoTIFF]({url})")

    except Exception as e:
        #st.error(f"Error al exportar la imagen: {str(e)}")
        st.error(f"Error al exportar la imagen: Por favor, elija una área mas pequeña.")



#Funcion principal
def clasificacion_agua_tierra():
    st.write('Espere mientras se clasifica ⌛⌛⌛')
    global extencion
    global classified_b

    if extencion is None:
        st.write('Por favor, dibuje un poligono en el mapa ✏️')
        
    else:
        roi = None
        if st.session_state.get("roi") is not None:
            roi = st.session_state.get("roi")
    
        fecha = obtenerFecha() # Llama a la función para obtener las fechas
        #st.write('fecha', fecha)

        if fecha is not None:
            #st.write('Espere mientras se clasifica y se carga el resultado en el mapa')
            #st.write(f"Fecha inicio: {fecha[0].getInfo()}, Fecha fin: {fecha[1].getInfo()}")

            try:
                s2_b = ee.ImageCollection("COPERNICUS/S2_HARMONIZED") \
                    .filterDate(fecha[0], fecha[1]) \
                    .filterBounds(roi) \
                    .filterMetadata('CLOUDY_PIXEL_PERCENTAGE', 'less_than', 0.2)
                    
                # Comprobar el número de imágenes
                #image_count = s2_b.size().getInfo()
                #st.write(f"Número de imágenes disponibles: {image_count}")

                #if image_count == 0:
                #    st.warning('No hay imágenes disponibles para el rango de fechas seleccionado.')

                s2c_b = s2_b.reduce(ee.Reducer.median())
                #st.write('acaaaaaaa   2')
                
                s2c_b = s2c_b.clip(roi)
                #st.write('acaaaaaaa  3')

                # NDWI
                NDWI_b = s2c_b.normalizedDifference(['B3_median', 'B8_median']).rename('NDWImedian')
                #st.write('acaaaaaaa  4')
                
                # Stack
                stackIslas_b = NDWI_b
                #st.write('acaaaaaaa   5')
                
                # Clasificar la imagen
                classified_b = stackIslas_b.classify(classifier)
                #st.write('acaaaaaaa 6')
                
                #st.write(f'Tipo de classified_b: {type(classified_b)}')
                #st.write(classified_b.getInfo())  # Esto imprime la información de la imagen
            
            except ee.EEException as e:
                st.write('Por favor, elija otro rango de fechas o área. Es posible que no haya datos válidos para ese período')

    return classified_b



    
#################################### main
if data: # se ejecuta al cargar un archivo 
    extencion = uploaded_file_to_gdf(data)
    try:
        st.session_state["roi"] = geemap.gdf_to_ee(extencion, geodesic=False)
        Map.add_gdf(extencion, "ROI")
    except Exception as e:
        st.error(e)
        st.error("Dibuje otra área inténtelo de nuevo.")
 
 
    
# Asegurarse de que session_state tiene un espacio para guardar el resultado
if 'resultado_funcion' not in st.session_state:
    st.session_state['resultado_funcion'] = None


         
with col2:
    #selected_value = st.selectbox('Selecciona una carta: ', valoresCarac)
    #fecha_inicial = st.date_input('Fecha inicial:', datetime.date(2020, 1, 1))
    
    #st.markdown("""---""")
    st.subheader("Instrucciones:")
    st.markdown("1- Seleccionar un área de estudio. Opciones: ")
    st.markdown("- Dibujar en el mapa una geometría, exportarla mediante **Export** y luego subirla con la herramienta **Browse files**.")
    st.markdown("- Directamente subir una geometría en formato geojson, kml o zip.")
    st.markdown("2- Seleccionar un rango de fechas:")
    fecha_inicial = st.date_input('Fecha inicial:', datetime.date(2023, 10, 1))
    fecha_final = st.date_input('Fecha final:')
    st.markdown("3- Calcular! 💧")
    st.markdown("4- El resultado puede ser descargado. Tener en cuenta que la extención no sea demasiado grande!")
    left, middle = st.columns(2)
    
# Botón para calcular y almacenar el resultado en session_state
    if left.button("Calcular", type="primary", use_container_width=True):
        st.session_state['resultado_funcion'] = clasificacion_agua_tierra()
        #st.success("Imagen calculada y guardada")


# Botón para descargar (solo si ya se ha calculado una imagen)
    # Botón para descargar (solo si ya se ha calculado una imagen)
    if middle.button("Descargar", type="secondary", use_container_width=True):
        if st.session_state.get('resultado_funcion') is not None:
            export_image(st.session_state['resultado_funcion'])
        else:
            st.warning('No hay imagen disponible para descargar.')

   

    # Mostrar el resultado si existe
    if st.session_state['resultado_funcion'] is not None:
        Map.addLayer(st.session_state['resultado_funcion'],{'min': 1, 'max': 2, 'palette': N1Color}, 'Resultado')
        #st.write('Se ha cargado el resultado de la clasificación en el mapa 🏞️')
        st.success('Se ha cargado el resultado de la clasificación en el mapa 🏞️')
        #st.write('result funciom', resultado_funcion.getInfo())
        
    

#if selected_value is not None:  # Evitar el procesamiento si se selecciona la opción nula
#    geometria_seleccionada = cartas.filter(ee.Filter.eq("carac", selected_value))
#    Map.addLayer(geometria_seleccionada, {}, 'Geometría seleccionada')
   

with col1:
    Map.to_streamlit()
