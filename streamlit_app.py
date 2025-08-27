import streamlit as st
import pandas as pd
from langchain_perplexity import ChatPerplexity
from langchain_core.messages import HumanMessage, SystemMessage

chat = ChatPerplexity(
    temperature=0,
    pplx_api_key=st.secrets["pplx_api_key"],
    model="sonar"
)

uploaded_files = st.file_uploader("Envie Excel", type="xlsx", accept_multiple_files=True)
if uploaded_files:
    # ...código para consolidar os dataframes...
    if "ATIVOS" in dataframes:
        df = dataframes["ATIVOS"]
        resumo = f"N.º funcionários: {len(df)}\nColunas: {list(df.columns)}\nAmostra:\n{df.head().to_string(index=False)}"
        pergunta = st.text_input("Digite sua pergunta")
        if st.button("Consultar IA") and pergunta:
            prompt = resumo + "\n\nPergunta: " + pergunta
            response = chat.invoke([HumanMessage(content=prompt)])
            st.write(response.content)
else:
    st.info("Envie os arquivos Excel para iniciar.")
