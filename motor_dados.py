import pandas as pd

def pivotar_planilha(caminho_arq: str, colunas_id: list) -> pd.DataFrame:
    """ Transforma a planilha inserida que contenha o formado wide em
    tidy, ou seja, formato long
    
    Parâmetros:
    caminho_arq: Precisa ser uma string e que contenha o caminho para a planilha (csv ou xlsx)
    colunas_id: COlunas identificadoras, aquelas que permaneceram e não seram pivotadas
    """
    # Inserindo planilha
    df = pd.read_excel(caminho_arq)

    # Transformar os cabeçalhos em str
    df.columns = [str(col).split(' ')[0] if isinstance(col, pd.Timestamp) else
                str(col) for col in df.columns]
    # Transformação estrutural
    df_tidy = df.melt(
        id_vars=colunas_id,
        var_name='Data',
        value_name='Estagio'
    )
    # TIpagem
    df_tidy['Data'] = pd.to_datetime(df_tidy['Data'], errors='coerce')
    df_tidy = df_tidy.dropna(subset=['Data'])

    #Truncamento visual
    df_tidy["Data"] = df_tidy["Data"].dt.strftime('%Y-%m-%d')

    df_tidy['Estagio'] = df_tidy['Estagio'].astype(str).str.strip().str.upper()
    df_tidy.loc[~df_tidy['Estagio'].isin(['F','B']), 'Estagio'] = pd.NA
    df_tidy['Estagio'] = df_tidy['Estagio'].astype('category')

    return df_tidy.sort_values(by=colunas_id + ['Data']).reset_index(drop=True)


def gerar_sumarizacoes(df_tidy: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Recebe a base limpa e calcula as métricas"""

    # Garante que a data é lida corrente para realizar cálculos temporais
    df_temp = df_tidy.copy()
    df_temp['Data_Calc'] = pd.to_datetime(df_temp['Data'], format='%Y-%m-%d', errors='coerce')
    
    # ALerta de polinização
    # Encontra a data mais recente do dataset e subtrai 30 dias
    # data_maxima = df_temp['Data_Calc'].max()
    # ANCORA INTELIGENTE
    datas_com_dados = df_temp.loc[df_temp['Estagio'].isin(['F','B']), 'Data_Calc']

    # Captura a data exata do dia de hoje (Zerando as horas matematicamente)
    hoje = pd.Timestamp.today().normalize()

    if datas_com_dados.empty:
        # Planilha vazia (nunca preenchida)
        data_maxima = hoje
    else:
        ultima_anotacao = datas_com_dados.max()
        # Arovre de decisão
        if ultima_anotacao > hoje:
            # Anti-Erro: A pessoa preencheu uma coluna no futuro
            data_maxima = hoje
        elif (hoje - ultima_anotacao).days <= 45:
            # Operação em funcionamento: Mesmo que não preencham há 2 semanas, o tempo continua contando
            data_maxima = hoje
        else:
            # Auditoria histórica
            data_maxima = ultima_anotacao
    janela_corte = data_maxima - pd.Timedelta(days=60)

    # Filtra o df apenas para o ultimo mes antes de agrupar
    df_recente = df_temp[df_temp['Data_Calc'] >= janela_corte].copy()
    
    # Cria a coluna da semana
    df_recente['Semana'] = df_recente['Data_Calc'].dt.to_period('W-MON').dt.start_time.dt.strftime('%Y-%m-%d')
    
    # Resumo semanal
    resumo_semanal = df_recente.groupby(['Semana', 'especie', 'matriz'], observed=True).agg(
        Estagios_Apresentados=('Estagio', lambda x: ', '.join(x.dropna().unique().astype(str))),
        ALERTA_POLINIZACAO=('Estagio', lambda x: (x == 'F').any()),
        Dias_com_F=('Estagio', lambda x: (x == 'F').sum())
    ).reset_index()

    resumo_semanal = resumo_semanal[resumo_semanal['Estagios_Apresentados'] != '']

    # DURAÇÃO DA FLORAÇÃO =============================================================================
    df_apenas_f = df_recente[df_recente['Estagio']== 'F']
    primeiro_f = df_apenas_f.groupby(['especie', 'matriz'], observed=True)['Data_Calc'].max().reset_index(name='Data_Primeiro_F')
    
    # Mescla as datas com o resumo semanal
    resumo_semanal = resumo_semanal.merge(primeiro_f, on=['especie', 'matriz'], how='left')

    # Calcula a duração contínua
    resumo_semanal['Dias_Desde_Inicio_Floracao'] = (data_maxima - resumo_semanal['Data_Primeiro_F']).dt.days

    # Formatação limpa: Substituindo os NaN das matrizes sem o F por 0
    resumo_semanal['Dias_Desde_Inicio_Floracao'] = resumo_semanal['Dias_Desde_Inicio_Floracao'].fillna(0).astype(int)
    resumo_semanal['Data_Primeiro_F'] = resumo_semanal['Data_Primeiro_F'].dt.strftime('%Y-%m-%d').fillna('N/A')

    # COpia a data para as linhas apenas onde o 'Estagio' não é nulo ==================================
    df_temp['Data_Valida'] = df_temp['Data_Calc'].where(df_temp['Estagio'].notna())

    # Plantas que nunca floresceram 
    historico = df_temp.groupby(['especie', 'matriz'], observed=True).agg(
        # Lista todos os estágios que a matriz ja teve
        estagios_historicos=('Estagio', lambda x: ', '.join(x.dropna().unique().astype(str))),

        # Dias efetivamente avaliada
        dias_avaliados=('Estagio', lambda x: x.dropna().count()),
        
        Ja_Floresceu=('Estagio', lambda x: (x == 'F').any()),
        # Rigor estatístico, min a max aplicados somente nas datas em que houveram observações
        Primeira_Observacao=('Data_Valida', 'min'),
        Ultima_Observacao=('Data_Valida', 'max')
    ).reset_index()
    # Transformação tardia
    historico['Primeira_Observacao'] = historico['Primeira_Observacao'].dt.strftime('%Y-%m-%d')
    historico['Ultima_Observacao'] = historico['Ultima_Observacao'].dt.strftime('%Y-%m-%d')
    matrizes_nunca_floresceram = historico[~historico['Ja_Floresceu']].drop(columns=['Ja_Floresceu'])

    return resumo_semanal, matrizes_nunca_floresceram