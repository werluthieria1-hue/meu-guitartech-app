import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF
import urllib.parse

# Configuração Mobile-First
st.set_page_config(page_title="GuitarTech Manager", layout="centered")

# --- FUNÇÃO DO PDF (CORRIGIDA) ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'COMPROVANTE DE SERVICO - GUITARTECH', 0, 1, 'C')
        self.ln(5)

def gerar_pdf(cliente, instrumento, servico, total, entrada):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Cabeçalho de dados
    pdf.cell(0, 10, f"Data: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    pdf.cell(0, 10, f"Cliente: {cliente}", ln=True)
    pdf.cell(0, 10, f"Instrumento: {instrumento}", ln=True)
    pdf.ln(5)
    
    # Tratamento para evitar erro de acentos no PDF
    # Removemos caracteres que a fonte padrão do PDF não entende
    servico_limpo = servico.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, f"Detalhes do Servico: {servico_limpo}")
    
    pdf.ln(5)
    pdf.cell(0, 10, f"Valor Total: R$ {total:.2f}", ln=True)
    pdf.cell(0, 10, f"Entrada: R$ {entrada:.2f}", ln=True)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Saldo a Pagar: R$ {total - entrada:.2f}", ln=True)
    
    # Retorna o arquivo em formato de Bytes (O QUE RESOLVE O ERRO)
    pdf_output = pdf.output(dest='S')
    return bytes(pdf_output)

# --- BANCO DE DADOS (SQLITE) ---
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

# --- INTERFACE DO APP ---
st.title("🎸 GuitarTech Manager")

aba1, aba2, aba3 = st.tabs(["📋 Nova OS", "🛠️ Produção", "💰 Financeiro"])

with aba1:
    st.header("Novo Orçamento")
    with st.form("os_form"):
        cliente_input = st.text_input("Nome do Cliente")
        instrumento_input = st.text_input("Instrumento")
        servico_input = st.text_area("Descrição do Serviço")
        col1, col2 = st.columns(2)
        valor_total = col1.number_input("Valor Total (R$)", min_value=0.0)
        valor_entrada = col2.number_input("Entrada (R$)", min_value=0.0)
        data_entrega = st.date_input("Prazo de Entrega")
        
        submit = st.form_submit_button("Salvar Ordem de Serviço")
        
        if submit:
            conn = sqlite3.connect('oficina.db')
            c = conn.cursor()
            c.execute("INSERT INTO ordens (cliente, instrumento, servico, total, entrada, status, data) VALUES (?,?,?,?,?,?,?)",
                      (cliente_input, instrumento_input, servico_input, valor_total, valor_entrada, 'Em Produção', data_entrega))
            conn.commit()
            conn.close()
            st.success(f"OS de {cliente_input} salva com sucesso!")

    # Sessão de Gerar Documento (aparece após preencher)
    if cliente_input:
        st.divider()
        st.subheader("📄 Documentação")
        
        try:
            pdf_bytes = gerar_pdf(cliente_input, instrumento_input, servico_input, valor_total, valor_entrada)
            
            st.download_button(
                label="📥 Baixar PDF para o Celular",
                data=pdf_bytes,
                file_name=f"OS_{cliente_input}.pdf",
                mime="application/pdf"
            )
            
            # Preparar mensagem de WhatsApp
            msg_wpp = f"Olá {cliente_input}, aqui está o orçamento da manutenção do seu {instrumento_input}. Segue o PDF em anexo."
            texto_formatado = urllib.parse.quote(msg_wpp)
            st.markdown(f"### [💬 Enviar WhatsApp para {cliente_input}](https://wa.me/?text={texto_formatado})")
        
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")

with aba2:
    st.header("🛠️ Relatório de Produção")
    conn = sqlite3.connect('oficina.db')
    df = pd.read_sql_query("SELECT id, cliente, instrumento, data as 'Prazo de Entrega', total - entrada as 'Saldo' FROM ordens WHERE status = 'Em Produção'", conn)
    conn.close()
    
    if not df.empty:
        st.write("Serviços ativos na bancada:")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhum serviço em produção no momento.")

with aba3:
    st.header("💰 Fluxo de Caixa")
    conn = sqlite3.connect('oficina.db')
    resumo = pd.read_sql_query("SELECT SUM(entrada) as entradas, SUM(total - entrada) as pendente FROM ordens", conn)
    conn.close()
    
    c1, c2 = st.columns(2)
    val_entrada = resumo['entradas'][0] if resumo['entradas'][0] else 0
    val_pendente = resumo['pendente'][0] if resumo['pendente'][0] else 0
    
    c1.metric("Já Recebido (Entradas)", f"R$ {val_entrada:.2f}")
    c2.metric("A Receber (Saldos)", f"R$ {val_pendente:.2f}")
