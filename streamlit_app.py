from langchain import LLMChain, PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.callbacks import get_openai_callback
from langchain.chat_models import ChatModel
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain_experimental.chat import ChatCompletion

from langchain_perplexity import ChatPerplexity

def gerar_resposta(llm, system_message, user_message):
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]
    # Chamando generate explicitamente com mensagens
    response = llm.generate(messages)
    return response.generations[0][0].text

def gerar_vr_com_langchain(df):
    # Construir prompt
    sistema = "Você é um assistente especializado em RH e folha de pagamento."
    user_content = f"Calcule o VR conforme as regras (80% empresa, 20% desconto), dado:\n{df.head(10).to_dict()}"

    # Ler token
    api_key = st.secrets["PPLX_API_KEY"]
    llm = ChatPerplexity(temperature=0, openai_api_key=api_key, model="sonar")

    resposta = gerar_resposta(llm, sistema, user_content)
    # Aqui pode parsear resposta e aplicar no df
    return df

# Fluxo principal (similar ao seu código)
def main():
    st.title("Calculadora Automática VR")
    files = st.file_uploader("Upload arquivos Excel", accept_multiple_files=True, type=["xls","xlsx"])
    if files:
        with st.spinner("Carregando..."):
            data = carregar_arquivos(files)
            consolidad = consolidar_bases(data)
            st.dataframe(consolidad.head())

        if st.button("Gerar VR"):
            with st.spinner("Gerando VR..."):
                resultado = gerar_vr_com_langchain(consolidad)
                resultado = calcular_vr(resultado)
                st.dataframe(resultado.head())
                buffer = io.BytesIO()
                resultado.to_excel(buffer, index=False)
                buffer.seek(0)
                st.download_button("Baixar Excel", data=buffer,
                                   file_name="resultado_vr.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == "__main__":
    main()
