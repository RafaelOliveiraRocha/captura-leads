"""Coleta externa opcional. Dependências carregadas somente após --externo e configuração."""

import argparse
import json
import os
import time
from pathlib import Path
from urllib.parse import urlsplit

from extracao import CAMPOS
from tratamento import deduplicar, preparar_resultado, salvar_csv


class ErroExterno(ValueError):
    """Mensagens fixas, sem URLs de requisição ou conteúdo de exceções externas."""


def ler_configuracao(caminho, timeout_padrao, pausa_padrao):
    try:
        config = json.loads(Path(caminho).read_text(encoding="utf-8"))
        obrigatorios = ("url_pesquisa", "id_mecanismo", "dominio_perfis", "driver")
        if any(not isinstance(config.get(campo), str) or not config[campo].strip()
               or config[campo].startswith("PREENCHA") for campo in obrigatorios):
            raise ValueError
        url = urlsplit(config["url_pesquisa"])
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query:
            raise ValueError
        dominio = config["dominio_perfis"]
        if urlsplit("https://" + dominio).netloc != dominio or "/" in dominio:
            raise ValueError
        if not Path(config["driver"]).expanduser().is_file():
            raise ValueError
        config["timeout_http"] = float(config.get("timeout_http", 15))
        config["timeout_pagina"] = float(config.get("timeout_pagina", timeout_padrao))
        config["pausa_segundos"] = float(config.get("pausa_segundos", pausa_padrao))
        if not (0 < config["timeout_http"] <= 120 and 0 < config["timeout_pagina"] <= 120
                and 0 <= config["pausa_segundos"] <= 120):
            raise ValueError
        seletores = config["seletores"]
        if not isinstance(seletores, dict) or not {"nome", "bio"} <= seletores.keys():
            raise ValueError
        for campo, seletor in seletores.items():
            if (campo not in CAMPOS or seletor.get("por") not in ("css", "xpath")
                    or not isinstance(seletor.get("valor"), str)
                    or not seletor["valor"].strip() or seletor["valor"].startswith("PREENCHA")):
                raise ValueError
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        raise ErroExterno("Confira a configuração externa: URL HTTPS, mecanismo, driver e seletores.") from None
    chave = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not chave:
        raise ErroExterno("Configure GOOGLE_API_KEY no ambiente antes de executar a coleta.")
    return config, chave


def coletar(config, chave, segmento, cidade, bairro, limite):
    # Nenhuma dependência de automação é importada pela tela ou pelos modos de ajuda.
    try:
        import requests
        from selenium import webdriver
        from selenium.common.exceptions import NoSuchElementException, TimeoutException
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait
    except ImportError:
        raise ErroExterno("Instale as dependências de requirements-externo.txt para este modo.") from None
    driver = None
    resultados = []
    try:
        options = Options()
        options.add_argument("--incognito")
        driver = webdriver.Chrome(
            service=Service(str(Path(config["driver"]).expanduser())), options=options)
        driver.set_page_load_timeout(config["timeout_pagina"])
        query = " ".join(filter(None, (segmento, cidade, bairro, "site:" + config["dominio_perfis"])))
        for start in range(1, limite + 1, 10):
            try:
                resposta = requests.get(config["url_pesquisa"], timeout=config["timeout_http"],
                                        params={"q": query, "key": chave, "cx": config["id_mecanismo"],
                                                "start": start, "num": min(10, limite - start + 1)})
                resposta.raise_for_status()
                dados = resposta.json()
                if "error" in dados:
                    raise ErroExterno("O mecanismo de pesquisa retornou um erro.")
            except (requests.RequestException, ValueError):
                raise ErroExterno("Falha na consulta HTTP. Confira acesso e configuração do mecanismo.") from None
            for item in dados.get("items", []):
                perfil = item.get("link", "")
                url = urlsplit(perfil)
                dominio = config["dominio_perfis"].lower()
                if (url.scheme != "https" or url.username or url.password
                        or not (url.hostname == dominio or (url.hostname or "").endswith("." + dominio))):
                    continue
                candidato = {"perfil": perfil, "segmento": segmento, "cidade": cidade, "bairro": bairro}
                campos = {}
                try:
                    driver.get(perfil)
                    final = urlsplit(driver.current_url)
                    if not (final.hostname == dominio or (final.hostname or "").endswith("." + dominio)):
                        continue
                    for campo, seletor in config["seletores"].items():
                        por = By.CSS_SELECTOR if seletor["por"] == "css" else By.XPATH
                        localizador = (por, seletor["valor"])
                        try:
                            elemento = (WebDriverWait(driver, config["timeout_pagina"]).until(
                                EC.presence_of_element_located(localizador))
                                if campo in ("nome", "bio") else driver.find_element(*localizador))
                            campos[campo] = (elemento.get_attribute(seletor["atributo"])
                                             if seletor.get("atributo") else elemento.text) or ""
                        except NoSuchElementException:
                            campos[campo] = ""
                    resultados.append(preparar_resultado(candidato, campos, "Coleta externa"))
                except TimeoutException:
                    linha = preparar_resultado(candidato, campos, "Coleta externa")
                    linha["ESTADO"] = "Falha técnica: timeout na navegação ou extração."
                    resultados.append(linha)
                time.sleep(config["pausa_segundos"])
    except ErroExterno:
        raise
    except Exception:
        raise ErroExterno("Falha técnica na coleta externa; detalhes de configuração omitidos.") from None
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
    return deduplicar(resultados)


def main(argv=None, timeout_padrao=35, pausa_padrao=10):
    parser = argparse.ArgumentParser(description="Consulta externa opcional, com configuração própria.")
    parser.add_argument("--externo", action="store_true", help="Autoriza explicitamente o modo externo.")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--segmento")
    parser.add_argument("--cidade")
    parser.add_argument("--bairro", default="")
    parser.add_argument("--saida", type=Path, default=Path("outputs/coleta.csv"))
    parser.add_argument("--max-resultados", type=int, default=100)
    args = parser.parse_args(argv)
    if not args.externo:
        parser.print_help()
        return
    if not args.config or not args.segmento or not args.cidade or not 1 <= args.max_resultados <= 100:
        parser.error("Informe --config, --segmento, --cidade e um limite entre 1 e 100.")
    if args.saida.exists():
        parser.error("A saída já existe. Escolha um nome novo.")
    try:
        config, chave = ler_configuracao(args.config, timeout_padrao, pausa_padrao)
        linhas = coletar(config, chave, args.segmento, args.cidade, args.bairro, args.max_resultados)
        salvar_csv(linhas, args.saida)
        print(f"CSV gravado: {len(linhas)} perfis, com estado da extração.")
    except ErroExterno as erro:
        parser.exit(1, str(erro) + "\n")
    except OSError:
        parser.exit(1, "Não foi possível gravar a saída. Escolha um caminho novo e acessível.\n")
