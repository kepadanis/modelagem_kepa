# Lab 09 - Modelo computacional das barcaças (Projeto BVE, Grupo G112)

Modelo SimPy da frota de barcaças em ciclo contínuo: carga na base, navegação até o terminal, abastecimento e retorno. O terminal e a demanda de cada atendimento são sorteados; no Lab 10 esse sorteio é substituído pelas decisões do PCO.

| Arquivo | Conteúdo |
|:--|:--|
| `G112_D09.ipynb` | Relatório e modelo: alterações do modelo conceitual (v1.2), prompt, implementação em SimPy, 14 testes de verificação e conclusões |
| `G112_D09.html` | Relatório exportado, com as saídas da execução |
| `entrada/D08_2_BVE_MComp_Navios_-_Dados.md` | Dados do cenário-base dos navios (taxas de chegada, probabilidade de compra e volumes) |
| `entrada/D09_2_BVE_MComp_Barcas_-_Dados.md` | Dados do cenário-base das barcaças (frota, base, distâncias) |
| `entrada/cenario.csv` | Configuração: horizonte de 365 dias, semente 20260, berços e taxa de carga da base. **É lido pelo notebook; não é gerado** |
| `entrada/frota.csv`, `entrada/terminais.csv` | Gerados pelo notebook a partir dos dois arquivos `.md` |
| `saida/log_barcacas.csv` | Log das barcaças: 1 replicação do cenário-base, 365 dias, 17.383 registros |

## Como executar

```bash
pip install simpy numpy pandas jupyter
jupyter nbconvert --to notebook --execute G112_D09.ipynb
```

Execute a partir desta pasta (os caminhos são relativos). O notebook gera `entrada/frota.csv` e `entrada/terminais.csv`, lê `entrada/cenario.csv`, simula e grava `saida/log_barcacas.csv`.
