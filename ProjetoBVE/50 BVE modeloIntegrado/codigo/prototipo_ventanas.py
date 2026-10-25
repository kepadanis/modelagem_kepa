"""PROTOTIPO (no es el modelo integrado): prediccion de la ventana de servicio de cada navio
en el instante de la notificacion, y comprobacion contra la ventana real.

Idea: por terminal, un 'previsor' mantiene (a) un clon del flujo rng_operacao (misma SeedSequence,
mismo orden de sorteo) y (b) un heap con los instantes en que quedara libre cada berco.
Hipotesis a verificar: el k-esimo navio notificado en un terminal es el k-esimo en conseguir berco
(FIFO + antecedencia constante) => recibe el k-esimo sorteo de operacion.
El previsor NO consume el rng real: no altera el orden de sorteo del modelo de navios.

LIMITES (vigentes mientras no se demuestre lo contrario):
 - Exige antecedencia y tempo_manobra CONSTANTES por terminal, berco FIFO y numero de bercos fijo.
   Si el PCO/modelo introdujera manobra aleatoria, prioridades o reordenaciones de cola, la prediccion
   por heap dejaria de ser exacta y habria que repetir las pruebas.
 - ORACULO: la duracion de operacion del navio se sortea por adelantado (al notificar). Eso equivale a
   suponer que el PCO conoce la ventana exacta al notificar. Que el PCO conozca la ventana exacta es
   una hipotesis del modelo, no un dato confirmado (decision pendiente del profesor).
 - Causalidad: notificar() solo usa t_notif y el estado acumulado por notificaciones ANTERIORES.
"""
import heapq
import numpy as np
import simpy
import modelo_navios as mn


class PrevisorTerminal:
    def __init__(self, linha, semilla_operacao):
        self.rng = np.random.default_rng(semilla_operacao)       # clon del flujo real
        self.libres = [0.0] * int(linha["n_bercos"])             # instantes de liberacion de cada berco
        heapq.heapify(self.libres)
        self.ant = float(linha["antecedencia"]); self.man = float(linha["tempo_manobra"])
        self.dist = linha["dist_operacao"]; self.par = (linha["op_p1"], linha["op_p2"], linha["op_p3"])

    def notificar(self, t_notif):
        chegada = t_notif + self.ant
        libre = heapq.heappop(self.libres)
        ini_man = max(chegada, libre)
        ini_op = ini_man + self.man
        fim_op = ini_op + mn.sortear(self.rng, self.dist, *self.par)
        fim_man = fim_op + self.man
        heapq.heappush(self.libres, fim_man)
        return {"t_chegada": chegada, "t_ini_manobra": ini_man, "t_ini_operacao": ini_op,
                "t_fim_operacao": fim_op, "t_fim_manobra": fim_man}


def simular_con_prevision(terminais, cenario, rep, clase_previsor=None):
    """Copia de mn.simular con UN hook: al notificar, guarda la prevision. Mismos sorteos, mismo orden."""
    clase_previsor = clase_previsor or PrevisorTerminal
    horizonte_h = float(cenario["horizonte"]) * mn.HORAS_POR_DIA
    fator = float(cenario["fator_demanda"])
    env = simpy.Environment()
    sem = np.random.SeedSequence([int(cenario["semente"]), int(rep)]).spawn(4 * len(terminais))
    term, prev = {}, {}
    for i, (_, l) in enumerate(terminais.iterrows()):
        term[l["id_terminal"]] = mn.Terminal(env, l, fator, sem[4 * i:4 * i + 4])
        prev[l["id_terminal"]] = clase_previsor(l, sem[4 * i + 3])
    registros, todos, previsiones, cont = [], [], {}, {"n": 0}

    def gerador(t):
        while True:
            yield env.timeout(t.rng_chegada.exponential(1.0 / t.taxa))
            if env.now >= horizonte_h:
                break
            cont["n"] += 1; t.n_notificados += 1
            comprador = int(t.rng_compra.random() < t.prob_compra)
            volume = mn.sortear(t.rng_volume, t.dist_vol, *t.par_vol) if comprador else 0.0
            idn = f"N{cont['n']:06d}"
            previsiones[idn] = prev[t.id].notificar(env.now)          # <-- hook (unico cambio)
            reg = {"id_cenario": cenario["id_cenario"], "rep": int(rep), "id_navio": idn, "id_classe": t.classe,
                   "id_terminal": t.id, "t_notificacao": env.now, "t_chegada": np.nan, "t_ini_manobra": np.nan,
                   "t_ini_operacao": np.nan, "t_fim_operacao": np.nan, "t_fim_manobra": np.nan,
                   "comprador": comprador, "volume_t": volume}
            todos.append(reg); env.process(navio(t, reg))

    def navio(t, reg):
        yield env.timeout(t.antecedencia)
        reg["t_chegada"] = env.now; t.N += 1; t.N_max = max(t.N_max, t.N)
        with t.bercos.request() as req:
            t.fila_max = max(t.fila_max, len(t.bercos.queue))
            yield req
            reg["t_ini_manobra"] = env.now; t.ocupacao_max = max(t.ocupacao_max, t.bercos.count)
            yield env.timeout(t.manobra); reg["t_ini_operacao"] = env.now
            yield env.timeout(mn.sortear(t.rng_operacao, t.dist_op, *t.par_op)); reg["t_fim_operacao"] = env.now
            yield env.timeout(t.manobra); reg["t_fim_manobra"] = env.now
        t.N -= 1; registros.append(reg)

    for t in term.values():
        env.process(gerador(t))
    env.run(until=horizonte_h)
    return registros, todos, previsiones, term


CAMPOS = ["t_chegada", "t_ini_manobra", "t_ini_operacao", "t_fim_operacao", "t_fim_manobra"]


class Resultado:
    """Resultado de comparar prevision vs real.
    n_por_campo: nº de valores comparados por campo (solo los que ya ocurrieron antes del fin del horizonte).
    OJO: t_chegada = t_notificacao + antecedencia en ambos lados (casi tautologico); los valores
    'no triviales' son los otros cuatro campos."""
    def __init__(self, n_por_campo, max_dif, n_mal, log_igual, n_navios):
        self.n_por_campo, self.max_dif, self.n_mal = n_por_campo, max_dif, n_mal
        self.log_igual, self.n_navios = log_igual, n_navios

    @property
    def n(self):
        return sum(self.n_por_campo.values())

    @property
    def n_no_triviales(self):
        return self.n - self.n_por_campo["t_chegada"]


def comparar(terminais, cenario, rep, clase_previsor=None):
    """Prevision (previsor, en el instante de la notificacion) vs valor real (env.now del proceso SimPy
    con simpy.Resource). Ademas comprueba que el log de la copia con hook == log del modelo original mn.simular."""
    registros, todos, prev, _ = simular_con_prevision(terminais, cenario, rep, clase_previsor)
    n_campo = {c: 0 for c in CAMPOS}; bad = 0; mx = 0.0
    for r in todos:                      # todos los notificados; solo se compara lo ya ocurrido en el horizonte
        for c in CAMPOS:
            real = r[c]
            if real != real:             # NaN: aun no ocurrio al fin del horizonte
                continue
            d = abs(real - prev[r["id_navio"]][c]); mx = max(mx, d); n_campo[c] += 1
            if d > 1e-9: bad += 1
    log_orig, _ = mn.simular(terminais, cenario, rep)
    log_hook = mn.montar_log(registros, cenario)
    return Resultado(n_campo, mx, bad, log_orig.reset_index(drop=True).equals(log_hook.reset_index(drop=True)), len(todos))


def predecir_desde_notificaciones(terminais, cenario, rep, notificados):
    """Referencia INDEPENDIENTE del hook: usa solo el log de notificaciones que devuelve mn.simular
    (diag['notificados']) y reconstruye los previsores desde la semilla. Devuelve {id_navio: prevision en horas}."""
    sem = np.random.SeedSequence([int(cenario["semente"]), int(rep)]).spawn(4 * len(terminais))
    prev = {l["id_terminal"]: PrevisorTerminal(l, sem[4 * i + 3]) for i, (_, l) in enumerate(terminais.iterrows())}
    origen = np.datetime64(cenario["data_inicio"])
    out = {}
    nots = notificados.sort_values("t_notificacao", kind="stable")
    for _, r in nots.iterrows():
        t = (np.datetime64(r["t_notificacao"]) - origen) / np.timedelta64(1, "h")
        out[r["id_navio"]] = prev[r["id_terminal"]].notificar(float(t))
    return out
