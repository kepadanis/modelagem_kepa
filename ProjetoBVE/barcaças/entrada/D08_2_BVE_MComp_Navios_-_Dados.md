# Dados – Cenário-base: Operação do Porto Mar Azul

## 1. Quantos terminais há no porto e quantos berços tem cada um?
- M = 6 terminais (T1, T2, ..., T6)
- T1: 3 berços
- T2: 5 berços
- T3: 4 berços
- T4: 3 berços
- T5: 2 berços
- T6: 1 berço

## 2. Quais tipos de navios cada terminal atende?
- Cada terminal atende um único tipo de navio: T1 atende o tipo C1, T2 atende o tipo C2, e assim por diante.
- Os berços de um mesmo terminal são equivalentes: o navio pode atracar em qualquer berço livre do seu terminal.

## 3. Qual é a taxa de chegada de navios em cada terminal?
- T1: 2,5 navios/dia
- T2: 4,0 navios/dia
- T3: 4,5 navios/dia
- T4: 3,5 navios/dia
- T5: 2,0 navios/dia
- T6: 1,0 navio/dia

## 4. Há algum tipo de sazonalidade na chegada de navios?
- Não.

## 5. Qual é a antecedência de notificação da chegada?
- Todos os terminais: 48 h.

## 6. Em que ordem os navios são atendidos?
- Por ordem de chegada ao fundeio, em cada terminal. Não há prioridade entre navios nem desistência.

## 7. Qual é o tempo de manobra entre o fundeio e o terminal?
- O tempo é praticamente constante e igual na entrada (atracação) e na saída (desatracação).
- T1: 1 h 40 min
- T2: 1 h 30 min
- T3: 1 h 20 min
- T4: 1 h 20 min
- T5: 1 h 5 min
- T6: 55 min

## 8. Qual é o tempo de operação dos navios no terminal (mínimo, mais provável, máximo)?
- T1: Tri(12, 15, 19) h
- T2: Tri(14, 18, 22) h
- T3: Tri(9, 12, 15) h
- T4: Tri(12, 15, 18) h
- T5: Tri(9, 12, 15) h
- T6: Tri(8, 10, 12) h

## 9. Qual é a probabilidade de um navio comprar combustível?
- T1: 70%
- T2: 60%
- T3: 50%
- T4: 65%
- T5: 55%
- T6: 50%

## 10. Qual é a quantidade de combustível demandada por navio comprador (mínimo, mais provável, máximo)?
- T1: Tri(600, 1000, 1800) t
- T2: Tri(800, 1200, 2000) t
- T3: Tri(400, 700, 1200) t
- T4: Tri(500, 900, 1600) t
- T5: Tri(300, 600, 1000) t
- T6: Tri(250, 500, 900) t

## 11. Distâncias (em km)
Base = base de combustível da BVE. As distâncias serão utilizadas no modelo das barcaças.

| De \ Para | Base | T1 | T2 | T3 | T4 | T5 | T6 |
|:--|:--|:--|:--|:--|:--|:--|:--|
| Base | 0,0 | 2,1 | 3,7 | 5,8 | 7,5 | 9,2 | 10,6 |
| T1 | 2,1 | 0,0 | 2,0 | 4,1 | 5,7 | 7,6 | 9,4 |
| T2 | 3,7 | 2,0 | 0,0 | 2,1 | 3,8 | 5,6 | 7,4 |
| T3 | 5,8 | 4,1 | 2,1 | 0,0 | 1,8 | 3,5 | 5,4 |
| T4 | 7,5 | 5,7 | 3,8 | 1,8 | 0,0 | 2,3 | 4,7 |
| T5 | 9,2 | 7,6 | 5,6 | 3,5 | 2,3 | 0,0 | 2,5 |
| T6 | 10,6 | 9,4 | 7,4 | 5,4 | 4,7 | 2,5 | 0,0 |
