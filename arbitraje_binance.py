import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime

# --- Configuración de la página (Responsiva para Celular) ---
st.set_page_config(page_title="Arbitraje BNC-Binance", page_icon="🔄", layout="centered")

# --- Comisiones Fijas (Ocultas en UI, activas en cálculos) ---
# Intervención (0.50%) + Tarjeta (1.50%) + Plataforma (4.10%) = 6.10%
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
        return 756.71 # Respaldo

@st.cache_data(ttl=60) 
def obtener_tasa_binance(inversion_usd, tasa_usdt_estimada):
    try:
        url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        headers = {"Content-Type": "application/json"}
        
        # Filtro de capital fidedigno: Dólares de inversión * Tasa USDT estimada
        monto_ves_fidedigno = int(inversion_usd * tasa_usdt_estimada)
        
        data = {
            "fiat": "VES",
            "page": 1,
            "rows": 20,
            "tradeType": "BUY",  # Tú vendes USDT, los compradores te pagan en Bs.
            "asset": "USDT",
            "payTypes": ["PagoMovil", "BNC"], # Restringido a Pago Móvil y BNC
            "publisherType": None,
            "filterType": "all",
            "transAmount": str(monto_ves_fidedigno) # Límite fidedigno en Bolívares
        }

        respuesta = requests.post(url, headers=headers, json=data, timeout=5)
        anuncios = respuesta.json().get('data', [])
        
        if not anuncios:
             return 850.00

        # 1. FILTRO DE CONFIANZA (+90% de órdenes completadas y +50 órdenes al mes)
        precios_confiables = []
        for anuncio in anuncios:
            vendedor = anuncio.get('advertiser', {})
            ratio_completadas = float(vendedor.get('monthFinishRate', 0))
            ordenes_mes = int(vendedor.get('monthOrderCount', 0))
            
            if ratio_completadas >= 0.90 and ordenes_mes >= 50:
                precios_confiables.append(float(anuncio['adv']['price']))
        
        # Si el filtro es muy estricto, mantiene la lista original por seguridad
        if not precios_confiables:
            precios_confiables = [float(a['adv']['price']) for a in anuncios]

        # 2. TASA CONSERVADORA (Promedio de las posiciones 3ra, 4ta y 5ta reales)
        if len(precios_confiables) >= 5:
            muestra = precios_confiables[2:5] 
            return sum(muestra) / len(muestra)
        elif len(precios_confiables) >= 2:
            return precios_confiables[1] 
        else:
            return precios_confiables[0] 
            
    except:
        return 850.00 

# --- Interfaz de Usuario ---
st.title("🔄 Arbitraje BNC ➔ Binance")
st.markdown("Calculadora P2P optimizada con filtros de capital fidedignos.")

# --- Panel Lateral ---
st.sidebar.header("⚙️ Configuración")
modo_automatico = st.sidebar.toggle("Tasas automáticas en vivo", value=True)

st.sidebar.divider()

# PRIORIDAD PRINCIPAL: Monto a Invertir
st.sidebar.header("💰 Inversión")
inversion = st.sidebar.number_input("Monto a Inyectar ($)", value=20.0, step=10.0, format="%.2f")

st.sidebar.divider()

# SECUNDARIO: Tasas de Cambio
st.sidebar.header("📊 Tasas de Cambio")

if modo_automatico:
    tasa_bcv_actual = obtener_tasa_bcv()
    
    # Proyección fidedigna de tasa USDT (BCV * 1.12 aproximadamente) para calcular el monto en Bs.
    tasa_usdt_proyectada = tasa_bcv_actual * 1.12
    tasa_binance_actual = obtener_tasa_binance(inversion, tasa_usdt_proyectada)
    
    st.sidebar.success(f"✅ Actualizado a las {datetime.datetime.now().strftime('%H:%M')}")
else:
    tasa_bcv_actual = 756.71
    tasa_binance_actual = 849.71 
    st.sidebar.warning("⚠️ Modo Manual Activo")

tasa_bcv = st.sidebar.number_input("Tasa BCV (Bs/$)", value=tasa_bcv_actual, step=1.00, format="%.2f", disabled=modo_automatico)
tasa_binance = st.sidebar.number_input("Tasa Venta Binance (Bs/$)", value=tasa_binance_actual, step=1.00, format="%.2f", disabled=modo_automatico)

# --- Cálculos Matemáticos ---
bs_compra = tasa_bcv * (1 + TOTAL_COMISIONES)

costo_total_bs = inversion * bs_compra
ingreso_total_bs = inversion * tasa_binance
profit_total_bs = ingreso_total_bs - costo_total_bs

# Ganancia en USDT basada estrictamente en la Tasa de Venta de Binance
profit_total_usd_binance = profit_total_bs / tasa_binance if tasa_binance > 0 else 0

# Rendimiento relativo al ingreso total de la venta
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
