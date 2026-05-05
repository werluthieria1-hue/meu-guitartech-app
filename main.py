import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF
import urllib.parse

st.set_page_config(page_title="GuitarTech Pro", layout="wide")

# --- CONFIGURAÇÕES DA SUA OFICINA ---
NOME_OFICINA = "WILLIAN REGES GUITAR TECH"
TELEFONE = "(66) 99944-7355"
CIDADE = "Rondonopolis - MT"

# --- BANCO DE DADOS ---
def iniciar_db():
    conn = sqlite3.connect('oficina.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ordens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente TEXT, instrumento TEXT, servico_nome TEXT, 
                    descricao_detalhada TEXT, total REAL, entrada REAL, 
                    status TEXT, data DATE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS catalogo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT, preco REAL, descricao_base TEXT)''')
    conn.commit()
    conn.close()

iniciar_db()

# --- FUNÇÃO DO PDF ---
class PDF(FPDF):
    def header(self):
        self.rect(5, 5, 200, 287)
        self.set_font('Arial', 'B', 20)
        self.cell(0, 15, NOME_OFICINA, 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 5, f"{CIDADE} | WhatsApp: {TELEFONE}", 0, 1, 'C')
        self.ln(10)
        self.line(10, 35, 200, 35)

def gerar_pdf(cliente, instrumento, servico_nome, desc_detalhada, total, entrada):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"ORDEM DE SERVICO #{datetime.now().strftime('%Y%m%d%H%M')}", ln=True, align='R')
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, " DADOS DO CLIENTE E INSTRUMENTO", ln=True, fill=True)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 8, f"Cliente: {cliente}", ln=True)
    pdf.cell(0, 8, f"Instrumento: {instrumento}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, f" SERVICO: {servico_nome}", ln=True, fill=True)
    pdf.set_font("Arial", size=10)
    servico_limpo = desc_detalhada.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 8, servico_limpo)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(100, 10, "RESUMO FINANCEIRO", fill=True)
    pdf.cell(90, 10, "", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.cell(100, 8, f"Valor Total:")
    pdf.cell(90, 8, f"R$ {total:.2f}", ln=True, align='R')
    pdf.cell(100, 8, f"Entrada:")
    pdf.cell(90, 8, f"R$ {entrada:.2f}", ln=True, align='R')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, f"SALDO A PAGAR:")
    pdf.cell(90, 10, f"R$ {total - entrada:.2f}", ln=True, align='R')
    return bytes(pdf.output(dest='S'))

# --- INTERFACE ---
st.title("🎸 GuitarTech Pro Manager")

aba1, aba2, aba3, aba4 = st.tabs(["📋 Nova OS", "🛠️ Produção", "💰 Financeiro", "⚙️ Cadastros"])

with aba4:
    st.header("⚙️ Catálogo de Serviços")
    with st.expander("➕ Cadastrar Novo Tipo de Serviço"):
        with st.form("cad_servico", clear_on_submit=True):
            nome_s = st.text_input("Nome do Serviço")
            preco_s = st.number_input("Preço Sugerido (R$)", min_value=0.0)
            desc_s = st.text_area("Descrição Padrão")
            if st.form_submit_button("Salvar no Catálogo"):
                conn = sqlite3.connect('oficina.db')
                conn.execute("INSERT INTO catalogo (nome, preco, descricao_base) VALUES (?,?,?)", (nome_s, preco_s, desc_s))
                conn.commit()
                conn.close()
                st.success("Serviço adicionado!")
    conn = sqlite3.connect('oficina.db')
    df_cat = pd.read_sql_query("SELECT nome, preco FROM catalogo", conn)
    conn.close()
    st.table(df_cat)

with aba1:
    st.header("📋 Abrir Ordem de Serviço")
    conn = sqlite3.connect('oficina.db')
    servicos_disponiveis = pd.read_sql_query("SELECT * FROM catalogo", conn)
    conn.close()

    # Variáveis de controle para o PDF fora do form
    status_salvo = False

    with st.form("os_form"):
        cliente = st.text_input("Cliente")
        instrumento = st.text_input("Instrumento")
        escolha = st.selectbox("Serviço", servicos_disponiveis['nome'].tolist() if not servicos_disponiveis.empty else ["Cadastre primeiro"])
        
        dados_sel = servicos_disponiveis[servicos_disponiveis['nome'] == escolha]
        preco_sug = float(dados_sel['preco'].iloc[0]) if not dados_sel.empty else 0.0
        desc_sug = dados_sel['descricao_base'].iloc[0] if not dados_sel.empty else ""

        desc_final = st.text_area("Descrição/Observações", value=desc_sug)
        col1, col2 = st.columns(2)
        total_os = col1.number_input("Total (R$)", value=preco_sug)
        entrada_os = col2.number_input("Entrada (R$)", min_value=0.0)
        
        if st.form_submit_button("Salvar OS"):
            conn = sqlite3.connect('oficina.db')
            conn.execute("INSERT INTO ordens (cliente, instrumento, servico_nome, descricao_detalhada, total, entrada, status, data) VALUES (?,?,?,?,?,?,?,?)",
                      (cliente, instrumento, escolha, desc_final, total_os, entrada_os, 'Em Produção', datetime.now().date()))
            conn.commit()
            conn.close()
            st.success("Dados salvos! Role para baixo para gerar o PDF.")
            status_salvo = True

    # GERAR PDF FORA DO FORMULÁRIO (CORREÇÃO DO ERRO)
    if status_salvo or (cliente and instrumento):
        st.divider()
        st.subheader("📄 Ações para esta OS")
        try:
            pdf_b = gerar_pdf(cliente, instrumento, escolha, desc_final, total_os, entrada_os)
            st.download_button("📥 Baixar PDF Profissional", data=pdf_b, file_name=f"OS_{cliente}.pdf", mime="application/pdf")
            
            msg = f"Olá {cliente}, orçamento do seu {instrumento}: R$ {total_os:.2f}. Segue o PDF."
            st.markdown(f"### [💬 Enviar WhatsApp](https://wa.me/?text={urllib.parse.quote(msg)})")
        except:
            st.info("Preencha os campos acima para habilitar o PDF.")

with aba2:
    st.header("🛠️ Produção")
    conn = sqlite3.connect('oficina.db')
    df_p = pd.read_sql_query("SELECT id, cliente, instrumento, total-entrada as Saldo FROM ordens WHERE status='Em Produção'", conn)
    conn.close()
    st.dataframe(df_p, use_container_width=True)

with aba3:
    st.header("💰 Financeiro")
    conn = sqlite3.connect('oficina.db')
    res = pd.read_sql_query("SELECT SUM(entrada) as e, SUM(total-entrada) as p FROM ordens", conn)
    conn.close()
    st.metric("Recebido", f"R$ {res['e'][0] or 0:.2f}")
    st.metric("Pendente", f"R$ {res['p'][0] or 0:.2f}")
