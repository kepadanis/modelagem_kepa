# Projeto BVE - Grupo G112

Consultoria de simulação para a Buena Vista Energy (PRO3342, 2026).

| Arquivo | Conteúdo |
|:--|:--|
| `G112_Proposta.ipynb` | Proposta de consultoria |
| `G112_Modelo_Conceitual.ipynb` | Modelo conceitual (v1.1) |
| `G112_Dados.ipynb` | Solicitação de dados |
| `G112_D08_Modelo_Computacional_Navios.ipynb` | Modelo computacional dos navios (SimPy), saída e verificação |
| `entrada/` | Dados do cenário-base (`D08_2_...md`) e arquivos de entrada `terminais.csv`, `cenario.csv`, `distancias.csv` |
| `saida/log_navios.csv` | Log dos navios: 1 replicação do cenário-base, 365 dias |

## Como executar o modelo dos navios

```bash
pip install simpy numpy pandas jupyter
jupyter nbconvert --to notebook --execute G112_D08_Modelo_Computacional_Navios.ipynb
```

Executar a partir desta pasta (caminhos relativos). O notebook gera `entrada/terminais.csv` e `entrada/distancias.csv` a partir do arquivo de dados, lê `entrada/cenario.csv`, simula e grava `saida/log_navios.csv`. Para outro cenário, basta alterar os arquivos de `entrada/`.
