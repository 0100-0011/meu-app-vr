import streamlit as st
import pandas as pd
import io
from langchain_perplexity import ChatPerplexity
from langchain_core.messages import HumanMessage

st.title("App com API Perplexity e Planilhas")

# Sempre defina a variável antes
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
        st.write(df)

        # Seu código de prompt e chamada ao Perplexity...
        # exemplo:
        resumo = f"N.º funcionários: {len(df)}\nColunas: {list(df.columns)}\nAmostra:\n{df.head().to_string(index=False)}"
        pergunta = st.text_input("Digite sua pergunta")
        if st.button("Consultar IA") and pergunta:
            chat = ChatPerplexity(
                temperature=0,
                pplx_api_key=st.secrets["pplx_api_key"],
                model="sonar"
            )
            prompt = resumo + "\n\nPergunta: " + pergunta
            resposta = chat.invoke([HumanMessage(content=prompt)])
            st.write(resposta.content)
else:
    st.info("Envie os arquivos Excel para iniciar.")
