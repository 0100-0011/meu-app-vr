import streamlit as st
import pandas as pd
import io
from langchain_perplexity import ChatPerplexity

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
        consolidated_df = pd.merge(
            consolidated_df, dataframes['FERIAS'][ferias_cols], on='MATRICULA', how='left'
        )

    if 'DESLIGADOS' in dataframes:
        desligados_cols = ['MATRICULA ', 'DATA DEMISSÃO', 'COMUNICADO DE DESLIGAMENTO']
        consolidated_df = pd.merge(
            consolidated_df, dataframes['DESLIGADOS'][desligados_cols],
            left_on='MATRICULA', right_on='MATRICULA ', how='left'
        )
        consolidated_df.drop(columns=['MATRICULA '], inplace=True)
    
    if 'ADMISSAO_ABRIL' in dataframes:
        admissao_cols = ['MATRICULA', 'Admissão', 'Cargo', 'SITUAÇÃO']
        consolidated_df = pd.merge(
            consolidated_df, dataframes['ADMISSAO_ABRIL'][admissao_cols], on='MATRICULA', how='left'
        )

    if 'DIAS_UTEIS' in dataframes:
        dias_uteis_df = dataframes['DIAS_UTEIS'].copy()
        if 'SINDICADO' in dias_uteis_df.columns:
            dias_uteis_df.rename(columns={'SINDICADO': 'Sindicato'}, inplace=True)
        elif 'Sindicato' not in dias_uteis_df.columns:
            st.warning("Coluna 'Sindicato' ou 'SINDICADO' não encontrada em DIAS_UTEIS. Pulando junção.")
            dias_uteis_df['Sindicato'] = None
        required_cols = ['Sindicato', 'DIAS UTEIS (DE 15/04 a 15/05)']
        if all(col in dias_uteis_df.columns for col in required_cols):
            consolidated_df = pd.merge(
                consolidated_df, dias_uteis_df[required_cols], on='Sindicato', how='left'
            )
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
    consolidated_df = consolidated_df[
        ~consolidated_df['MATRICULA'].astype(str).isin(exclusao_matriculas)
    ]

    if 'Cargo' in consolidated_df.columns:
        consolidated_df = consolidated_df[
            ~consolidated_df['Cargo'].str.contains('diretor', case=False, na=False)
        ]

    return consolidated_df

def calcular_vr(df):
    # Define valor diário por sindicato - exemplo fixo, ajuste conforme necessário
    valor_diario_por_sindicato = {
        'Sindicato A': 30.0,
        'Sindicato B': 28.5,
        'Sindicato C': 25.0,
    }
    valor_padrao = 27.0

    df['VALOR DIÁRIO VR'] = df['Sindicato'].map(valor_diario_por_sindicato).fillna(valor_padrao)
    df['DIAS DE FERIAS'] = df['DIAS DE FERIAS'].fillna(0)
    df['DIAS UTEIS (DE 15/04 a 15/05)'] = df['DIAS UTEIS (DE 15/04 a 15/05)'].fillna(0)
    df['DIAS TRABALHADOS'] = df['DIAS UTEIS (DE 15/04 a 15/05)'] - df['DIAS DE FERIAS']

    # Total VR
    df['TOTAL VR'] = (df['VALOR DIÁRIO VR'] * df['DIAS TRABALHADOS']).clip(lower=0)

    # Calcula Custo Empresa e Desconto Profissional
    df['Custo Empresa'] = df['TOTAL VR'] * 0.8
    df['Desconto profissional'] = df['TOTAL VR'] * 0.2

    # Coluna de observações gerais
    def obs_gerais(row):
        obs = []
        if row.get('DATA DEMISSÃO'):
            obs.append(f"Desligado em {row['DATA DEMISSÃO']}")
        if row.get('COMUNICADO DE DESLIGAMENTO'):
            obs.append(f"Comunicado: {row['COMUNICADO DE DESLIGAMENTO']}")
        if row.get('SITUAÇÃO'):
            obs.append(f"Situação: {row['SITUAÇÃO']}")
        return '; '.join(obs)

    df['OBS GERAIS'] = df.apply(obs_gerais, axis=1)

    return df

def main():
    st.title("Calculadora Automática de VR Mensal com LangChain e Perplexity")

    uploaded_files = st.sidebar.file_uploader(
        "Selecione os arquivos Excel necessários", accept_multiple_files=True,
        type=['xlsx', 'xls']
    )
    if uploaded_files:
        with st.spinner("Carregando e consolidando bases..."):
            dataframes = carregar_excel_arquivos(uploaded_files)
            consolidated_df = consolidar_bases(dataframes)
            st.write("## Dados consolidados após limpeza e exclusões")
            st.dataframe(consolidated_df.head())

        pplx_api_key = st.sidebar.text_input("Chave API Perplexity", type="password")

        if pplx_api_key and st.button("Gerar VR Mensal"):
            with st.spinner("Processando cálculo do Vale Refeição..."):
                # Call LangChain here if needed, or skip and just calculate
                resultado_df = calcular_vr(consolidated_df)
                st.write("## Planilha final com cálculos de VR")
                st.dataframe(resultado_df.head())
                
                buffer = io.BytesIO()
                resultado_df.to_excel(buffer, index=False)
                buffer.seek(0)

                st.download_button(
                    label="Baixar arquivo Excel VR Mensal",
                    data=buffer,
                    file_name="VR_Mensal_Final.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

if __name__ == "__main__":
    main()
