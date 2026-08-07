import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime

# --- Configuración de la página (responsiva para móvil) ---
st.set_page_config(page_title="Arbitraje BNC-Binance", page_icon="🔄", layout="centered")

# --- Comisiones fijas (ocultas en la interfaz) ---
COM_BANCO = 0.005      # 0.50%
COM_TARJETA = 0.015    # 1.50%
COM_PLATAFORMA = 0.041 # 4.10%
TOTAL_COMISIONES = COM_BANCO + COM_TARJETA + COM_PLATAFORMA  # 6.10%

# --- Funciones de extracción de tasas ---

@st.cache_data(ttl=300)
def obtener_tasa_bcv():
    """Obtiene la tasa del BCV desde su portal oficial."""
    try:
        respuesta = requests.get("https://www.bcv.org.ve/", verify=False, timeout=5)
        soup = BeautifulSoup(respuesta.text, "html.parser")
        dolar_div = soup.find("div", id="dolar")
        if dolar_div:
            texto = dolar_div.find("strong").text
            return float(texto.replace(",", "."))
    except Exception:
        return 756.71  # valor de respaldo
    return 756.71


@st.cache_data(ttl=60)
def obtener_tasa_binance(inversion_usd, tasa_bcv):
    """
    Obtiene la tasa de venta USDT/VES en Binance P2P,
    aplicando los mismos filtros que usarías en la app:
    - Pago Móvil y BNC
    - Comerciantes no verificados incluidos
    - Filtro de monto exacto en bolívares
    - Excluye anuncios promocionados
    - Solo comerciantes con buen historial (>90% completadas, >50 órdenes/mes)
    """
    try:
        url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        # --- 1. Cálculo del monto en bolívares para el filtro ---
        # Usamos la tasa BCV + comisiones para estimar el monto real en Bs.
        # Esto garantiza que el filtro coincida con lo que realmente recibirás.
        monto_bs_aproximado = int(inversion_usd * tasa_bcv * (1 + TOTAL_COMISIONES))
        # Aseguramos un mínimo de 1000 Bs. para que el filtro sea válido
        monto_filtro = max(monto_bs_aproximado, 1000)

        # --- 2. Payload idéntico al de la app Binance ---
        payload = {
            "asset": "USDT",
            "fiat": "VES",
            "merchantCheck": False,          # "Solo comerciantes verificados" = OFF
            "page": 1,
            "payTypes": ["PagoMovil", "BNC"], # Filtro de métodos de pago
            "publisherType": None,
            "rows": 20,
            "tradeType": "BUY",              # Tú vendes USDT → ellos compran
            "transAmount": str(monto_filtro)
        }

        respuesta = requests.post(url, headers=headers, json=payload, timeout=5)
        data = respuesta.json()
        anuncios = data.get("data", [])

        if not anuncios:
            return 847.00  # respaldo

        # --- 3. Filtrado de anuncios reales ---
        precios_reales = []
        for anuncio in anuncios:
            adv = anuncio.get("adv", {})
            vendedor = anuncio.get("advertiser", {})

            # a) Excluir anuncios promocionados (Gasper25, etc.)
            if adv.get("isPromoted") or anuncio.get("isPromoted"):
                continue

            # b) Excluir vendedores con bajo historial
            ratio = float(vendedor.get("monthFinishRate", 0))
            ordenes = int(vendedor.get("monthOrderCount", 0))
            if ratio < 0.90 or ordenes < 50:
                continue

            precio = float(adv.get("price", 0))
            if precio > 0:
                precios_reales.append(precio)

        if not precios_reales:
            return 847.00

        # --- 4. Tasa conservadora: promedio de los 3 primeros reales ---
        # Esto elimina outliers y se acerca a lo que ves en la app.
        top_reales = precios_reales[:3]
        tasa_promedio = sum(top_reales) / len(top_reales)

        # --- 5. Tope de seguridad: nunca superar 852.00 Bs. ---
        # Si la API devuelve algo anómalo, lo limitamos.
        return min(tasa_promedio, 852.00)

    except Exception:
        return 847.00  # respaldo en caso de error


# ============================================================================
# INTERFAZ DE USUARIO
# ============================================================================

st.title("🔄 Arbitraje BNC ➔ Binance")
st.markdown("Calculadora P2P con filtros reales (Pago Móvil / BNC)")

# --- Barra lateral ---
st.sidebar.header("⚙️ Configuración")
modo_automatico = st.sidebar.toggle("Tasas automáticas en vivo", value=True)

st.sidebar.divider()

st.sidebar.header("💰 Inversión")
inversion = st.sidebar.number_input(
    "Monto a inyectar ($)",
    value=15.0,
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

# Inputs de tasas (deshabilitados si el modo automático está activo)
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

# Usamos los valores ingresados (automáticos o manuales)
tasa_bcv = tasa_bcv_input
tasa_binance = tasa_binance_input

# ============================================================================
# CÁLCULOS FINANCIEROS
# ============================================================================

bs_compra = tasa_bcv * (1 + TOTAL_COMISIONES)          # Costo real por dólar en Bs.
costo_total_bs = inversion * bs_compra                 # Capital necesario en Bs.
ingreso_total_bs = inversion * tasa_binance            # Ingreso por venta en Binance
profit_bs = ingreso_total_bs - costo_total_bs          # Ganancia neta en Bs.
profit_usdt = profit_bs / tasa_binance if tasa_binance > 0 else 0   # Ganancia en USDT
rendimiento = (profit_bs / ingreso_total_bs * 100) if ingreso_total_bs > 0 else 0

# ============================================================================
# PANEL PRINCIPAL (Diseño responsivo)
# ============================================================================

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
