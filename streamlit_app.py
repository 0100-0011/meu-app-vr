import streamlit as st
import pandas as pd
import io
from langchain_perplexity import ChatPerplexity

def carregar_excel_arquivos(file_buffers):
    dataframes = {}
    for f in file_buffers:
        nome = f.name.split('.')[0]
        df = pd.read_excel(f)
        dataframes[nome] = df
    return dataframes

def consolidar_bases(dataframes):
    consolidated_df = dataframes['ATIVOS'].copy()
    if 'FERIAS' in dataframes:
        ferias_cols_candidatas = [
            ['MATRICULA', 'DESC. SITUACAO', 'DIAS DE FERIAS'],
            ['MATRICULA', 'DESC. SITUACAO', 'DIAS FERIAS'],
            ['MATRICULA', 'Descricao Situacao', 'Dias de Ferias']
        ]
        ferias_df = dataframes['FERIAS']
        cols_para_uso = None
        for cols in ferias_cols_candidatas:
            if all(col in ferias_df.columns for col in cols):
                cols_para_uso = cols
                break
        if cols_para_uso:
            consolidated_df = consolidated_df.merge(ferias_df[cols_para_uso], on='MATRICULA', how='left')
        else:
            st.warning("Não foram encontradas as colunas necessárias para FERIAS.")
    if 'DESLIGADOS' in dataframes:
        required_cols = ['MATRICULA ', 'DATA DEMISSÃO', 'COMUNICADO DE DESLIGAMENTO']
        deslig_df = dataframes['DESLIGADOS']
        if all(col in deslig_df.columns for col in required_cols):
            consolidated_df = consolidated_df.merge(deslig_df[required_cols], left_on='MATRICULA', right_on='MATRICULA ', how='left')
            consolidated_df.drop(columns=['MATRICULA '], inplace=True)
        else:
            st.warning("Colunas necessárias para DESLIGADOS não encontradas.")
    if 'ADMISSAO_ABRIL' in dataframes:
        required_cols = ['MATRICULA', 'Admissão', 'Cargo', 'SITUAÇÃO']
        admissao_df = dataframes['ADMISSAO_ABRIL']
        if all(col in admissao_df.columns for col in required_cols):
            consolidated_df = consolidated_df.merge(admissao_df[required_cols], on='MATRICULA', how='left')
        else:
            st.warning("Colunas necessárias para ADMISSAO_ABRIL não encontradas.")
    if 'DIAS_UTEIS' in dataframes:
        dias_uteis_df = dataframes['DIAS_UTEIS'].copy()
        if 'SINDICADO' in dias_uteis_df.columns:
            dias_uteis_df.rename(columns={'SINDICADO': 'Sindicato'}, inplace=True)
        if all(col in dias_uteis_df.columns for col in ['Sindicato', 'DIAS UTEIS (DE 15/04 a 15/05)']):
            consolidated_df = consolidated_df.merge(dias_uteis_df[['Sindicato', 'DIAS UTEIS (DE 15/04 a 15/05)']], on='Sindicato', how='left')
        else:
            st.warning("Colunas necessárias para DIAS_UTEIS não encontradas.")
    exclusao_matriculas = []
    def adicionar_matriculas_exclusao(df, col='MATRICULA'):
        if df is not None and col in df.columns:
            exclusao_matriculas.extend(df[col].dropna().astype(str).tolist())
    for tab in ['ESTAGIARIOS', 'APRENDIZES', 'AFASTAMENTOS', 'EXTERIOR']:
        if tab in dataframes:
            df_tab = dataframes[tab]
            if 'MATRICULA' in df_tab.columns:
                adicionar_matriculas_exclusao(df_tab, 'MATRICULA')
            elif 'Matrícula' in df_tab.columns:
                adicionar_matriculas_exclusao(df_tab, 'Matrícula')
    consolidated_df = consolidated_df.loc[~consolidated_df['MATRICULA'].astype(str).isin(exclusao_matriculas)]
    if 'Cargo' in consolidated_df.columns:
        consolidated_df = consolidated_df.loc[~consolidated_df['Cargo'].str.contains('diretor', case=False, na=False)]
    return consolidated_df

def calcular_vr(df):
    valores_por_estado = {
        'Paraná': 35.0,
        'Rio de Janeiro': 35.0,
        'Rio Grande do Sul': 35.0,
        'São Paulo': 37.5
    }
    valor_padrao = 30.0
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
    df['OBSERVAÇÕES'] = df.apply(obs_gerais, axis=1)
    return df

def gerar_vr_com_langchain(consolidated_df):
    system_msg = "Você é um assistente especializado em RH e folha de pagamento."
    resumo_texto = "Calcule o Vale Refeição mensal conforme regras de custo 80% empresa e 20% desconto profissional."
    dados = consolidated_df.head(20).to_dict(orient='records')
    messages = [
        ("system", system_msg),
        ("user", f"{resumo_texto} Dados: {dados}")
    ]
    pplx_api_key = st.secrets["PPLX_API_KEY"]
    chat = ChatPerplexity(temperature=0, pplx_api_key=pplx_api_key, model="sonar")

    resposta = chat.invoke(messages)
    # TODO: implementar parsing da resposta se necessário

    return consolidated_df

def main():
    st.title("Calculadora Automática de VR Mensal com LangChain e Perplexity")

    uploaded_files = st.sidebar.file_uploader(
        "Selecione os arquivos Excel necessários", accept_multiple_files=True, type=["xlsx", "xls"]
    )

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
                st.download_button(
                    label="Baixar arquivo Excel VR Mensal",
                    data=buffer,
                    file_name="VR_Mensal_Final.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

if __name__ == "__main__":
    main()
