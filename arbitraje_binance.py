import streamlit as st
import requests
from bs4 import BeautifulSoup
import datetime
import re
import statistics

st.set_page_config(page_title="Arbitraje BNC-Binance", page_icon="🔄", layout="centered")

# Comisiones fijas (ocultas)
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

@st.cache_data(ttl=30)  # Actualiza cada 30 segundos para ser más reactivo
def obtener_tasa_binance(inversion_usd, tasa_bcv):
    try:
        url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        headers = {"Content-Type": "application/json"}

        # Monto en Bs. con comisiones para el filtro transAmount
        monto_bs = int(inversion_usd * tasa_bcv * (1 + TOTAL_COMISIONES))
        monto_filtro = max(monto_bs, 1000)

        payload = {
            "asset": "USDT",
            "fiat": "VES",
            "merchantCheck": False,
            "page": 1,
            "payTypes": ["PagoMovil"],  # Solo Pago Móvil
            "publisherType": None,
            "rows": 100,  # Más anuncios para tener mejor muestra
            "tradeType": "BUY",
            "transAmount": str(monto_filtro)
        }

        r = requests.post(url, headers=headers, json=payload, timeout=5)
        data = r.json()
        anuncios = data.get('data', [])

        if not anuncios:
            return 847.00  # respaldo

        # --- Filtrar anuncios válidos ---
        validos = []
        for ad in anuncios:
            adv = ad.get('adv', {})
            # Excluir promocionados
            if adv.get('isPromoted') or ad.get('isPromoted'):
                continue

            # Verificar que acepte Pago Móvil (por si la API no filtra bien)
            pay_types = adv.get('payTypes', [])
            texto_pagos = ' '.join(pay_types).lower()
            if not re.search(r'pago\s*movil', texto_pagos):
                continue

            precio = float(adv.get('price', 0))
            if precio <= 0:
                continue

            # Obtener el monto máximo de la orden (para ponderar)
            max_amount = float(adv.get('maxSingleTransAmount', 0))
            if max_amount == 0:
                max_amount = 1  # Si no tiene límite, le damos un peso pequeño

            validos.append({
                'precio': precio,
                'max_amount': max_amount
            })

        if not validos:
            # Si no hay con Pago Móvil, tomar el primer no promocionado (cualquier método)
            for ad in anuncios:
                adv = ad.get('adv', {})
                if not (adv.get('isPromoted') or ad.get('isPromoted')):
                    precio = float(adv.get('price', 0))
                    if precio > 0:
                        return precio
            return 847.00

        # --- Ordenar por precio (ascendente) ---
        validos.sort(key=lambda x: x['precio'])

        # Tomar los 10 mejores precios (para evitar outliers muy bajos)
        top = validos[:10]

        # --- Promedio ponderado por el monto máximo ---
        # Los anuncios con mayor capacidad de transacción tienen más peso
        total_peso = sum(item['max_amount'] for item in top)
        if total_peso == 0:
            total_peso = len(top)

        promedio_ponderado = sum(item['precio'] * item['max_amount'] for item in top) / total_peso

        # Redondear a 2 decimales
        return round(promedio_ponderado, 2)

    except Exception:
        return 847.00


# --- Interfaz de usuario ---
st.title("🔄 Arbitraje BNC ➔ Binance")
st.markdown("Tasa P2P real con Pago Móvil y promedio ponderado por liquidez")

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
