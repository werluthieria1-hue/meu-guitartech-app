import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF
import urllib.parse

st.set_page_config(page_title="GuitarTech Pro", layout="wide")

# --- CONFIGURAÇÕES DA SUA OFICINA ---
NOME_OFICINA = "REGES CUSTOMIZAÇÕES"
TELEFONE = "(66) 99944-7355" # Seu telefone de Ponta Porã
CIDADE = "Rondonóplis - MT"

# --- BANCO DE DADOS ---
def iniciar_db():
    conn = sqlite3.connect('oficina.db')
    c = conn.cursor()
    # Tabela de ordens
    c.execute('''CREATE TABLE IF NOT EXISTS ordens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente TEXT, instrumento TEXT, servico_nome TEXT, 
                    descricao_detalhada TEXT, total REAL, entrada REAL, 
                    status TEXT, data DATE)''')
    # Tabela de catálogo de serviços
    c.execute('''CREATE TABLE IF NOT EXISTS catalogo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT, preco REAL, descricao_base TEXT)''')
    conn.commit()
    conn.close()

iniciar_db()

# --- FUNÇÃO DO PDF (LAYOUT NOVO) ---
class PDF(FPDF):
    def header(self):
        # Moldura decorativa
        self.rect(5, 5, 200, 287)
        self.set_font('Arial', 'B', 20)
        self.set_text_color(30, 30, 30)
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
    
    # Dados do Cliente
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, " DADOS DO CLIENTE E INSTRUMENTO", ln=True, fill=True)
    pdf.set_font("Arial", size=11)
    pdf.ln(2)
    pdf.cell(0, 8, f"Cliente: {cliente}", ln=True)
    pdf.cell(0, 8, f"Instrumento: {instrumento}", ln=True)
    pdf.cell(0, 8, f"Data de Entrada: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    
    # Descrição
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, f" SERVICO: {servico_nome}", ln=True, fill=True)
    pdf.set_font("Arial", size=10)
    pdf.ln(2)
    pdf.multi_cell(0, 8, desc_detalhada.encode('latin-1', 'replace').decode('latin-1'))
    
    # Financeiro
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(100, 10, "RESUMO FINANCEIRO", fill=True)
    pdf.cell(90, 10, "", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.cell(100, 8, f"Valor Total do Servico:")
    pdf.cell(90, 8, f"R$ {total:.2f}", ln=True, align='R')
    pdf.cell(100, 8, f"Valor de Entrada (Sinal):")
    pdf.cell(90, 8, f"R$ {entrada:.2f}", ln=True, align='R')
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(200, 0, 0)
    pdf.cell(100, 10, f"SALDO A PAGAR NO FINAL:")
    pdf.cell(90, 10, f"R$ {total - entrada:.2f}", ln=True, align='R')
    
    return bytes(pdf.output(dest='S'))

# --- INTERFACE ---
st.title("🎸 GuitarTech Pro Manager")

aba1, aba2, aba3, aba4 = st.tabs(["📋 Nova OS", "🛠️ Produção", "💰 Financeiro", "⚙️ Cadastros"])

# ABA 4: CADASTRO DE SERVIÇOS (A BASE DE TUDO)
with aba4:
    st.header("⚙️ Catálogo de Serviços")
    with st.expander("➕ Cadastrar Novo Tipo de Serviço"):
        with st.form("cad_servico"):
            nome_s = st.text_input("Nome do Serviço (Ex: Regulagem Standard)")
            preco_s = st.number_input("Preço Sugerido (R$)", min_value=0.0)
            desc_s = st.text_area("Descrição Padrão (O que está incluso?)")
            if st.form_submit_button("Salvar no Catálogo"):
                conn = sqlite3.connect('oficina.db')
                conn.execute("INSERT INTO catalogo (nome, preco, descricao_base) VALUES (?,?,?)", (nome_s, preco_s, desc_s))
                conn.commit()
                conn.close()
                st.success("Serviço adicionado!")

    # Mostrar Tabela de Serviços
    conn = sqlite3.connect('oficina.db')
    df_cat = pd.read_sql_query("SELECT nome, preco FROM catalogo", conn)
    conn.close()
    st.table(df_cat)

# ABA 1: NOVA OS (COM SELEÇÃO AUTOMÁTICA)
with aba1:
    st.header("📋 Abrir Ordem de Serviço")
    
    # Carregar serviços para o Selectbox
    conn = sqlite3.connect('oficina.db')
    servicos_disponiveis = pd.read_sql_query("SELECT * FROM catalogo", conn)
    conn.close()

    with st.form("os_form"):
        cliente = st.text_input("Cliente")
        instrumento = st.text_input("Instrumento")
        
        # Seleção do serviço cadastrado
        escolha = st.selectbox("Selecione o Serviço", servicos_disponiveis['nome'].tolist() if not servicos_disponiveis.empty else ["Cadastre um serviço primeiro"])
        
        # Puxa o preço e a descrição automaticamente se houver seleção
        dados_selecionados = servicos_disponiveis[servicos_disponiveis['nome'] == escolha]
        preco_sugerido = float(dados_selecionados['preco'].iloc[0]) if not dados_selecionados.empty else 0.0
        desc_sugerida = dados_selecionados['descricao_base'].iloc[0] if not dados_selecionados.empty else ""

        desc_final = st.text_area("Descrição/Observações para o PDF", value=desc_sugerida)
        
        col1, col2 = st.columns(2)
        total = col1.number_input("Valor Final (R$)", value=preco_sugerido)
        entrada = col2.number_input("Entrada (Sinal R$)", min_value=0.0)
        
        if st.form_submit_button("Gerar OS e Salvar"):
            conn = sqlite3.connect('oficina.db')
            conn.execute("INSERT INTO ordens (cliente, instrumento, servico_nome, descricao_detalhada, total, entrada, status, data) VALUES (?,?,?,?,?,?,?,?)",
                      (cliente, instrumento, escolha, desc_final, total, entrada, 'Em Produção', datetime.now().date()))
            conn.commit()
            conn.close()
            st.success("OS Salva!")
            
            # Gerar PDF após salvar
            pdf_b = gerar_pdf(cliente, instrumento, escolha, desc_final, total, entrada)
            st.download_button("📥 Baixar PDF Profissional", data=pdf_b, file_name=f"OS_{cliente}.pdf", mime="application/pdf")
            
            msg = f"Olá {cliente}, segue o orçamento do seu {instrumento}. Total: R$ {total:.2f}. Anexo o PDF."
            st.markdown(f"[💬 Enviar via WhatsApp](https://wa.me/?text={urllib.parse.quote(msg)})")

# AS OUTRAS ABAS CONTINUAM IGUAIS (PRODUÇÃO E FINANCEIRO)
with aba2:
    st.header("🛠️ Bancada")
    conn = sqlite3.connect('oficina.db')
    df_p = pd.read_sql_query("SELECT cliente, instrumento, servico_nome as Servico, total-entrada as Saldo FROM ordens WHERE status='Em Produção'", conn)
    conn.close()
    st.dataframe(df_p, use_container_width=True)

with aba3:
    st.header("💰 Resumo")
    conn = sqlite3.connect('oficina.db')
    res = pd.read_sql_query("SELECT SUM(entrada) as e, SUM(total-entrada) as p FROM ordens", conn)
    conn.close()
    st.metric("Caixa", f"R$ {res['e'][0] or 0:.2f}")
    st.metric("Pendente", f"R$ {res['p'][0] or 0:.2f}")
