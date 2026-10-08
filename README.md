# Captura de perfis e informações de contato

Scripts históricos em Python para pesquisar perfis do Instagram com a Google Custom Search JSON API, consultar páginas com Selenium e organizar informações em CSV. O projeto tem registro de janeiro de 2024.

## Funcionamento

- `cod.py` e `leads.py` são alternativas de coleta. Paginam a pesquisa em passos de dez, abrem os links no Chrome e esperam elementos `h1`/`h2`. URLs sem `instagram.com` são ignoradas.
- Extraem perfil, nome, contagens de publicações e seguidores, bio e link da bio. Ambos gravam `informacoes_de_contato.csv`, com as colunas `IG`, `NOME`, `N° PUBLICAÇÕES`, `N° SEGUIDORES`, `BIO` e `LINK DA BIO`.
- As alternativas usam consultas, pausas e tempos de espera distintos. Escolha uma: ambas escrevem no mesmo arquivo.
- `tratamento.py` lê esse CSV, extrai sequências de telefone de `BIO` por expressão regular, acrescenta `NUMERO` e grava `informacoes_de_contato_com_info.csv`.

Os caminhos são relativos ao diretório corrente. Os CSVs são sobrescritos, usam vírgula como separador e o encoding padrão do ambiente. Resultados, logs e configurações locais são ignorados pelo Git.

## Dependências e configuração

Requisitos: Python 3, requests, Selenium, pandas, Chrome e ChromeDriver compatíveis. A pesquisa requer um mecanismo Google Custom Search e uma chave própria com acesso à API. As versões das dependências não estão fixadas.

Na raiz do projeto, em Bash/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install requests selenium pandas
```

Antes de usar um coletor:

1. Ajuste `chrome_driver_path` no script para o executável ChromeDriver. O caminho existente aponta para geckodriver, embora o código use `webdriver.Chrome`.
2. Configure `search_engine_id` e as consultas de `pesquisa_avancada` para o mecanismo e a pesquisa desejados.
3. Defina sua chave no ambiente da sessão:

```bash
export GOOGLE_API_KEY='SUBSTITUA_POR_SUA_CHAVE'
```

Os scripts leem `GOOGLE_API_KEY` do ambiente e interrompem se estiver ausente ou vazia. **Não carregam `.env` automaticamente.** Não grave a chave nos fontes ou nos logs. Arquivos `.env` são ignorados pelo Git, mas precisam ser carregados no ambiente por outro mecanismo, caso utilizados.

## Execução

Confira previamente o acesso à API, suas cotas e os custos aplicáveis. Execute somente uma alternativa de coleta:

```bash
python cod.py
# Alternativa: python leads.py

# Depois da coleta:
python tratamento.py
```

Os coletores também iniciam o fluxo quando importados, pois não têm guarda `if __name__ == "__main__"`. Não há demonstração offline.

## Limitações

- A coleta depende dos seletores das páginas e do acesso aos serviços externos; mudanças nesses serviços podem interromper o fluxo.
- É necessário configurar o driver antes da execução. Não há ambiente de dependências fixado para reprodução.
- As requisições HTTP não têm timeout explícito; campos ausentes seguem o tratamento existente nos scripts.
- A expressão regular de telefone não valida DDD, titularidade ou natureza do número.
- A coleta pode produzir dados pessoais. A disponibilidade de um perfil não estabelece permissão para reutilizar seus dados; armazenamento e compartilhamento precisam respeitar o contexto de uso.
- Evite logging de requisições completas, que podem conter a chave de acesso.
