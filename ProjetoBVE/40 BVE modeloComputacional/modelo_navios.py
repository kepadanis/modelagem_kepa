from pathlib import Path

import numpy as np
import pandas as pd
import simpy

HORAS_POR_DIA = 24.0

COLUNAS_LOG = ["id_cenario", "rep", "id_navio", "id_classe", "id_terminal",
               "t_notificacao", "t_chegada", "t_ini_manobra", "t_ini_operacao",
               "t_fim_operacao", "t_fim_manobra", "comprador", "volume_t"]
COLUNAS_TEMPO = [c for c in COLUNAS_LOG if c.startswith("t_")]


def carregar_parametros(pasta, id_cenario=None):
    pasta = Path(pasta)
    terminais = pd.read_csv(pasta / "terminais.csv")
    cenarios = pd.read_csv(pasta / "cenario.csv", parse_dates=["data_inicio"])
    if id_cenario is None:
        cenario = cenarios.iloc[0]
    else:
        cenario = cenarios.loc[cenarios["id_cenario"] == id_cenario].iloc[0]
    return terminais, cenario


def sortear(rng, dist, p1, p2=None, p3=None):
    if dist == "constante":
        return float(p1)
    if dist == "uniforme":
        return rng.uniform(p1, p2)
    if dist == "exponencial":
        return rng.exponential(p1)
    if dist == "triangular":
        return rng.triangular(p1, p2, p3)
    if dist == "erlang":
        return rng.gamma(p1, p2)
    if dist == "lognormal":
        return rng.lognormal(p1, p2)
    raise ValueError(f"Distribuição desconhecida: {dist}")


class Terminal:
    def __init__(self, env, linha, sequencias):
        self.id = linha["id_terminal"]
        self.classe = linha["id_classe"]
        self.n_bercos = int(linha["n_bercos"])
        self.taxa = float(linha["taxa_chegada"])
        self.antecedencia = float(linha["antecedencia"])
        self.manobra = float(linha["tempo_manobra"])
        self.dist_op = linha["dist_operacao"]
        self.par_op = (linha["op_p1"], linha["op_p2"], linha["op_p3"])
        self.prob_compra = float(linha["prob_compra"])
        self.dist_vol = linha["dist_volume"]
        self.par_vol = (linha["vl_p1"], linha["vl_p2"], linha["vl_p3"])
        self.bercos = simpy.Resource(env, capacity=self.n_bercos)
        self.rng_chegada, self.rng_compra, self.rng_volume, self.rng_operacao = (
            np.random.default_rng(s) for s in sequencias)
        self.N = 0
        self.n_notificados = 0
        self.ocupacao_max = 0
        self.fila_max = 0
        self.N_max = 0


def simular(terminais, cenario, rep):
    horizonte_h = float(cenario["horizonte"]) * HORAS_POR_DIA
    env = simpy.Environment()
    sementes = np.random.SeedSequence([int(cenario["semente"]), int(rep)]).spawn(4 * len(terminais))
    term = {}
    for i, (_, linha) in enumerate(terminais.iterrows()):
        term[linha["id_terminal"]] = Terminal(env, linha, sementes[4 * i:4 * i + 4])

    registros = []
    todos = []
    contador = {"navios": 0}

    def gerador_navios(t):
        while True:
            yield env.timeout(t.rng_chegada.exponential(1.0 / t.taxa))
            if env.now >= horizonte_h:
                break
            contador["navios"] += 1
            t.n_notificados += 1
            comprador = int(t.rng_compra.random() < t.prob_compra)
            volume = sortear(t.rng_volume, t.dist_vol, *t.par_vol) if comprador else 0.0
            reg = {"id_cenario": cenario["id_cenario"], "rep": int(rep),
                   "id_navio": f"N{contador['navios']:06d}", "id_classe": t.classe,
                   "id_terminal": t.id, "t_notificacao": env.now, "t_chegada": np.nan,
                   "t_ini_manobra": np.nan, "t_ini_operacao": np.nan, "t_fim_operacao": np.nan,
                   "t_fim_manobra": np.nan, "comprador": comprador, "volume_t": volume}
            todos.append(reg)
            env.process(navio(t, reg))

    def navio(t, reg):
        yield env.timeout(t.antecedencia)
        reg["t_chegada"] = env.now
        t.N += 1
        t.N_max = max(t.N_max, t.N)
        with t.bercos.request() as req:
            t.fila_max = max(t.fila_max, len(t.bercos.queue))
            yield req
            reg["t_ini_manobra"] = env.now
            t.ocupacao_max = max(t.ocupacao_max, t.bercos.count)
            yield env.timeout(t.manobra)
            reg["t_ini_operacao"] = env.now
            yield env.timeout(sortear(t.rng_operacao, t.dist_op, *t.par_op))
            reg["t_fim_operacao"] = env.now
            yield env.timeout(t.manobra)
            reg["t_fim_manobra"] = env.now
        t.N -= 1
        registros.append(reg)

    for t in term.values():
        env.process(gerador_navios(t))
    env.run(until=horizonte_h)

    diag = {
        "horizonte_h": horizonte_h,
        "n_notificados": {k: t.n_notificados for k, t in term.items()},
        "ocupacao_max": {k: t.ocupacao_max for k, t in term.items()},
        "fila_max": {k: t.fila_max for k, t in term.items()},
        "N_max": {k: t.N_max for k, t in term.items()},
        "n_registrados": len(registros),
        "n_total_notificados": contador["navios"],
        "notificados": montar_log(todos, cenario),
    }
    return montar_log(registros, cenario), diag


def montar_log(registros, cenario):
    log = pd.DataFrame(registros, columns=COLUNAS_LOG)
    origem = pd.Timestamp(cenario["data_inicio"])
    for c in COLUNAS_TEMPO:
        log[c] = origem + pd.to_timedelta(log[c], unit="h")
    log = log.sort_values("id_navio").reset_index(drop=True)
    log["rep"] = log["rep"].astype(int)
    log["comprador"] = log["comprador"].astype(int)
    log["volume_t"] = log["volume_t"].astype(float)
    return log


def gravar_log(log, caminho):
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    log.to_csv(caminho, index=False, date_format="%Y-%m-%d %H:%M:%S.%f")


def executar(pasta_entrada, pasta_saida, id_cenario=None):
    terminais, cenario = carregar_parametros(pasta_entrada, id_cenario)
    logs, diags = [], []
    for rep in range(1, int(cenario["n_rep"]) + 1):
        log, diag = simular(terminais, cenario, rep)
        logs.append(log)
        diags.append(diag)
    log = pd.concat(logs, ignore_index=True)
    gravar_log(log, Path(pasta_saida) / "log_navios.csv")
    return log, diags


if __name__ == "__main__":
    import sys
    log, diags = executar(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    print(len(log), "navios registrados em", Path(sys.argv[2]) / "log_navios.csv")
