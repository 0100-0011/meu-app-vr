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

        # Apenas exibe o dataframe simples para confirmação
        st.write("Base completa dos ativos:")
        st.dataframe(df)

        # Entrada da pergunta do usuário
        pergunta = st.text_input("Digite sua pergunta para a IA")

        # Só processa e mostra resultados após clique no botão
        if st.button("Consultar IA e gerar planilhas") and pergunta.strip() != "":
            # Calcula todos funcionários em férias
            ferias_df = df[df["DESC. SITUACAO"] == "Férias"]
            qtd_ferias = len(ferias_df)

            # Monta o resumo para o prompt IA
            resumo = (
                f"Número de funcionários na base: {len(df)}\n"
                f"Número de funcionários em férias: {qtd_ferias}\n\n"
                f"Amostra dos funcionários em férias:\n{ferias_df.head().to_string(index=False)}"
            )
            prompt = resumo + "\n\nPergunta: " + pergunta

            # Cria cliente ChatPerplexity
            chat = ChatPerplexity(
                temperature=0,
                pplx_api_key=st.secrets["pplx_api_key"],
                model="sonar"
            )
            resposta = chat.invoke([HumanMessage(content=prompt)])

            # Exibe resposta da IA
            st.markdown("### Resposta da IA:")
            st.write(resposta.content)

            # Exibe e oferece download dos funcionários em férias
            st.markdown(f"### Funcionários em férias ({qtd_ferias})")
            st.dataframe(ferias_df)

            towrite_ferias = io.BytesIO()
            ferias_df.to_excel(towrite_ferias, index=False, engine="openpyxl")
            towrite_ferias.seek(0)
            st.download_button(
                label="Baixar lista de funcionários em férias",
                data=towrite_ferias,
                file_name="funcionarios_ferias.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            # Geração do dataframe final com cabeçalhos específicos
            cols_desejadas = [
                "Matrícula",
                "Sindicato do Colaborador",
                "Competência",
                "Dias",
                "VALOR DIÁRIO VR",
                "TOTAL",
                "Custo Empresa",
                "Desconto profissional",
                "OBS GERAIS",
            ]

            # Ajuste o nome do dataframe final conforme seu código real
            # Exemplo usa 'consolidated_df' se existir, senão tenta 'df'
            df_final = dataframes.get("CONSOLIDATED_DF", df)

            # Verifica se as colunas existem para evitar erro
            cols_existe = [col for col in cols_desejadas if col in df_final.columns]
            df_cabecalhos = df_final[cols_existe]

            st.markdown("### Cabeçalho do dataframe final:")
            st.dataframe(df_cabecalhos.head())

            towrite_final = io.BytesIO()
            df_cabecalhos.to_excel(towrite_final, index=False, engine="openpyxl")
            towrite_final.seek(0)
            st.download_button(
                label="Baixar planilha com cabeçalhos específicos",
                data=towrite_final,
                file_name="dataframe_final_cabecalhos.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
else:
    st.info("Envie os arquivos Excel para iniciar.")
