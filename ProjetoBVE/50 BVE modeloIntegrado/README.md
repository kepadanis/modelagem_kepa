# Lab 10: modelo integrado BVE (navios, barcaças e PCO)

Grupo G112, PRO3342. Replicação única de 365 dias do cenário-base (semente 20260).

| Pasta ou arquivo | Conteúdo |
|:--|:--|
| `G112_D10.ipynb`, `G112_D10.html` | Relatório executado (objetivo, prompt, modelo, saídas, verificações, referências) |
| `codigo/modelo_bve_pco.py` | Modelo integrado: PCO, barcaças, função principal `simular_bve` e `executar_bve` |
| `codigo/modelo_navios.py`, `modelo_barcacas.py`, `modelo_bve.py`, `prototipo_ventanas.py` | Módulos reaproveitados dos Labs 08 e 09 e da preparação |
| `entrada/` | `cenario.csv`, `terminais.csv`, `frota.csv` (arquivos do Lab 09, sem alteração), `distancias.csv` (Lab 08), `parametros_pco.csv` (novo, com estado e fonte de cada valor) |
| `entrada/sensibilidade/` | Variantes usadas só na exploração preliminar da seção 4 |
| `saida/` | `log_navios.csv`, `log_barcacas.csv` (formato da pré-aula 9) e `log_pedidos.csv` |

Executar o modelo (Python com `simpy`, `numpy` e `pandas`):

```python
import sys; sys.path.insert(0, "codigo")
from pathlib import Path
from modelo_bve_pco import simular_bve
E = Path("entrada")
indicadores = simular_bve(E / "cenario.csv", E / "terminais.csv", E / "frota.csv", E / "distancias.csv",
                          E / "parametros_pco.csv", semente=20260, gravar_logs=False)
```

Com `gravar_logs=True` e `pasta_logs="saida"` os CSV são gravados; sem isso os registros ficam só em memória.
Os valores marcados como `HIPOTESE_PROVISORIA` em `parametros_pco.csv` não foram confirmados pelo professor.
