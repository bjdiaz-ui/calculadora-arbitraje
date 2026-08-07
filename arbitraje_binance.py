import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime

# --- Configuración de la página (Responsiva) ---
st.set_page_config(page_title="Arbitraje BNC-Binance", page_icon="🔄", layout="centered")

# --- Comisiones Fijas (Ocultas en la UI, pero activas en la matemática) ---
# Intervención (0.50%) + Tarjeta (1.50%) + Plataforma (4.10%) = 6.10%
COM_BANCO = 0.005
COM_TARJETA = 0.015
COM_PLATAFORMA = 0.041
TOTAL_COMISIONES = COM_BANCO + COM_TARJETA + COM_PLATAFORMA

# --- Funciones para obtener tasas automáticamente ---
@st.cache_data(ttl=300) # Se refresca cada 5 minutos
def obtener_tasa_bcv():
    try:
        respuesta = requests.get("https://www.bcv.org.ve/", verify=False, timeout=5)
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        dolar_div = soup.find('div', id='dolar')
        if dolar_div:
            texto_dolar = dolar_div.find('strong').text
            return float(texto_dolar.replace(',', '.'))
    except:
        return 756.90 # Tasa de respaldo

@st.cache_data(ttl=120) # Se refresca cada 2 minutos en Binance
def obtener_tasa_binance(monto_ves_estimado=None):
    try:
        url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        headers = {"Content-Type": "application/json"}
        
        # Buscamos Anuncios de COMPRA (Nosotros vamos a VENDERLES a ellos).
        # publisherType: None incluye a los compradores no verificados (mejor tasa).
        data = {
            "fiat": "VES",
            "page": 1,
            "rows": 1,
            "tradeType": "BUY", 
            "asset": "USDT",
            "payTypes": [],
            "publisherType": None 
        }
        
        # Filtramos por el monto que vamos a cambiar para evitar límites inválidos
        if monto_ves_estimado:
            data["transAmount"] = str(monto_ves_estimado)

        respuesta = requests.post(url, headers=headers, json=data, timeout=5)
        precio = respuesta.json()['data'][0]['adv']['price']
        return float(precio)
    except:
        return 850.00 # Tasa de respaldo

# --- Interfaz de Usuario ---
st.title("🔄 Arbitraje BNC ➔ Binance")
st.markdown("Calculadora inteligente P2P.")

# --- Panel Lateral (Orden de Prioridad Ajustado) ---
st.sidebar.header("⚙️ Configuración")
modo_automatico = st.sidebar.toggle("Tasas automáticas en vivo", value=True)

st.sidebar.divider()

# PRIORIDAD: Monto a Invertir
st.sidebar.header("💰 Inversión")
inversion = st.sidebar.number_input("Monto a Inyectar ($)", value=92.0, step=10.0, format="%.2f")

st.sidebar.divider()

# SECUNDARIO: Tasas de Cambio
st.sidebar.header("📊 Tasas de Cambio")

if modo_automatico:
    tasa_bcv_actual = obtener_tasa_bcv()
    
    # Calculamos cuántos bolívares representa la inversión para buscar una tasa realista
    monto_fiat_estimado = inversion * tasa_bcv_actual
    tasa_binance_actual = obtener_tasa_binance(monto_fiat_estimado)
    
    st.sidebar.success(f"✅ Tasas obtenidas a las {datetime.datetime.now().strftime('%H:%M')}")
else:
    tasa_bcv_actual = 756.71
    tasa_binance_actual = 851.00
    st.sidebar.warning("⚠️ Modo Manual Activo")

tasa_bcv = st.sidebar.number_input("Tasa BCV (Bs/$)", value=tasa_bcv_actual, step=1.00, format="%.2f", disabled=modo_automatico)
tasa_binance = st.sidebar.number_input("Tasa Venta Binance (Bs/$)", value=tasa_binance_actual, step=1.00, format="%.2f", disabled=modo_automatico)


# --- Cálculos Matemáticos ---
bs_compra = tasa_bcv * (1 + TOTAL_COMISIONES)
profit_por_dolar = tasa_binance - bs_compra

costo_total_bs = inversion * bs_compra
ingreso_total_bs = inversion * tasa_binance
profit_total_bs = ingreso_total_bs - costo_total_bs
profit_total_usd = profit_total_bs / tasa_bcv if tasa_bcv > 0 else 0

# --- Dashboard Principal ---
st.subheader("Desglose Operativo")
col1, col2 = st.columns(2)
col1.metric("Costo por $ (Bs. Compra)", f"Bs. {bs_compra:,.2f}")
col2.metric("Comisiones Aplicadas", f"{TOTAL_COMISIONES * 100:.2f}%")

st.divider()

st.subheader("Resultados del Ciclo")
col3, col4 = st.columns(2)
col3.metric("Capital a Descontar (BNC)", f"Bs. {costo_total_bs:,.2f}")
col4.metric("Ingreso Venta (Binance)", f"Bs. {ingreso_total_bs:,.2f}")

# Contenedor visual para la ganancia/pérdida
st.write("")
if profit_total_bs > 0:
    st.success(f"""
    ### 🎉 Operación Rentable
    **Ganancia Neta:** Bs. {profit_total_bs:,.2f}  
    **Equivalente USD:** $ {profit_total_usd:,.2f} (a tasa BCV)  
    **Profit por Dólar Inyectado:** Bs. {profit_por_dolar:,.2f}
    """)
else:
    st.error(f"""
    ### ⚠️ Operación a Pérdida
    **Pérdida Neta:** Bs. {profit_total_bs:,.2f}  
    **Equivalente USD:** $ {profit_total_usd:,.2f} (a tasa BCV)  
    No se recomienda inyectar con estas tasas en este monto.
    """)
