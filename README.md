LEIA SOBRE - Funcionamento dos Scripts e Bibliotecas

Este projeto automatiza a extração, processamento, análise e exportação de posts do blog da 99App. Abaixo está um resumo da lógica de cada script principal e as bibliotecas necessárias.

---

🏗️ Arquitetura da Solução
O projeto é modular, garantindo que cada etapa do processamento seja executada com eficiência e facilidade de manutenção:

1. Orquestração e Extração

 main.py
- Orquestra todo o pipeline: baixa URLs do sitemap, verifica histórico, extrai conteúdo dos posts, aplica NLP, exporta para Excel e gerencia logs.
- Inicializa o ChromeDriver para navegação automatizada.
- Garante que URLs já processadas não sejam repetidas.
- Exporta os dados para múltiplas abas no Excel: Dados Brutos, Motorista, 99Pay.

crawler.py
- Baixa e filtra URLs do sitemap.
- Extrai título, resumo, data de publicação e conteúdo dos posts usando Selenium e Newspaper3k.
- Categoriza cada URL.

2. Inteligência e NLP

nlp_utils.py
- Aplica processamento de linguagem natural (NLP) usando spaCy e scikit-learn.
- Identifica topic clusters para cada post com base em palavras-chave.
- Gera a coluna 'topic_clusters' para análise temática dos posts.

3. Exportação e Gestão

exportador.py
- Exporta o DataFrame final para um arquivo Excel (.xlsx) com múltiplas abas.
- Aba 'Motorista' inclui URLs de /blog/motorista e /blog/99moto.
- Aba '99Pay' inclui URLs de /blog/99pay.
- Aba 'Dados Brutos' contém todos os dados.

gera_historico_urls_do_excel.py (executado uma única vez)
- Este script é utilizado para gerar o arquivo de histórico de URLs processadas a partir de um Excel já existente, normalmente apenas uma vez para inicializar o histórico.
- O arquivo de histórico (historico_urls_processadas.txt) é alimentado automaticamente toda vez que o main.py roda, evitando reprocessamento de URLs já tratadas.

Reextrai_urls_com_erro.py (executado separadamente)
- Este script é chamado de forma independente, fora do fluxo principal do main.py.
- Serve para reprocessar URLs que apresentaram erro na extração anterior, utilizando o crawler e exportador para tentar novamente e salvar resultados.

---

🧠 Decisões Técnicas e Curadoria Humana
Diferente de uma abordagem puramente automatizada, este projeto utiliza uma metodologia de IA assistida para garantir resultados acionáveis:

Taxonomia Direcionada: Para superar as limitações de criatividade de modelos genéricos, desenvolvi uma biblioteca própria de palavras-chave de contexto. O modelo busca nessa "biblioteca" os termos que melhor se encaixam no conteúdo lido, garantindo uma categorização fiel ao universo de negócios da 99.

Otimização por Meta-Descrição: Por decisão de engenharia e performance, o script realiza a categorização a partir da leitura das meta-descrições. Isso garante a captura do resumo estratégico do post e otimiza o tempo de processamento sem perda de qualidade na clusterização.

Escalabilidade de Dados: O pipeline foi capaz de processar quase 1.000 posts históricos. Na execução inicial, o script operou por 11 horas ininterruptas, um investimento de tempo computacional que substitui um esforço manual que seria humanamente inviável, mantendo a padronização total da base.


Bibliotecas que precisam ser instaladas (requirements.txt) e seus propósitos:

1. pandas, numpy: Manipulação e análise de dados em DataFrames e arrays.
2. openpyxl, xlsxwriter: Leitura e escrita de arquivos Excel (.xlsx).
3. selenium, webdriver-manager: Automação de navegação web para extração de conteúdo dos posts. O WebDriver pode variar conforme o sistema e recursos disponíveis (ex: Chrome, Firefox, Edge).
4. beautifulsoup4, lxml: Extração e parsing de HTML para obter informações dos posts.
5. requests: Requisições HTTP para baixar o sitemap e páginas web.
6. newspaper3k: Extração alternativa de conteúdo de notícias/posts.
7. scikit-learn, scipy: Algoritmos de machine learning e cálculos de similaridade para análise de tópicos.
8. spacy, sentence-transformers: Processamento de linguagem natural (NLP) para identificar clusters temáticos. O modelo NLP pode ser ajustado conforme o sistema e memória disponível (ex: modelos menores ou maiores, GPU/CPU).
9. python-dateutil, pytz: Manipulação de datas e fusos horários.
10. logging (nativo do Python): Registro de logs do pipeline e dos scripts.
11. Outros utilitários: Auxiliam em tarefas específicas conforme listados no requirements.txt.

Observação importante:
- A escolha do WebDriver (selenium) e do modelo NLP (spaCy, transformers) pode variar conforme o sistema operacional, memória RAM e recursos disponíveis. Avalie o que melhor atende ao seu ambiente para garantir performance e compatibilidade.

Para instalar todas as dependências, execute:
    pip install -r requirements.txt

---


Resumo do fluxo:
1. main.py inicia o pipeline, baixa URLs e extrai dados.
2. crawler.py faz a extração e categorização dos posts.
3. nlp_utils.py aplica análise de tópicos (NLP).
4. exportador.py exporta os dados processados para Excel com abas temáticas.
5. Scripts auxiliares (reextrai_urls_com_erro.py e gera_historico_urls_do_excel.py) são executados separadamente conforme necessidade.

Consulte cada script para detalhes específicos de parâmetros e funções.