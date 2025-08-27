import streamlit as st
import pandas as pd
import io
from langchain_perplexity import ChatPerplexity
from langchain_core.messages import HumanMessage

st.title("App Automação VR com Dados e IA")

dataframes = {}
uploaded_files = st.file_uploader(
    "Carregue arquivos Excel", type="xlsx", accept_multiple_files=True
)

def clean_columns(df):
    df.columns = df.columns.str.strip()
    return df

if uploaded_files:
    for f in uploaded_files:
        df_name = f.name.split(".")[0].upper()
        df = pd.read_excel(f)
        df = clean_columns(df)
        dataframes[df_name] = df
    st.success("Arquivos carregados e limpos com sucesso!")

    # Consolidar dados (seguindo seu fluxo e ajustes)
    consolidated_df = clean_columns(dataframes['ATIVOS'].copy())
    # (aplique os merges conforme já feito...)

    # Exemplo; adaptar merges adequadamente aqui

    # Gerar texto resumo para IA com informações importantes
    def resumo_para_ia(df):
        resumo = (
            f"Número total de funcionários: {len(df)}\n"
            f"Colunas: {list(df.columns)}\n"
            "Exemplo de linhas:\n"
            f"{df.head(5).to_string(index=False)}"
        )
        return resumo

    pergunta = st.text_input("Digite sua pergunta para a IA sobre os dados")

    chat = ChatPerplexity(
        temperature=0,
        pplx_api_key=st.secrets["pplx_api_key"],
        model="sonar"
    )

    if st.button("Perguntar à IA") and pergunta.strip():
        resumo = resumo_para_ia(consolidated_df)
        prompt = resumo + "\n\nPergunta: " + pergunta
        resposta = chat.invoke([HumanMessage(content=prompt)])
        st.markdown("### Resposta:")
        st.write(resposta.content)

    if st.button("Gerar e baixar planilha final VR"):
        # Geração do arquivo Excel conforme seu cálculo...
        calc_df = consolidated_df.copy()
        # Realize renomeações, cálculos e geracoes de colunas OBS GERAIS aqui

        # Exemplo simplificado para exportar o dataframe pronto
        towrite = io.BytesIO()
        calc_df.to_excel(towrite, index=False, engine="openpyxl")
        towrite.seek(0)
        st.download_button(
            label="Download planilha final",
            data=towrite,
            file_name="VR_Final.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Envie os arquivos Excel para iniciar.")
