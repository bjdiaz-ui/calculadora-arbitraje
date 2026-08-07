import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime

# --- Configuración de la página ---
st.set_page_config(page_title="Arbitraje BNC-Binance", page_icon="🔄", layout="centered")

# --- Comisiones Fijas ---
COM_BANCO = 0.005
COM_TARJETA = 0.015
COM_PLATAFORMA = 0.041
TOTAL_COMISIONES = COM_BANCO + COM_TARJETA + COM_PLATAFORMA

# --- Funciones de Extracción de Tasas ---
@st.cache_data(ttl=300) 
def obtener_tasa_bcv():
    try:
        respuesta = requests.get("https://www.bcv.org.ve/", verify=False, timeout=5)
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        dolar_div = soup.find('div', id='dolar')
        if dolar_div:
            texto_dolar = dolar_div.find('strong').text
            return float(texto_dolar.replace(',', '.'))
    except:
        return 756.71

@st.cache_data(ttl=60) 
def obtener_tasa_binance(inversion_usd, tasa_usdt_estimada):
    try:
        url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        headers = {"Content-Type": "application/json"}
        
        # Monto exacto en Bs. para filtrar la búsqueda (Ej: 17,000 VES)
        monto_ves_fidedigno = int(inversion_usd * tasa_usdt_estimada)
        
        # Payload alineado punto por punto con tus capturas
        data = {
            "asset": "USDT",
            "fiat": "VES",
            "merchantCheck": False,        # "Solo comerciantes Verificados" = OFF
            "page": 1,
            "payTypes": ["PagoMovil", "BNC"], # Pago Móvil y BNC
            "publisherType": None,
            "rows": 20,
            "tradeType": "BUY",             # Pestana VENTA en la app
            "transAmount": str(monto_ves_fidedigno)
        }

        respuesta = requests.post(url, headers=headers, json=data, timeout=5)
        anuncios = respuesta.json().get('data', [])
        
        if not anuncios:
             return 846.90

        # Filtrado de ofertas reales (excluyendo promocionadas)
        precios_reales = []
        for ad in anuncios:
            adv = ad.get('adv', {})
            
            # Excluir anuncios promocionados
            if adv.get('isPromoted') or ad.get('isPromoted'):
                continue
                
            precio = float(adv.get('price', 0))
            if precio > 0:
                precios_reales.append(precio)
        
        if not precios_reales:
            return 846.90

        # Promedio del top 3 de anuncios reales en pantalla (Ej: 846.92, 846.70, 846.50)
        top_anuncios = precios_reales[:3]
        return sum(top_anuncios) / len(top_anuncios)
            
    except:
        return 846.90 

# --- Interfaz de Usuario ---
st.title("🔄 Arbitraje BNC ➔ Binance")

st.sidebar.header("⚙️ Configuración")
modo_automatico = st.sidebar.toggle("Tasas automáticas en vivo", value=True)

st.sidebar.divider()

st.sidebar.header("💰 Inversión")
inversion = st.sidebar.number_input("Monto a Inyectar ($)", value=20.0, step=10.0, format="%.2f")

st.sidebar.divider()

st.sidebar.header("📊 Tasas de Cambio")

if modo_automatico:
    tasa_bcv_actual = obtener_tasa_bcv()
    tasa_usdt_proyectada = tasa_bcv_actual * 1.12
    tasa_binance_actual = obtener_tasa_binance(inversion, tasa_usdt_proyectada)
    
    st.sidebar.success(f"✅ Actualizado a las {datetime.datetime.now().strftime('%H:%M')}")
else:
    tasa_bcv_actual = 756.71
    tasa_binance_actual = 846.92 
    st.sidebar.warning("⚠️ Modo Manual Activo")

tasa_bcv = st.sidebar.number_input("Tasa BCV (Bs/$)", value=tasa_bcv_actual, step=1.00, format="%.2f", disabled=modo_automatico)
tasa_binance = st.sidebar.number_input("Tasa Venta Binance (Bs/$)", value=tasa_binance_actual, step=1.00, format="%.2f", disabled=modo_automatico)

# --- Cálculos Matemáticos ---
bs_compra = tasa_bcv * (1 + TOTAL_COMISIONES)

costo_total_bs = inversion * bs_compra
ingreso_total_bs = inversion * tasa_binance
profit_total_bs = ingreso_total_bs - costo_total_bs

profit_total_usd_binance = profit_total_bs / tasa_binance if tasa_binance > 0 else 0
margen_ganancia_porcentaje = (profit_total_bs / ingreso_total_bs * 100) if ingreso_total_bs > 0 else 0

# --- Dashboard Principal ---
st.subheader("Desglose Operativo")
col1, col2 = st.columns(2)
col1.metric("Costo Real por $ (Bs.)", f"Bs. {bs_compra:,.2f}")
col2.metric("Comisiones Aplicadas", f"{TOTAL_COMISIONES * 100:.2f}%")

st.divider()

st.subheader("Resultados del Ciclo")
col3, col4 = st.columns(2)
col3.metric("Capital a Descontar (BNC)", f"Bs. {costo_total_bs:,.2f}")
col4.metric("Ingreso Venta (Binance)", f"Bs. {ingreso_total_bs:,.2f}")

st.write("")
if profit_total_bs > 0:
    st.success(f"""
    ### 🎉 Operación Rentable
    **Ganancia Neta (Bolívares):** Bs. {profit_total_bs:,.2f}  
    **Ganancia Neta (Líquida):** {profit_total_usd_binance:,.2f} USDT  
    **Rendimiento del Ciclo:** {margen_ganancia_porcentaje:,.2f}% 
    """)
else:
    st.error(f"""
    ### ⚠️ Operación a Pérdida
    **Pérdida Neta:** Bs. {profit_total_bs:,.2f}  
    No se recomienda inyectar capital en este momento.
    """)
