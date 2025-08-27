import streamlit as st
import pandas as pd
import io
import os
from langchain_perplexity import ChatPerplexity
from langchain_core.messages import HumanMessage

st.title("App Automação VR com Perguntas e Geração de Planilha Final")

# Mantém os dataframes carregados
dataframes = {}
uploaded_files = st.file_uploader(
    "Carregue arquivos Excel", type="xlsx", accept_multiple_files=True
)

if uploaded_files:
    for f in uploaded_files:
        df_name = f.name.split(".")[0].upper()
        dataframes[df_name] = pd.read_excel(f)
    st.success("Arquivos carregados com sucesso!")

    # Consolidação dos dados conforme seu script original
    consolidated_df = dataframes['ATIVOS'].copy()

    # Unifica FERIAS
    if 'FERIAS' in dataframes:
        ferias_cols = ['MATRICULA', 'DESC. SITUACAO', 'DIAS DE FERIAS']
        consolidated_df = pd.merge(consolidated_df, dataframes['FERIAS'][ferias_cols], on='MATRICULA', how='left', suffixes=('', '_FERIAS'))

    # Unifica DESLIGADOS
    if 'DESLIGADOS' in dataframes:
        desligados_cols = ['MATRICULA ', 'DATA DEMISSÃO', 'COMUNICADO DE DESLIGAMENTO']
        consolidated_df = pd.merge(consolidated_df, dataframes['DESLIGADOS'][desligados_cols], left_on='MATRICULA', right_on='MATRICULA ', how='left', suffixes=('', '_DESLIGADOS'))
        consolidated_df = consolidated_df.drop('MATRICULA ', axis=1)

    # Unifica ADMISSAO_ABRIL
    if 'ADMISSAO_ABRIL' in dataframes:
        admissao_cols = ['MATRICULA', 'Admissão', 'Cargo', 'SITUAÇÃO']
        consolidated_df = pd.merge(consolidated_df, dataframes['ADMISSAO_ABRIL'][admissao_cols], on='MATRICULA', how='left', suffixes=('', '_ADMISSAO'))

    # Unifica DIAS_UTEIS (renomeia para 'Sindicato')
    if 'DIAS_UTEIS' in dataframes:
        dias_uteis_df = dataframes['DIAS_UTEIS'].rename(columns={'SINDICADO': 'Sindicato'})
        dias_uteis_cols = ['Sindicato', 'DIAS UTEIS (DE 15/04 a 15/05)']
        consolidated_df = pd.merge(consolidated_df, dias_uteis_df[dias_uteis_cols], on='Sindicato', how='left')

    st.markdown("### Dados consolidados prontos.")

    # Entrada para pergunta da IA
    pergunta = st.text_input("Pergunte sobre os dados da planilha")

    # Instancia cliente Perplexity
    chat = ChatPerplexity(
        temperature=0,
        pplx_api_key=st.secrets["pplx_api_key"],
        model="sonar"
    )

    if st.button("Consultar IA") and pergunta.strip() != "":
        # Monta resumo básico para enviar à IA
        resumo = (
            f"Número total de funcionários: {len(consolidated_df)}\n"
            f"Colunas disponíveis: {list(consolidated_df.columns)}\n"
            f"Amostra de dados:\n{consolidated_df.head(5).to_string(index=False)}"
        )
        prompt = resumo + "\n\nPergunta: " + pergunta
        resposta = chat.invoke([HumanMessage(content=prompt)])
        st.markdown("### Resposta da IA:")
        st.write(resposta.content)

    # Botão para gerar e oferecer download da planilha final formatada
    if st.button("Gerar e baixar planilha final VR"):
        calc_df = consolidated_df.copy()

        # Cálculo dos custos
        calc_df['Custo Empresa'] = calc_df['Total_VR'] * 0.80
        calc_df['Desconto profissional'] = calc_df['Total_VR'] * 0.20

        # Renomeia colunas conforme especificado
        calc_df = calc_df.rename(columns={
            'MATRICULA': 'Matrícula',
            'Sindicato': 'Sindicato do Colaborador',
            'Final_Working_Days': 'Dias',
            'VR_Daily_Value': 'VALOR DIÁRIO VR',
            'Total_VR': 'TOTAL',
            'Custo Empresa': 'Custo Empresa',
            'Desconto profissional': 'Desconto profissional'
        })

        # Adiciona coluna competência
        calc_df['Competência'] = '05.2025'  # Pode ser parametrizado futuramente

        # Cria coluna OBS GERAIS
        def gerar_obs(row):
            obs = []
            if pd.notna(row.get('DESC. SITUACAO_FERIAS')) and row['DESC. SITUACAO_FERIAS'] == 'Férias':
                if pd.notna(row.get('DIAS DE FERIAS')):
                    obs.append(f"Férias: {int(row['DIAS DE FERIAS'])} dias.")
                else:
                    obs.append("Férias.")
            if pd.notna(row.get('Admissão')):
                obs.append(f"Admissão: Proporcional a partir de {row['Admissão'].strftime('%d-%m-%Y')}.")
            if pd.notna(row.get('DATA DEMISSÃO')):
                obs.append(f"Desligamento: Em {row['DATA DEMISSÃO'].strftime('%d-%m-%Y')}.")
            return " ".join(obs) if obs else ""

        calc_df['OBS GERAIS'] = calc_df.apply(gerar_obs, axis=1)

        # Seleciona e reordena colunas para saída final
        colunas_final = [
            'Matrícula',
            'Sindicato do Colaborador',
            'Competência',
            'Dias',
            'VALOR DIÁRIO VR',
            'TOTAL',
            'Custo Empresa',
            'Desconto profissional',
            'OBS GERAIS'
        ]
        final_df = calc_df[colunas_final]

        # Criação do arquivo Excel para download
        towrite = io.BytesIO()
        final_df.to_excel(towrite, index=False, engine='openpyxl')
        towrite.seek(0)

        st.download_button(
            label="Baixar planilha final de VR",
            data=towrite,
            file_name="VR_MENSAL_05_2025.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Envie os arquivos Excel para iniciar.")
