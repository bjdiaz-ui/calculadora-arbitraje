import streamlit as st

# Configuración de la página
st.set_page_config(page_title="Calculadora Arbitraje BNC-Binance", layout="centered")

st.title("🔄 Calculadora de Arbitraje: BNC a Binance")
st.markdown("Calcula la rentabilidad esperada de tu ciclo de inyección de divisas.")

# --- Barra lateral para ingresar los datos (Inputs) ---
st.sidebar.header("📊 Tasas de Cambio")
tasa_bcv = st.sidebar.number_input("Tasa BCV (Bs/$)", value=755.90, step=1.00, format="%.2f")
tasa_binance = st.sidebar.number_input("Tasa Venta Binance USDT (Bs/$)", value=844.00, step=1.00, format="%.2f")

st.sidebar.header("💸 Comisiones (%)")
com_banco = st.sidebar.number_input("Intervención Bancaria (%)", value=0.50, step=0.10) / 100
com_tarjeta = st.sidebar.number_input("Uso de Tarjeta (%)", value=5.00, step=0.10) / 100
com_bpay = st.sidebar.number_input("Comisión Bpay/Zinli (%)", value=4.10, step=0.10) / 100

st.sidebar.header("💰 Inversión")
inversion = st.sidebar.number_input("Monto a Invertir ($)", value=500.0, step=50.0)

# --- Cálculos del Excel ---
total_comisiones = com_banco + com_tarjeta + com_bpay
bs_compra = tasa_bcv * (1 + total_comisiones)
profit_por_dolar = tasa_binance - bs_compra

costo_total_bs = inversion * bs_compra
ingreso_total_bs = inversion * tasa_binance
profit_total_bs = ingreso_total_bs - costo_total_bs
profit_total_usd = profit_total_bs / tasa_bcv if tasa_bcv > 0 else 0

# --- Resultados en Pantalla (Dashboard) ---
st.subheader("Desglose del Costo")
col_costo1, col_costo2 = st.columns(2)
col_costo1.metric("Total Comisiones Aplicadas", f"{total_comisiones * 100:.2f}%")
col_costo2.metric("Costo Real por $ (Bs. Compra)", f"Bs. {bs_compra:,.2f}")

st.divider()

st.subheader("Resultados de la Operación (Ciclo Completo)")
col_res1, col_res2 = st.columns(2)
col_res1.metric("Capital Inicial Necesario", f"Bs. {costo_total_bs:,.2f}")
col_res2.metric("Ingreso en P2P Binance", f"Bs. {ingreso_total_bs:,.2f}")

# Mostrar alerta de pérdida si el profit es negativo
if profit_total_bs > 0:
    st.success(f"### 🎉 Ganancia Neta: Bs. {profit_total_bs:,.2f}  |  $ {profit_total_usd:,.2f} (a tasa BCV)")
else:
    st.error(f"### ⚠️ Pérdida Neta: Bs. {profit_total_bs:,.2f}  |  $ {profit_total_usd:,.2f} (a tasa BCV). ¡No es rentable operar con estas tasas!")
