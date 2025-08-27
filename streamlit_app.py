import streamlit as st
import pandas as pd
import io
from langchain_perplexity import ChatPerplexity

# Token fixo da API (substitua pela sua chave válida)
PPLX_API_KEY = "your_actual_api_key_here"

def carregar_excel_arquivos(file_buffers):
    dataframes = {}
    for file_buffer in file_buffers:
        nome = file_buffer.name.split('.')[0]
        df = pd.read_excel(file_buffer)
        dataframes[nome] = df
    return dataframes

def consolidar_bases(dataframes):
    consolidated_df = dataframes['ATIVOS'].copy()

    if 'FERIAS' in dataframes:
        ferias_cols = ['MATRICULA', 'DESC. SITUACAO', 'DIAS DE FERIAS']
        consolidated_df = pd.merge(consolidated_df, dataframes['FERIAS'][ferias_cols], on='MATRICULA', how='left')

    if 'DESLIGADOS' in dataframes:
        desligados_cols = ['MATRICULA ', 'DATA DEMISSÃO', 'COMUNICADO DE DESLIGAMENTO']
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

def calcular_vr(df):
    valores_por_estado = {
        'Paraná': 35.00,
        'Rio de Janeiro': 35.00,
        'Rio Grande do Sul': 35.00,
        'São Paulo': 37.50
    }
    valor_padrao = 35.00

    df['VALOR DIÁRIO VR'] = df['ESTADO'].map(valores_por_estado).fillna(valor_padrao)

    df['DIAS DE FERIAS'] = df['DIAS DE FERIAS'].fillna(0)
    df['DIAS UTEIS (DE 15/04 a 15/05)'] = df['DIAS UTEIS (DE 15/04 a 15/05)'].fillna(0)
    df['DIAS TRABALHADOS'] = df['DIAS UTEIS (DE 15/04 a 15/05)'] - df['DIAS DE FERIAS']

    df['TOTAL VR'] = (df['VALOR DIÁRIO VR'] * df['DIAS TRABALHADOS']).clip(lower=0)
    df['Custo Empresa'] = df['TOTAL VR'] * 0.8
    df['Desconto profissional'] = df['TOTAL VR'] * 0.2

    def obs_gerais(row):
        obs = []
        if pd.notna(row.get('DATA DEMISSÃO')):
            obs.append(f"Desligado em {row['DATA DEMISSÃO']}")
        if pd.notna(row.get('COMUNICADO DE DESLIGAMENTO')):
            obs.append(f"Comunicado: {row['COMUNICADO DE DESLIGAMENTO']}")
        if pd.notna(row.get('SITUAÇÃO')):
            obs.append(f"Situação: {row['SITUAÇÃO']}")
        return '; '.join(obs)

    df['OBS GERAIS'] = df.apply(obs_gerais, axis=1)

    return df

def gerar_vr_com_langchain(consolidated_df):
    system_msg = "Você é um assistente especializado em RH e folha de pagamento."
    resumo_texto = "Calcule o Vale Refeição mensal conforme regras de custo 80% empresa e 20% desconto profissional."
    dados = consolidated_df.head(20).to_dict(orient='records')  # limita para evitar problema
    user_msg = f"{resumo_texto} Dados: {dados}"
    chat = ChatPerplexity(temperature=0, pplx_api_key=PPLX_API_KEY, model="sonar")
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg}
    ]
    resposta = chat.invoke(messages)
    # Não implementado parser da resposta ainda
    return consolidated_df

def main():
    st.title("Calculadora Automática de VR Mensal com LangChain e Perplexity")

    uploaded_files = st.sidebar.file_uploader("Selecione os arquivos Excel necessários", accept_multiple_files=True, type=['xlsx', 'xls'])
    if uploaded_files:
        with st.spinner("Carregando e consolidando bases..."):
            dataframes = carregar_excel_arquivos(uploaded_files)
            consolidated_df = consolidar_bases(dataframes)
            st.write("## Dados consolidados após limpeza e exclusões")
            st.dataframe(consolidated_df.head())

        if st.button("Gerar VR Mensal"):
            with st.spinner("Processando cálculo do Vale Refeição..."):
                df_langchain = gerar_vr_com_langchain(consolidated_df)
                resultado_df = calcular_vr(df_langchain)
                st.write("## Planilha final com cálculos de VR")
                st.dataframe(resultado_df.head())
                buffer = io.BytesIO()
                resultado_df.to_excel(buffer, index=False)
                buffer.seek(0)
                st.download_button(label="Baixar arquivo Excel VR Mensal",
                                   data=buffer,
                                   file_name="VR_Mensal_Final.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == "__main__":
    main()
