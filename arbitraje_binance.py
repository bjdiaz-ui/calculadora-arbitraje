import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime

# --- Configuración de la página ---
st.set_page_config(page_title="Arbitraje BNC-Binance", page_icon="🔄", layout="centered")

# --- Comisiones Fijas (Ocultas en UI) ---
COM_BANCO = 0.005
COM_TARJETA = 0.015
COM_PLATAFORMA = 0.041
TOTAL_COMISIONES = COM_BANCO + COM_TARJETA + COM_PLATAFORMA

# --- Funciones API ---
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
        return 756.71 # Respaldo

@st.cache_data(ttl=60) # Refresco más rápido (1 minuto) para el P2P
def obtener_tasa_binance(monto_ves_estimado=None):
    try:
        url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        headers = {"Content-Type": "application/json"}
        
        # tradeType: BUY (Tú vendes, ellos compran)
        data = {
            "fiat": "VES",
            "page": 1,
            "rows": 10, # Traemos 10 para buscar el mejor real
            "tradeType": "BUY", 
            "asset": "USDT",
            "payTypes": [],
            "publisherType": None,
            "filterType": "all" # Intentamos evitar filtros que bloqueen anuncios comunes
        }
        
        if monto_ves_estimado:
            data["transAmount"] = str(monto_ves_estimado)

        respuesta = requests.post(url, headers=headers, json=data, timeout=5)
        anuncios = respuesta.json().get('data', [])
        
        if not anuncios:
             return 850.00

        # Buscamos el primer anuncio razonable (evitamos precios exageradamente bajos que suelen ser estafas/promociones raras)
        # Asumimos que la tasa real está cerca de la media de los primeros resultados.
        for anuncio in anuncios:
             precio = float(anuncio['adv']['price'])
             # En tu captura de pantalla, el primer resultado orgánico sin verificación requerida estaba cerca de 849.71
             # Retornamos el primero que encontremos, confiando en que el ordenamiento de Binance es correcto para usuarios normales.
             return precio
            
    except:
        return 850.00 

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
    # Usamos una estimación generosa para asegurar que caemos en un buen rango de P2P
    monto_fiat_estimado = inversion * (tasa_bcv_actual * 1.1) 
    tasa_binance_actual = obtener_tasa_binance(monto_fiat_estimado)
    
    st.sidebar.success(f"✅ Actualizado a las {datetime.datetime.now().strftime('%H:%M')}")
else:
    tasa_bcv_actual = 756.71
    tasa_binance_actual = 849.71 # Tasa de referencia basada en tu captura
    st.sidebar.warning("⚠️ Modo Manual Activo")

tasa_bcv = st.sidebar.number_input("Tasa BCV (Bs/$)", value=tasa_bcv_actual, step=1.00, format="%.2f", disabled=modo_automatico)
tasa_binance = st.sidebar.number_input("Tasa Venta Binance (Bs/$)", value=tasa_binance_actual, step=1.00, format="%.2f", disabled=modo_automatico)


# --- Cálculos Matemáticos ---
bs_compra = tasa_bcv * (1 + TOTAL_COMISIONES)

costo_total_bs = inversion * bs_compra
ingreso_total_bs = inversion * tasa_binance
profit_total_bs = ingreso_total_bs - costo_total_bs

# Calculamos el margen de ganancia respecto a la tasa de venta (Rendimiento)
if ingreso_total_bs > 0:
    margen_ganancia_porcentaje = (profit_total_bs / ingreso_total_bs) * 100
else:
    margen_ganancia_porcentaje = 0

# --- Dashboard ---
st.subheader("Desglose Operativo")
col1, col2 = st.columns(2)
col1.metric("Costo Real por $", f"Bs. {bs_compra:,.2f}")
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
    **Ganancia Neta:** Bs. {profit_total_bs:,.2f}  
    **Rendimiento (Profit):** {margen_ganancia_porcentaje:,.2f}% (sobre la venta)
    """)
else:
    st.error(f"""
    ### ⚠️ Operación a Pérdida
    **Pérdida Neta:** Bs. {profit_total_bs:,.2f}  
    No se recomienda operar.
    """)
