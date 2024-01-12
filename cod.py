import csv
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time

# Configure o caminho para o ChromeDriver
chrome_driver_path = '/home/rocha/Área de Trabalho/geckodriver-v0.32.0-linux64.tar.gz/geckodriver.exe'

# Chave de API da Pesquisa Customizada do Google
api_key = 'AIzaSyC0xVgWxTryxmc7KaNhgk_fEk3o9X3GpLM'

# ID do Mecanismo de Pesquisa da Pesquisa Customizada do Google
search_engine_id = '51d207a426e7b415a'

def acessar_links_e_capturar_h1_h2(pesquisa_avancada, num_results=100, timeout=35):
    informacoes_de_contato = []

    for query in pesquisa_avancada:
        try:
            # Iterar sobre as páginas de resultados (cada página tem 10 resultados)
            for start in range(1, num_results, 10):
                # Use a API de Pesquisa Customizada para obter os resultados da pesquisa
                url = f'https://www.googleapis.com/customsearch/v1?q={query}&key={api_key}&cx={search_engine_id}&start={start}'

                response = requests.get(url)
                data = response.json()

                # Iterar sobre os resultados da página atual
                for item in data.get('items', []):
                    link = item.get('link', '')

                    # Use o Selenium para obter h1 e h2 dos links
                    chrome_options = Options()
                    chrome_options.add_argument("--incognito")  # Ativar modo incógnito
                    with webdriver.Chrome(service=Service(chrome_driver_path), options=chrome_options) as driver:
                        driver.get(link)
                        
                        try:
                            # Espera até timeout segundos para que h1 e h2 estejam disponíveis
                            wait = WebDriverWait(driver, timeout)
                            h1_element = wait.until(EC.presence_of_element_located((By.TAG_NAME, 'h1')))
                            h2_element = wait.until(EC.presence_of_element_located((By.TAG_NAME, 'h2')))
                            
                            # Verifica se a página é a home do Instagram (um exemplo de verificação, pode precisar de ajustes)
                            if "instagram.com" not in driver.current_url:
                                print(f"A URL não é a home do Instagram para a URL: {link}")
                                continue  # Pula para a próxima iteração
                            
                            # Restante do seu código...
                            try:
                              span_element = driver.find_element(By.XPATH, "//span[@class='x1lliihq x193iq5w x6ikm8r x10wlt62 xlyipyv xuxw1ft']")
                              link_text = span_element.text

                              dados_publi = driver.find_elements(By.XPATH, "//span[@class='html-span xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x1hl2dhg x16tdsg8 x1vvkbs']")
                              if len(dados_publi) >= 2:
                                  seguidores = dados_publi[1].text
                                  publicacoes = dados_publi[0].text
                            except:
                              print(f"Elemento não encontrado para a URL: {url}")
                              continue  # Pula para a próxima iteração
                        except TimeoutException as e:
                            print(f"Timeout ao aguardar o carregamento da página para a URL: {link}")
                            print(f"Erro: {str(e)}")
                            print(f"Elementos não encontrados para a URL: {link}")
                            continue  # Pula para a próxima iteração
                        
                        informacoes_de_contato.append({
                            "IG": link,
                            "NOME": h2_element.text if h2_element else "",
                            "N° PUBLICAÇÕES": publicacoes if 'publicacoes' in locals() else '',
                            "N° SEGUIDORES": seguidores if 'seguidores' in locals() else '',
                            "BIO": h1_element.text if h1_element else "",
                            "LINK DA BIO": link_text
                        })      

                        # Adicione um atraso entre as solicitações
                        time.sleep(10)  # Atraso de 10 segundos

        except Exception as e:
            print(f"Erro ao processar a pesquisa: {str(e)}")
            pass
            time.sleep(7)

    return informacoes_de_contato

# Pesquisa google
pesquisa_avancada = ["Restaurantes Ipiranga - SP site:instagram.com"]
informacoes_de_contato = acessar_links_e_capturar_h1_h2(pesquisa_avancada, num_results=100)

# Salva as informações em um arquivo CSV
with open('informacoes_de_contato.csv', 'w', newline='') as file:
    fieldnames = ["IG", "NOME", "N° PUBLICAÇÕES", "N° SEGUIDORES", "BIO", "LINK DA BIO"]
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(informacoes_de_contato)
