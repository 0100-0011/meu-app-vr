import streamlit as st
import pandas as pd
import io

# Cria cliente com chave segura
chat = ChatPerplexity(
    temperature=0,
    pplx_api_key=st.secrets["pplx_api_key"],
    model="sonar"
)

st.title("App com API Perplexity e Planilhas")

uploaded_files = st.file_uploader("Envie Excel", type="xlsx", accept_multiple_files=True)

if uploaded_files:
    dataframes = {}
    for f in uploaded_files:
        n = f.name.split(".")[0].upper()
        dataframes[n] = pd.read_excel(f)

    if "ATIVOS" in dataframes:
        consolidated_df = dataframes["ATIVOS"].copy()
        st.dataframe(consolidated_df)

        summary = (
            f"Número funcionários: {len(consolidated_df)}\n"
            f"Colunas: {list(consolidated_df.columns)}\n"
            f"Amostra:\n{consolidated_df.head().to_string(index=False)}"
        )

        pergunta = st.text_input("Digite sua pergunta")

        if st.button("Enviar para Perplexity") and pergunta:
            prompt = summary + "\n\nPergunta: " + pergunta
            resposta = chat([HumanMessage(content=prompt)])
            st.markdown("### Resposta:")
            st.write(resposta)

        towrite = io.BytesIO()
        consolidated_df.to_excel(towrite, index=False, engine="openpyxl")
        towrite.seek(0)
        st.download_button(
            "Baixar planilha consolidada",
            towrite,
            file_name="consolidado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
else:
    st.info("Envie os arquivos Excel para iniciar.")
