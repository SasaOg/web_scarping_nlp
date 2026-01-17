import pandas as pd
import numpy as np
import spacy
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Carregar o modelo spaCy para português
try:
    nlp = spacy.load("pt_core_news_sm")
    logger.info("✅ Modelo spaCy 'pt_core_news_sm' carregado com sucesso.")
except OSError:
    logger.error("❌ Modelo spaCy 'pt_core_news_sm' não encontrado. Baixando agora...")
    spacy.cli.download("pt_core_news_sm")
    nlp = spacy.load("pt_core_news_sm")
    logger.info("✅ Modelo spaCy 'pt_core_news_sm' baixado e carregado com sucesso.")

# --- DEFINIÇÃO DOS TOPIC CLUSTERS E SUAS PALAVRAS-CHAVE ---
# Dicionário que mapeia a categoria principal para um dicionário de Topic Clusters
# Cada Topic Cluster tem uma lista de palavras-chave associadas (case-insensitive)
# AJUSTE ESTE DICIONÁRIO COM SEUS PRÓPRIOS TOPIC CLUSTERS E PALAVRAS-CHAVE.
TOPIC_CLUSTERS_KEYWORDS = {
    "99Pay": {
        "Minhas Finanças": ["conta de luz", "conta de água", "economizar dinheiro", "gastos mensais", "planilha de gastos", "render dinheiro", "guardar dinheiro", "controle de gastos mensais", "planejamento financeiro familiar", "endividamento"],
        "Renda Extra": ["renda extra", "freelancer", "empreendedorismo", "microempreendedorismo"],
        "Quero Investir": ["CDI", "taxa selic", "lucratividade", "rendimento", "metas financeiras", "criptomoedas"],
        "Vida de empreendedor": ["empreendedorismo", "empreender", "negócios", "novos negócios"],
        "Tributos e Impostos": ["IPTU", "imposto de renda", "MEI", "ME", "restituição de imposto de renda", "DARF", "IPVA", "cartão de crédito"],
        "Notícias de Economia": ["tarifaço", "IOS", "economia", "dicas de economia", "notícias", "selic", "inflação"],
        "Meu Negócio": ["gestão financeira", "controle financiero", "MEI", "autônomo"],
        "Por Dentro da 99Pay": ["app da 99Pay", "funcionalidades", "lucratividade"],
        "Empréstimo": ["vantagens empréstimos 99Pay", "empréstimo 99Pay", "educação financeira", "crédito pessoal"],
        "Dinheiro Delas": ["mulheres empreendedoras", "mulheres chefes de casa", "empreendedora", "mães"]
    },
    "Motorista": {
        "Multas": ["multa", "infração", "legislação", "lei", "pontos na cnh", "blitz"],
        "Documentos": ["documento", "licenciamento", "regularização", "transferência", "detran", "papelada"],
        "Seguro": ["seguro", "proteção", "assistência", "apólice", "sinistro", "cobertura"],
        "CNH": ["cnh", "habilitação", "recurso", "pontuação", "suspensão", "renovação cnh"],
        "Impostos": ["impostos", "IPVA", "SPVAT", "tributo veicular", "taxas"],
        "Carros": ["tipos de carro", "chassi", "modelos", "veículo", "automóvel", "carro novo", "carro usado", "junta de cabeçote", "motor"], 
        "Manutenção": ["manutenção", "peças", "mecânica", "revisão", "troca de óleo", "pneu", "alinhamento", "balanceamento", "freios", "suspensão", "óleo", "filtro"], 
        "Segurança": ["segurança", "direção", "acidente", "saúde", "riscos", "prevenção", "direção segura"],
        "Combustível": ["combustível", "gasolina", "etanol", "diesel", "abastecer", "preço da gasolina"],
        "Compra de carro": ["compra de carro", "aluguel de carro", "consórcio", "financiamento de carro", "venda de carro", "leasing"]
    },
    "99Moto": {
        "Segurança Moto": ["segurança moto", "capacete", "equipamento moto", "pilotagem segura", "direção defensiva moto", "acidente moto"],
        "Manutenção Moto": ["manutenção moto", "pneu moto", "óleo moto", "revisão moto", "peças moto"],
        "Legislação Moto": ["cnh moto", "multa moto", "lei seca moto"],
        "Dicas de Pilotagem": ["pilotar moto", "motociclismo", "viagem de moto"],
        # ... outros para 99Moto
    },
    "99Food": {
        "Culinária e Receitas": ["receita", "culinária", "ingredientes", "cozinhar", "comida caseira", "pratos"],
        "Restaurantes e Bares": ["restaurante", "bar", "melhores lugares", "onde comer", "gastronomia", "delivery"],
        "Dicas de Alimentação": ["alimentação saudável", "dieta", "nutrição", "alimentos"],
        "Pedidos Online": ["pedido online", "aplicativo comida", "delivery de comida"],
        # ... outros para 99Food
    },
    "Outros": {
        "Notícias Gerais": ["notícias", "atualidade", "eventos", "novidades", "acontecimentos"],
        "Dicas Gerais": ["dicas", "tutoriais", "como fazer", "passo a passo", "guia"],
        "Tecnologia": ["tecnologia", "inovação", "aplicativos", "digital"],
        "Cultura e Lazer": ["filmes", "música", "livros", "entretenimento", "viagem", "lazer"],
        # ... outros genéricos para a categoria 'Outros'
    }
}


def preprocess_text(text):
    """Remove caracteres especiais, números e tokeniza/lemmatiza o texto."""
    if pd.isna(text) or not isinstance(text, str):
        return ""
    text = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚçÇâêîôûÂÊÎÔÛãõÃÕàèìòùÀÈÌÒÙ\s]', '', text) # Remove não-letras e números
    text = text.lower()
    doc = nlp(text)
    # Exclui stopwords e pontuação, retorna lemmas
    tokens = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct and token.is_alpha]
    return " ".join(tokens)

def calculate_similarity(text1, text2):
    """Calcula a similaridade de cosseno entre dois textos."""
    if not text1 or not text2:
        return 0.0
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([text1, text2])
    return cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

# --- FUNÇÃO PARA IDENTIFICAR TOPIC CLUSTERS ---
def identificar_topic_clusters_nlp(categoria_principal, titulo, resumo_meta):
    """
    Identifica topic clusters com base na categoria principal e nas palavras-chave
    presentes no título e meta-descrição.
    Inclui um fallback para gerar um cluster genérico se nenhum for encontrado.
    """
    identified_clusters = []
    
    # Concatena título e resumo_meta para formar o "contexto" de busca
    text_to_analyze_lower = "" # Versão em minúsculas para comparação
    if pd.notna(titulo) and isinstance(titulo, str):
        text_to_analyze_lower += titulo.lower() + " "
    if pd.notna(resumo_meta) and isinstance(resumo_meta, str):
        text_to_analyze_lower += resumo_meta.lower()

    if not text_to_analyze_lower.strip(): # Verifica se há algum texto útil
        # Se não há texto para analisar, atribui um cluster padrão
        return ["Sem Conteúdo"]

    # Busca topic clusters específicos para a categoria principal
    if categoria_principal in TOPIC_CLUSTERS_KEYWORDS:
        for cluster_name, keywords in TOPIC_CLUSTERS_KEYWORDS[categoria_principal].items():
            for keyword in keywords:
                # Compara a keyword em minúsculas com o texto em minúsculas
                if keyword.lower() in text_to_analyze_lower:
                    identified_clusters.append(cluster_name)
                    break # Encontrou uma keyword para este cluster, pode ir para o próximo cluster
    
    # Remove duplicatas
    identified_clusters = list(set(identified_clusters))

    # --- Lógica de Fallback (SÓ se NENHUM cluster específico for identificado) ---
    if not identified_clusters:
        if categoria_principal == "Outros":
            identified_clusters.append("Geral")
        elif categoria_principal in TOPIC_CLUSTERS_KEYWORDS:
            identified_clusters.append(f"{categoria_principal} - Genérico")
        else:
            identified_clusters.append("Cluster Desconhecido - Genérico")

    return identified_clusters


def run_nlp_pipeline(df):
    logger.info("Iniciando pipeline de NLP...")

    # A função identificar_topic_clusters_nlp já lida com os campos 'titulo' e 'resumo_meta'
    # diretamente, sem necessidade de pré-processamento para este fim específico.
    # As linhas abaixo podem ser comentadas/removidas se não forem usadas em outras partes
    # do seu pipeline NLP que dependam de texto processado.
    # df['conteudo_processado'] = df['conteudo'].apply(preprocess_text)
    # df['titulo_processado'] = df['titulo'].apply(preprocess_text)
    # df['resumo_meta_processado'] = df['resumo_meta'].apply(preprocess_text)

    # --- Aplica a função de identificação de Topic Clusters ---
    df['topic_clusters'] = df.apply(
        lambda row: identificar_topic_clusters_nlp(
            row['categoria'], # Usa a categoria já identificada pelo crawler
            row['titulo'],    # Usa o título original
            row['resumo_meta']# Usa a meta-descrição original
        ),
        axis=1
    )
    logger.info("✅ Topic clusters identificados (com fallback de categoria genérica).")

    logger.info("Pipeline de NLP concluído.")
    return df

# Exemplo de uso (Você provavelmente chamará isso do seu main.py ou posprocessa_excel.py)
if __name__ == "__main__":
    # Simula um DataFrame de entrada
    sample_data = {
        'url': [
            'https://99app.com/blog/99pay/como-investir-na-taxa-selic/',
            'https://99app.com/blog/motorista/dicas-sobre-multas-de-transito/',
            'https://99app.com/blog/99pay/ganhe-renda-extra-com-99pay/',
            'https://99app.com/blog/motorista/documentacao-para-seu-carro/',
            'https://99app.com/blog/outros/noticias-gerais-da-semana/',
            'https://99app.com/blog/motorista/seguro-auto-entenda/',
            'https://99app.com/blog/99food/receita-de-bolo-de-cenoura/',
            'https://99app.com/blog/outros/um-artigo-bem-generico-sem-keywords/', # Exemplo para testar fallback "Geral"
            'https://99app.com/blog/motorista/guia-completo-do-motorista-novato/', # Exemplo para testar fallback "Motorista - Genérico"
            'https://99app.com/blog/99pay/o-universo-das-financas-pessoais-descomplicado/', # Exemplo para testar fallback "99Pay - Genérico"
            'https://99app.com/blog/99moto/novidades-para-motociclistas/', # Exemplo para 99Moto
            'https://99app.com/blog/motorista/problema-na-junta-do-cabecote/' # NOVO EXEMPLO para testar "Junta de Cabeçote"
        ],
        'titulo': [
            'Como Investir na Taxa Selic em 2024 e Fazer Seu Dinheiro Render Mais',
            'Evite Multas de Trânsito: Conheça a Legislação',
            'Renda Extra com 99Pay: Saiba Como Ganhar Dinheiro Fácil',
            'Documentos do Carro: Tudo Sobre Licenciamento e Transferência',
            'Novidades do App: Atualizações e Melhorias Gerais',
            'Guia Completo do Seguro Auto: Proteção e Apólice',
            'Receita de Bolo de Cenoura com Cobertura de Chocolate',
            'Este é um título genérico sem palavras-chave muito específicas.',
            'Guia Completo para o Motorista Novato no Trânsito Urbano.',
            'Entenda o Universo das Finanças Pessoais de Forma Simples e Prática.',
            'As Últimas Novidades para Motociclistas e o Mundo das Duas Rodas.',
            'Problema na Junta do Cabeçote: Sintomas e Soluções para o Seu Carro.' # NOVO TÍTULO
        ],
        'resumo_meta': [
            'Descubra como a Taxa Selic influencia seus investimentos e aprenda a investir de forma inteligente no 99Pay.',
            'Saiba como evitar infrações e pontos na CNH com a nova lei de trânsito.',
            'Aprenda métodos eficazes para gerar renda extra usando as funcionalidades do 99Pay. Dinheiro online garantido!',
            'Guia completo para a regularização dos documentos do seu veículo no Detran.',
            'Fique por dentro das últimas notícias e funcionalidades adicionadas ao nosso aplicativo.',
            'Conheça as coberturas do seguro e como ele oferece proteção para o seu carro contra sinistros.',
            'A melhor receita de bolo de cenoura caseiro para fazer no fim de semana. Culinária fácil e deliciosa.',
            'Um resumo meta que não se encaixa em nenhum cluster predefinido, apenas informações gerais.',
            'Dicas essenciais para quem está começando a dirigir e navegar pelas ruas da cidade.',
            'Descomplicando conceitos financeiros para ajudar você a gerenciar melhor seu dinheiro e alcançar a liberdade.',
            'Fique por dentro das últimas notícias, tendências e dicas para quem ama andar de moto.',
            'Aprenda a identificar falhas na junta do cabeçote do motor do seu veículo e as melhores formas de manutenção.' # NOVO RESUMO
        ],
        'conteudo': [
            'O Banco Central define a Taxa Selic, que é crucial para seus juros e investimentos. Entenda o COPOM.',
            'Para a manutenção do seu carro, é vital verificar os freios e fazer a troca de óleo regularmente.',
            'Com o 99Pay, você pode ganhar uma grana extra participando de promoções e desafios.',
            'Para evitar multas, todo motorista deve conhecer o código de trânsito e o que fazer em caso de infração.',
            'Este artigo aborda notícias gerais do universo mobile e tecnologia.',
            'Pilotagem segura com a moto exige capacete e atenção no trânsito.',
            'Uma receita de bolo de cenoura simples e gostosa.',
            'Conteúdo muito simples aqui.',
            'Dirigir na cidade pode ser um desafio para o motorista novato.',
            'Educação financeira é a chave para o sucesso financeiro.',
            'Motos estão ganhando cada vez mais espaço no trânsito urbano.',
            'A junta do cabeçote é fundamental para o bom funcionamento do motor.' # NOVO CONTEÚDO
        ],
        'categoria': [
            '99Pay', 'Motorista', '99Pay', 'Motorista', 'Outros', 'Motorista', '99Food', 'Outros', 'Motorista', '99Pay', '99Moto', 'Motorista' # Adicionado 'Motorista' para o novo exemplo
        ],
        'data_captura': ['2025-07-25 10:00:00'] * 12 # Ajustado o número de entradas
    }
    sample_df = pd.DataFrame(sample_data)

    # Executa o pipeline de NLP
    df_result = run_nlp_pipeline(sample_df.copy())
    print("\nDataFrame com Topic Clusters:")
    # Aqui, você verá a coluna 'topic_clusters' com a lista (ainda não formatada para string)
    print(df_result[['url', 'categoria', 'titulo', 'resumo_meta', 'topic_clusters']])

    # Lembre-se que o posprocessa_excel.py é quem transforma 'topic_clusters' em 'topic_clusters_formatado'
    # e salva nas abas.