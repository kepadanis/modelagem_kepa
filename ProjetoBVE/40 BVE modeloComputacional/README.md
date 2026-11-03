# Lab 08 - Modelo computacional dos navios (Projeto BVE, Grupo G112)

Modelo SimPy da operação dos navios no Porto Mar Azul. Gera o log de navios (a demanda de combustível) que alimenta os modelos das barcaças e do PCO.

| Arquivo | Conteúdo |
|:--|:--|
| `G112_D08.ipynb` | Relatório e modelo: prompt, implementação em SimPy, 15 testes de verificação e conclusões |
| `G112_D08.html` | Relatório exportado, com as saídas da execução |
| `modelo_navios.py` | O mesmo modelo, em módulo Python com linha de comando; é o que o Lab 10 importa |
| `entrada/D08_2_BVE_MComp_Navios_-_Dados.md` | Dados do cenário-base fornecidos pelo professor |
| `entrada/terminais.csv`, `entrada/distancias.csv` | Gerados pelo notebook a partir do arquivo de dados |
| `entrada/cenario.csv` | Cenário-base: data inicial, horizonte de 365 dias, replicações, semente 20260 e `fator_demanda` |
| `saida/log_navios.csv` | Log dos navios: 1 replicação do cenário-base, 365 dias, 6.407 navios |

## Como executar

```bash
pip install simpy numpy pandas jupyter
jupyter nbconvert --to notebook --execute G112_D08.ipynb
```

Execute a partir desta pasta (os caminhos são relativos). O notebook gera `entrada/terminais.csv` e `entrada/distancias.csv` a partir do arquivo de dados, lê `entrada/cenario.csv`, simula e grava `saida/log_navios.csv`. Para outro cenário, altere os arquivos de `entrada/`.

Pela linha de comando, com os mesmos arquivos de entrada:

```bash
python modelo_navios.py entrada saida
```
