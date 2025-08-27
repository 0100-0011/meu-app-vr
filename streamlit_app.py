import streamlit as st
import pandas as pd
import io
from langchain_perplexity import ChatPerplexity

def carregar_excel_arquivos(file_buffers):
    dataframes = {}
    for f in file_buffers:
        nome = f.name.split('.')[0]
        df = pd.read_excel(f)
        dataframes[nome] = df
    return dataframes

def consolidar_bases(dataframes):
    df = dataframes['ATIVOS'].copy()
    if 'FERIAS' in dataframes:
        df = df.merge(dataframes['FERIAS'][['MATRICULA','DESC. SITUACAO','DIAS FERIAS']], on='MATRICULA', how='left')
    if 'DESLIGADOS' in dataframes:
        desligados = dataframes['DESLIGADOS'][['MATRICULA ','DATA DEMISSÃO','COMUNICADO DE DESLIGAMENTO']]
        df = df.merge(desligados, left_on='MATRICULA', right_on='MATRICULA ', how='left').drop(columns=['MATRICULA '])
    if 'ADMISSAO_ABRIL' in dataframes:
        admissao = dataframes['ADMISSAO_ABRIL'][['MATRICULA','Admissão','Cargo','SITUAÇÃO']]
        df = df.merge(admissao, on='MATRICULA', how='left')
    if 'DIAS_UTEIS' in dataframes:
        dias_uteis = dataframes['DIAS_UTEIS'].copy()
        if 'SINDICADO' in dias_uteis.columns:
            dias_uteis = dias_uteis.rename(columns={'SINDICADO':'Sindicato'})
        if all(col in dias_uteis.columns for col in ['Sindicato','DIAS UTEIS (DE 15/04 a 15/05)']):
            df = df.merge(dias_uteis[['Sindicato','DIAS UTEIS (DE 15/04 a 15/05)']], on='Sindicato', how='left')
    exclusao = []
    def coletar_matriculas(df_, col='MATRICULA'):
        if df_ is not None and col in df_.columns:
            exclusao.extend(df_[col].dropna().astype(str).tolist())
    for tabela in ['ESTAGIARIOS','APRENDIZES','AFASTAMENTOS','EXTERIOR']:
        if tabela in dataframes:
            df_ = dataframes[tabela]
            if 'MATRICULA' in df_.columns:
                coletar_matriculas(df_)
            elif 'Matrícula' in df_.
