import streamlit as st
import geemap.foliumap as geemap
import ee
import os
import json
import datetime
import fiona
import geopandas as gpd
import tempfile
import os
import uuid
import geemap as gm

from google.oauth2 import service_account  # Importar la biblioteca adecuada
import folium

######################################## INTERFAZ VISUAL
st.set_page_config(layout="wide")

#################################### Lee las credenciales del archivo JSON 
gcp_service_account = os.getenv('GCP_SERVICE_ACCOUNT')

if gcp_service_account:
    #st.write("✅ GCP_SERVICE_ACCOUNT cargada correctamente")

    try:
        service_account_info = json.loads(gcp_service_account)
        project_id = service_account_info.get("project_id", "No encontrado")
        #st.write(f"🔍 Proyecto detectado: {project_id}")

        # Carga credenciales
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/earthengine"]
        )

        # 🔹 VERIFICACIÓN EXTRA
        #st.write("⚡ Intentando inicializar GEE...")
        ee.Initialize(credentials, project=project_id)
        #st.write("🚀 GEE inicializado con éxito!")

    except Exception as e:
        st.error(f"❌ Error al inicializar GEE: {e}")
else:
    st.error("❌ No se encontró GCP_SERVICE_ACCOUNT en las variables de entorno.")
    

    


# st.sidebar.title("Timelapse")

# texto1_side = """
# Esta herramienta permite generar un TIMELAPSE, en formato .gif, de una región y un período en particular a partir de imágenes Landsat.
# """
# st.sidebar.info(texto1_side)
# st.sidebar.markdown("""---""")


st.title("Aplicación Timelapse")
st.markdown("Este algoritmo utiliza librerías de código abierto como GeeMap que consume Google Earth Engine (GEE) para procesar y generar imágenes satelitales. El proceso de selección de las imágenes se basa en tomar la primer imagen Landsat de cada año que cumpla con los parámetros de calidad.")
st.markdown("""---""")


data_timelapse = st.file_uploader(
            "Cargue un archivo **GeoJSON**, **kml** o **SHP** (en formato ZIP) para usarlo como área de interés 👇",
            type=["geojson", "kml", "zip"],
    )

col1, col_medio, col2 = st.columns([5,0.15,3]) #3 columnas principales

    
################################## Mapa Base
Map = geemap.Map(
            basemap="HYBRID",
            #basemap=None,  # No usar basemap por defecto
            plugin_Draw=True,
            Draw_export=True,
            locate_control=True,
            plugin_LatLngPopup=False,
            center=[-38.4161, -63.6167],  # Coordenadas para centrar el mapa
            zoom=4  # Nivel de zoom inicial
        )

# Agregar la capa TMS personalizada
tms_url = "https://wms.ign.gob.ar/geoserver/gwc/service/tms/1.0.0/capabaseargenmap@EPSG%3A3857@png/{z}/{x}/{-y}.png"
tms_layer = folium.TileLayer(
    tiles=tms_url,
    attr="IGN",
    name="ArgenMap",
    overlay=False,
    control=True
)

tms_layer.add_to(Map)
   
################################## Variables
#global img_L
#img_L= None

#img_S = None

global timelapse_L
timelapse_L = None

global extencion
extencion = None

global resultado_funcion_T
resultado_funcion_T = None #Inicializar la variable para el resultado

global out_gif
out_gif = None


################################## 
# Inicializar el estado del mensaje si no está definido
if 'message_type' not in st.session_state:
    st.session_state['message_type'] = None  # Puede ser 'success', 'error', 'warning'
if 'message_content' not in st.session_state:
    st.session_state['message_content'] = ''
    

#################################### FUNCIONES
def timelapse():
    
    #st.write('Espere mientras se clasifica ⌛⌛⌛')
    global timelapse_L
    global extencion
    
   
    if titulo == "":
        out_gif = 'timelapse.gif'
    else:
        out_gif = f'{titulo}.gif'
    # else:
    #     out_gif = None
    
    # #video mp4
    # if checkBox_descarga_video:
    #     mp4 = True
    # else:
    #     mp4 = False
    
    #desvanecimiento
    if desvanecimiento:
        fading = True
    else:
        fading = False
        
    #nubes
    if nubes:
        apply_fmask = True
    else:
        apply_fmask = False
        
    
    #periodo    
    start_month = meses[0]
    end_month = meses[1]
    
    # Obtener el valor correspondiente a la selección del usuario
    bandas_valor = opciones_bandas[bandas]
    #st.write('control 1')   
    
    if extencion is None:
        #st.write('Por favor, dibuje un poligono en el mapa ✏️') # controlar extencion adentro o fuera??
        st.session_state['message_type'] = 'warning'
        st.session_state['message_content'] = "Por favor, dibuje un poligono en el mapa ✏️"
        
        out_gif = None
    else:
        roi = None
        if st.session_state.get("roi") is not None:
            roi = st.session_state.get("roi")
            
    #st.write('aca empieza')     
        try:
            timelapse_L = geemap.landsat_timelapse(
                roi=roi,
                out_gif=out_gif, 
                start_year=anios[0], 
                end_year=anios[1], 
                start_date = f'{start_month:02d}-01',
                end_date = f'{end_month:02d}-28',
                frequency='year',
                bands = bandas_valor.split('/'),
                frames_per_second=frames,
                title=titulo, #titulo
                font_color=color_fuente,
                font_size=fuente,
                progress_bar_color=color_barra_progreso,
                mp4=False, #
                apply_fmask=apply_fmask,
                fading=fading,
            )
        #st.write('ok')
         
        # # Comprobar si el archivo GIF existe
        # if os.path.exists(out_gif):
        #     st.image(out_gif)  # Mostrar el GIF en la página web
        #     st.success("Timelapse generado correctamente.")
        # else:
        #     st.error("No se pudo generar el timelapse. Inténtalo nuevamente.")
            
        except FileNotFoundError:
            print("Error: No se pudo encontrar el archivo de imagen GIF. Por favor, intenta nuevamente más tarde.")
        
        except Exception as e:
            print("Error inesperado:", e)
    

    extencion  = None            
    return out_gif        
            
            
            
                 
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
        #st.warning('La fecha final no puede ser mayor o igual que la fecha inicial')
        st.session_state['message_type'] = 'warning'
        st.session_state['message_content'] = "La fecha final no puede ser mayor o igual que la fecha inicial"
        
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
def uploaded_file_to_gdf(data_timelapse):
    _, file_extension = os.path.splitext(data_timelapse.name)
    file_id = str(uuid.uuid4())
    file_path = os.path.join(tempfile.gettempdir(), f"{file_id}{file_extension}")

    with open(file_path, "wb") as file:
        file.write(data_timelapse.getbuffer())

    if file_path.lower().endswith(".kml"):
        fiona.drvsupport.supported_drivers["KML"] = "rw"
        gdf = gpd.read_file(file_path, driver="KML")
    else:
        gdf = gpd.read_file(file_path)

    return gdf




#################################### main
if data_timelapse: # se ejecuta al cargar un archivo 
    extencion = uploaded_file_to_gdf(data_timelapse)
    try:
        st.session_state["roi"] = geemap.gdf_to_ee(extencion, geodesic=False)
        Map.add_gdf(extencion, "ROI")
    except Exception as e:
        #st.error(e)
        #st.error("Dibuje otra área inténtelo de nuevo.")
        st.session_state['message_type'] = 'error'
        st.session_state['message_content'] = "Dibuje otra área inténtelo de nuevo."
        
 
 
    
# Asegurarse de que session_state tiene un espacio para guardar el resultado VER
if 'resultado_funcion_T' not in st.session_state:
    st.session_state['resultado_funcion_T'] = None
    
    
# Store the initial value of widgets in session state  VER
if "visibility" not in st.session_state:
    st.session_state.visibility = "visible"
    st.session_state.disabled = False
    
    # Diccionario que relaciona las opciones visibles con los valores internos

opciones_bandas = {
        'Color verdadero': 'Red/Green/Blue',
        'Color natural': 'NIR/Red/Green',
        'Falso color de vegetación': 'SWIR2/SWIR1/NIR',
        'Color de vegetación': 'NIR/SWIR1/Red',
        'Índice de vegetación de diferencia normalizada (NDVI)': 'SWIR2/NIR/Red',
        'Índice de agua (NDWI)': 'SWIR2/SWIR1/Red',
        'Índice de suelo (Soil Index)': 'SWIR1/NIR/Blue',
        'Índice de humedad del suelo (Soil Moisture Index)': 'NIR/SWIR1/Blue',
        'Índice de vegetación de ajuste de suelo (SAVI)': 'SWIR2/NIR/Green',
        'Índice de vegetación mejorado (EVI)': 'SWIR1/NIR/Red'
    }
    
  

          
with col2:
    st.subheader("Instrucciones:")
    st.markdown("1- Seleccionar un área de estudio. Opciones: ")
    st.markdown("- Dibujar en el mapa una geometría (rectángulo o plígono), exportarla mediante **Export** y luego subirla con la herramienta **Browse files**.")
    st.markdown("- Directamente subir una geometría en formato geojson, kml o shp (zip).")
    

    
    #st.markdown("Elija un área y complete los parámetros para generar el Timelpase con imágenes Landsat:")
    
    #colA, colB = st.columns([3,3]) 
    
    st.markdown("2- Completar parámetros: ")
    
    bandas = st.selectbox(
    "**Combinación de bandas:**",
    list(opciones_bandas.keys()),  # Mostrar solo las claves (nombres visibles)
    index=0,  # Cambia este valor si deseas que se seleccione otra opción por defecto
    label_visibility=st.session_state.visibility,
    disabled=st.session_state.disabled
    )
    

    
    st.markdown("**Período de búsqueda de imágenes:**")
    
    left, middle = st.columns(2)
    anios = left.slider("Período anual: ", 1984, 2024, (2015, 2023))
    meses = middle.slider("Período mensual: ", 1, 12, (1, 4))
    
    #st.divider()
    #st.markdown("**Estilo:**")
    
    titulo = st.text_input(
        "Título: ",
        label_visibility=st.session_state.visibility,
        disabled=st.session_state.disabled,
        #placeholder=st.session_state.placeholder,
    )
    
    left, middle = st.columns(2)
    frames = left.slider("Frames por segundo: ", 1, 5, 3)
    fuente = middle.slider("Tamaño de fuente: ", 8, 50, 30)
    
    
    desvanecimiento = left.checkbox("Desvanecimiento de imágenes")
    nubes = middle.checkbox("Máscara de nubes")
    
    color_fuente = left.color_picker("Color de fuente:", "#FFFFFF")
    color_barra_progreso = middle.color_picker("Color de la barra de progreso:", "#200BFD")
    
   
    # #st.divider()
    # st.markdown("**Descarga:**")
    
    # left, middle = st.columns(2)

    # nombre_gif = left.text_input(
    #     "Nombre del archivo: ",
    #     label_visibility=st.session_state.visibility,
    #     disabled=st.session_state.disabled,
    #     #placeholder=st.session_state.placeholder,
    # )
    
    # checkBox_descarga_gif = middle.checkbox("Descargar en formato gif")
    # checkBox_descarga_video = middle.checkbox("Descargar en formato video")
    

    #left, middle, = st.columns(2)
    
# Botón para calcular y almacenar el resultado en session_state
    #if st.button("Calcular  📷", type="primary", use_container_width=True):
        #timelapse()

    # Botón para calcular y almacenar el resultado en session_state
    if st.button("Calcular  📷", type="primary", use_container_width=True):
        st.session_state['resultado_funcion_T'] = timelapse()
        #st.success("Imagen calculada y guardada")
        
        #st.session_state['message_type'] = 'success'
        #st.session_state['message_content'] = 'Se ha cargado el resultado a continuación y habilitado la opción de descarga 👇'
        
        
    # Placeholder para mensajes de la clasificación
    placeholder = st.empty()
                  
        
        # Mostrar el resultado si existe
    if st.session_state['resultado_funcion_T'] is not None:
        st.session_state['message_type'] = 'success'
        st.session_state['message_content'] = 'Se cargó el resultado a continuación y habilitó la opción de descarga 👇'
        
    
        st.image(st.session_state['resultado_funcion_T'])
        #st.write('Se ha cargado el resultado de la clasificación en el mapa 🏞️')
        #st.success('Se ha cargado el resultado de la clasificación en el mapa 🏞️')
        #st.write('result funciom', resultado_funcion_T.getInfo())

    # Botón para descargar (solo si ya se ha calculado una imagen)
    # Botón para descargar (solo si ya se ha calculado una imagen)
    #if st.button("Descargar", type="secondary", use_container_width=True):
    if st.session_state.get('resultado_funcion_T') is not None:
        with open(st.session_state['resultado_funcion_T'], "rb") as file:
            st.download_button(
                    label="Descargar Timelapse en formato GIF",
                    data=file,
                    #file_name=st.session_state['resultado_funcion_T'],
                    file_name=f'timelapse_{anios[0]}-{anios[1]}.gif',
                    mime="image/gif"
                )
    else:
        #st.warning('No hay imagen disponible para descargar.')
        pass

    # Control de qué mensaje mostrar según el estado actual
    if st.session_state['message_type'] == 'success':
        placeholder.success(st.session_state['message_content'])
    elif st.session_state['message_type'] == 'error':
        placeholder.error(st.session_state['message_content'])
    elif st.session_state['message_type'] == 'warning':
        placeholder.warning(st.session_state['message_content'])
    
        
with col1:      
    #Map.to_streamlit() 
    Map.to_streamlit(height=750)  
            
                          
                
