import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Sistema Integral de Rifas - APRID",
    page_icon="🎟️",
    layout="wide"
)

# --- CONFIGURACIÓN DE NEGOCIO ---
VALOR_CUOTA = 4000
CANT_CUOTAS = 10
VALOR_TOTAL = VALOR_CUOTA * CANT_CUOTAS  # 40000
COMISION_VENTA_PCT = 0.10
COMISION_COBRANZA_PCT = 0.20

# --- CONEXIÓN A BASE DE DATOS SEGURA (SQLite) ---
def init_db():
    conn = sqlite3.connect('rifas_aprid.db', check_same_thread=False)
    cursor = conn.cursor()
    # Tabla de Transacciones (Ventas y Cuotas)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transacciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            numero_rifa INTEGER,
            es_primer_pago TEXT,
            participante TEXT,
            telefono TEXT,
            monto REAL,
            vendedor TEXT
        )
    ''')
    # Tabla de Rendiciones a Caja Central
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rendiciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            cobrador TEXT,
            monto_rendido REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def run_query(query, params=()):
    conn = sqlite3.connect('rifas_aprid.db', check_same_thread=False)
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def execute_db(query, params=()):
    conn = sqlite3.connect('rifas_aprid.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()

# --- INTERFAZ LATERAL (MENÚ) ---
st.sidebar.title("🧭 Panel de Control")
menu = st.sidebar.selectbox(
    "Seleccionar Módulo",
    ["1. Registrar Transacción (Calle)", "2. Estado de Cartones y Auditoría", "3. Liquidación de Vendedores", "4. Caja y Rendiciones", "5. Sorteos (Ganadores)", "6. Dashboard Visual"]
)

# ==========================================
# MÓDULO 1: REGISTRO DE TRANSACCIONES (FORMULARIO)
# ==========================================
if menu == "1. Registrar Transacción (Calle)":
    st.title("📝 Carga de Operaciones en Campo")
    st.markdown("Registre la venta inicial o el cobro de cuotas subsiguientes.")

    with st.form("form_transaccion", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            num_rifa = st.number_input("Número de Rifa", min_value=1, max_value=500, step=1)
            es_primer_pago = st.selectbox("¿Es el primer pago que realiza este adquirente?", ["No (Cuota subsiguiente)", "Sí (Primer pago / Venta)"])
            
        with col2:
            # Lista de promotores / cobradores (Incluyendo miembros de comisión etiquetados)
            lista_vendedores = [
                "JORGE SANCHEZ", "LUCIA RUBINO", "NESTOR ALCOBA", "AYELEN", "FABIAN QUIROGA",
                "Sonia Coche (Comisión)", "Ofelia (Comisión)", "Sergio Ferraro (Comisión)", 
                "Bianchi (Comisión)", "Ariel (Comisión)", "Romina (Comisión)"
            ]
            vendedor = st.selectbox("Promotor / Cobrador", lista_vendedores)
            monto_cobrado = st.number_input("Monto Cobrado ($)", min_value=100.0, max_value=float(VALOR_TOTAL), step=500.0)

        # Datos adicionales solo si es primer pago
        participante = ""
        telefono = ""
        if "Sí" in es_primer_pago:
            st.markdown("---")
            st.subheader("Datos del Nuevo Adquirente")
            c3, c4 = st.columns(2)
            with c3:
                participante = st.text_input("Nombre y Apellido del Participante")
            with c4:
                telefono = st.text_input("Teléfono de Contacto")

        submit = st.form_submit_button("💾 Guardar Transacción")

        if submit:
            is_first = "SI" if "Sí" in es_primer_pago else "NO"
            if is_first == "SI" and not participante.strip():
                st.error("⚠️ Error: Debe ingresar el nombre del participante para una venta nueva.")
            else:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                execute_db(
                    "INSERT INTO transacciones (timestamp, numero_rifa, es_primer_pago, participante, telefono, monto, vendedor) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (timestamp, int(num_rifa), is_first, participante.upper(), telefono, float(monto_cobrado), vendedor)
                 खातों = True
                st.success(f"✅ ¡Transacción registrada con éxito para la Rifa N° {num_rifa}!")

# ==========================================
# MÓDULO 2: ESTADO DE CARTONES Y AUDITORÍA
# ==========================================
elif menu == "2. Estado de Cartones y Auditoría":
    st.title("📊 Control de Cartera y Alertas de Auditoría")
    
    df_tx = run_query("SELECT * FROM transacciones")
    
    if df_tx.empty:
        st.info("Aún no hay transacciones registradas.")
    else:
        # Consolidar por Rifa
        rifas_unicas = sorted(df_tx['numero_rifa'].unique())
        resumen_rifas = []
        
        for r in rifas_unicas:
            df_r = df_tx[df_tx['numero_rifa'] == r]
            
            # Obtener datos del primer pago
            df_first = df_r[df_r['es_primer_pago'] == 'SI']
            part = df_first['participante'].iloc[0] if not df_first.empty else "SIN REGISTRO DE DUEÑO"
            tel = df_first['telefono'].iloc[0] if not df_first.empty else ""
            vend = df_first['vendedor'].iloc[0] if not df_first.empty else "DESCONOCIDO"
            
            total_pagado = df_r['monto'].sum()
            saldo_pendiente = max(0, VALOR_TOTAL - total_pagado)
            
            # Estado
            if total_pagado >= VALOR_TOTAL:
                estado = "PAGADO"
            elif total_pagado > 0:
                estado = "PARCIAL"
            else:
                estado = "PENDIENTE"
                
            # Obsequio 2 cuotas (Pagó >= 8000 en el primer pago exacto)
            primer_monto = df_first['monto'].sum() if not df_first.empty else 0
            obsequio_2c = "SI" if not df_first.empty and primer_monto >= (VALOR_CUOTA * 2) else "NO"
            
            # Obsequio Contado
            obsequio_contado = "SI" if total_pagado >= VALOR_TOTAL and not df_first.empty and primer_monto >= VALOR_TOTAL else "NO"

            # Auditoría / Alertas
            cant_primer_pago = len(df_first)
            if cant_primer_pago > 1:
                alerta = "⚠️ ALERTA: DOBLE VENTA"
            elif total_pagado > VALOR_TOTAL:
                alerta = "⚠️ ALERTA: EXCESO DE PAGO"
            elif total_pagado > 0 and df_first.empty:
                alerta = "⚠️ ALERTA: COBRO SIN DUEÑO"
            else:
                alerta = "OK"

            resumen_rifas.append({
                "N° Rifa": r,
                "Participante": part,
                "Teléfono": tel,
                "Vendedor": vend,
                "Total Pagado": total_pagado,
                "Saldo Pendiente": saldo_pendiente,
                "Estado": estado,
                "Obsequio 2 Cuotas": obsequio_2c,
                "Obsequio Contado": obsequio_contado,
                "Auditoría": alerta
            })
            
        df_resumen = pd.DataFrame(resumen_rifas)
        
        # Filtro de alertas
        filtro_alerta = st.selectbox("Filtrar por Estado de Auditoría", ["Todos", "Solo con Alertas", "OK"])
        if filtro_alerta == "Solo con Alertas":
            df_resumen = df_resumen[df_resumen['Auditoría'] != "OK"]
        elif filtro_alerta == "OK":
            df_resumen = df_resumen[df_resumen['Auditoría'] == "OK"]
            
        st.dataframe(df_resumen, use_container_width=True)

# ==========================================
# MÓDULO 3: LIQUIDACIÓN DE VENDEDORES
# ==========================================
elif menu == "3. Liquidación Vendedores":
    st.title("💰 Liquidación de Comisiones")
    st.markdown("Cálculo automático: 10% por venta ($4.000 fijos por cartón colocado) y 20% por cobranza de cuotas.")

    df_tx = run_query("SELECT * FROM transacciones")
    if not df_tx.empty:
        # Calcular columnas auxiliares para cada transacción
        # Base Venta (10%): min(monto, 4000) si es primer pago, sino 0
        # Base Cuotas (20%): max(0, monto - 4000) si es primer pago, sino monto
        
        def calc_bases(row):
            if row['es_primer_pago'] == 'SI':
                v = min(row['monto'], VALOR_CUOTA)
                c = max(0.0, row['monto'] - VALOR_CUOTA)
            else:
                v = 0.0
                c = row['monto']
            return pd.Series([v, c])

        df_tx[['base_venta', 'base_cuotas']] = df_tx.apply(calc_bases, axis=1)
        
        # Agrupar por vendedor
        vendedores_unicos = df_tx['vendedor'].unique()
        liquidaciones = []
        
        for v in vendedores_unicos:
            df_v = df_tx[df_tx['vendedor'] == v]
            rifas_vendidas = len(df_v[df_v['es_primer_pago'] == 'SI'])
            total_recaudado = df_v['monto'].sum()
            
            # Si es de la comisión, comisiones = 0
            es_comision = "(Comisión)" in v
            
            if es_comision:
                comision_venta = 0.0
                comision_cobranza = 0.0
            else:
                # Comision venta: 10% del total de la rifa (es decir, $4000 por cada base de venta recolectada)
                comision_venta = df_v['base_venta'].sum() * (COMISION_VENTA_PCT * 10) # 10% de 40000 = 4000
                comision_cobranza = df_v['base_cuotas'].sum() * COMISION_COBRANZA_PCT
                
            total_comisiones = comision_venta + comision_cobranza
            
            liquidaciones.append({
                "Vendedor": v,
                "Rifas Vendidas": rifas_vendidas,
                "Total Recaudado ($)": total_recaudado,
                "Comisión Venta (10%)": comision_venta,
                "Comisión Cobranza (20%)": comision_cobranza,
                "Total Comisiones a Pagar": total_comisiones
            })
            
        df_liq = pd.DataFrame(liquidaciones)
        st.dataframe(df_liq, use_container_width=True)
    else:
        st.info("No hay datos para liquidar.")

# ==========================================
# MÓDULO 4: CAJA Y RENDICIONES
# ==========================================
elif menu == "4. Caja y Rendiciones":
    st.title("🏛️ Caja Central - Control de Rendiciones (Jueves y Viernes)")
    
    col_reg, col_hist = st.columns([1, 2])
    
    with col_reg:
        st.subheader("Registrar Ingreso a Caja")
        with st.form("form_rendicion"):
            lista_cobradores = run_query("SELECT DISTINCT vendedor FROM transacciones")['vendedor'].tolist()
            if not lista_cobradores:
                lista_cobradores = ["JORGE SANCHEZ", "LUCIA RUBINO", "NESTOR ALCOBA"]
            cobrador_rend = st.selectbox("Cobrador / Responsable", lista_cobradores)
            monto_rend = st.number_input("Monto Entregado ($)", min_value=100.0, step=1000.0)
            btn_rend = st.form_submit_button("📥 Registrar Entrega")
            
            if btn_rend:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                execute_db("INSERT INTO rendiciones (timestamp, cobrador, monto_rendido) VALUES (?, ?, ?)", (ts, cobrador_rend, monto_rend))
                st.success(f"✅ Se registraron ${monto_rend:,.2f} entregados por {cobrador_rend}.")

    with col_hist:
        st.subheader("Estado de Cuentas por Cobrador")
        df_tx = run_query("SELECT * FROM transacciones")
        df_rend = run_query("SELECT * FROM rendiciones")
        
        if not df_tx.empty:
            def calc_b(row):
                if row['es_primer_pago'] == 'SI':
                    return max(0.0, row['monto'] - VALOR_CUOTA)
                return row['monto']
            df_tx['base_c'] = df_tx.apply(calc_b, axis=1)
            
            vendedores = df_tx['vendedor'].unique()
            tabla_rend = []
            
            for v in vendedores:
                df_v = df_tx[df_tx['vendedor'] == v]
                total_historico = df_v['monto'].sum()
                
                if "(Comisión)" in v:
                    comisiones = 0.0
                else:
                    cv = df_v[df_v['es_primer_pago'] == 'SI']['monto'].apply(lambda x: min(x, VALOR_CUOTA)).sum()
                    cc = df_v['base_c'].sum() * COMISION_COBRANZA_PCT
                    comisiones = cv + cc
                    
                deuda_total = total_historico - comisiones
                
                # Entregas previas
                entregas_previas = df_rend[df_rend['cobrador'] == v]['monto_rendido'].sum() if not df_rend.empty else 0.0
                saldo_hoy = deuda_total - entregas_previas
                
                tabla_rend.append({
                    "Cobrador": v,
                    "Total Calle ($)": total_historico,
                    "Comisiones ($)": comisiones,
                    "Deuda Neta ($)": deuda_total,
                    "Ya Rendido ($)": entregas_previas,
                    "SALDO A RENDIR HOY ($)": saldo_hoy
                })
                
            st.dataframe(pd.DataFrame(tabla_rend), use_container_width=True)
            
            st.markdown("---")
            st.subheader("Historial de Transacciones en Caja (`Log_Rendiciones`)")
            if not df_rend.empty:
                st.dataframe(df_rend, use_container_width=True)
            else:
                st.info("No hay rendiciones registradas todavía.")

# ==========================================
# MÓDULO 5: SORTEOS (GANADORES)
# ==========================================
elif menu == "5. Sorteos (Ganadores)":
    st.title("🎟️ Listados Oficiales para Sorteos")
    
    df_tx = run_query("SELECT * FROM transacciones")
    if not df_tx.empty:
        rifas_unicas = df_tx['numero_rifa'].unique()
        aptos_2c = []
        aptos_contado = []
        
        for r in rifas_unicas:
            df_r = df_tx[df_tx['numero_rifa'] == r]
            df_first = df_r[df_r['es_primer_pago'] == 'SI']
            
            if not df_first.empty:
                part = df_first['participante'].iloc[0]
                tel = df_first['telefono'].iloc[0]
                primer_monto = df_first['monto'].sum()
                total_pagado = df_r['monto'].sum()
                
                # Regla 2 cuotas: Pagó >= 8000 en el primer pago
                if primer_monto >= (VALOR_CUOTA * 2):
                    aptos_2c.append({"N° Rifa": r, "Participante": part, "Teléfono": tel})
                    
                # Regla Contado: Pagó el total de 40000 de contado en el primer pago
                if total_pagado >= VALOR_TOTAL and primer_monto >= VALOR_TOTAL:
                    aptos_contado.append({"N° Rifa": r, "Participante": part, "Teléfono": tel})
                    
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.subheader("🌟 Aptos: Sorteo 2 Cuotas Juntas")
            if aptos_2c:
                st.dataframe(pd.DataFrame(aptos_2c), use_container_width=True)
            else:
                st.info("Aún no hay participantes aptos.")
                
        with col_s2:
            st.subheader("💎 Aptos: Sorteo Pago Contado")
            if aptos_contado:
                st.dataframe(pd.DataFrame(aptos_contado), use_container_width=True)
            else:
                st.info("Aún no hay participantes aptos.")
    else:
        st.info("No hay datos cargados.")

# ==========================================
# MÓDULO 6: DASHBOARD VISUAL
# ==========================================
elif menu == "6. Dashboard Visual":
    st.title("📈 Tablero de Comando Ejecutivo")
    
    df_tx = run_query("SELECT * FROM transacciones")
    if not df_tx.empty:
        total_recaudado_gral = df_tx['monto'].sum()
        meta_total = len(df_tx['numero_rifa'].unique()) * VALOR_TOTAL
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Dinero Recaudado en Calle", f"${total_recaudado_gral:,.2f}")
        col_m2.metric("Total de Operaciones Registradas", len(df_tx))
        col_m3.metric("Promotores Activos", len(df_tx['vendedor'].unique()))
        
        st.markdown("---")
        
        c_g1, c_g2 = st.columns(2)
        with c_g1:
            st.subheader("Recaudación por Vendedor")
            df_vend_sum = df_tx.groupby('vendedor')['monto'].sum().reset_index()
            fig_vend = px.bar(df_vend_sum, x='vendedor', y='monto', title="Ingresos Totales por Cobrador", text_auto='$,.0f')
            st.plotly_chart(fig_vend, use_container_width=True)
            
        with c_g2:
            st.subheader("Distribución de Pagos (Primer Pago vs Cuotas)")
            df_tipo = df_tx.groupby('es_primer_pago')['monto'].sum().reset_index()
            fig_tipo = px.pie(df_tipo, names='es_primer_pago', values='monto', title="Proporción Ingresos Iniciales vs Cuotas", hole=0.4)
            st.plotly_chart(fig_tipo, use_container_width=True)
    else:
        st.info("No hay datos suficientes para mostrar gráficos.")
