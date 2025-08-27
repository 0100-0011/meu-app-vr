import streamlit as st
import pandas as pd
import io
from langchain_perplexity import ChatPerplexity
from langchain_core.messages import HumanMessage

st.title("App com API Perplexity e Planilhas")

dataframes = {}
uploaded_files = st.file_uploader(
    "Carregue arquivos Excel", type="xlsx", accept_multiple_files=True
)

if uploaded_files:
    for f in uploaded_files:
        df_name = f.name.split(".")[0].upper()
        dataframes[df_name] = pd.read_excel(f)
    if "ATIVOS" in dataframes:
        df = dataframes["ATIVOS"]
        st.write("Base completa dos ativos:")
        st.dataframe(df)

        # Calcula e exibe todos os funcionários de férias
        ferias_df = df[df["DESC. SITUACAO"] == "Férias"]
        qtd_ferias = len(ferias_df)
        st.markdown(f"### Funcionários em férias: {qtd_ferias}")
        st.dataframe(ferias_df)

        # Opcional: botão para baixar a lista de férias
        towrite = io.BytesIO()
        ferias_df.to_excel(towrite, index=False, engine="openpyxl")
        towrite.seek(0)
        st.download_button(
            label="Baixar lista de funcionários em férias",
            data=towrite,
            file_name="funcionarios_ferias.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        # Continuação: IA pode comentar sobre a política/fenômeno de férias baseada no resultado
        pergunta = st.text_input("Pergunte para a IA sobre esse grupo de funcionários ou sobre as férias:")
        if st.button("Consultar IA") and pergunta:
            chat = ChatPerplexity(
                temperature=0,
                pplx_api_key=st.secrets["pplx_api_key"],
                model="sonar"
            )
            prompt = f"Existem {qtd_ferias} funcionários em férias nesta base, conforme tabela a seguir:\n{ferias_df.head().to_string(index=False)}\n\nPergunta: {pergunta}"
            resposta = chat.invoke([HumanMessage(content=prompt)])
            st.write(resposta.content)
else:
    st.info("Envie os arquivos Excel para iniciar.")
