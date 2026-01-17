import pandas as pd
import crawler
import exportador
import logging
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium import webdriver
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def inicializar_driver():
    driver_folder_path = r"C:\\Users\\SarahOgbonna\\OneDrive - Ogilvy\\Documents\\Blog_99_Automacao\\chromedriver-win64"
    driver_executable_path = f"{driver_folder_path}\\chromedriver.exe"
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
    return driver

def reextrair_urls_com_erro(arquivo_txt, nome_saida="reextracao_resultado.xlsx"):
    with open(arquivo_txt, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    logger.info(f"Total de URLs para reextração: {len(urls)}")
    all_posts_data = []
    driver = inicializar_driver()
    for i, url in enumerate(urls):
        try:
            post_data = crawler.extrair_conteudo_da_url(url, driver)
            all_posts_data.append(post_data)
            logger.info(f"{i+1}/{len(urls)}: {url} extraída.")
        except WebDriverException as e:
            logger.error(f"Erro do WebDriver para {url}: {e}")
            driver.quit()
            time.sleep(2)
            driver = inicializar_driver()
        except Exception as e:
            logger.error(f"Erro inesperado para {url}: {e}")
    driver.quit()
    df = pd.DataFrame(all_posts_data)
    exportador.exportar_para_excel(df, nome_base=nome_saida.replace('.xlsx',''))
    logger.info(f"Arquivo exportado: {nome_saida}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python reextrai_urls_com_erro.py 'ULRS COM ERRO.txt' [saida.xlsx]")
    else:
        reextrair_urls_com_erro(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "reextracao_resultado.xlsx")
