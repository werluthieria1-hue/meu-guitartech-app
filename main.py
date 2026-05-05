import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF
import urllib.parse
import io
from PIL import Image

st.set_page_config(page_title="GuitarTech ERP", layout="wide")

# --- CONFIGURAÇÕES ---
NOME_OFICINA = "WILLIAN REGES GUITAR TECH"
TELEFONE = "(66) 99944-7355"

# --- BANCO DE DADOS ATUALIZADO ---
def iniciar_db():
    conn = sqlite3.connect('oficina.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ordens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente TEXT, instrumento TEXT, servico_nome TEXT, 
                    descricao_detalhada TEXT, total REAL, entrada REAL, 
                    status TEXT, data_entrada DATE, data_entrega DATE,
                    forma_pagto TEXT, acessorio TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS catalogo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT, preco REAL, descricao_base TEXT)''')
    conn.commit()
    conn.close()

iniciar_db()

# --- FUNÇÃO DO PDF ---
def gerar_pdf_os(dados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"ORDEM DE SERVIÇO - {dados['status'].upper()}", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Cliente: {dados['cliente']} | OS: #{dados['id']}", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 8, f"Instrumento: {dados['instrumento']}", ln=True)
    pdf.cell(0, 8, f"Acessório: {dados['acessorio']}", ln=True)
    pdf.cell(0, 8, f"Previsão de Entrega: {dados['data_entrega']}", ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, "DESCRIÇÃO DO SERVIÇO", fill=False, ln=True)
    pdf.set_font("Arial", size=10)
    desc = dados['descricao_detalhada'].encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 7, desc)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, "FINANCEIRO", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 8, f"Total: R$ {dados['total']:.2f}", ln=True)
    pdf.cell(0, 8, f"Entrada: R$ {dados['entrada']:.2f} ({dados['forma_pagto']})", ln=True)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"SALDO PENDENTE: R$ {dados['total'] - dados['entrada']:.2f}", ln=True)
    
    return bytes(pdf.output(dest='S'))

# --- INTERFACE ---
st.title("🎸 GuitarTech ERP")

abas = st.tabs(["📄 Orçamentos", "⚙️ Faturar OS", "🛠️ Produção", "💰 Caixa", "⚙️ Catálogo"])

# 1. ABA DE ORÇAMENTOS (SEM FINANCEIRO AINDA)
with abas[0]:
    st.header("Novo Orçamento")
    conn = sqlite3.connect('oficina.db')
    cat = pd.read_sql_query("SELECT * FROM catalogo", conn)
    conn.close()

    with st.form("form_orc"):
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Cliente")
        instrumento = c2.text_input("Instrumento")
        servico = st.selectbox("Tipo de Serviço", cat['nome'].tolist() if not cat.empty else ["Cadastre primeiro"])
        
        dados_cat = cat[cat['nome'] == servico]
        preco_base = float(dados_cat['preco'].iloc[0]) if not dados_cat.empty else 0.0
        desc_base = dados_cat['descricao_base'].iloc[0] if not dados_cat.empty else ""
        
        detalhes = st.text_area("Observações do Orçamento", value=desc_base)
        valor = st.number_input("Valor Estimado (R$)", value=preco_base)
        
        if st.form_submit_button("Salvar Orçamento"):
            conn = sqlite3.connect('oficina.db')
            conn.execute("INSERT INTO ordens (cliente, instrumento, servico_nome, descricao_detalhada, total, entrada, status, data_entrada) VALUES (?,?,?,?,?,?,?,?)",
                      (cliente, instrumento, servico, detalhes, valor, 0, 'Orçamento', datetime.now().date()))
            conn.commit()
            conn.close()
            st.success("Orçamento salvo! Vá em 'Faturar' quando o cliente aprovar.")

# 2. ABA DE FATURAMENTO (TRANSFORMA ORÇAMENTO EM OS)
with abas[1]:
    st.header("Faturar Orçamento")
    conn = sqlite3.connect('oficina.db')
    pendentes = pd.read_sql_query("SELECT id, cliente, instrumento FROM ordens WHERE status='Orçamento'", conn)
    conn.close()

    if not pendentes.empty:
        escolha_id = st.selectbox("Selecione o Orçamento para Aprovar", pendentes['id'].tolist(), format_func=lambda x: f"ID {x} - {pendentes[pendentes['id']==x]['cliente'].values[0]}")
        
        with st.expander("Dados de Faturamento e Recebimento"):
            data_ent = st.date_input("Data Prometida de Entrega")
            pagto = st.selectbox("Forma de Pagto da Entrada", ["Pix", "Cartão", "Dinheiro"])
            valor_ent = st.number_input("Valor da Entrada (Sinal)", min_value=0.0)
            
            st.subheader("Checklist e Fotos")
            tem_capa = st.checkbox("Instrumento ficou com Capa/Case?")
            
            foto_inst = st.camera_input("Foto do Instrumento")
            foto_capa = None
            if tem_capa:
                foto_capa = st.camera_input("Foto da Capa/Case")
            
            if st.button("Confirmar Faturamento"):
                conn = sqlite3.connect('oficina.db')
                conn.execute("UPDATE ordens SET status='Em Produção', data_entrega=?, forma_pagto=?, entrada=?, acessorio=? WHERE id=?",
                          (data_ent, pagto, valor_ent, "Com Capa" if tem_capa else "Sem Capa", escolha_id))
                conn.commit()
                conn.close()
                st.success("OS Faturada! Agora ela aparece na Produção e no Financeiro.")
                st.balloons()
    else:
        st.info("Não há orçamentos pendentes para faturar.")

# 3. ABA DE PRODUÇÃO (RELATÓRIO DIÁRIO)
with abas[2]:
    st.header("🛠️ Relatório de Produção")
    conn = sqlite3.connect('oficina.db')
    df_prod = pd.read_sql_query("SELECT id, cliente, instrumento, servico_nome, data_entrega, acessorio FROM ordens WHERE status='Em Produção' ORDER BY data_entrega", conn)
    conn.close()
    
    if not df_prod.empty:
        st.dataframe(df_prod, use_container_width=True)
        # Botão para gerar PDF da OS selecionada
        id_pdf = st.number_input("Digite o ID para gerar PDF da OS", min_value=1, step=1)
        if st.button("Gerar PDF da OS"):
            conn = sqlite3.connect('oficina.db')
            dados_os = pd.read_sql_query(f"SELECT * FROM ordens WHERE id={id_pdf}", conn).iloc[0]
            conn.close()
            pdf_bytes = gerar_pdf_os(dados_os)
            st.download_button("Baixar PDF da OS", pdf_bytes, file_name=f"OS_{id_pdf}.pdf")
    else:
        st.info("Bancada limpa!")

# FINANCEIRO E CATÁLOGO (Mantêm a lógica anterior)
with abas[3]:
    st.header("💰 Caixa")
    conn = sqlite3.connect('oficina.db')
    res = pd.read_sql_query("SELECT SUM(entrada) as e, SUM(total-entrada) as p FROM ordens WHERE status='Em Produção'", conn)
    conn.close()
    st.metric("Entradas Acumuladas", f"R$ {res['e'][0] or 0:.2f}")
    st.metric("Saldo a Receber na Entrega", f"R$ {res['p'][0] or 0:.2f}")

with abas[4]:
    st.header("⚙️ Catálogo de Serviços")
    with st.form("cad_novo"):
        n = st.text_input("Nome do Serviço")
        p = st.number_input("Preço")
        d = st.text_area("Descrição Padrão")
        if st.form_submit_button("Salvar"):
            conn = sqlite3.connect('oficina.db')
            conn.execute("INSERT INTO catalogo (nome, preco, descricao_base) VALUES (?,?,?)", (n, p, d))
            conn.commit()
            conn.close()
            st.rerun()
