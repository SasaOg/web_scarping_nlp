import pandas as pd
import sys

"""
Script para gerar o arquivo historico_urls_processadas.txt a partir de um Excel já processado.
Uso:
    python gera_historico_urls_do_excel.py seu_arquivo.xlsx [nome_coluna_url]
Se não informar o nome da coluna, será usado 'url' por padrão.
"""

def main():
    if len(sys.argv) < 2:
        print("Uso: python gera_historico_urls_do_excel.py seu_arquivo.xlsx [nome_coluna_url]")
        return
    excel_path = sys.argv[1]
    col_url = sys.argv[2] if len(sys.argv) > 2 else 'url'
    df = pd.read_excel(excel_path)
    if col_url not in df.columns:
        print(f"Coluna '{col_url}' não encontrada no arquivo. Colunas disponíveis: {list(df.columns)}")
        return
    urls = df[col_url].dropna().astype(str).unique()
    with open('historico_urls_processadas.txt', 'w', encoding='utf-8') as f:
        for url in urls:
            f.write(url.strip() + '\n')
    print(f"Arquivo 'historico_urls_processadas.txt' gerado com {len(urls)} URLs.")

if __name__ == "__main__":
    main()
