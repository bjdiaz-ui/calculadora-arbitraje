import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime

# --- Configuración de la página (Responsiva) ---
st.set_page_config(page_title="Arbitraje BNC-Binance", page_icon="🔄", layout="centered")

# --- Funciones para obtener tasas automáticamente ---
@st.cache_data(ttl=300) # Guarda los datos por 5 minutos para cargar rápido
def obtener_tasa_bcv():
    try:
        # Extraemos la tasa directo del portal del BCV (ignorando errores de certificado)
        respuesta = requests.get("https://www.bcv.org.ve/", verify=False, timeout=5)
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        dolar_div = soup.find('div', id='dolar')
        if dolar_div:
            texto_dolar = dolar_div.find('strong').text
            return float(texto_dolar.replace(',', '.'))
    except:
        return 756.90 # Tasa por defecto si falla el BCV

@st.cache_data(ttl=300)
def obtener_tasa_binance():
    try:
        url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        headers = {"Content-Type": "application/json"}
        # Buscamos a cómo compran el USDT los comerciantes (TradeType: BUY)
        data = {
            "fiat": "VES",
            "page": 1,
            "rows": 1,
            "tradeType": "BUY",
            "asset": "USDT",
            "payTypes": [],
            "publisherType": None
        }
        respuesta = requests.post(url, headers=headers, json=data, timeout=5)
        precio = respuesta.json()['data'][0]['adv']['price']
        return float(precio)
    except:
        return 848.00 # Tasa por defecto si falla Binance

# --- Interfaz de Usuario ---
st.title("🔄 Arbitraje BNC ➔ Binance")
st.markdown("Calculadora inteligente con actualización de tasas en tiempo real.")

# --- Panel Lateral (Configuración) ---
st.sidebar.header("⚙️ Configuración")
modo_automatico = st.sidebar.toggle("Usar tasas automáticas en vivo", value=True)

if modo_automatico:
    tasa_bcv_actual = obtener_tasa_bcv()
    tasa_binance_actual = obtener_tasa_binance()
    st.sidebar.success(f"Tasas actualizadas a las {datetime.datetime.now().strftime('%H:%M')}")
else:
    tasa_bcv_actual = 756.71
    tasa_binance_actual = 851.00
    st.sidebar.warning("Modo Manual Activo")

st.sidebar.divider()

st.sidebar.header("📊 Tasas de Cambio")
tasa_bcv = st.sidebar.number_input("Tasa BCV (Bs/$)", value=tasa_bcv_actual, step=1.00, format="%.2f", disabled=modo_automatico)
tasa_binance = st.sidebar.number_input("Tasa Binance P2P (Bs/$)", value=tasa_binance_actual, step=1.00, format="%.2f", disabled=modo_automatico)

st.sidebar.header("💸 Comisiones (%)")
# Ajustadas a tus nuevos valores optimizados
com_banco = st.sidebar.number_input("Intervención Bancaria (%)", value=0.50, step=0.10) / 100
com_tarjeta = st.sidebar.number_input("Uso de Tarjeta (%)", value=1.50, step=0.10) / 100
com_bpay = st.sidebar.number_input("Comisión Plataforma (%)", value=4.10, step=0.10) / 100

st.sidebar.header("💰 Inversión")
inversion = st.sidebar.number_input("Monto a Invertir ($)", value=92.0, step=10.0)

# --- Cálculos Matemáticos ---
total_comisiones = com_banco + com_tarjeta + com_bpay
bs_compra = tasa_bcv * (1 + total_comisiones)
profit_por_dolar = tasa_binance - bs_compra

costo_total_bs = inversion * bs_compra
ingreso_total_bs = inversion * tasa_binance
profit_total_bs = ingreso_total_bs - costo_total_bs
profit_total_usd = profit_total_bs / tasa_bcv if tasa_bcv > 0 else 0

# --- Dashboard (Diseño Responsivo) ---
st.subheader("Desglose Operativo")
col1, col2 = st.columns(2)
col1.metric("Costo por $ (Bs. Compra)", f"Bs. {bs_compra:,.2f}")
col2.metric("Total Comisiones", f"{total_comisiones * 100:.2f}%")

st.divider()

st.subheader("Resultados del Ciclo")
col3, col4 = st.columns(2)
col3.metric("Capital Inicial (Bs)", f"Bs. {costo_total_bs:,.2f}")
col4.metric("Ingreso P2P (Bs)", f"Bs. {ingreso_total_bs:,.2f}")

# Contenedor visual para la ganancia/pérdida
st.write("")
if profit_total_bs > 0:
    st.success(f"""
    ### 🎉 Operación Rentable
    **Ganancia Neta:** Bs. {profit_total_bs:,.2f}  
    **Equivalente USD:** $ {profit_total_usd:,.2f} (a tasa BCV)  
    **Profit por cada Dólar:** Bs. {profit_por_dolar:,.2f}
    """)
else:
    st.error(f"""
    ### ⚠️ Operación a Pérdida
    **Pérdida Neta:** Bs. {profit_total_bs:,.2f}  
    **Equivalente USD:** $ {profit_total_usd:,.2f} (a tasa BCV)  
    No se recomienda inyectar con estas tasas.
    """)
if profit_total_bs > 0:
    st.success(f"### 🎉 Ganancia Neta: Bs. {profit_total_bs:,.2f}  |  $ {profit_total_usd:,.2f} (a tasa BCV)")
else:
    st.error(f"### ⚠️ Pérdida Neta: Bs. {profit_total_bs:,.2f}  |  $ {profit_total_usd:,.2f} (a tasa BCV). ¡No es rentable operar con estas tasas!")
