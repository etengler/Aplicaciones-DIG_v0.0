import streamlit as st

st.set_page_config(layout="wide")

#SOLAPA IZQUIERDA
logo_ign = 'recursos/logo_ign_largo_azul.png'
st.logo(logo_ign)


#st.sidebar.markdown("<h1 style='text-align: center;'>Aplicaciones web DIG - IGN</h1>", unsafe_allow_html=True)

markdown = """
Aplicaciones web desarrolladas en la Dirección de Información Geoespacial del Instituto Geográfico Nacional
"""
st.sidebar.info(markdown)



# PAGINA PRINCIPAL
st.image(logo_ign)

# Customize page title
st.title("Aplicaciones web DIG - IGN")

st.markdown(
    """
    Aplicaciones web desarrolladas en el departamento de **Ciencia de Datos Geoespaciales** de la Dirección de Información Geoespacial del IGN.
    """
)

#st.sidebar.image(logo_ign)