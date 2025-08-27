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
    # resto das operações conforme antes...
    return consolidated_df

def gerar_vr_com_langchain(consolidated_df: pd.DataFrame, pplx_api_key: str) -> pd.DataFrame:
    resumo_texto = (
        "Calcule o Vale Refeição mensal para os colaboradores conforme os dados:\n"
        "Sindicato, dias úteis, dias de férias, afastamentos, desligamentos, admissões e valor diário por sindicato.\n"
        "Siga as regras de custo 80% empresa, 20% desconto profissional, proporcionalidade para desligados."
    )
    system_msg = "Você é um assistente especializado em RH e folha de pagamento."
    dados_dict = consolidated_df.to_dict(orient='records')
    prompt_text = f"{system_msg}\n{resumo_texto}\nDados: {dados_dict}"

    chat = ChatPerplexity(temperature=0, pplx_api_key=pplx_api_key, model="sonar")
    resposta = chat.invoke(prompt_text)
    return consolidated_df

def main():
    st.title("Calculadora Automática de VR Mensal com LangChain e Perplexity")
    uploaded_files = st.sidebar.file_uploader("Selecione os arquivos", accept_multiple_files=True, type=['xlsx', 'xls'])
    if uploaded_files:
        with st.spinner("Carregando e consolidando bases de dados..."):
            dataframes = carregar_excel_arquivos(uploaded_files)
            consolidated_df = consolidar_bases(dataframes)
            st.write("### Dados consolidados após limpeza e exclusões:")
            st.dataframe(consolidated_df.head())
        pplx_api_key = st.sidebar.text_input("Chave API Perplexity", type="password")
        if pplx_api_key and st.button("Gerar VR Mensal com LangChain + Perplexity"):
            with st.spinner("Consultando LangChain + Perplexity e calculando VR..."):
                vr_final_df = gerar_vr_com_langchain(consolidated_df, pplx_api_key)
                st.write("### Planilha final calculada de VR para envio:")
                st.dataframe(vr_final_df.head())
                buffer = io.BytesIO()
                vr_final_df.to_excel(buffer, index=False)
                buffer.seek(0)
                st.download_button(
                    label="Baixar arquivo Excel VR Mensal",
                    data=buffer,
                    file_name="VR_Mensal_Final.xlsx",
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )

if __name__ == "__main__":
    main()
