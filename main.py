import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF
import urllib.parse

st.set_page_config(page_title="GuitarTech ERP", layout="wide")

# --- BANCO DE DADOS ---
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
    pdf.cell(0, 10, f"ORDEM DE SERVICO - {dados['status'].upper()}", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Cliente: {dados['cliente']} | OS: #{dados['id']}", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 8, f"Instrumento: {dados['instrumento']}", ln=True)
    pdf.cell(0, 8, f"Acessorio: {dados['acessorio']}", ln=True)
    pdf.cell(0, 8, f"Entrega: {dados['data_entrega']}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, "DESCRICAO DO SERVICO", ln=True)
    pdf.set_font("Arial", size=10)
    desc = dados['descricao_detalhada'].encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 7, desc)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, f"Total: R$ {dados['total']:.2f} | Entrada: R$ {dados['entrada']:.2f}", ln=True)
    pdf.cell(0, 10, f"SALDO PENDENTE: R$ {dados['total'] - dados['entrada']:.2f}", ln=True)
    return bytes(pdf.output(dest='S'))

# --- INTERFACE ---
st.title("🎸 GuitarTech ERP")

abas = st.tabs(["📄 Orçamentos", "⚙️ Faturar OS", "🛠️ Produção", "💰 Caixa", "⚙️ Catálogo"])

# 1. ABA DE ORÇAMENTOS (SEM CÂMERA)
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
        
        detalhes = st.text_area("Observações", value=desc_base)
        valor = st.number_input("Valor Estimado (R$)", value=preco_base)
        
        if st.form_submit_button("Salvar Orçamento"):
            conn = sqlite3.connect('oficina.db')
            conn.execute("INSERT INTO ordens (cliente, instrumento, servico_nome, descricao_detalhada, total, entrada, status, data_entrada) VALUES (?,?,?,?,?,?,?,?)",
                      (cliente, instrumento, servico, detalhes, valor, 0, 'Orçamento', datetime.now().date()))
            conn.commit()
            conn.close()
            st.success("Orçamento salvo com sucesso!")

# 2. ABA DE FATURAMENTO (CÂMERA SOB DEMANDA)
with abas[1]:
    st.header("Faturar Orçamento")
    conn = sqlite3.connect('oficina.db')
    pendentes = pd.read_sql_query("SELECT id, cliente, instrumento FROM ordens WHERE status='Orçamento'", conn)
    conn.close()

    if not pendentes.empty:
        escolha_id = st.selectbox("Selecione o Orçamento", pendentes['id'].tolist(), format_func=lambda x: f"ID {x} - {pendentes[pendentes['id']==x]['cliente'].values[0]}")
        
        with st.container(border=True):
            data_ent = st.date_input("Data Prometida de Entrega")
            pagto = st.selectbox("Forma de Pagto da Entrada", ["Pix", "Cartão", "Dinheiro"])
            valor_ent = st.number_input("Valor da Entrada (Sinal R$)", min_value=0.0)
            tem_capa = st.checkbox("Instrumento ficou com Capa/Case?")

            # LÓGICA DA CÂMERA COM BOTÃO
            st.divider()
            col_f1, col_f2 = st.columns(2)
            
            # Foto Instrumento
            with col_f1:
                if 'foto_inst_ativa' not in st.session_state: st.session_state.foto_inst_ativa = False
                if st.button("📸 Tirar Foto do Instrumento"):
                    st.session_state.foto_inst_ativa = True
                if st.session_state.foto_inst_ativa:
                    foto_i = st.camera_input("Capture o Instrumento")
                    if foto_i: st.image(foto_i, caption="Foto capturada", width=200)

            # Foto Capa (Se marcado)
            with col_f2:
                if tem_capa:
                    if 'foto_capa_ativa' not in st.session_state: st.session_state.foto_capa_ativa = False
                    if st.button("📸 Tirar Foto da Capa"):
                        st.session_state.foto_capa_ativa = True
                    if st.session_state.foto_capa_ativa:
                        foto_c = st.camera_input("Capture a Capa")
                        if foto_c: st.image(foto_c, caption="Foto da capa capturada", width=200)

            st.divider()
            if st.button("✅ Confirmar Faturamento e Gerar OS"):
                conn = sqlite3.connect('oficina.db')
                conn.execute("UPDATE ordens SET status='Em Produção', data_entrega=?, forma_pagto=?, entrada=?, acessorio=? WHERE id=?",
                          (data_ent, pagto, valor_ent, "Com Capa" if tem_capa else "Sem Capa", escolha_id))
                conn.commit()
                conn.close()
                st.success("OS Faturada! Vá para a aba Produção para imprimir o PDF.")
                # Resetar estados da câmera para a próxima
                st.session_state.foto_inst_ativa = False
                st.session_state.foto_capa_ativa = False
    else:
        st.info("Nenhum orçamento para faturar.")

# 3. PRODUÇÃO E 4. CAIXA (Mantidos)
with abas[2]:
    st.header("🛠️ Relatório de Produção")
    conn = sqlite3.connect('oficina.db')
    df_prod = pd.read_sql_query("SELECT id, cliente, instrumento, data_entrega, acessorio FROM ordens WHERE status='Em Produção'", conn)
    conn.close()
    if not df_prod.empty:
        st.dataframe(df_prod, use_container_width=True)
        id_pdf = st.number_input("ID da OS para PDF", min_value=1, step=1)
        if st.button("Gerar PDF da OS"):
            conn = sqlite3.connect('oficina.db')
            dados_os = pd.read_sql_query(f"SELECT * FROM ordens WHERE id={id_pdf}", conn).iloc[0]
            conn.close()
            st.download_button("Baixar PDF OS", gerar_pdf_os(dados_os), file_name=f"OS_{id_pdf}.pdf")

with abas[3]:
    st.header("💰 Caixa")
    conn = sqlite3.connect('oficina.db')
    res = pd.read_sql_query("SELECT SUM(entrada) as e, SUM(total-entrada) as p FROM ordens WHERE status='Em Produção'", conn)
    conn.close()
    st.metric("Recebido (Entradas)", f"R$ {res['e'][0] or 0:.2f}")

with abas[4]:
    st.header("⚙️ Catálogo")
    with st.form("cad"):
        n = st.text_input("Serviço")
        p = st.number_input("Preço")
        d = st.text_area("Descrição Padrão")
        if st.form_submit_button("Salvar"):
            conn = sqlite3.connect('oficina.db')
            conn.execute("INSERT INTO catalogo (nome, preco, descricao_base) VALUES (?,?,?)", (n, p, d))
            conn.commit()
            conn.close()
            st.rerun()
