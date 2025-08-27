import streamlit as st
import pandas as pd
from langchain_perplexity import ChatPerplexity
from langchain_core.prompts import ChatPromptTemplate

# Função para carregar arquivos excel selecionados pelo usuário e retornar dicionário de dataframes
def carregar_excel_arquivos(file_buffers):
    dataframes = {}
    for file_buffer in file_buffers:
        nome = file_buffer.name.split('.')[0]
        df = pd.read_excel(file_buffer)
        dataframes[nome] = df
    return dataframes

# Função para consolidar os dataframes conforme notebook de referência
def consolidar_bases(dataframes):
    # Base inicial
    consolidated_df = dataframes['ATIVOS'].copy()

    # Junção FERIAS
    if 'FERIAS' in dataframes:
        ferias_cols = ['MATRICULA', 'DESC. SITUACAO', 'DIAS DE FERIAS']
        consolidated_df = pd.merge(consolidated_df, dataframes['FERIAS'][ferias_cols], on='MATRICULA', how='left')

    # Junção DESLIGADOS
    if 'DESLIGADOS' in dataframes:
        desligados_cols = ['MATRICULA ', 'DATA DEMISSÃO', 'COMUNICADO DE DESLIGAMENTO']
        consolidated_df = pd.merge(consolidated_df, dataframes['DESLIGADOS'][desligados_cols], left_on='MATRICULA', right_on='MATRICULA ', how='left')
        consolidated_df.drop(columns=['MATRICULA '], inplace=True)

    # Junção ADMISSAO_ABRIL
    if 'ADMISSAO_ABRIL' in dataframes:
        admissao_cols = ['MATRICULA', 'Admissão', 'Cargo', 'SITUAÇÃO']
        consolidated_df = pd.merge(consolidated_df, dataframes['ADMISSAO_ABRIL'][admissao_cols], on='MATRICULA', how='left')

    # Junção DIAS_UTEIS (ajuste conforme coluna Sindicato)
    if 'DIAS_UTEIS' in dataframes:
        dias_uteis_df = dataframes['DIAS_UTEIS'].rename(columns={'SINDICADO': 'Sindicato'})
        dias_uteis_cols = ['Sindicato', 'DIAS UTEIS (DE 15/04 a 15/05)']
        consolidated_df = pd.merge(consolidated_df, dias_uteis_df[dias_uteis_cols], on='Sindicato', how='left')

    # Aplicar exclusões: diretores, estagiários, aprendizes, afastados, exterior baseado em matrículas
    exclusao_matriculas = []
    if 'ESTAGIARIOS' in dataframes:
        exclusao_matriculas.extend(dataframes['ESTAGIARIOS']['MATRICULA'].tolist())
    if 'APRENDIZES' in dataframes:
        exclusao_matriculas.extend(dataframes['APRENDIZES']['MATRICULA'].tolist())
    if 'AFASTAMENTOS' in dataframes:
        exclusao_matriculas.extend(dataframes['AFASTAMENTOS']['MATRICULA'].tolist())
    if 'EXTERIOR' in dataframes:
        exclusao_matriculas.extend(dataframes['EXTERIOR']['MATRICULA'].tolist())

    # Remover exclusões da base
    consolidated_df = consolidated_df[~consolidated_df['MATRICULA'].isin(exclusao_matriculas)]

    # Remover cargos diretores
    if 'Cargo' in consolidated_df.columns:
        consolidated_df = consolidated_df[~consolidated_df['Cargo'].str.contains('diretor', case=False, na=False)]

    return consolidated_df

# Função para invocar LangChain com prompt para gerar VR mensal conforme regras, passando dados consolidados como contexto resumido ou prompt
def gerar_vr_com_langchain(consolidated_df: pd.DataFrame, pplx_api_key: str) -> pd.DataFrame:
    # Preparar texto com resumo dos dados essenciais (exemplo, limitado para contexto)
    resumo_texto = f\"\"\"Calcule o Vale Refeição mensal para os colaboradores conforme os dados:
Sindicato, dias úteis, dias de férias, afastamentos, desligamentos, admissões e valor diário por sindicato.
Siga as regras de custo 80% empresa, 20% desconto profissional, proporcionalidade para desligados.\"\"\"

    # Prompt para o LLM
    system = \"Você é um assistente especializado em RH e folha de pagamento.\"
    human = f\"{resumo_texto} Dados: {consolidated_df.head(10).to_dict(orient='records')}\"  # Limitar para exemplo

    prompt = ChatPromptTemplate.from_messages([(\"system\", system), (\"human\", human)])
    chat = ChatPerplexity(temperature=0, pplx_api_key=pplx_api_key, model=\"sonar\")
    chain = prompt | chat
    resposta = chain.invoke({\"input\": human})
    
    # Aqui deveria haver parsing da resposta para um dataframe estruturado
    # Como placeholder, retornamos o DataFrame original para fluxo
    # Em produção, implementar parser da resposta gerada pelo LLM para output estruturado.
    return consolidated_df

# Streamlit interface
def main():
    st.title(\"Calculadora Automática de VR Mensal com LangChain e Perplexity\")

    # Upload dos arquivos Excel
    st.sidebar.header(\"Faça upload dos arquivos Excel necessários\")
    uploaded_files = st.sidebar.file_uploader(\"Selecione os arquivos\", accept_multiple_files=True, type=['xlsx', 'xls'])
    
    if uploaded_files:
        with st.spinner(\"Carregando e consolidando bases de dados...\"):
            dataframes = carregar_excel_arquivos(uploaded_files)
            consolidated_df = consolidar_bases(dataframes)
            st.write(\"### Dados consolidados após limpeza e exclusões:\")
            st.dataframe(consolidated_df.head())

        # API Key para LangChain Perplexity
        pplx_api_key = st.sidebar.text_input(\"Chave API Perplexity\", type=\"password\")
        
        if pplx_api_key and st.button(\"Gerar VR Mensal com LangChain + Perplexity\"):
            with st.spinner(\"Consultando LangChain + Perplexity e calculando VR...\"):
                vr_final_df = gerar_vr_com_langchain(consolidated_df, pplx_api_key)
                st.write(\"### Planilha final calculada de VR para envio:\")
                st.dataframe(vr_final_df.head())
                
                # Permitir download em excel
                excel_bytes = vr_final_df.to_excel(index=False)
                st.download_button(label=\"Baixar arquivo Excel VR Mensal\", data=excel_bytes, file_name=\"VR_Mensal_Final.xlsx\", mime='application/vnd.ms-excel')

if __name__ == \"__main__\":
    main()
