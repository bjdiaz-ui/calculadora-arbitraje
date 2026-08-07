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
    return 756.71

@st.cache_data(ttl=60)
def obtener_tasa_binance(inversion_usd, tasa_bcv):
    try:
        url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        # Monto estimado en Bs. que recibirás (con comisiones)
        monto_bs_estimado = int(inversion_usd * tasa_bcv * (1 + TOTAL_COMISIONES))
        # Aseguramos un mínimo de 1000 Bs. para que el filtro tenga sentido
        monto_filtro = max(monto_bs_estimado, 1000)

        payload = {
            "asset": "USDT",
            "fiat": "VES",
            "merchantCheck": False,
            "page": 1,
            "payTypes": ["PagoMovil", "BNC"],
            "publisherType": None,
            "rows": 20,
            "tradeType": "BUY",
            "transAmount": str(monto_filtro)
        }

        respuesta = requests.post(url, headers=headers, json=payload, timeout=5)
        data = respuesta.json()
        anuncios = data.get('data', [])

        if not anuncios:
            return 847.00  # respaldo

        # Filtramos anuncios reales (no promocionados, con buen historial, y que acepten PagoMovil o BNC)
        precios_reales = []
        for anuncio in anuncios:
            adv = anuncio.get('adv', {})
            vendedor = anuncio.get('advertiser', {})

            # Excluir promocionados
            if adv.get('isPromoted') or anuncio.get('isPromoted'):
                continue

            # Verificar que el método de pago esté en la lista de aceptados (por si la API no filtró bien)
            pay_types = adv.get('payTypes', [])
            if not any(p in ["PagoMovil", "BNC"] for p in pay_types):
                continue

            # Excluir vendedores con bajo historial
            ratio = float(vendedor.get('monthFinishRate', 0))
            ordenes = int(vendedor.get('monthOrderCount', 0))
            if ratio < 0.90 or ordenes < 50:
                continue

            # Verificar que el monto de la transacción esté dentro del rango del anuncio
            min_amount = float(adv.get('minSingleTransAmount', 0))
            max_amount = float(adv.get('maxSingleTransAmount', 0))
            if min_amount > monto_bs_estimado or max_amount < monto_bs_estimado:
                continue  # este anuncio no acepta nuestro monto

            precio = float(adv.get('price', 0))
            if precio > 0:
                precios_reales.append(precio)

        if not precios_reales:
            # Si no encontramos ninguno con todos los filtros, tomamos el primero que no sea promocionado
            for anuncio in anuncios:
                adv = anuncio.get('adv', {})
                if not (adv.get('isPromoted') or anuncio.get('isPromoted')):
                    precio = float(adv.get('price', 0))
                    if precio > 0:
                        precios_reales.append(precio)
                        break

        if not precios_reales:
            return 847.00

        # Tomamos el promedio de los 3 primeros reales (sin tope)
        tasa_final = sum(precios_reales[:3]) / len(precios_reales[:3])
        return tasa_final

    except Exception:
        return 847.00


# --- Interfaz de Usuario ---
st.title("🔄 Arbitraje BNC ➔ Binance")
st.markdown("Calculadora P2P con filtros reales (Pago Móvil / BNC)")

st.sidebar.header("⚙️ Configuración")
modo_automatico = st.sidebar.toggle("Tasas automáticas en vivo", value=True)

st.sidebar.divider()

st.sidebar.header("💰 Inversión")
inversion = st.sidebar.number_input(
    "Monto a inyectar ($)",
    value=40.0,
    step=5.0,
    min_value=1.0,
    format="%.2f"
)

st.sidebar.divider()

st.sidebar.header("📊 Tasas de cambio")

if modo_automatico:
    tasa_bcv = obtener_tasa_bcv()
    tasa_binance = obtener_tasa_binance(inversion, tasa_bcv)
    st.sidebar.success(f"✅ Actualizado a las {datetime.datetime.now().strftime('%H:%M:%S')}")
else:
    tasa_bcv = 756.71
    tasa_binance = 847.00
    st.sidebar.warning("⚠️ Modo manual activo")

tasa_bcv_input = st.sidebar.number_input(
    "Tasa BCV (Bs/$)",
    value=tasa_bcv,
    step=1.00,
    format="%.2f",
    disabled=modo_automatico
)

tasa_binance_input = st.sidebar.number_input(
    "Tasa venta Binance (Bs/$)",
    value=tasa_binance,
    step=0.10,
    format="%.2f",
    disabled=modo_automatico
)

tasa_bcv = tasa_bcv_input
tasa_binance = tasa_binance_input

# --- Cálculos ---
bs_compra = tasa_bcv * (1 + TOTAL_COMISIONES)
costo_total_bs = inversion * bs_compra
ingreso_total_bs = inversion * tasa_binance
profit_bs = ingreso_total_bs - costo_total_bs
profit_usdt = profit_bs / tasa_binance if tasa_binance > 0 else 0
rendimiento = (profit_bs / ingreso_total_bs * 100) if ingreso_total_bs > 0 else 0

# --- Dashboard ---
st.subheader("📋 Desglose operativo")
col1, col2 = st.columns(2)
col1.metric("Costo real por $ (Bs.)", f"Bs. {bs_compra:,.2f}")
col2.metric("Comisiones aplicadas", f"{TOTAL_COMISIONES * 100:.2f}%")

st.divider()

st.subheader("📊 Resultados del ciclo")
col3, col4 = st.columns(2)
col3.metric("Capital a descontar (BNC)", f"Bs. {costo_total_bs:,.2f}")
col4.metric("Ingreso por venta (Binance)", f"Bs. {ingreso_total_bs:,.2f}")

st.write("")

if profit_bs > 0:
    st.success(f"""
    ### 🎉 Operación rentable
    **Ganancia neta:** Bs. {profit_bs:,.2f}  
    **Ganancia líquida:** {profit_usdt:,.2f} USDT  
    **Rendimiento del ciclo:** {rendimiento:,.2f}%
    """)
else:
    st.error(f"""
    ### ⚠️ Operación a pérdida
    **Pérdida neta:** Bs. {profit_bs:,.2f}  
    No se recomienda inyectar capital en este momento.
    """)
