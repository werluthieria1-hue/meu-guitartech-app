import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF
import urllib.parse

# --- CONFIGURAÇÕES DA SUA OFICINA (ALTERE AQUI) ---
NOME_OFICINA = "REGIS GUITAR TECH" 
TELEFONE = "(67) 9XXXX-XXXX"
CIDADE = "Ponta Porã - MS"
ENDERECO = "Rua Exemplo, 123 - Centro"

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
                    forma_pagto TEXT, acessorio TEXT, funcionario TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS catalogo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT, preco REAL, descricao_base TEXT)''')
    conn.commit()
    conn.close()

iniciar_db()

# --- FUNÇÃO DO PDF COM CABEÇALHO COMPLETO ---
class PDF(FPDF):
    def header(self):
        # Moldura
        self.rect(5, 5, 200, 287)
        # Dados da Oficina
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, NOME_OFICINA.encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, f"{ENDERECO} - {CIDADE}".encode('latin-1', 'replace').decode('latin-1'), ln=True, align='C')
        self.cell(0, 5, f"WhatsApp: {TELEFONE}", ln=True, align='C')
        self.ln(5)
        self.line(10, 35, 200, 35)
        self.ln(10)

def gerar_pdf_os(dados):
    pdf = PDF()
    pdf.add_page()
    
    # Título e ID
    pdf.set_font("Arial", 'B', 14)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 10, f"ORDEM DE SERVICO #{dados['id']} - {dados['status'].upper()}", ln=True, align='C', fill=True)
    pdf.ln(5)
    
    # Seção Cliente/Técnico
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, "INFORMACOES GERAIS", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(100, 7, f"Cliente: {dados['cliente']}", ln=0)
    pdf.cell(90, 7, f"Tecnico: {dados['funcionario']}", ln=1)
    pdf.cell(100, 7, f"Instrumento: {dados['instrumento']}", ln=0)
    pdf.cell(90, 7, f"Acessorio: {dados['acessorio']}", ln=1)
    pdf.cell(100, 7, f"Entrada: {dados['data_entrada']}", ln=0)
    pdf.cell(90, 7, f"Previsao Entrega: {dados['data_entrega']}", ln=1)
    
    # Descrição do Serviço
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, "DESCRICAO DOS SERVICOS", ln=True, fill=True)
    pdf.set_font("Arial", size=10)
    desc_limpa = dados['descricao_detalhada'].encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 7, desc_limpa)
    
    # Financeiro
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, "RESUMO FINANCEIRO", ln=True, fill=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(100, 7, f"Valor Total do Servico:")
    pdf.cell(90, 7, f"R$ {dados['total']:.2f}", ln=True, align='R')
    pdf.cell(100, 7, f"Entrada (Sinal) - {dados['forma_pagto']}:")
    pdf.cell(90, 7, f"R$ {dados['entrada']:.2f}", ln=True, align='R')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, "SALDO A RECEBER NA ENTREGA:")
    pdf.cell(90, 10, f"R$ {dados['total'] - dados['entrada']:.2f}", ln=True, align='R')
    
    return bytes(pdf.output(dest='S'))

# --- INTERFACE ---
st.title("🎸 GuitarTech ERP")

abas = st.tabs(["📄 Orçamentos", "⚙️ Faturar OS", "🛠️ Produção", "💰 Caixa", "⚙️ Catálogo"])

# 1. ABA DE ORÇAMENTOS
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
        desc_base = dados_cat['descricao_base'].iloc[0] if not dados_cat.empty else ""
        preco_base = float(dados_cat['preco'].iloc[0]) if not dados_cat.empty else 0.0
        
        detalhes = st.text_area("Observações", value=desc_base)
        valor = st.number_input("Valor Estimado (R$)", value=preco_base)
        
        if st.form_submit_button("Salvar Orçamento"):
            conn = sqlite3.connect('oficina.db')
            conn.execute("INSERT INTO ordens (cliente, instrumento, servico_nome, descricao_detalhada, total, entrada, status, data_entrada) VALUES (?,?,?,?,?,?,?,?)",
                      (cliente, instrumento, servico, detalhes, valor, 0, 'Orçamento', datetime.now().date()))
            conn.commit()
            conn.close()
            st.success("Orçamento salvo!")

# 2. ABA DE FATURAMENTO
with abas[1]:
    st.header("Faturar Orçamento")
    conn = sqlite3.connect('oficina.db')
    pendentes = pd.read_sql_query("SELECT id, cliente, instrumento FROM ordens WHERE status='Orçamento'", conn)
    conn.close()

    if not pendentes.empty:
        escolha_id = st.selectbox("Selecione o Orçamento", pendentes['id'].tolist(), format_func=lambda x: f"ID {x} - {pendentes[pendentes['id']==x]['cliente'].values[0]}")
        
        with st.container(border=True):
            data_ent = st.date_input("Data de Entrega")
            tecnico = st.text_input("Funcionário Responsável", value="Regis")
            pagto = st.selectbox("Forma de Pagto Entrada", ["Pix", "Cartão", "Dinheiro"])
            valor_ent = st.number_input("Valor da Entrada", min_value=0.0)
            tem_capa = st.checkbox("Ficou com Capa/Case?")

            col_f1, col_f2 = st.columns(2)
            with col_f1:
                if st.button("📸 Foto Instrumento"): st.session_state.f_i = True
                if st.session_state.get('f_i'): st.camera_input("Capturar Instrumento", key="cam_i")
            with col_f2:
                if tem_capa:
                    if st.button("📸 Foto Capa"): st.session_state.f_c = True
                    if st.session_state.get('f_c'): st.camera_input("Capturar Capa", key="cam_c")

            if st.button("✅ Confirmar Faturamento"):
                conn = sqlite3.connect('oficina.db')
                conn.execute("UPDATE ordens SET status='Em Produção', data_entrega=?, forma_pagto=?, entrada=?, acessorio=?, funcionario=? WHERE id=?",
                          (data_ent, pagto, valor_ent, "Com Capa" if tem_capa else "Sem Capa", tecnico, escolha_id))
                conn.commit()
                conn.close()
                st.success("OS Faturada!")
    else:
        st.info("Sem orçamentos pendentes.")

# 3. PRODUÇÃO (GERA PDF COM CABEÇALHO)
with abas[2]:
    st.header("🛠️ Produção")
    conn = sqlite3.connect('oficina.db')
    df_prod = pd.read_sql_query("SELECT id, cliente, instrumento, funcionario, data_entrega FROM ordens WHERE status='Em Produção'", conn)
    conn.close()
    
    if not df_prod.empty:
        st.dataframe(df_prod, use_container_width=True)
        id_pdf = st.number_input("ID da OS para Gerar PDF", min_value=1, step=1)
        if st.button("📄 Gerar PDF Completo"):
            conn = sqlite3.connect('oficina.db')
            dados_os = pd.read_sql_query(f"SELECT * FROM ordens WHERE id={id_pdf}", conn).iloc[0]
            conn.close()
            st.download_button("Clique aqui para baixar", gerar_pdf_os(dados_os), file_name=f"OS_{id_pdf}.pdf")

# 4. CAIXA E 5. CATÁLOGO
with abas[3]:
    st.header("💰 Caixa")
    conn = sqlite3.connect('oficina.db')
    res = pd.read_sql_query("SELECT SUM(entrada) as e FROM ordens WHERE status='Em Produção'", conn)
    conn.close()
    st.metric("Total em Caixa (Entradas)", f"R$ {res['e'][0] or 0:.2f}")

with abas[4]:
    st.header("⚙️ Catálogo")
    with st.form("cad"):
        n = st.text_input("Serviço")
        p = st.number_input("Preço")
        d = st.text_area("Descrição Base")
        if st.form_submit_button("Salvar"):
            conn = sqlite3.connect('oficina.db')
            conn.execute("INSERT INTO catalogo (nome, preco, descricao_base) VALUES (?,?,?)", (n, p, d))
            conn.commit()
            conn.close()
            st.rerun()
