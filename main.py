import crawler
import pandas as pd
import xlsxwriter 
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import WebDriverException, SessionNotCreatedException
from datetime import datetime
import logging
import os
import nlp_utils
import glob

# --- CONFIGURAÇÃO DE LOGGING MANUAL E EXPLÍCITA ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Formatter para definir o formato da mensagem de log
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Handler para imprimir no terminal
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# Handler para escrever no arquivo
log_filename = f"pipeline_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def inicializar_driver():
    """
    Inicializa uma nova instância do ChromeDriver com opções para melhorar a estabilidade,
    usando um ChromeDriver baixado manualmente de um caminho específico.
    """
    try:
        driver_folder_path = r"C:\Users\SarahOgbonna\OneDrive - Ogilvy\Documents\Blog_99_Automacao\chromedriver-win64"
        driver_executable_path = os.path.join(driver_folder_path, "chromedriver.exe")
        
        service = ChromeService(driver_executable_path) 

        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--log-level=3')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36')

        driver = webdriver.Chrome(service=service, options=options)
        logger.info("✅ ChromeDriver inicializado com sucesso (modo headless com opções de estabilidade).")
        return driver
    except SessionNotCreatedException as e:
        logger.error(f"❌ Erro ao iniciar o ChromeDriver: {e}. Verifique a compatibilidade do Chrome e ChromeDriver ou o caminho especificado.")
        return None
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao inicializar o ChromeDriver: {e}")
        return None

def gerenciar_arquivos_log():
    """
    Remove arquivos de log antigos, mantendo apenas os 3 mais recentes.
    """
    try:
        lista_arquivos_log = glob.glob('pipeline_log_*.txt')
        lista_arquivos_log.sort(key=os.path.getmtime)
        arquivos_para_excluir = lista_arquivos_log[:-3]
        
        if arquivos_para_excluir:
            logger.info(f"Encontrados {len(arquivos_para_excluir)} arquivos de log antigos para exclusão.")
            for arquivo in arquivos_para_excluir:
                os.remove(arquivo)
                logger.info(f"Arquivo '{arquivo}' excluído com sucesso.")
        else:
            logger.info("Nenhum arquivo de log antigo foi encontrado para exclusão. Total de logs: 3 ou menos.")
    except Exception as e:
        logger.error(f"❌ Erro ao tentar gerenciar arquivos de log: {e}")

def main():
    try:
        logger.info("=========================================================")
        logger.info("Iniciando o pipeline de extração e análise de blog posts.")
        logger.info("=========================================================")

        logger.info("Etapa 1: Baixando URLs do sitemap do blog...")
        urls = crawler.baixar_sitemap_filtrado()

        historico_path = "historico_urls_processadas.txt"
        urls_processadas = set()
        if os.path.exists(historico_path):
            with open(historico_path, "r", encoding="utf-8") as f:
                urls_processadas = set(line.strip() for line in f if line.strip())
            logger.info(f"Histórico carregado: {len(urls_processadas)} URLs já processadas.")
        else:
            logger.info("Nenhum histórico anterior encontrado. Processando todas as URLs.")

        urls_novas = [u for u in urls if u not in urls_processadas]
        logger.info(f"Total de URLs novas a processar: {len(urls_novas)} (de {len(urls)})")

        if not urls_novas:
            logger.info("Nenhuma URL nova para processar. Pipeline encerrado.")
            return

        all_posts_data = []
        driver = None
        urls_processed_since_last_restart = 0
        RESTART_DRIVER_AFTER_N_URLS = 150

        logger.info("Etapa 2: Extraindo conteúdo dos blog posts...")
        import time
        for i, url in enumerate(urls_novas):
            if driver is None or urls_processed_since_last_restart >= RESTART_DRIVER_AFTER_N_URLS:
                if driver:
                    driver.quit()
                    logger.info(f"WebDriver encerrado após {urls_processed_since_last_restart} URLs. Reiniciando...")
                driver = inicializar_driver()
                if driver is None:
                    logger.error("Não foi possível inicializar o WebDriver. Pulando as URLs restantes.")
                    break
                urls_processed_since_last_restart = 0
            
            start_time = time.time()
            try:
                post_data = crawler.extrair_conteudo_da_url(url, driver)
                elapsed = time.time() - start_time
                logger.info(f"URL {i+1}/{len(urls_novas)}: {url} processada em {elapsed:.2f} segundos.")
                if post_data:
                    all_posts_data.append(post_data)
                    with open(historico_path, "a", encoding="utf-8") as f:
                        f.write(url + "\n")
                urls_processed_since_last_restart += 1
            except WebDriverException as e:
                elapsed = time.time() - start_time
                logger.error(f"❌ Erro do WebDriver para {url} após {elapsed:.2f} segundos. Detalhes: {e}. Tentando reiniciar o driver imediatamente.")
                if driver:
                    driver.quit()
                driver = None
                urls_processed_since_last_restart = 0
                continue
        
        if driver:
            driver.quit()

        logger.info("Etapa 3: Pós-processamento e exportação (aplicando a lógica de NLP)...")
        if all_posts_data:
            df_coleta = pd.DataFrame(all_posts_data)
            
            df_processado = nlp_utils.run_nlp_pipeline(df_coleta)
            df_processado['topic_cluster'] = df_processado['topic_clusters'].apply(lambda x: ', '.join(x) if x else 'Sem Cluster')
            
            colunas_finais = [
                'data_captura', 'data_publicacao', 'url', 'categoria', 'titulo',
                'resumo_meta', 'topic_cluster'
            ]
            df_novos_dados = df_processado[colunas_finais].copy()

            nome_arquivo = "blog99_resultado.xlsx"
            
            try:
                dict_abas = {}
                if os.path.exists(nome_arquivo):
                    logger.info(f"Arquivo '{nome_arquivo}' encontrado. Lendo abas existentes...")
                    dict_abas = pd.read_excel(nome_arquivo, sheet_name=None)
                    logger.info(f"Abas existentes: {list(dict_abas.keys())}")
                
                df_aba_dados = pd.concat([dict_abas.get('Dados Brutos', pd.DataFrame()), df_novos_dados], ignore_index=True)
                dict_abas['Dados Brutos'] = df_aba_dados.drop_duplicates(subset=['url'])
                
                df_99pay_novos = df_novos_dados[df_novos_dados['url'].str.contains('/blog/99pay', case=False, na=False)]
                df_aba_99pay = pd.concat([dict_abas.get('99Pay', pd.DataFrame()), df_99pay_novos], ignore_index=True)
                dict_abas['99Pay'] = df_aba_99pay.drop_duplicates(subset=['url'])

                df_motorista_novos = df_novos_dados[df_novos_dados['url'].str.contains('/blog/motorista|/blog/passageiro|/blog/99Moto', case=False, na=False)]
                df_aba_motorista = pd.concat([dict_abas.get('Motorista', pd.DataFrame()), df_motorista_novos], ignore_index=True)
                dict_abas['Motorista'] = df_aba_motorista.drop_duplicates(subset=['url'])
                
                with pd.ExcelWriter(nome_arquivo, engine='xlsxwriter') as writer:
                    for sheet_name, df_sheet in dict_abas.items():
                        df_sheet.to_excel(writer, sheet_name=sheet_name, index=False)
                        logger.info(f"✅ Dados exportados para a aba '{sheet_name}'.")

            except Exception as e:
                logger.error(f"❌ Falha ao exportar dados para Excel: {e}")
        else:
            logger.warning("Nenhum dado de post foi coletado para exportação.")

        logger.info("=========================================================")
        logger.info("Pipeline concluído.")
        logger.info("=========================================================")
    finally:
        # Encerra os handlers para garantir que o arquivo de log seja salvo
        for handler in logger.handlers:
            handler.close()
            logger.removeHandler(handler)
        
        gerenciar_arquivos_log()

if __name__ == "__main__":
    main()