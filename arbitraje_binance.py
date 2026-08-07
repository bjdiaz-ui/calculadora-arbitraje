import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime

# --- Configuración de la página (Responsiva) ---
st.set_page_config(page_title="Arbitraje BNC-Binance", page_icon="🔄", layout="centered")

# --- Comisiones Fijas (Ocultas en UI, activas en matemática) ---
# Intervención (0.50%) + Tarjeta (1.50%) + Plataforma (4.10%) = 6.10%
COM_BANCO = 0.005
COM_TARJETA = 0.015
COM_PLATAFORMA = 0.041
TOTAL_COMISIONES = COM_BANCO + COM_TARJETA + COM_PLATAFORMA

# --- Funciones para obtener tasas automáticamente ---
@st.cache_data(ttl=300) # Se refresca cada 5 minutos
def obtener_tasa_bcv():
    try:
        # Se extrae del portal del BCV
        respuesta = requests.get("https://www.bcv.org.ve/", verify=False, timeout=5)
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        dolar_div = soup.find('div', id='dolar')
        if dolar_div:
            texto_dolar = dolar_div.find('strong').text
            return float(texto_dolar.replace(',', '.'))
    except:
        return 756.71 # Tasa de respaldo en caso de fallo de conexión

@st.cache_data(ttl=60) # Se refresca cada minuto para el P2P
def obtener_tasa_binance(monto_ves_estimado=None):
    try:
        url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        headers = {"Content-Type": "application/json"}
        
        # Parámetros: Tú vendes (TradeType BUY para el comerciante)
        data = {
            "fiat": "VES",
            "page": 1,
            "rows": 10,
            "tradeType": "BUY", 
            "asset": "USDT",
            "payTypes": [],
            "publisherType": None,
            "filterType": "all" 
        }
        
        # Filtramos por tu monto para asegurar que los límites de orden coincidan
        if monto_ves_estimado:
            # Convertimos a entero (string) para evitar problemas con la API
            data["transAmount"] = str(int(monto_ves_estimado))

        respuesta = requests.post(url, headers=headers, json=data, timeout=5)
        anuncios = respuesta.json().get('data', [])
        
        if not anuncios:
             return 850.00 # Respaldo

        # LÓGICA CONSERVADORA: Ignorar el primer anuncio (suele ser poco realista) 
        # y sacar un promedio de los siguientes 3 disponibles en la lista.
        if len(anuncios) >= 4:
             precios = [float(anuncio['adv']['price']) for anuncio in anuncios[1:4]]
             tasa_promedio_realista = sum(precios) / len(precios)
             return tasa_promedio_realista
        else:
             # Si el volumen es bajo y hay pocos anuncios, toma el que haya
             return float(anuncios[0]['adv']['price'])
            
    except:
        return 850.00 

# --- Interfaz de Usuario ---
st.title("🔄 Arbitraje BNC ➔ Binance")
st.markdown("Calculadora P2P con métricas conservadoras de mercado.")

# --- Panel Lateral ---
st.sidebar.header("⚙️ Configuración")
modo_automatico = st.sidebar.toggle("Tasas automáticas en vivo", value=True)

st.sidebar.divider()

# PRIORIDAD: Monto a Invertir
st.sidebar.header("💰 Inversión")
inversion = st.sidebar.number_input("Monto a Inyectar ($)", value=20.0, step=10.0, format="%.2f")

st.sidebar.divider()

# SECUNDARIO: Tasas de Cambio
st.sidebar.header("📊 Tasas de Cambio")

if modo_automatico:
    tasa_bcv_actual = obtener_tasa_bcv()
    
    # Calculamos el estimado de Bolívares para buscar la mejor tasa de ese rango exacto
    monto_fiat_estimado = inversion * (tasa_bcv_actual * 1.1) 
    tasa_binance_actual = obtener_tasa_binance(monto_fiat_estimado)
    
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

# Ganancia real en dólares (USDT líquidos) al finalizar la venta en P2P
profit_total_usd_binance = profit_total_bs / tasa_binance if tasa_binance > 0 else 0

# Rendimiento (Profit) basado en el monto total de la venta
if ingreso_total_bs > 0:
    margen_ganancia_porcentaje = (profit_total_bs / ingreso_total_bs) * 100
else:
    margen_ganancia_porcentaje = 0

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
    **Ganancia Neta (Líquido):** {profit_total_usd_binance:,.2f} USDT  
    **Rendimiento del Ciclo:** {margen_ganancia_porcentaje:,.2f}% 
    """)
else:
    st.error(f"""
    ### ⚠️ Operación a Pérdida
    **Pérdida Neta:** Bs. {profit_total_bs:,.2f}  
    No se recomienda inyectar capital en este momento.
    """)
