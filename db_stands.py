import pandas as pd
import plotly.express as px
import streamlit as st

# Configuración inicial de Streamlit
st.set_page_config(page_title="Análisis de Tiendas", layout="wide")

# Título del dashboard
st.title("Análisis de Facturación y Ventas por Tienda")

# Cargar el archivo automáticamente
@st.cache_data
def load_data():
    return pd.read_csv('datasets/stands.csv', delimiter=";", usecols=[
        "Fecha", 
        "Origen - Base de datos",
        "Item - Cantidad",
        "Artículo - Código",
        "Artículo",
        "Item - Monto con impuestos",
        "Item - Descuento con impuestos",
        "Item - Monto Neto"
    ]).rename(columns={
        "Origen - Base de datos": "Tienda",
        "Item - Cantidad": "Cantidad",
        "Artículo - Código": "SKU",
        "Artículo": "Título",
        "Item - Monto con impuestos": "Precio_prod",
        "Item - Descuento con impuestos": "Descuento",
        "Item - Monto Neto": "Precio_neto"
    })

# Cargar y procesar datos
stands = load_data()

# Limpieza de datos
stands.dropna(how='all', inplace=True)
stands.fillna(0, inplace=True)

# Formateo de columnas
stands['Fecha'] = pd.to_datetime(stands['Fecha'], format='%d/%m/%y', errors='coerce')

money_columns = ['Precio_prod', 'Descuento', 'Precio_neto']
stands[money_columns] = stands[money_columns].apply(lambda x: x.astype(str).str.split(',').str[0].astype(float), axis=0)

stands['Cantidad'] = pd.to_numeric(stands['Cantidad'], errors='coerce')
stands['Título'] = stands['Título'].str.split(' ', n=1).str[1]

stands['Tienda'] = stands['Tienda'].replace('JUNCAL', 'ALTOPALERMO')
stands.sort_values(by=['Tienda', 'Fecha'], ascending=[True, True], inplace=True)

# Crear DataFrame resumen
resumen_tiendas = stands.groupby('Tienda').agg({
    'Precio_neto': 'sum',
    'Cantidad': 'sum'    
}).reset_index().sort_values(by='Precio_neto', ascending=False)

# Visualización de gráficos
fig = px.bar(
    resumen_tiendas, 
    x='Tienda', 
    y='Precio_neto', 
    title='Facturación Total por Tienda', 
    labels={"Precio_neto": "Facturación", "Tienda": "Tienda"},
    text_auto=True,
    template='plotly_white'
)
fig.update_layout(
    xaxis=dict(tickangle=45),
    yaxis_tickformat="$,.0f"
)
st.plotly_chart(fig)

fig = px.bar(
    resumen_tiendas, 
    x='Tienda', 
    y='Cantidad', 
    title='Cantidad Total de Artículos Vendidos por Tienda', 
    labels={"Cantidad": "Cantidad Vendida", "Tienda": "Tienda"},
    text_auto=True,
    template='plotly_white'
)
fig.update_layout(xaxis=dict(tickangle=45))
st.plotly_chart(fig)

# Gráfico interactivo con Plotly
ventas_tiempo = stands.groupby(['Fecha', 'Tienda']).agg({'Precio_neto': 'sum'}).reset_index()
fig = px.line(
    ventas_tiempo,
    x='Fecha',
    y='Precio_neto',
    color='Tienda',
    title='Evolución de la Facturación por Tienda',
    markers=True
)
fig.update_layout(
    title_font_size=16,
    xaxis_title_font_size=12,
    yaxis_title_font_size=12,
    legend_title_font_size=12,
    legend=dict(title='Tienda', x=1.05, y=1),
    template='plotly_white',
    hovermode='x unified'
)
st.plotly_chart(fig)

# Gráfico de torta
fig = px.pie(
    resumen_tiendas, 
    values='Precio_neto', 
    names='Tienda', 
    title='Participación de la Facturación Total por Tienda',
    template='plotly_white'
)
st.plotly_chart(fig)

# Tabla de productos más vendidos
st.subheader("Top Productos Vendidos por Tienda")
def top_products(stands, top_n=10):
    result = {}
    for tienda in stands['Tienda'].unique():
        tienda_data = stands[stands['Tienda'] == tienda]
        top_products = tienda_data.groupby(['SKU', 'Título']).agg({
            'Cantidad': 'sum',
            'Precio_neto': lambda x: x.mode().iloc[0] if not x.mode().empty else 0
        }).reset_index().sort_values(by='Cantidad', ascending=False)
        top_products['Cantidad'] = top_products['Cantidad'].map("{:.0f}".format)
        top_products['Precio_neto'] = top_products['Precio_neto'].map("${:.0f}".format)
        result[tienda] = top_products.head(top_n)
    return result

top = top_products(stands)
for tienda, data in top.items():
    st.write(f"### Tienda: {tienda}")
    st.write("**Top Productos Vendidos:**")
    st.table(data)