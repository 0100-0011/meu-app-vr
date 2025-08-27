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
    df = dataframes['ATIVOS'].copy()
    if 'FERIAS' in dataframes:
        df = df.merge(dataframes['FERIAS'][['MATRICULA','DESC. SITUACAO','DIAS FERIAS']], on='MATRICULA', how='left')
    if 'DESLIGADOS' in dataframes:
        desligados = dataframes['DESLIGADOS'][['MATRICULA ','DATA DEMISSÃO','COMUNICADO DE DESLIGAMENTO']]
        df = df.merge(desligados, left_on='MATRICULA', right_on='MATRICULA ', how='left').drop(columns=['MATRICULA '])
    if 'ADMISSAO_ABRIL' in dataframes:
        admissao = dataframes['ADMISSAO_ABRIL'][['MATRICULA','Admissão','Cargo','SITUAÇÃO']]
        df = df.merge(admissao, on='MATRICULA', how='left')
    if 'DIAS_UTEIS' in dataframes:
        dias_uteis = dataframes['DIAS_UTEIS'].copy()
        if 'SINDICADO' in dias_uteis.columns:
            dias_uteis = dias_uteis.rename(columns={'SINDICADO':'Sindicato'})
        if all(col in dias_uteis.columns for col in ['Sindicato','DIAS UTEIS (DE 15/04 a 15/05)']):
            df = df.merge(dias_uteis[['Sindicato','DIAS UTEIS (DE 15/04 a 15/05)']], on='Sindicato', how='left')
    exclusao = []
    def coletar_matriculas(df_, col='MATRICULA'):
        if df_ is not None and col in df_.columns:
            exclusao.extend(df_[col].dropna().astype(str).tolist())
    for tabela in ['ESTAGIARIOS','APRENDIZES','AFASTAMENTOS','EXTERIOR']:
        if tabela in dataframes:
            df_ = dataframes[tabela]
            if 'MATRICULA' in df_.columns:
                coletar_matriculas(df_)
            elif 'Matrícula' in df_.columns:
                coletar_matriculas(df_, 'Matrícula')
    df = df.loc[~df['MATRICULA'].astype(str).isin(exclusao)]
    if 'Cargo' in df.columns:
        df = df.loc[~df['Cargo'].str.contains('diretor', case=False, na=False)]
    return df

def calcular_vr(df):
    valores_estado = {'Paraná':35.0,'Rio de Janeiro':35.0,'Rio Grande do Sul':35.0,'São Paulo':37.5}
    padrao = 30.0
    df['VALOR DIÁRIO VR'] = df['ESTADO'].map(valores_estado).fillna(padrao)
    df['DIAS FERIAS'] = df['DIAS FERIAS'].fillna(0)
    df['DIAS UTEIS (DE 15/04 a 15/05)'] = df['DIAS UTEIS (DE 15/04 a 15/05)'].fillna(0)
    df['DIAS TRABALHADOS'] = df['DIAS UTEIS (DE 15/04 a 15/05)'] - df['DIAS FERIAS']
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

def gerar_vr_com_langchain(df):
    sistema = "Você é um assistente especializado em RH e folha de pagamento."
    pergunta = "Calcule o VR mensal com custo 80% empresa e 20% desconto, conforme dados:"
    dados = df.head(20).to_dict(orient='records')
    prompt = f"{sistema}\n{pergunta}\nDados: {dados}"

    token = st.secrets.get("PPLX_API_KEY")
    chat = ChatPerplexity(temperature=0, openai_api_key=token, model="sonar")

    resposta = chat.invoke(prompt)
    # Aqui você pode implementar parser da resposta para atualizar df

    return df

def main():
    st.title("Calculadora Vale Refeição Automática")

    arquivos = st.sidebar.file_uploader(
        "Faça upload dos arquivos Excel", accept_multiple_files=True, type=["xls", "xlsx"]
    )

    if arquivos:
        with st.spinner("Carregando e processando dados..."):
            data = carregar_excel_arquivos(arquivos)
            consolidado = consolidar_bases(data)
            st.write("Dados consolidados:")
            st.dataframe(consolidado.head())

        if st.button("Gerar VR Mensal"):
            with st.spinner("Calculando VR..."):
                df_langchain = gerar_vr_com_langchain(consolidado)
                resultado = calcular_vr(df_langchain)
                st.write("Planilha final com cálculos:")
                st.dataframe(resultado.head())

                buffer = io.BytesIO()
                resultado.to_excel(buffer, index=False)
                buffer.seek(0)

                st.download_button(
                    "Baixar planilha Excel",
                    data=buffer,
                    file_name="VR_Mensal.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )


if __name__ == "__main__":
    main()
