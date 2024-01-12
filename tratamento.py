import pandas as pd
import re

# Ler o arquivo CSV
df = pd.read_csv('informacoes_de_contato.csv')

# Função para extrair todos os números do texto
def extract_all_numbers(bio):
    number_pattern = r'\b\d{4,5}[-.\s]?\d{4}\b'
    all_numbers = re.findall(number_pattern, bio)
    return all_numbers

# Aplicar a função para extrair todos os números e criar uma nova coluna
df['NUMERO'] = df['BIO'].apply(extract_all_numbers)

# Reordenar e renomear as colunas
df = df[['IG', 'NOME', 'N° PUBLICAÇÕES', 'N° SEGUIDORES', 'NUMERO', 'LINK DA BIO', 'BIO']]

# Salvar o arquivo com as novas colunas
df.to_csv('informacoes_de_contato_com_info.csv', index=False)

