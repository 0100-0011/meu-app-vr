import streamlit as st
import pandas as pd
import io
import requests

# Função para chamar a API Perplexity - ajuste URL e API key
def call_perplexity_api(prompt: str) -> str:
    api_key = st.secrets["PERPLEXITY_API_KEY"]
    headers = {"Authorization": f"Bearer {api_key}"}
    url = "https://api.perplexity.ai/chat/completions"
    data = {"query": prompt}
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    return response.json().get("answer", "")

st.title("Consolidação VR integrada com Perplexity")

uploaded_files = st.file_uploader(
    "Envie arquivos Excel/CSV", type=['xlsx','csv'], accept_multiple_files=True)

dataframes = {}
if uploaded_files:
    for uf in uploaded_files:
        if uf.name.endswith('.xlsx'):
            dataframes[uf.name.split('.')[0]] = pd.read_excel(uf)
        else:
            dataframes[uf.name.split('.')[0]] = pd.read_csv(uf)
    st.success(f"{len(dataframes)} arquivos carregados.")

user_command = st.text_input("Digite seu comando para análise:")

if user_command and st.button("Enviar à API Perplexity"):
    answer = call_perplexity_api(user_command)
    st.markdown("**Resposta do agente:**")
    st.write(answer)

    # Simples lógica para executar consolidação caso o usuário queira:
    if "consolida" in user_command.lower() and 'ATIVOS' in dataframes:
        consolidated_df = dataframes['ATIVOS'].copy()
        if 'FERIAS' in dataframes:
            ferias_cols = ['MATRICULA', 'DESC. SITUACAO', 'DIAS DE FERIAS']
            consolidated_df = pd.merge(consolidated_df, dataframes['FERIAS'][ferias_cols],
                                       on='MATRICULA', how='left')
        # Acrescente suas demais etapas de consolidação aqui

        st.dataframe(consolidated_df.head())
        towrite = io.BytesIO()
        consolidated_df.to_excel(towrite, index=False, engine='openpyxl')
        towrite.seek(0)
        st.download_button(
            "Download Excel Consolidado",
            towrite,
            "consolidado_vr.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
