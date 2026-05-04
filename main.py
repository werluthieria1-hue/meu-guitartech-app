import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF
import urllib.parse

st.set_page_config(page_title="GuitarTech Manager", layout="centered")

# --- FUNÇÃO DO PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'COMPROVANTE DE SERVIÇO - GUITARTECH', 0, 1, 'C')
        self.ln(5)

def gerar_pdf(cliente, instrumento, servico, total, entrada):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(0, 10, f"Data: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    pdf.cell(0, 10, f"Cliente: {cliente}", ln=True)
    pdf.cell(0, 10, f"Instrumento: {instrumento}", ln=True)
    pdf.ln(5)
    pdf.multi_cell(0, 10, f"Serviço: {servico}")
    pdf.ln(5)
    pdf.cell(0, 10, f"Valor Total: R$ {total:.2f}", ln=True)
    pdf.cell(0, 10, f"Entrada: R$ {entrada:.2f}", ln=True)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Saldo a Pagar: R$ {total - entrada:.2f}", ln=True)
    
    return pdf.output(dest='S')

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
    with st.form("os_form"):
        cliente = st.text_input("Nome do Cliente")
        instrumento = st.text_input("Instrumento")
        servico = st.text_area("Descrição do Serviço")
        col1, col2 = st.columns(2)
        valor_total = col1.number_input("Valor Total (R$)", min_value=0.0)
        valor_entrada = col2.number_input("Entrada (R$)", min_value=0.0)
        data_entrega = st.date_input("Prazo de Entrega")
        
        submit = st.form_submit_button("Salvar OS")
        
        if submit:
            conn = sqlite3.connect('oficina.db')
            c = conn.cursor()
            c.execute("INSERT INTO ordens (cliente, instrumento, servico, total, entrada, status, data) VALUES (?,?,?,?,?,?,?)",
                      (cliente, instrumento, servico, valor_total, valor_entrada, 'Em Produção', data_entrega))
            conn.commit()
            conn.close()
            st.success(f"OS de {cliente} registrada!")

    # Fora do formulário para o download funcionar bem
    if cliente:
        st.subheader("Gerar Documento")
        pdf_out = gerar_pdf(cliente, instrumento, servico, valor_total, valor_entrada)
        
        st.download_button(
            label="📥 Baixar PDF para Enviar",
            data=pdf_out,
            file_name=f"OS_{cliente}.pdf",
            mime="application/pdf"
        )
        
        # Link para o WhatsApp
        msg = f"Olá {cliente}, aqui está o orçamento do seu {instrumento}. Total: R${valor_total:.2f}. Segue o PDF em anexo."
        texto_zap = urllib.parse.quote(msg)
        st.markdown(f"[💬 Abrir WhatsApp para avisar o cliente](https://wa.me/?text={texto_zap})")

with aba2:
    st.header("🛠️ Produção")
    conn = sqlite3.connect('oficina.db')
    df = pd.read_sql_query("SELECT id, cliente, instrumento, total - entrada as saldo, data FROM ordens WHERE status = 'Em Produção'", conn)
    conn.close()
    st.dataframe(df, use_container_width=True)

with aba3:
    st.header("💰 Financeiro")
    conn = sqlite3.connect('oficina.db')
    resumo = pd.read_sql_query("SELECT SUM(entrada) as entradas, SUM(total - entrada) as pendente FROM ordens", conn)
    conn.close()
    st.metric("Total em Caixa", f"R$ {resumo['entradas'][0] or 0:.2f}")
    st.metric("A Receber", f"R$ {resumo['pendente'][0] or 0:.2f}")
