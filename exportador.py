import pandas as pd
from datetime import datetime
import os
import logging # Importa o módulo de logging

# Pega o logger para este módulo (exportador.py)
logger = logging.getLogger(__name__)

def exportar_para_excel(df_posts, nome_base="blog99_resultado"):
    """
    Exporta o DataFrame com os posts processados para um arquivo .xlsx com um nome fixo.
    Inclui validações para garantir que o DataFrame não está vazio.
    As colunas são exportadas na ordem especificada pelo usuário, sem a coluna 'conteudo'.

    Args:
        df_posts (pd.DataFrame): DataFrame do pandas com os dados tratados.
        nome_base (str): Nome base do arquivo Excel (sem extensão).

    Returns:
        str: Caminho completo do arquivo gerado ou None se falhar/vazio.
    """
    if df_posts.empty:
        logger.warning("🚫 Nenhum post processado para exportar. O arquivo Excel não será criado.")
        return None

    try:
        nome_arquivo = f"{nome_base}.xlsx" # Nome fixo, sem data/hora

        # --- CORREÇÃO: Ordem EXATA das colunas conforme sua solicitação e REMOÇÃO de 'conteudo' ---
        colunas_ordenadas = [
            'data_captura',
            'data_publicacao',
            'url',
            'categoria',
            'titulo',
            'resumo_meta',
            'topic_cluster'
        ]
        # --- FIM DA CORREÇÃO ---

        # Garante que todas as colunas existentes no DataFrame estejam na lista.
        # Se houver alguma coluna no DataFrame que não está na colunas_ordenadas (e.g., uma nova adicionada no futuro),
        # ela será adicionada ao final para evitar perda de dados.
        final_cols = [col for col in colunas_ordenadas if col in df_posts.columns]
        for col in df_posts.columns:
            if col not in final_cols:
                final_cols.append(col)
                logger.warning(f"Coluna '{col}' não estava na ordem predefinida e foi adicionada ao final.")


        df_para_excel = df_posts[final_cols].copy() # Cria uma cópia para evitar SettingWithCopyWarning

        # Filtra Motorista: urls que contenham /blog/motorista ou /blog/99moto
        motorista_mask = df_para_excel['url'].str.contains(r"/blog/(motorista|99moto)", case=False, na=False)
        df_motorista = df_para_excel[motorista_mask].copy()

        # Filtra 99Pay: urls que contenham /blog/99pay
        pay_mask = df_para_excel['url'].str.contains(r"/blog/99pay", case=False, na=False)
        df_99pay = df_para_excel[pay_mask].copy()

        # Exporta para Excel com múltiplas abas
        with pd.ExcelWriter(nome_arquivo, engine='xlsxwriter') as writer:
            df_para_excel.to_excel(writer, sheet_name='Dados Brutos', index=False)
            df_motorista.to_excel(writer, sheet_name='Motorista', index=False)
            df_99pay.to_excel(writer, sheet_name='99Pay', index=False)

        logger.info(f"✅ Arquivo Excel exportado com sucesso: '{nome_arquivo}' (3 abas)")
        logger.info(f"Aba 'Dados Brutos': {len(df_para_excel)} linhas")
        logger.info(f"Aba 'Motorista': {len(df_motorista)} linhas")
        logger.info(f"Aba '99Pay': {len(df_99pay)} linhas")
        logger.debug(f"Colunas exportadas na ordem: {list(df_para_excel.columns)}")
        return nome_arquivo

    except Exception as e:
        logger.exception(f"❌ ERRO GRAVE: Falha ao exportar dados para o arquivo Excel '{nome_arquivo}'. Detalhes: {e}")
        return None