import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import re
import logging
from newspaper import Article

# Importações Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

logger = logging.getLogger(__name__)

SITEMAP_URL = "https://99app.com/sitemap/main.xml"
EXCLUDE_KEYWORDS = ["author", "category", "tag"] # Mantidas, mas não utilizadas no filtro de URLs
SITEMAP_POST_FILTER = "/blog/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"
}

# --- Funções Auxiliares ---
def extrair_titulo(soup):
    title = soup.find('h1')
    if title:
        return title.get_text(strip=True)
    meta_title = soup.find('meta', attrs={'property': 'og:title'})
    if meta_title and meta_title.get('content'):
        return meta_title['content'].strip()
    logger.warning("Título não encontrado para o post.")
    return "Título Indisponível"

def extrair_resumo_meta(soup):
    meta_description = soup.find('meta', attrs={'name': 'description'})
    if meta_description and meta_description.get('content'):
        return meta_description['content'].strip()
    logger.warning("Resumo (meta description) não encontrado para o post.")
    return "Resumo Meta Indisponível"

def extrair_data_publicacao(soup):
    meta_pub_time = soup.find('meta', attrs={'property': 'article:published_time'})
    if meta_pub_time and meta_pub_time.get('content'):
        try:
            return datetime.fromisoformat(meta_pub_time['content'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            logger.warning("Formato de data de publicação inválido na meta tag.")

    time_tag = soup.find('time')
    if time_tag and time_tag.get('datetime'):
        try:
            return datetime.fromisoformat(time_tag['datetime']).strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            logger.warning("Formato de data de publicação inválido na tag <time>.")

    date_patterns = [
        re.compile(r'\b\d{1,2}\s+(?:de\s+)?(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+(?:de\s+)?\d{4}\b', re.IGNORECASE),
        re.compile(r'\b\d{4}-\d{2}-\d{2}\b'), # YYYY-MM-DD
        re.compile(r'\b\d{2}/\d{2}/\d{4}\b') # DD/MM/YYYY
    ]
    for tag in soup.find_all(['p', 'span', 'div', 'li']):
        text = tag.get_text(strip=True)
        for pattern in date_patterns:
            match = pattern.search(text)
            if match:
                try:
                    logger.debug(f"Data encontrada no texto: {match.group(0)}")
                    return match.group(0)
                except Exception:
                    pass

    logger.warning("Data de publicação não encontrada ou formato não reconhecido para o post.")
    return None

def extrair_conteudo_com_selenium(driver):
    selectors = [
        "article.entry-content",
        "div.entry-content",
        "div.post-content",
        "div.td-post-content",
        "main",
        "body"
    ]

    for selector in selectors:
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            element = driver.find_element(By.CSS_SELECTOR, selector)
            for undesirable_tag in element.find_elements(By.TAG_NAME, 'script') + \
                                   element.find_elements(By.TAG_NAME, 'style') + \
                                   element.find_elements(By.TAG_NAME, 'aside') + \
                                   element.find_elements(By.CSS_SELECTOR, 'figcaption'):
                driver.execute_script("arguments[0].remove();", undesirable_tag)
            return element.text
        except Exception:
            continue
    logger.warning("Não foi possível encontrar um seletor de conteúdo principal com Selenium.")
    return None

def extrair_com_newspaper(url):
    try:
        article = Article(url, language='pt')
        article.download()
        article.parse()
        published_date_str = None
        if article.publish_date:
            published_date_str = article.publish_date.strftime('%Y-%m-%d %H:%M:%S')

        logger.info(f"✅ Extração com newspaper3k bem-sucedida para: {url}")
        return {
            "titulo": article.title if article.title else "Título Indisponível (Newspaper)",
            "conteudo": article.text if article.text else "",
            "resumo_meta": article.meta_description if article.meta_description else "Resumo Meta Indisponível (Newspaper)",
            "data_publicacao": published_date_str
        }
    except Exception as e:
        logger.error(f"❌ Falha na extração com newspaper3k para {url}. Erro: {e}")
        return None

# --- Funções Principais do Crawler ---

# Função de categorização adicionada diretamente no crawler.py
def categorizar(url):
    """
    Categoriza a URL com base em palavras-chave presentes nela.
    """
    url = url.lower()
    if "motorista" in url:
        return "Motorista"
    elif "99pay" in url or "99-pay" in url:
        return "99Pay"
    elif "moto" in url:
        return "99Moto"
    elif "food" in url:
        return "99Food"
    else:
        return "Outros"

def baixar_sitemap_filtrado():
    logger.info(f"Processando sitemap: {SITEMAP_URL}")
    try:
        response = requests.get(SITEMAP_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "xml")

        all_urls = [loc.text.strip() for loc in soup.find_all("loc")]

        # Aplica o filtro exato da sua versão anterior que encontrava 752 posts
        # Esta regex busca URLs que contenham "/blog/" seguido de pelo menos um segmento não-barra, e terminando com barra.
        blog_urls = [url for url in all_urls if re.search(r"/blog/[^/]+/", url)]
        # Remove duplicatas preservando a ordem original
        from collections import OrderedDict
        blog_urls = list(OrderedDict.fromkeys(blog_urls))

        logger.info(f"🔎 Total de URLs encontradas no sitemap ({SITEMAP_URL}): {len(all_urls)}")
        logger.info(f"📌 Total de URLs de blog filtradas pelo padrão /blog/*/: {len(blog_urls)}")
        logger.info(f"❌ URLs ignoradas (fora do padrão /blog/*/): {len(all_urls) - len(blog_urls)}")

        return blog_urls

    except requests.exceptions.RequestException as e:
        logger.warning(f"❌ Erro ao baixar ou processar sitemap '{SITEMAP_URL}'. Detalhes: {e}")
        return [] # Retorna lista vazia em caso de erro
    except Exception as e:
        logger.exception(f"❌ Ocorreu um erro inesperado ao processar sitemap '{SITEMAP_URL}'. Detalhes: {e}")
        return [] # Retorna lista vazia em caso de erro

def extrair_conteudo_da_url(url, driver):
    """
    Extrai o título, conteúdo, resumo meta e data de publicação de uma única URL.
    Sempre retorna um dicionário, mesmo que a extração falhe, usando placeholders.
    """
    logger.info(f"Iniciando extração para URL: {url}")

    post_data = {
        "url": url,
        "titulo": "Título Indisponível",
        "conteudo": "Conteúdo Indisponível",
        "resumo_meta": "Resumo Meta Indisponível",
        "data_publicacao": "Data Indisponível",
        "data_captura": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "categoria": "Aguardando NLP" # Placeholder inicial antes da categorização
    }

    for tentativa in range(2):
        try:
            driver.get(url)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            post_data["titulo"] = extrair_titulo(soup)
            post_data["resumo_meta"] = extrair_resumo_meta(soup)
            post_data["data_publicacao"] = extrair_data_publicacao(soup)
            post_data["conteudo"] = extrair_conteudo_com_selenium(driver)

            if post_data["conteudo"] is None or len(post_data["conteudo"].split()) < 30:
                logger.warning(f"Conteúdo Selenium insuficiente ou não encontrado para {url}. Tentando fallback newspaper3k...")
                resultado_np = extrair_com_newspaper(url)
                if resultado_np:
                    post_data["titulo"] = resultado_np["titulo"]
                    post_data["conteudo"] = resultado_np["conteudo"]
                    post_data["resumo_meta"] = resultado_np["resumo_meta"]
                    post_data["data_publicacao"] = resultado_np["data_publicacao"]
                    logger.info(f"✅ Extração de conteúdo para {url} bem-sucedida (via Newspaper3k).")
                else:
                    logger.error(f"❌ {url} | Não foi possível extrair conteúdo nem com Selenium nem com newspaper3k. Usando placeholders.")
            else:
                logger.info(f"✅ Extração de conteúdo para {url} bem-sucedida (via Selenium).")

            # Chama a função de categorização após a extração
            post_data["categoria"] = categorizar(url)
            logger.info(f"✅ Post '{post_data['titulo']}' extraído e categorizado como '{post_data['categoria']}'.")
            return post_data

        except WebDriverException as e:
            if "invalid session id" in str(e).lower():
                logger.warning(f"Invalid session id para {url}. Reiniciando driver e tentando novamente.")
                try:
                    driver.quit()
                except Exception:
                    pass
                import time
                time.sleep(3)
                options = webdriver.ChromeOptions()
                options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                service = ChromeService(executable_path="chromedriver-win64/chromedriver-win64/chromedriver.exe")
                driver = webdriver.Chrome(service=service, options=options)
                continue
            else:
                logger.error(f"❌ Erro do WebDriver ao acessar {url}. Detalhes: {e}. Usando placeholders.")
                break
        except TimeoutException:
            logger.error(f"❌ Tempo esgotado (Timeout) ao carregar a URL: {url}. Usando placeholders.")
            break
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro de rede ao acessar {url}. Detalhes: {e}. Usando placeholders.")
            break
        except Exception as e:
            logger.exception(f"❌ Erro inesperado ao extrair conteúdo da URL: {url}. Detalhes: {e}. Usando placeholders.")
            break
    return post_data

# --- Função para reiniciar o driver com delay ---
import time
def reiniciar_driver_com_delay(driver):
    try:
        if driver:
            driver.quit()
    except Exception:
        pass
    time.sleep(3)
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # Caminho fixo para o chromedriver compatível
    service = ChromeService(executable_path="chromedriver-win64/chromedriver-win64/chromedriver.exe")
    new_driver = webdriver.Chrome(service=service, options=options)
    return new_driver