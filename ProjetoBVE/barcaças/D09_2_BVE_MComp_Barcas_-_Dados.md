# Dados – Cenário-base: Operação das barcaças da BVE

## 1. Onde as barcaças são carregadas?
- Na base de combustível da BVE (local 0), que tem 2 berços de carga.
- Os dois berços são equivalentes: a barcaça carrega no primeiro berço livre.
- Se os dois berços estiverem ocupados, a barcaça aguarda na fila, por ordem de chegada.

## 2. Qual é a taxa de carga das barcaças na base?
- 400 t/h, em ambos os berços.
- A barcaça sempre carrega até completar o tanque, ou seja, carrega a diferença entre a sua capacidade e o combustível que ainda tem a bordo.

## 3. Como é a frota de barcaças?
- A frota atual tem 4 barcaças iguais, com as seguintes características:

| Característica | Valor |
|:--|:--|
| Capacidade do tanque | 3.000 t |
| Velocidade de navegação no canal | 4,5 km/h |
| Taxa de bombeio para o navio | 200 t/h |

- A BVE estuda a aquisição de novas barcaças, que podem ter características diferentes das atuais.

## 4. Qual é a situação das barcaças no início da operação?
- Todas as barcaças estão na base, com o tanque cheio, e partem imediatamente para o primeiro atendimento.

## 5. Como é definido o destino de cada barcaça?
- Cada viagem atende um único navio, em um dos terminais T1 a T6 (locais 1 a 6). Ao final do abastecimento, a barcaça retorna à base.
- Neste modelo, enquanto não há integração com os navios e o PCO, o terminal de destino é sorteado com probabilidade proporcional à taxa de chegada de navios compradores do terminal.
- Sorteado o terminal, a quantidade de combustível a fornecer é sorteada pela distribuição de demanda do terminal (pergunta 7).

## 6. A BVE atualizou alguma informação do cenário-base?
- Sim. As probabilidades de compra de combustível foram revisadas e substituem as informadas no Lab 08:

| Terminal | Probabilidade de compra |
|:--|:--|
| T1 | 63% |
| T2 | 54% |
| T3 | 45% |
| T4 | 59% |
| T5 | 50% |
| T6 | 45% |

- As taxas de chegada de navios não mudaram: T1 2,5; T2 4,0; T3 4,5; T4 3,5; T5 2,0; T6 1,0 navios/dia.

## 7. Qual é a quantidade de combustível demandada por navio comprador (mínimo, mais provável, máximo)?
- Sem alteração em relação ao Lab 08.
- T1: Tri(600, 1000, 1800) t
- T2: Tri(800, 1200, 2000) t
- T3: Tri(400, 700, 1200) t
- T4: Tri(500, 900, 1600) t
- T5: Tri(300, 600, 1000) t
- T6: Tri(250, 500, 900) t

## 8. Quais são as distâncias entre a base e os terminais?

| De \ Para | T1 | T2 | T3 | T4 | T5 | T6 |
|:--|:--|:--|:--|:--|:--|:--|
| Base | 2,1 km | 3,7 km | 5,8 km | 7,5 km | 9,2 km | 10,6 km |

- A matriz completa de distâncias, informada no Lab 08, não será necessária, pois neste modelo a barcaça atende apenas um navio por viagem.

## 9. Os tempos de navegação, carga e bombeio são aleatórios?
- Não. Os tempos são calculados a partir das características da barcaça e da operação:
  - navegação = distância / velocidade da barcaça;
  - bombeio = quantidade fornecida / taxa de bombeio da barcaça;
  - carga = quantidade carregada / taxa de carga da base.
- A variabilidade dos tempos vem dos sorteios do destino e da quantidade (pergunta 5) e, no caso de frotas heterogêneas, das diferenças de velocidade e de taxa de bombeio entre as barcaças.
- Os tempos de atracação, conexão e desconexão das mangueiras são pequenos e podem ser desconsiderados.

## 10. A barcaça precisa esperar o navio no terminal?
- Neste modelo, considere que o navio está sempre disponível para o abastecimento quando a barcaça chega. A sincronização com a operação dos navios será tratada no Lab 10.

## 11. A operação das barcaças é contínua?
- Sim, 24 horas por dia, 7 dias por semana, sem paradas programadas ou falhas.

## 12. Qual período deve ser simulado?
- Uma replicação de 365 dias, a partir do início da operação (instante 0, em horas).
- A semente do gerador de números aleatórios fica a critério do grupo, mas deve ser informada no arquivo de entrada para que os resultados sejam reprodutíveis.
