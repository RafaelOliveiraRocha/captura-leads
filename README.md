# Captura de perfis e informações de contato

Scripts históricos em Python, registrados em janeiro de 2024, para pesquisar perfis do Instagram com a **Google Custom Search JSON API**, consultar páginas com Selenium e organizar as informações em CSV. Esta revisão retira a chave literal, usa configuração por ambiente e remove URLs e detalhes de exceções das mensagens dos scripts.

Não há comprovação de funcionamento atual dos seletores, disponibilidade da API ou autorização dos perfis consultados. O projeto não atribui clientes, vínculo profissional ou resultados comerciais.

## Fluxo observado

- `cod.py` e `leads.py` são alternativas de coleta: paginam a pesquisa em passos de dez, abrem os links no Chrome e esperam elementos `h1`/`h2`. Resultados cuja URL não contém `instagram.com` são ignorados.
- Extraem perfil, nome, contagens de publicações/seguidores, bio e link da bio. Ambos escrevem `informacoes_de_contato.csv`, com as colunas `IG`, `NOME`, `N° PUBLICAÇÕES`, `N° SEGUIDORES`, `BIO` e `LINK DA BIO`.
- As alternativas mantêm consultas, pausas e tempos de espera distintos. Escolha **uma**; executar ambas sobrescreve o mesmo resultado.
- `tratamento.py` lê esse CSV, extrai sequências de telefone da coluna `BIO` por regex, acrescenta `NUMERO`, reorganiza as colunas e grava `informacoes_de_contato_com_info.csv`. A regex não valida titularidade, DDD ou natureza do número.

Os caminhos são relativos ao diretório corrente. Os dois CSVs são sobrescritos; a coleta usa vírgula como separador e o encoding padrão do ambiente, sem configuração explícita. Resultados, logs e configurações locais ficam ignorados pelo Git.

## Dependências e preparação

Dependências identificadas por leitura: **Python 3**, `requests`, `selenium` e `pandas`; `csv`, `os`, `time` e `re` pertencem à biblioteca padrão. A coleta requer Google Custom Search configurado, Chrome e ChromeDriver compatíveis. Não foram instaladas dependências nem verificadas versões de execução nesta revisão.

Exemplo de preparação em Bash/Linux, na raiz do projeto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install requests selenium pandas
```

Antes de executar:

1. Em **cada script que for usar**, ajuste `chrome_driver_path` para o executável ChromeDriver. O caminho histórico aponta para geckodriver, embora o código instancie `webdriver.Chrome`; esse caminho não é uma configuração portátil válida.
2. Confira `search_engine_id`, o identificador do mecanismo de pesquisa (não é uma chave secreta), e a lista `pesquisa_avancada`. Use mecanismo e consultas autorizados.
3. Configure sua própria chave autorizada no ambiente da sessão:

```bash
export GOOGLE_API_KEY='SUBSTITUA_POR_SUA_CHAVE_AUTORIZADA'
```

Substitua o marcador antes de usar. Os scripts leem somente `GOOGLE_API_KEY` do ambiente e interrompem com mensagem clara se estiver ausente ou vazia. **Não leem `.env` automaticamente.** Não grave chaves nos fontes, commits ou logs; arquivos `.env` são ignorados, mas não são carregados pelo projeto.

## Execução

Somente após configurar e conferir autorização, cotas e custos aplicáveis:

```bash
# Escolha uma alternativa de coleta:
python cod.py
# ou: python leads.py

# Com o CSV produzido, aplique o tratamento:
python tratamento.py
```

Os coletores iniciam a coleta também quando importados, pois não há guarda `if __name__ == "__main__"`. Evite importá-los para explorar o código. Não há modo de demonstração ou coleta offline.

## Limitações e credenciais

Os seletores do Instagram e o acesso à Custom Search precisam de conferência antes de uso; dependem de serviços externos. O código preserva os filtros, a lógica e as saídas históricas, incluindo requisições sem timeout HTTP explícito e o tratamento original de campos ausentes. Não foram executados coleta, testes de credenciais ou tratamento de dados nesta revisão.

As mensagens dos scripts omitem URLs e detalhes de exceções para não registrar a chave. Isso não controla ferramentas externas, depuradores ou logging habilitado fora do projeto; evite registrar requisições completas. Dados de contato eventualmente coletados exigem autorização e cuidado no armazenamento e compartilhamento.

**Retirar uma chave do Git não a revoga no provedor.** A titularidade, validade e necessidade de revogação/rotação da chave histórica continuam pendentes de avaliação pelo titular. Não reutilize essa chave por ela ter estado no repositório.
