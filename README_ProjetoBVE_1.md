# Projeto BVE: simulação do abastecimento de combustível no Porto Mar Azul

**PRO3342 – Modelagem e Simulação de Sistemas de Produção** (Poli-USP) · **Grupo G112** · 2026

Equipe: Francisco Rocha Freitas Brandão, Vasco Oliveira, Inigo Anduaga e Kepa Danis.

## 1. Contexto e objetivo

A Buena Vista Energy (BVE) abastece navios no Porto Mar Azul por meio de barcaças. Elas são carregadas na base da BVE (dois berços), navegam pelo canal até os navios em operação nos seis terminais do porto (T1 a T6) e transferem o combustível por bombeamento. A programação das barcaças cabe à equipe de programação e controle da operação (PCO). Com o crescimento da demanda, a BVE quer expandir em 20% a capacidade do sistema.

O projeto representa, por simulação de eventos discretos (Python e SimPy), a operação de abastecimento e a coordenação entre a **demanda** (navios que chegam e compram combustível) e a **oferta** (barcaças e base de carga), mediada pelo PCO. Este repositório cobre a definição do projeto e a construção dos modelos (Labs 07 a 10). Verificação e validação completas, várias replicações e a comparação das alternativas de expansão ainda não estão incluídas.

## 2. Arquitetura

| Bloco | Pasta | Lab | Conteúdo |
|:--|:--|:--|:--|
| Definição e modelo conceitual | [`10 BVE definicaoProjeto`](10%20BVE%20definicaoProjeto/) | 07 | [Proposta](10%20BVE%20definicaoProjeto/Proposta%20consultoria%20g112%20%281%29.ipynb), [modelo conceitual (v1.1)](10%20BVE%20definicaoProjeto/Modelo%20Conceitual%20%20g112%20%281%29.ipynb) e [solicitação de dados](10%20BVE%20definicaoProjeto/Dados%20g112%20%281%29.ipynb) |
| Modelo dos navios | [`40 BVE modeloComputacional`](40%20BVE%20modeloComputacional/) | 08 | Chegada dos navios, filas nos terminais e geração dos pedidos de combustível |
| Modelo das barcaças | [`barcaças`](barca%C3%A7as/) | 09 | Ciclo das barcaças (carga, navegação, bombeamento, retorno), com terminal e volume sorteados |
| Modelo integrado com PCO | [`50 BVE modeloIntegrado`](50%20BVE%20modeloIntegrado/) | 10 | Navios, barcaças e PCO em uma única simulação |

Nos Labs 08 e 09 os modelos são independentes. No Lab 10 rodam juntos em um único `simpy.Environment`: cada navio comprador notifica o PCO e o PCO decide qual barcaça atende cada pedido, no lugar dos sorteios do Lab 09.

```text
navios (Lab 08) ── pedido + janela de atendimento ──▶ PCO (Lab 10) ── programação ──▶ barcaças e base (Lab 09)
```

## 3. Estrutura do diretório

```text
modelagem_kepa/
├── .gitignore
└── ProjetoBVE/
    ├── README.md
    ├── requirements.txt
    ├── 10 BVE definicaoProjeto/        3 notebooks do Lab 07
    ├── 40 BVE modeloComputacional/     Lab 08
    │   ├── G112_D08_Modelo_Computacional_Navios.ipynb, modelo_navios.py, README.md
    │   ├── D08_2_BVE_MComp_Navios_-_Dados.md
    │   ├── entrada/                    cenario.csv, terminais.csv, distancias.csv e cópia do .md de dados
    │   └── saida/                      log_navios.csv
    ├── barcaças/                       Lab 09 (arquivos soltos, sem entrada/ nem saida/)
    │   ├── G112_D09_Modelo_Computacional_Barcacas.ipynb (e .html)
    │   ├── D08_2_...Dados.md, D09_2_BVE_MComp_Barcas_-_Dados.md
    │   ├── cenario.csv, frota.csv, terminais.csv
    │   └── log_barcacas.csv
    └── 50 BVE modeloIntegrado/         Lab 10
        ├── G112_D10.ipynb (e .html), README.md
        ├── codigo/                     modelo_bve_pco.py e módulos reaproveitados
        ├── entrada/                    cenario, terminais, frota, distancias, parametros_pco e sensibilidade/
        └── saida/                      log_navios.csv, log_barcacas.csv, log_pedidos.csv
```

Os arquivos `nono` (pastas 10 e 40) e `barcaças/barcaças` contêm apenas uma quebra de linha e servem de marcadores de pasta.

## 4. Módulos

**Lab 08, navios** ([notebook](40%20BVE%20modeloComputacional/G112_D08_Modelo_Computacional_Navios.ipynb), [README](40%20BVE%20modeloComputacional/README.md)). Em cada terminal, as notificações seguem um processo de Poisson; o navio chega ao fundeio 48 h depois, espera berço livre (FIFO), faz a manobra de entrada, opera (janela de atendimento) e faz a manobra de saída. Cada navio é comprador com a probabilidade `prob_compra` do terminal e, se comprador, demanda um volume triangular. Só entram em `log_navios.csv` os navios que concluem a manobra de saída dentro do horizonte.

**Lab 09, barcaças** ([notebook](barca%C3%A7as/G112_D09_Modelo_Computacional_Barcacas.ipynb), [HTML](barca%C3%A7as/G112_D09_Modelo_Computacional_Barcacas.html), [dados](barca%C3%A7as/D09_2_BVE_MComp_Barcas_-_Dados.md)). As barcaças partem cheias da base em t = 0, navegam até um terminal, bombeiam, retornam, esperam berço (FIFO) e carregam até completar o tanque. O terminal (proporcional a λ·`prob_compra`) e o volume de cada viagem são sorteados, e os tempos são determinísticos. O código-fonte também está em [`50 BVE modeloIntegrado/codigo/modelo_barcacas.py`](50%20BVE%20modeloIntegrado/codigo/modelo_barcacas.py), idêntico ao do notebook, exceto pelo bloco de linha de comando.

**Lab 10, integrado** ([notebook](50%20BVE%20modeloIntegrado/G112_D10.ipynb), [HTML](50%20BVE%20modeloIntegrado/G112_D10.html), [README](50%20BVE%20modeloIntegrado/README.md)). Função principal: `simular_bve` em [`codigo/modelo_bve_pco.py`](50%20BVE%20modeloIntegrado/codigo/modelo_bve_pco.py). Às 09:30 e às 16:30, o PCO ordena a carteira de pedidos pelo menor fim de janela e atribui cada pedido à **primeira barcaça viável** da frota (combustível suficiente e atendimento concluído dentro da janela), com no máximo uma nova programação por barcaça e por rodada. Pedido cuja janela fecha sem atendimento é perdido.

### Qual `modelo_navios.py` vale

| Arquivo | Versão | Uso |
|:--|:--|:--|
| `50 BVE modeloIntegrado/codigo/modelo_navios.py` | Vigente (aplica `fator_demanda`, registra `N_final`) | Importado pelo modelo integrado (Lab 10) |
| `40 BVE modeloComputacional/modelo_navios.py` | Versão anterior (não tem `fator_demanda`) | Execução do Lab 08 pela linha de comando; o notebook D08 traz o mesmo código em uma célula, sem o bloco de linha de comando |

Com `fator_demanda = 1,0` (cenário-base) a versão anterior gera o mesmo log do Lab 08 (verificado em 26/10/2026: 6.407 navios, instantes idênticos; só mudam os fins de linha).

## 5. Dependências

Python **3.12 ou superior** (testado com 3.12 e 3.13; o Python 3.11 não serve com as versões fixadas, pois o NumPy 2.5.3 exige 3.12), SimPy, NumPy, pandas e, para os notebooks, `nbconvert` e `ipykernel`. As versões testadas estão em [`requirements.txt`](requirements.txt). Não se sabe se o código roda com versões anteriores das bibliotecas.

## 6. Instalação e execução

Os comandos `cd`, `python`, `pip` e `jupyter` são os mesmos em Linux, macOS e Windows; só muda a ativação do ambiente virtual. Em alguns sistemas o interpretador se chama `python3`. Os comandos foram testados em **Linux**; Windows e macOS não foram testados.

```bash
git clone https://github.com/kepadanis/modelagem_kepa.git
cd modelagem_kepa/ProjetoBVE
python -m venv .venv
source .venv/bin/activate          # Windows (PowerShell): .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Cada bloco abaixo parte de `ProjetoBVE/` e termina de volta nela.

### Lab 08: navios

```bash
cd "40 BVE modeloComputacional"
python modelo_navios.py entrada saida                # grava saida/log_navios.csv (6.407 navios)
# ou, com verificação (15 testes):
jupyter nbconvert --to notebook --execute G112_D08_Modelo_Computacional_Navios.ipynb
cd ..
```

### Lab 09: barcaças

Pelo módulo (usa as entradas do Lab 10, idênticas às de `barcaças/`); grava `saida_lab09/log_barcacas.csv` (17.383 linhas):

```bash
cd "50 BVE modeloIntegrado/codigo"
python modelo_barcacas.py ../entrada ../saida_lab09
cd ../..
```

Pelo notebook, que exige uma pasta `entrada/` com os dois arquivos de dados e `cenario.csv` (ele gera `frota.csv` e `terminais.csv` e cria `saida/`). Sem essa pasta, a execução falha com `FileNotFoundError: entrada/D08_2_...md`.

```bash
cd "barcaças"
mkdir -p entrada
cp D08_2_BVE_MComp_Navios_-_Dados.md D09_2_BVE_MComp_Barcas_-_Dados.md cenario.csv entrada/
jupyter nbconvert --to notebook --execute G112_D09_Modelo_Computacional_Barcacas.ipynb   # 14 testes
cd ..
```

Equivalente em PowerShell (não testado):

```powershell
cd "barcaças"
New-Item -ItemType Directory -Force entrada | Out-Null
Copy-Item D08_2_BVE_MComp_Navios_-_Dados.md, D09_2_BVE_MComp_Barcas_-_Dados.md, cenario.csv entrada/
jupyter nbconvert --to notebook --execute G112_D09_Modelo_Computacional_Barcacas.ipynb
cd ..
```

### Lab 10: modelo integrado

```bash
cd "50 BVE modeloIntegrado"
python
```

e, no interpretador, cole o bloco abaixo (ou salve-o como um arquivo `.py` nesta pasta e execute `python arquivo.py`, o que funciona igual em qualquer sistema):

```python
import sys; sys.path.insert(0, "codigo")
from pathlib import Path
from modelo_bve_pco import simular_bve
E = Path("entrada")
ind = simular_bve(E / "cenario.csv", E / "terminais.csv", E / "frota.csv", E / "distancias.csv",
                  E / "parametros_pco.csv", semente=20260, gravar_logs=True, pasta_logs="saida_execucao")
print(ind["n_pedidos"], ind["n_atendidos"], ind["n_perdidos"], round(100 * ind["nivel_servico"], 1))
```

A assinatura é `simular_bve(arq_cenario, arq_terminais, arq_frota, arq_distancias, arq_pco, semente, gravar_logs=False, pasta_logs=None, id_cenario=None)`. Com `gravar_logs=False` os logs ficam só em memória. O resultado esperado é `3444 2441 964 70.9`. Para executar o relatório completo (3 verificações):

```bash
jupyter nbconvert --to notebook --execute G112_D10.ipynb
cd ..
```

### Arquivos versionados que a execução reescreve

Os notebooks dos Labs 08 e 10 (e `modelo_navios.py` do Lab 08) regravam arquivos que já estão no repositório. O conteúdo é o mesmo, mas o `git diff` mostrará fins de linha diferentes em `entrada/` e 1 µs de diferença de arredondamento nos instantes dos logs. Para restaurá-los: `git checkout -- "40 BVE modeloComputacional/entrada" "40 BVE modeloComputacional/saida" "50 BVE modeloIntegrado/saida"`. O `nbconvert` cria também arquivos `*.nbconvert.ipynb`, que o `.gitignore` ignora. A execução do notebook do Lab 09 cria ainda as pastas `barcaças/entrada/` e `barcaças/saida/`, que **não** são ignoradas: aparecem como não versionadas no `git status` e podem ser apagadas.

## 7. Entradas e saídas

Tempos em horas na simulação e em data-hora nos logs (a partir de `data_inicio`, 01/01/2026); volumes em t; distâncias em km; velocidades em km/h; vazões em t/h.

| Arquivo | Onde | Função |
|:--|:--|:--|
| `cenario.csv` | 40, barcaças, 50 | Horizonte (dias), replicações, semente, `fator_demanda`; a partir do Lab 09, também berços e taxa de carga da base, horários e horizonte de programação e `regra_pco` |
| `terminais.csv` | 40, barcaças, 50 | Por terminal: berços, taxa de chegada, antecedência, manobra, distribuição da operação, `prob_compra`, distribuição do volume e, nos Labs 09 e 10, `dist_base` |
| `frota.csv` | barcaças, 50 | Por barcaça: capacidade, velocidade, vazão de bombeamento, carga inicial |
| `distancias.csv` | 40, 50 | Matriz de distâncias (formato longo, inclui a base) |
| `parametros_pco.csv` | 50 | `t_conexao`, `t_desconexao`, `t_manobra_base` (h), cada um com estado e fonte |
| `log_navios.csv` | 40, 50 | Um registro por navio que concluiu a manobra de saída |
| `log_barcacas.csv` | barcaças, 50 | Um registro por estado concluído de cada barcaça |
| `log_pedidos.csv` | 50 | Um registro por pedido de navio comprador, com estado final e barcaça |

`cenario.csv`, `terminais.csv` e `frota.csv` de `barcaças/` e de `50 BVE modeloIntegrado/entrada/` são idênticos. `distancias.csv` é igual nas pastas 40 e 50 (a menos do fim de linha).

## 8. Diferenças entre os modelos

Estas diferenças existem e **não estão todas resolvidas**; as marcadas como documentadas estão explicadas no relatório do Lab 10 (`G112_D10`, seções 3.3 e 3.4).

| Aspecto | Lab 08 | Lab 09 | Lab 10 | Situação |
|:--|:--|:--|:--|:--|
| `prob_compra` (T1 a T6) | 70, 60, 50, 65, 55, 50 % | 63, 54, 45, 59, 50, 45 % (revisão da BVE) | Igual ao Lab 09 | Documentada. O `log_navios` do Lab 08 e o do Lab 10 têm os mesmos navios e instantes, mas 376 compradores diferentes (3.781 contra 3.405) |
| Número de barcaças | n/a | 4 | 4 | Documentada (H8). O modelo conceitual v1.1 e a proposta falam em 6; o relatório do Lab 09 cita uma versão 1.2 do conceitual que **não está publicada** (o do Lab 10 cita a 1.1) |
| Origem de terminal e volume | n/a | Sorteados por barcaça | Pedidos reais dos navios, via PCO | Por desenho |
| Regra de alocação do PCO | n/a | n/a | Primeira barcaça viável; no máximo 1 programação por barcaça e rodada | Documentada. O conceitual v1.1 descreve a barcaça de menor tempo de conclusão, rotas com vários pedidos e reprogramação por falha |
| Conexão, desconexão e manobra na base | n/a | Desprezadas | 1,5 h, 1,5 h e 0 h (`parametros_pco.csv`) | Conflito entre as fontes (D-05), sem decisão |
| Janela do navio para o PCO | n/a | n/a | Conhecida no instante da notificação por um previsor exato (H1) | Hipótese provisória. O conceitual diz que o PCO lê `log_navios.csv`; a implementação recebe os pedidos em memória |
| Estados do `log_barcacas` | n/a | 4 (`navegando`, `bombeando`, `fila_base`, `carregando`) | 8 (acrescenta `ociosa`, `aguardando_janela`, `conectando`, `desconectando`); `viagem` pode agrupar vários atendimentos | Formato ampliado. Não foi contrastado com a definição original da pré-aula 9 |
| Fim do horizonte | 60 navios em curso ficam fora do log | Estados em curso não gravados | Estados em curso encerrados no fim do horizonte; 39 pedidos em aberto | Tratamentos distintos, todos documentados |

## 9. Verificação

| Lab | Verificações | O que demonstram |
|:--|:--|:--|
| 08 | 15 testes (V01 a V15), seção 5 do notebook | Entradas lidas de arquivo, Poisson por terminal, capacidade de berços e FIFO, manobras, distribuições, fator de demanda, coerência do log, semente e utilização compatível com a teoria de filas |
| 09 | 14 testes (V01 a V14), seção 5 do notebook | Ciclo determinístico, estado inicial, tempos, destino e volume sorteados, berços e FIFO da base, frota heterogênea, continuidade do log, conservação do combustível, semente e comparação analítica |
| 10 | 3 verificações preliminares, seção 5 de `G112_D10` | Log de cada barcaça sem lacunas e com combustível conservado; janela usada pelo PCO igual à real, nenhum atendimento fora da janela e log de navios igual ao do Lab 08; regra da primeira barcaça viável cumprida |

Cada teste registra objetivo, configuração, resultado esperado, resultado obtido e conclusão. Em 26/10/2026, em Linux, a partir de um clone limpo do repositório, os comandos de linha de comando do Lab 08 e do Lab 09, o bloco do Lab 10 (Python 3.12 e 3.13) e a execução dos três notebooks (Python 3.13) terminaram sem erro e reproduziram os números citados; os módulos reproduziram os logs publicados, a menos de fim de linha e de 1 µs de arredondamento nos instantes. Isso mostra que os modelos são internamente consistentes e reproduzíveis. **Não os valida** contra a operação real da BVE.

## 10. Estado e limitações

**Resultados comprovados** (cenário-base, 1 replicação, 365 dias, semente 20260):

- Lab 08: 6.467 navios notificados, 6.407 no log.
- Lab 09: 17.383 linhas no log.
- Lab 10: 3.444 pedidos, 2.441 atendidos, 964 perdidos e 39 em aberto; nível de serviço de 70,9% (atendidos / pedidos gerados; 71,7% sobre pedidos resolvidos); utilização média das barcaças de 96,1% (tempo fora de `ociosa`, dos quais 80,9% em trabalho produtivo); utilização dos berços da base de 32,5%.

**Hipóteses do modelo** (não confirmadas pelo professor; H1 a H12 em `G112_D10`): PCO com janela exata na notificação (H1); conexão e desconexão de 1,5 h (H5), pois com 0 h o nível de serviço sobe a 79,7% (exploração preliminar, mesma semente); manobra na base de 0 h (H6); previsão do PCO sem fila na base (H7); 4 barcaças e probabilidades revisadas (H8).

**Limitações:** uma única replicação, sem intervalo de confiança; horizonte de 365 dias (o modelo conceitual prevê 500 para os experimentos); sem falhas, clima ou restrição de tráfego; os resultados do Lab 10 dependem das hipóteses acima e servem para conferir o funcionamento do modelo, não para recomendar a expansão.

**Pendências:** publicar a versão 1.2 do modelo conceitual e alinhá-la à implementação do PCO; decidir com o professor as hipóteses H1, H5 e H8; verificação e validação completas, com várias replicações.
