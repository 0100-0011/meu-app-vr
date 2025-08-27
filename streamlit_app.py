import streamlit as st
import pandas as pd
import io
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

# Função para consolidar os dataframes conforme notebook de referência com tratamento robusto de colunas
def consolidar_bases(dataframes):
    consolidated_df = dataframes['ATIVOS'].copy()

    if 'FERIAS' in dataframes:
        ferias_cols = ['MATRICULA', 'DESC. SITUACAO', 'DIAS DE FERIAS']
        consolidated_df = pd.merge(consolidated_df, dataframes['FERIAS'][ferias_cols], on='MATRICULA', how='left')

    if 'DESLIGADOS' in dataframes:
        desligados_cols = ['MATRICULA ', 'DATA DEMISSÃO', 'COMUNICADO DE DESLIGAMENTO']  # coluna com espaço no nome
        consolidated_df = pd.merge(consolidated_df, dataframes['DESLIGADOS'][desligados_cols], left_on='MATRICULA', right_on='MATRICULA ', how='left')
        consolidated_df.drop(columns=['MATRICULA '], inplace=True)

    if 'ADMISSAO_ABRIL' in dataframes:
        admissao_cols = ['MATRICULA', 'Admissão', 'Cargo', 'SITUAÇÃO']
        consolidated_df = pd.merge(consolidated_df, dataframes['ADMISSAO_ABRIL'][admissao_cols], on='MATRICULA', how='left')

    if 'DIAS_UTEIS' in dataframes:
        dias_uteis_df = dataframes['DIAS_UTEIS'].copy()
        if 'SINDICADO' in dias_uteis_df.columns:
            dias_uteis_df.rename(columns={'SINDICADO': 'Sindicato'}, inplace=True)
        elif 'Sindicato' not in dias_uteis_df.columns:
            st.warning("Coluna 'Sindicato' ou 'SINDICADO' não encontrada em DIAS_UTEIS. Pulando junção.")
            dias_uteis_df['Sindicato'] = None
        required_cols = ['Sindicato', 'DIAS UTEIS (DE 15/04 a 15/05)']
        if all(col in dias_uteis_df.columns for col in required_cols):
            consolidated_df = pd.merge(consolidated_df, dias_uteis_df[required_cols], on='Sindicato', how='left')
        else:
            st.warning(f"Colunas {required_cols} não encontradas em DIAS_UTEIS. Pulando junção.")

    exclusao_matriculas = []
    def adicionar_matriculas_para_exclusao(df, col_name='MATRICULA'):
        if df is not None and col_name in df.columns:
            exclusao_matriculas.extend(df[col_name].dropna().astype(str).tolist())

    if 'ESTAGIARIOS' in dataframes:
        adicionar_matriculas_para_exclusao(dataframes['ESTAGIARIOS'])

    if 'APRENDIZES' in dataframes:
        adicionar_matriculas_para_exclusao(dataframes['APRENDIZES'])

    if 'AFASTAMENTOS' in dataframes:
        adicionar_matriculas_para_exclusao(dataframes['AFASTAMENTOS'])

    if 'EXTERIOR' in dataframes:
        df_exterior = dataframes['EXTERIOR']
        if 'MATRICULA' in df_exterior.columns:
            adicionar_matriculas_para_exclusao(df_exterior, 'MATRICULA')
        elif 'Matrícula' in df_exterior.columns:
            adicionar_matriculas_para_exclusao(df_exterior, 'Matrícula')
        else:
            st.warning("Coluna de matrícula não encontrada em EXTERIOR para exclusão.")

    consolidated_df = consolidated_df[~consolidated_df['MATRICULA'].astype(str).isin(exclusao_matriculas)]

    if 'Cargo' in consolidated_df.columns:
        consolidated_df = consolidated_df[~consolidated_df['Cargo'].str.contains('diretor', case=False, na=False)]

    return consolidated_df

def gerar_vr_com_langchain(consolidated_df: pd.DataFrame, pplx_api_key: str) -> pd.DataFrame:
    resumo_texto = (
        "Calcule o Vale Refeição mensal para os colaboradores conforme os dados:\n"
        "Sindicato, dias úteis, dias de férias, afastamentos, desligamentos, admissões e valor diário por sindicato.\n"
        "Siga as regras de custo 80% empresa, 20% desconto profissional, proporcionalidade para desligados."
    )
    system_msg = "Você é um assistente especializado em RH e folha de pagamento."
    exemplos_dados = consolidated_df.head(20).to_dict(orient='records')

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_msg),
        ("human", f"{resumo_texto} Dados: {exemplos_dados}")
    ])

    chat = ChatPerplexity(temperature=0, pplx_api_key=pplx_api_key, model="sonar")

    prompt_text = prompt_template.format()
    resposta = chat.invoke(prompt_text)
    # TODO: implementar parser da resposta para dataframe final contendo cálculos do VR
    # Por enquanto, apenas retorna base consolidada
    return consolidated_df

def main():
    st.title("Calculadora Automática de VR Mensal com LangChain e Perplexity")
    st.sidebar.header("Faça upload dos arquivos Excel necessários")
    uploaded_files = st.sidebar.file_uploader("Selecione os arquivos", accept_multiple_files=True, type=['xlsx', 'xls'])
    if uploaded_files:
        with st.spinner("Carregando e consolidando bases de dados..."):
            dataframes = carregar_excel_arquivos(uploaded_files)
            consolidated_df = consolidar_bases(dataframes)
            st.write("### Dados consolidados após limpeza e exclusões:")
            st.dataframe(consolidated_df.head())
        pplx_api_key = st.sidebar.text_input("Chave API Perplexity", type="password")
        if pplx_api_key and st.button("Gerar VR Mensal com LangChain + Perplexity"):
            with st.spinner("Consultando LangChain + Perplexity e calculando VR..."):
                vr_final_df = gerar_vr_com_langchain(consolidated_df, pplx_api_key)
                st.write("### Planilha final calculada de VR para envio:")
                st.dataframe(vr_final_df.head())
                buffer = io.BytesIO()
                vr_final_df.to_excel(buffer, index=False)
                buffer.seek(0)
                st.download_button(
                    label="Baixar arquivo Excel VR Mensal",
                    data=buffer,
                    file_name="VR_Mensal_Final.xlsx",
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )

if __name__ == "__main__":
    main()
