import streamlit as st
import geemap.foliumap as geemap
import ee
import json
import folium

import os
from google.oauth2 import service_account  # Importar la biblioteca adecuada


######################################## INTERFAZ VISUAL
st.set_page_config(layout="wide")


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

 

 
 #inicilaizacion
 # Al inicio del script, inicializa el estado si no existe
if 'filtered_buildings' not in st.session_state:
    st.session_state.filtered_buildings = None
    st.session_state.provincia_seleccionada = None
    
########################################################################## funciones
def export_imagen(feature_collection, nombre_archivo, region):
    ## FeatureCollection of power plants in Belgium.
    collection =ee.FeatureCollection(feature_collection)
    collection.limit(5).getInfo()
    
    # Get a download URL for the FeatureCollection.
    download_url = collection.getDownloadURL(**{
    'filetype': 'geojson',
    'filename': nombre_archivo,
    })
    st.write('URL para descargar las huellas en formato geojson (tener en cuenta que puede demorar unos minutos): ')
    st.write(download_url)





    
                      
############################################################################    
st.title("Detección de Techos con Open Buildings")
st.write("Esta aplicación facilita la descarga de huellas de edificios identificadas mediante el proyecto Open Buildings, basado en imágenes satelitales de alta resolución (50 cm) correspondientes al año 2023. La clasificación se realiza por provincia y ofrece tres opciones de descarga según el puntaje de confianza, el cual representa la probabilidad de que la detección corresponda efectivamente a un edificio.")

st.page_link("https://sites.research.google/gr/open-buildings/", label="Visitar Open Buildings", icon="🌐")


st.markdown("""---""")



col1, col_medio, col2 = st.columns([5,0.15,3]) #3 columnas principales


################################## Mapa Basee
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




# Cargar colecciones de datos
buildings = ee.FeatureCollection('GOOGLE/Research/open-buildings/v3/polygons')
provincias = ee.FeatureCollection("projects/ee-dig-aplicaciones/assets/Recursos/Provincia")


with col2:
    st.markdown(" ")
    st.subheader("Instrucciones:")
    st.write("Seleccione una provincia de la lista desplegable. A continuacion, se habilitarán las opciones de descarga.")
    st.markdown(" ")
    
    # Obtener lista de nombres de provincias
    lista_provincias = provincias.aggregate_array('nam').getInfo()
    lista_provincias.sort()

    # Crear un desplegable para seleccionar provincia
    provincia_seleccionada = st.selectbox("Selecciona una provincia:", [""] + lista_provincias)

    # Filtrar la provincia seleccionada
    filtro = provincias.filter(ee.Filter.eq('nam', provincia_seleccionada))

    # Agregar capas al mapa
    Map.addLayer(filtro, {'color': 'blue'}, f'Provincia: {provincia_seleccionada}')
    
    
    # Reinicializar el estado si se selecciona una nueva provincia
    if provincia_seleccionada != st.session_state.provincia_seleccionada:
        st.session_state.filtered_buildings = None
        st.session_state.provincia_seleccionada = provincia_seleccionada

    # Botón para calcular
    if st.button("Calcular 🏠", type="primary", use_container_width=True):
        if provincia_seleccionada:
            # Filtrar edificios que intersectan con la provincia seleccionada
            filtered_buildings = buildings.filterBounds(filtro)

            # Crear capas de edificios por rangos de confianza
            t_065_070 = filtered_buildings.filter('confidence >= 0.65 && confidence < 0.7')
            t_070_075 = filtered_buildings.filter('confidence >= 0.7 && confidence < 0.75')
            t_gte_075 = filtered_buildings.filter('confidence >= 0.75')

            # Guardar resultados en el estado
            st.session_state.filtered_buildings = {
                "t_065_070": t_065_070,
                "t_070_075": t_070_075,
                "t_gte_075": t_gte_075
            }

            # Actualizar el mapa
            Map.centerObject(filtro, zoom=6)
            Map.addLayer(t_065_070, {'color': 'FF0000'}, 'Confidence [0.65, 0.7)')
            Map.addLayer(t_070_075, {'color': 'FFFF00'}, 'Confidence [0.7, 0.75)')
            Map.addLayer(t_gte_075, {'color': '00FF00'}, 'Confidence >= 0.75')
            
            st.success("Se ha procesado correctamente y a continuación se cargará el resulatdo en el mapa.")

       
        else:
            st.warning("Por favor selecciona una provincia.")

    # Mostrar opciones de descarga si se han calculado huellas
    if st.session_state.filtered_buildings:
        st.markdown("---")
        st.subheader("Descarga de huellas de edificios:")
        st.write("Seleccionar para generar el link de descarga:")
        
        if st.button('🔴 Nivel de confianza entre 0.65 - 0.7'):
            export_imagen(
                st.session_state.filtered_buildings['t_065_070'], 
                f'techos_065-070_{st.session_state.provincia_seleccionada}', 
                filtro
            )
        if st.button('🟡 Nivel de confianza entre 0.7 - 0.75'):
            export_imagen(
                st.session_state.filtered_buildings['t_070_075'], 
                f'techos_070-075_{st.session_state.provincia_seleccionada}', 
                filtro
            )
        if st.button('🟢 Nivel de confianza mayor a 0.75'):
            export_imagen(
                st.session_state.filtered_buildings['t_gte_075'], 
                f'techos_gte-075_{st.session_state.provincia_seleccionada}', 
                filtro
            )

    
    
    
with col1:
    Map.to_streamlit(height=750)
    
    
