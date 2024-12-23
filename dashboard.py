import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, date
import plotly.express as px
import folium
from streamlit_folium import st_folium
from stands import solapa_stands


#Page title configuration
st.set_page_config(page_title="Muy Biferdil", layout="wide")

#General title
st.markdown(
    """
    <div style='background-color: #ECE9E6; padding: 8px 0; width: 100%;'>
        <h1 style='text-align: center; color: black; font-family: Roboto, sans-serif;'>
        Muy Biferdil
        </h1>
    </div>
    """,
    unsafe_allow_html=True
)

#Sidebar style
st.markdown(
    """
    <style>
        [data-testid="stSidebar"] {
            background-color: #ECE9E6;
            color: grey;
        }
        [data-testid="stSidebar"] .css-1d391kg p {
            color: grey;
        }
    </style>
    """,
    unsafe_allow_html=True
)

@st.cache_data

#CARGA ECOMMERCE

#Load and clean data
def cargar_ecommerce():
    df_ecommerce = pd.read_csv('datasets/ecommerce_raw.csv', delimiter=";")

    #Drop unnecesary columns
    drop_columns = ['email', 'status', 'currency','subtotal','taxes','shipping', 'shipping_taxes', 'discount','payment_mode','invoice_num','receipt_num','has_invoice','article_options_variants','article_price','last_name','first_name','phone', 'company', 'vat_number',
       'shipping_address_last_name', 'shipping_address_first_name',
       'shipping_address', 'billing_address', 'shipping_tracking_num',
       'customer_note', 'internal_note', 'tax_amount_at_0.0',
       'taxable_amount_at_0.0', 'invoice_url', 'order_summary_url']
    df_ecommerce.drop(columns=drop_columns, axis=1, inplace=True)

    #Converting dtypes float into int
    float_cols=df_ecommerce.select_dtypes(include=['float64']).columns
    df_ecommerce[float_cols] = df_ecommerce[float_cols].fillna(0).astype('int64')
    
    #Converting 'total' column into proper format
    df_ecommerce['total'] = (
    df_ecommerce['total'].fillna(method='ffill')
    .str.replace('.','', regex=False)
    .astype(int)
    //100_000
)

    #Converting dtypes date into datetime
    df_ecommerce['date'] = pd.to_datetime(df_ecommerce['date'], format='%d/%m/%y', errors='coerce')
    df_ecommerce['date'] = df_ecommerce['date'].ffill()

    #Dealing null values
    df_ecommerce['promo_code'] = df_ecommerce['promo_code'].fillna('None')
    df_ecommerce[['shipping_method','origin']] = df_ecommerce[['shipping_method','origin']].ffill()
    df_ecommerce[['order_id','order_num']]=df_ecommerce[['order_id','order_num']].astype('str').replace('0', pd.NA).ffill()

    return df_ecommerce
    

#Execute load function
df_ecommerce = cargar_ecommerce().sort_values(by='date')

#SIDEBAR

#Navigator sidebar
st.sidebar.title("Tablero de Control")
view = st.sidebar.radio("Selecciona la consulta deseada",
                        ["Ecommerce", "Stands"])

#Common filters
st.sidebar.subheader("Seleccionar Fecha")
start_date = st.sidebar.date_input("Fecha de inicio", value= date.today().replace(day=1))
end_date = st.sidebar.date_input("Fecha de fin", value= date.today())

#Convert star_date y end_date to datetime
start_date = pd.to_datetime(start_date, format='%Y-%m-%d', errors='coerce')
end_date = pd.to_datetime(end_date, format='%Y-%m-%d', errors='coerce')

#Apply date filter
filtered_ecommerce = df_ecommerce[(df_ecommerce['date'] >= start_date) & (df_ecommerce['date'] <= end_date)].sort_values(by='date')

#Define function to show KPI's
def mostrar_kpis(filtered_ecommerce):
    total_ordenes = filtered_ecommerce['order_num'].nunique()
    total_articulos = filtered_ecommerce['article_quantity'].sum()
    facturacion_total = filtered_ecommerce.drop_duplicates(subset='order_num')['total'].sum()
    facturacion_promedio = facturacion_total / total_ordenes if total_ordenes != 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Total Órdenes", value= int(total_ordenes))
    with col2:
        st.metric(label="Total Artículos", value=int(total_articulos))
    with col3:
        st.metric(label="Facturación Total", value=f"${int(facturacion_total):,}".replace(',', '.'))
    with col4:
        st.metric(label="Facturación Promedio", value=f"${int(facturacion_promedio):}".replace(',', '.'))

#Views according to selected parameter
def ecommerce():
    mostrar_kpis(filtered_ecommerce)
    st.subheader("Ventas por día")
    sales_summary = (filtered_ecommerce
                     .drop_duplicates(subset='order_num')
                     .groupby(filtered_ecommerce['date'].dt.date)
                     .agg({'total':'sum','article_quantity':'sum', 'order_num':'count'})
                     .reset_index()
                     .rename(columns={'date': 'Fecha','total':'Facturación', 'article_quantity': 'Cant. Artículos','order_num':'Órdenes'}))

    # Convert 'date' to datetime to keep cronologyc order
    sales_summary['Fecha'] = pd.to_datetime(sales_summary['Fecha']).dt.date
    sales_summary = sales_summary.sort_values(by='Fecha')

    # Mostrar gráfico de barras y tabla con los valores formateados
    formatted_totals = sales_summary['Facturación'].apply(lambda x: round(x)).apply(lambda x: f"${x:,}".replace(',', '.'))
    sales_summary['formatted_total'] = formatted_totals
    st.bar_chart(sales_summary.set_index('Fecha')['Facturación'], use_container_width=True, height=400)
    col1, col2, col3= st.columns([2, 2, 2])
    
    with col1:
        sales_summary['Facturación'] = sales_summary['Facturación'].astype(int).apply(lambda x: f"${int(x)}")
        sales_summary['Fecha'] = sales_summary['Fecha'].apply(lambda x: x.strftime('%Y-%m-%d'))
        st.subheader("Datos por día")
        st.dataframe(sales_summary[['Fecha', 'Facturación', 'Cant. Artículos','Órdenes']].reset_index(drop=True))

    with col2:
        productos_mas_vendidos = filtered_ecommerce.groupby('article_title')['article_quantity'].sum().sort_values(ascending=False).head(10)
        fig = px.pie(values=productos_mas_vendidos.values, names=productos_mas_vendidos.index, title='Top 10 Productos Más Vendidos', hole=0.4)
        fig.update_traces(textinfo='percent', insidetextorientation='auto')
        fig.update_layout(title_font=dict(family='Roboto, sans-serif', size=20, color='black', weight='normal'), width=500, height=400)
        st.plotly_chart(fig, use_containter_width=True)
    
    with col3:
        # Mapa de ubicaciones de pedidos
        shipping_summary = filtered_ecommerce['shipping_method'].value_counts().reset_index()
        shipping_summary.columns = ['Método de Envío', 'Cantidad de Pedidos']
        fig_pie = px.pie(shipping_summary, values='Cantidad de Pedidos', names='Método de Envío', title='Distribución de Pedidos por Método de Envío', hole=0.4)           
        fig.update_traces(textinfo='percent', insidetextorientation='auto')
        fig_pie.update_layout(title_font=dict(family='Roboto, sans-serif', size=20, color='black', weight='normal'),width=500, height=400)
        st.plotly_chart(fig_pie, use_containter_width=True)


# CARGAR STANDS

def convertir_fecha(fecha):
    formatos = [
        "%d/%m/%y",  # Formato corto (DD/MM/YY)
        "%d/%m/%Y",  # Formato largo (DD/MM/YYYY)
        "%d-%m-%y",  # ISO (YYYY-MM-DD)
        "%d-%m-%Y",  # Guiones en formato largo (DD-MM-YYYY)
    
    ]
    for formato in formatos:
        try:
            return datetime.strptime(fecha, formato).strftime("%d/%m/%y")  # Formato unificado
        except ValueError:
            continue
    return fecha

def cargar_stands():
    df_stands = pd.read_csv('datasets/stands.csv', delimiter=";")

    df_stands.dropna(inplace=True)

    df_stands['Date'] = df_stands['Fecha'].apply(convertir_fecha)
    df_stands['Date'] = pd.to_datetime(df_stands['Date'], errors='coerce', infer_datetime_format=True)

    drop_columns = ['Fecha','Comprobante','Item - Monto sin impuestos', 'Item - Descuento sin impuestos', 'Item - Monto Neto sin impuestos']
    df_stands.drop(columns = drop_columns, axis=1, inplace=True)

    df_stands = df_stands.rename(columns={'Origen - Base de datos': 'Tienda',
                             'Item - Cantidad': 'Cantidad',
                            'Artículo - Código': 'SKU',
                            'Artículo': 'Título',
                            'Item - Monto con impuestos': 'Ingreso_total',
                            'Item - Descuento con impuestos': 'Descuento',
                            'Item - Monto Neto': 'Ingreso_neto',
                            })
    
    convert_columns=['Ingreso_total', 'Descuento','Ingreso_neto','Cantidad']
    for columns in convert_columns:
        df_stands[columns]=pd.to_numeric(df_stands[columns], errors='coerce')
    df_stands[convert_columns]=df_stands[convert_columns].fillna(0).astype('int64')

    df_stands['Título'] = df_stands['Título'].apply(lambda x: ' '.join(x.split(' ')[1:]))

    return df_stands

df_stands= cargar_stands().sort_values(by=['Tienda','Date'])

filtered_stands = df_stands[(df_stands['Date'] >= start_date) & (df_stands['Date'] <= end_date)].sort_values(by='Date')

def resumen_tiendas(filtered_stands):
    total_facturacion = filtered_stands['Ingreso_neto'].sum()
    cant_articulos = filtered_stands ['Cantidad'].sum()

    
    #resumen = filtered_stands.groupby('Tienda').agg(
    #    total_facturacion = ('Ingreso_neto', 'sum'),
    #    cant_articulos = ('Cantidad', 'sum')
    #).reset_index()
    
    #resumen = resumen.rename(columns={
    #    'total_facturacion': 'Facturación Total',
    #    'cant_articulos': 'Cantidad de Artículos'
    #})

    #esumen = resumen.sort_values(by='Facturación Total', ascending=False)

    #resumen['Facturación Total'] = resumen['Facturación Total'].apply(
    #    lambda x: f"${round(x):,}".replace(',', '.')
    #)


    col1, col2, col3 = st.columns(3)

    with col1:
        st.dataframe(total_facturacion.sort_values(by='Facturación Total', ascending=False)[['Tienda', 'Facturación Total']])

    with col2:
        st.dataframe(cant_articulos.sort_values(by='Cantidad de Artículos', ascending=False)[['Tienda', 'Cantidad de Artículos']])

    with col3:
      aggregated_data = filtered_stands.groupby(['Date', 'Tienda']).agg(
            total_facturacion=('Ingreso_total', 'sum')
        ).reset_index()

    fig = px.line(
            aggregated_data,
            x='Date',
            y='Facturación',
            color='Tienda',
            title='Facturación por Tienda'
        )
    st.plotly_chart(fig)



def solapa_stands():
    resumen_tiendas(filtered_stands)

if view == "Ecommerce":
    ecommerce()

elif view == "Stands":
    solapa_stands()


