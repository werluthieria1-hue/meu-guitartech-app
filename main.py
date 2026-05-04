import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# Configuração para Mobile
st.set_page_config(page_title="GuitarTech Manager", layout="centered")

# --- BANCO DE DADOS ---
def iniciar_db():
    conn = sqlite3.connect('oficina.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ordens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente TEXT, instrumento TEXT, servico TEXT, 
                    total REAL, entrada REAL, status TEXT, data DATE)''')
    conn.commit()
    conn.close()

iniciar_db()

# --- INTERFACE ---
st.title("🎸 GuitarTech Manager")

aba1, aba2, aba3 = st.tabs(["📋 Nova OS", "🛠️ Produção", "💰 Financeiro"])

with aba1:
    st.header("Novo Orçamento")
    with st.form("os_form", clear_on_submit=True):
        cliente = st.text_input("Nome do Cliente")
        instrumento = st.text_input("Instrumento (Marca/Modelo)")
        servico = st.text_area("Descrição do Serviço")
        col1, col2 = st.columns(2)
        valor_total = col1.number_input("Valor Total (R$)", min_value=0.0)
        valor_entrada = col2.number_input("Entrada (R$)", min_value=0.0)
        
        data_entrega = st.date_input("Prazo de Entrega")
        
        submit = st.form_submit_button("Salvar e Gerar Orçamento")
        
        if submit:
            conn = sqlite3.connect('oficina.db')
            c = conn.cursor()
            c.execute("INSERT INTO ordens (cliente, instrumento, servico, total, entrada, status, data) VALUES (?,?,?,?,?,?,?)",
                      (cliente, instrumento, servico, valor_total, valor_entrada, 'Em Produção', data_entrega))
            conn.commit()
            conn.close()
            st.success(f"OS de {cliente} registrada!")
            st.balloons()

with aba2:
    st.header("🛠️ Serviços em Andamento")
    conn = sqlite3.connect('oficina.db')
    df = pd.read_sql_query("SELECT cliente, instrumento, total - entrada as saldo, data FROM ordens WHERE status = 'Em Produção'", conn)
    conn.close()
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhum serviço na bancada hoje.")

with aba3:
    st.header("💰 Resumo Financeiro")
    conn = sqlite3.connect('oficina.db')
    total_entrada = pd.read_sql_query("SELECT SUM(entrada) as total FROM ordens", conn)['total'][0] or 0
    total_pendente = pd.read_sql_query("SELECT SUM(total - entrada) as total FROM ordens", conn)['total'][0] or 0
    conn.close()
    
    st.metric("Total em Caixa (Entradas)", f"R$ {total_entrada:.2f}")
    st.metric("Total a Receber", f"R$ {total_pendente:.2f}")
