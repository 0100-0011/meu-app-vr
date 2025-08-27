import streamlit as st
import pandas as pd
import io
from langchain_perplexity import ChatPerplexity
from langchain_core.messages import HumanMessage

st.title("App Automação VR com Consolidação Segura e IA")

dataframes = {}
uploaded_files = st.file_uploader(
    "Carregue arquivos Excel", type="xlsx", accept_multiple_files=True
)

def clean_columns(df):
    """Remove espaços e padroniza nomes das colunas para maiúsculas sem espaços no início/fim."""
    df.columns = df.columns.str.strip()
    return df

if uploaded_files:
    for f in uploaded_files:
        df_name = f.name.split(".")[0].upper()
        df = pd.read_excel(f)
        df = clean_columns(df)  # Limpa colunas ao carregar
        dataframes[df_name] = df
    st.success("Arquivos carregados e limpos com sucesso!")

    # Consolidação dos dados
    consolidated_df = clean_columns(dataframes['ATIVOS'].copy())

    # Unifica FERIAS
    if 'FERIAS' in dataframes:
        ferias_cols = ['MATRICULA', 'DESC. SITUACAO', 'DIAS DE FERIAS']
        ferias_df = clean_columns(dataframes['FERIAS'][ferias_cols])
        consolidated_df = pd.merge(consolidated_df, ferias_df, on='MATRICULA', how='left', suffixes=('', '_FERIAS'))

    # Unifica DESLIGADOS
    if 'DESLIGADOS' in dataframes:
        desligados_cols = ['MATRICULA', 'DATA DEMISSÃO', 'COMUNICADO DE DESLIGAMENTO']
        desligados_df = clean_columns(dataframes['DESLIGADOS'][desligados_cols])
        consolidated_df = pd.merge(consolidated_df, desligados_df, on='MATRICULA', how='left', suffixes=('', '_DESLIGADOS'))

    # Unifica ADMISSAO_ABRIL
    if 'ADMISSAO_ABRIL' in dataframes:
        admissao_cols = ['MATRICULA', 'Admissão', 'Cargo', 'SITUAÇÃO']
        admissao_df = clean_columns(dataframes['ADMISSAO_ABRIL'][admissao_cols])
        consolidated_df = pd.merge(consolidated_df, admissao_df, on='MATRICULA', how='left', suffixes=('', '_ADMISSAO'))

    # Unifica DIAS_UTEIS
    if 'DIAS_UTEIS' in dataframes:
        dias_uteis_df = clean_columns(dataframes['DIAS_UTEIS'])
        dias_uteis_df.rename(columns={'SINDICADO': 'Sindicato'}, inplace=True)
        # Procurar por coluna de dias uteis com nome variável
        dias_cols_candidates = [col for col in dias_uteis_df.columns if 'DIAS UTEIS' in col.upper()]
        if dias_cols_candidates:
            dias_uteis_df.rename(columns={dias_cols_candidates[0]: 'DIAS_UTEIS'}, inplace=True)
            dias_uteis_cols = ['Sindicato', 'DIAS_UTEIS']
        else:
            dias_uteis_cols = ['Sindicato']

        dias_uteis_cols = [col for col in dias_uteis_cols if col in dias_uteis_df.columns]
        consolidated_df = pd.merge(consolidated_df, dias_uteis_df[dias_uteis_cols], on='Sindicato', how='left')

    st.markdown("### Dados consolidados prontos.")

    pergunta = st.text_input("Pergunte sobre os dados da planilha")

    chat = ChatPerplexity(
        temperature=0,
        pplx_api_key=st.secrets["pplx_api_key"],
        model="sonar"
    )

    if st.button("Consultar IA") and pergunta.strip() != "":
        resumo = (
            f"Número total de funcionários: {len(consolidated_df)}\n"
            f"Colunas disponíveis: {list(consolidated_df.columns)}\n"
            f"Amostra de dados:\n{consolidated_df.head(5).to_string(index=False)}"
        )
        prompt = resumo + "\n\nPergunta: " + pergunta
        resposta = chat.invoke([HumanMessage(content=prompt)])
        st.markdown("### Resposta da IA:")
        st.write(resposta.content)

    if st.button("Gerar e baixar planilha final VR"):
        calc_df = consolidated_df.copy()
        # Padronizar colunas para evitar KeyError
        calc_df.columns = calc_df.columns.str.strip()
        # Determinar a coluna 'Total_VR' ou alternativa
        if 'Total_VR' not in calc_df.columns and 'TOTAL' in calc_df.columns:
            calc_df.rename(columns={'TOTAL': 'Total_VR'}, inplace=True)

        # Cálculos
        if 'Total_VR' in calc_df.columns:
            calc_df['Custo Empresa'] = calc_df['Total_VR'] * 0.80
            calc_df['Desconto profissional'] = calc_df['Total_VR'] * 0.20
        else:
            st.warning("Coluna 'Total_VR' não encontrada para calcular custos.")

        # Renomeações finais para layout
        calc_df.rename(columns={
            'MATRICULA': 'Matrícula',
            'Sindicato': 'Sindicato do Colaborador',
            'Final_Working_Days': 'Dias',
            'VR_Daily_Value': 'VALOR DIÁRIO VR',
            'Total_VR': 'TOTAL'
        }, inplace=True)

        calc_df['Competência'] = '05.2025'

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

        if all(col in calc_df.columns for col in colunas_final):
            final_df = calc_df[colunas_final]
        else:
            st.warning("Algumas colunas finais estão ausentes; exibindo as disponíveis.")
            cols_disponiveis = [col for col in colunas_final if col in calc_df.columns]
            final_df = calc_df[cols_disponiveis]

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
