import streamlit as st
import pandas as pd

# Importando funções de outro arquivo

from motor_dados import pivotar_planilha, gerar_sumarizacoes

st.set_page_config(page_title="Monitoramento PPC", page_icon='🌱', layout='wide')

st.cache_data
def carregar_e_processar(arquivo_upload):
    """Executa o motor de dados em cache para não travar"""
    base_limpa = pivotar_planilha(arquivo_upload, ['seq', 'matriz', 'numero_pl', 'especie', 'polen_jun_22', 'coletar', 'observacoes', 'floresceu'])
    df_semanal, df_improdutivas = gerar_sumarizacoes(base_limpa)
    return base_limpa, df_semanal, df_improdutivas

st.sidebar.title("⚙️ Painel de Controle")
st.sidebar.markdown("Faça o upload da planilha atualizada gerada na coleta de dados")
arquivo_excel = st.sidebar.file_uploader("Selecione o arquivo Excel", type=["xlsx"])

st.title("🌱 Monitoramento do PPC")

if arquivo_excel is None:
    st.info("Aguardando o upload da base de dados para iniciar")
else:
    with st.spinner("Processando as matrizes e calculando janelas temporais..."):
        base_limpa, df_semanal, df_improdutivas = carregar_e_processar(arquivo_excel)
        alertas_urgentes = df_semanal[df_semanal['ALERTA_POLINIZACAO'] == True].copy()

        # tab1, tab2, tab3 = st.tabs(["🚨 Ação Imediata", " 📉 Matrizes improdutivas", "📊Auditoria"])

        st.sidebar.markdown("---")
        menu_selecionado = st.sidebar.radio(
            "Navegação",
            ["🚨 Ação Imediata", "📉 Matrizes improdutivas", "📊Auditoria"]
        )

        if menu_selecionado == "🚨 Ação Imediata":
            st.header("Matrizes Disponíveis para Coleta/Polinização")
            st.markdown("Plantas com estágio **'F'** na última janela de 60 dias")
            col1, col2 = st.columns(2)
            col1.metric("Total de Alertas ", len(alertas_urgentes))
            col2.metric("Espécies Distintas", alertas_urgentes['especie'].nunique() if not alertas_urgentes.empty else 0)

            if not alertas_urgentes.empty:
                # Incluindo novas colunas temporais na visualização
                colunas_visiveis = [
                    'Semana', 'especie', 'matriz',
                    'Data_Primeiro_F', 'Dias_com_F', 'Dias_Desde_Inicio_Floracao'
                ]
                st.dataframe(alertas_urgentes[colunas_visiveis], use_container_width=True, hide_index=True)
            else:
                st.success("Nenhuma matriz disponível para coleta/polinização")

        elif menu_selecionado == "📉 Matrizes improdutivas":
            st.header("Análise de Inatividade")
            # Filtros dinâmicos da aba 2
            c1, c2 = st.columns(2)
            with c1:
                filtro_esp_imp = st.multiselect("Pesquisar Espécie", options=df_improdutivas['especie'].unique())
            with c2:
                filtro_mat_imp = st.text_input("Buscar Nome/Número da Matriz:", placeholder="Ex: GG-100")
            # APlicação vetorizada dos filtros
            df_imp_filtrado = df_improdutivas.copy()
            if filtro_esp_imp:
                df_imp_filtrado = df_imp_filtrado[df_imp_filtrado['especie'].isin(filtro_esp_imp)]
            if filtro_mat_imp:
                df_imp_filtrado[df_imp_filtrado['matriz'].astype(str).str.contains(filtro_mat_imp, case=False, na=False)]

            st.metric("Total filtrado", len(df_imp_filtrado))
            st.dataframe(df_imp_filtrado, use_container_width=True, hide_index=True)

        elif menu_selecionado == "📊Auditoria":
            st.header("Base de dados")

            # Filtros dinâmicos aba 3
            c3, c4, c5 = st.columns(3)
            with c3:
                filtro_esp_tidy = st.multiselect("Pesquisar Espécie:", options=base_limpa['especie'].unique(), key='esp_tidy')
            with c4:
                filtro_mat_tidy = st.text_input("Buscar Matriz:", key='mat_tidy')
            with c5:
                filtro_est_tidy = st.multiselect("Estágio:", options=base_limpa['Estagio'].dropna().unique())
            
            # Aplicação vetorizada dos filtros
            df_tidy_filtrado = base_limpa.copy()
            if filtro_esp_tidy:
                df_tidy_filtrado = df_tidy_filtrado[df_tidy_filtrado['especie'].isin(filtro_esp_tidy)]
            if filtro_mat_tidy:
                df_tidy_filtrado = df_tidy_filtrado[df_tidy_filtrado['matriz'].astype(str).str.contains(filtro_mat_tidy, case=False, na=False)]
            if filtro_est_tidy:
                df_tidy_filtrado = df_tidy_filtrado[df_tidy_filtrado['Estagio'].isin(filtro_est_tidy)]
            
            st.dataframe(df_tidy_filtrado, use_container_width=True, hide_index=True)