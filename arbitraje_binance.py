import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime

st.set_page_config(page_title="Arbitraje BNC-Binance", page_icon="🔄", layout="centered")

# Comisiones fijas
COM_BANCO = 0.005
COM_TARJETA = 0.015
COM_PLATAFORMA = 0.041
TOTAL_COMISIONES = COM_BANCO + COM_TARJETA + COM_PLATAFORMA

@st.cache_data(ttl=300)
def obtener_tasa_bcv():
    try:
        r = requests.get("https://www.bcv.org.ve/", verify=False, timeout=5)
        soup = BeautifulSoup(r.text, 'html.parser')
        dolar = soup.find('div', id='dolar')
        if dolar:
            texto = dolar.find('strong').text
            return float(texto.replace(',', '.'))
    except:
        return 756.71
    return 756.71

@st.cache_data(ttl=60)
def obtener_tasa_binance(inversion_usd, tasa_bcv):
    try:
        url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        headers = {"Content-Type": "application/json"}

        monto_bs = int(inversion_usd * tasa_bcv * (1 + TOTAL_COMISIONES))
        monto_filtro = max(monto_bs, 1000)

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

        r = requests.post(url, headers=headers, json=payload, timeout=5)
        data = r.json()
        anuncios = data.get('data', [])

        if not anuncios:
            return 847.00

        # --- FILTRO ESTRICTO ---
        for anuncio in anuncios:
            adv = anuncio.get('adv', {})
            vendedor = anuncio.get('advertiser', {})

            # 1. Descartar promocionados
            if adv.get('isPromoted') or anuncio.get('isPromoted'):
                continue

            # 2. Métodos de pago: normalizar y buscar "pago movil" o "bnc"
            pay_types = adv.get('payTypes', [])
            pay_types_lower = ' '.join(pay_types).lower()
            if not ('pago movil' in pay_types_lower or 'bnc' in pay_types_lower):
                continue

            # 3. Historial del vendedor
            ratio = float(vendedor.get('monthFinishRate', 0))
            ordenes = int(vendedor.get('monthOrderCount', 0))
            if ratio < 0.90 or ordenes < 50:
                continue

            # 4. Rango de monto (debe cubrir tu inversión en Bs.)
            min_amount = float(adv.get('minSingleTransAmount', 0))
            max_amount = float(adv.get('maxSingleTransAmount', 0))
            if not (min_amount <= monto_bs <= max_amount):
                continue

            # Si pasa todos los filtros, este es el primer anuncio real válido
            precio = float(adv.get('price', 0))
            if precio > 0:
                return precio

        # Si no se encontró ninguno, devolvemos el primer no promocionado como respaldo
        for anuncio in anuncios:
            adv = anuncio.get('adv', {})
            if not (adv.get('isPromoted') or anuncio.get('isPromoted')):
                precio = float(adv.get('price', 0))
                if precio > 0:
                    return precio

        return 847.00

    except Exception:
        return 847.00


# --- Interfaz ---
st.title("🔄 Arbitraje BNC ➔ Binance")
st.markdown("Tasa P2P real con filtros de Pago Móvil / BNC y rango de monto")

st.sidebar.header("⚙️ Configuración")
modo_auto = st.sidebar.toggle("Tasas automáticas en vivo", value=True)

st.sidebar.divider()
st.sidebar.header("💰 Inversión")
inversion = st.sidebar.number_input("Monto a inyectar ($)", value=40.0, step=5.0, min_value=1.0, format="%.2f")

st.sidebar.divider()
st.sidebar.header("📊 Tasas de cambio")

if modo_auto:
    tasa_bcv = obtener_tasa_bcv()
    tasa_binance = obtener_tasa_binance(inversion, tasa_bcv)
    st.sidebar.success(f"✅ Actualizado a las {datetime.datetime.now().strftime('%H:%M:%S')}")
else:
    tasa_bcv = 756.71
    tasa_binance = 847.00
    st.sidebar.warning("⚠️ Modo manual")

tasa_bcv = st.sidebar.number_input("Tasa BCV (Bs/$)", value=tasa_bcv, step=1.00, format="%.2f", disabled=modo_auto)
tasa_binance = st.sidebar.number_input("Tasa venta Binance (Bs/$)", value=tasa_binance, step=0.10, format="%.2f", disabled=modo_auto)

# Cálculos
bs_compra = tasa_bcv * (1 + TOTAL_COMISIONES)
costo_bs = inversion * bs_compra
ingreso_bs = inversion * tasa_binance
profit_bs = ingreso_bs - costo_bs
profit_usdt = profit_bs / tasa_binance if tasa_binance else 0
rendimiento = (profit_bs / ingreso_bs * 100) if ingreso_bs else 0

# Dashboard
st.subheader("📋 Desglose operativo")
c1, c2 = st.columns(2)
c1.metric("Costo real por $ (Bs.)", f"Bs. {bs_compra:,.2f}")
c2.metric("Comisiones aplicadas", f"{TOTAL_COMISIONES * 100:.2f}%")

st.divider()
st.subheader("📊 Resultados del ciclo")
c3, c4 = st.columns(2)
c3.metric("Capital a descontar (BNC)", f"Bs. {costo_bs:,.2f}")
c4.metric("Ingreso por venta (Binance)", f"Bs. {ingreso_bs:,.2f}")

st.write("")
if profit_bs > 0:
    st.success(f"""
    ### 🎉 Operación rentable
    **Ganancia neta:** Bs. {profit_bs:,.2f}  
    **Ganancia líquida:** {profit_usdt:,.2f} USDT  
    **Rendimiento:** {rendimiento:,.2f}%
    """)
else:
    st.error(f"""
    ### ⚠️ Operación a pérdida
    **Pérdida neta:** Bs. {profit_bs:,.2f}  
    No se recomienda inyectar.
    """)
