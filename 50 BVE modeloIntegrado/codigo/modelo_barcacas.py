from pathlib import Path

import numpy as np
import pandas as pd
import simpy

HORAS_POR_DIA = 24.0
COLUNAS_LOG = ["id_cenario", "rep", "id_barcaca", "viagem", "estado", "local",
               "t_inicio", "t_fim", "carga_t", "volume_t"]


def carregar_parametros(pasta, id_cenario=None):
    pasta = Path(pasta)
    frota = pd.read_csv(pasta / "frota.csv")
    terminais = pd.read_csv(pasta / "terminais.csv")
    cenarios = pd.read_csv(pasta / "cenario.csv", parse_dates=["data_inicio"])
    cenario = cenarios.iloc[0] if id_cenario is None else cenarios.loc[cenarios["id_cenario"] == id_cenario].iloc[0]
    return frota, terminais, cenario


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


class Barcaca:
    def __init__(self, linha, sequencias):
        self.id = linha["id_barcaca"]
        self.capacidade = float(linha["capacidade"])
        self.velocidade = float(linha["velocidade"])
        self.vazao_bomba = float(linha["vazao_bomba"])
        self.carga = float(linha["carga_inicial"])
        self.rng_destino, self.rng_volume = (np.random.default_rng(s) for s in sequencias)


class Frota:
    def __init__(self, frota, terminais, cenario, rep):
        self.cenario, self.rep = cenario, int(rep)
        self.env = simpy.Environment()
        self.horizonte_h = float(cenario["horizonte"]) * HORAS_POR_DIA
        self.bercos = simpy.Resource(self.env, capacity=int(cenario["n_bercos_base"]))
        self.taxa_carga = float(cenario["taxa_carga_base"])
        self.terminais = terminais.reset_index(drop=True)
        prob = np.minimum(1.0, self.terminais["prob_compra"].to_numpy() * float(cenario["fator_demanda"]))
        pesos = self.terminais["taxa_chegada"].to_numpy() * prob
        self.p_destino = pesos / pesos.sum()
        n_fluxos = 2  # destino, volume
        sementes = np.random.SeedSequence([int(cenario["semente"]), self.rep]).spawn(n_fluxos * len(frota))
        self.barcacas = [Barcaca(l, sementes[n_fluxos * i:n_fluxos * (i + 1)])
                         for i, (_, l) in enumerate(frota.iterrows())]
        self.registros = []
        self.ocupacao_max = 0
        self.fila_max = 0

    def registrar(self, b, viagem, estado, local, t_inicio, volume):
        self.registros.append({"id_cenario": self.cenario["id_cenario"], "rep": self.rep, "id_barcaca": b.id,
                               "viagem": viagem, "estado": estado, "local": local, "t_inicio": t_inicio,
                               "t_fim": self.env.now, "carga_t": b.carga, "volume_t": volume})

    def sortear_atendimento(self, b):
        j = b.rng_destino.choice(len(self.terminais), p=self.p_destino)
        t = self.terminais.iloc[j]
        volume = sortear(b.rng_volume, t["dist_volume"], t["vl_p1"], t["vl_p2"], t["vl_p3"])
        return t["id_terminal"], float(t["dist_base"]), volume

    def ciclo(self, b):
        env, viagem = self.env, 0
        while True:
            viagem += 1
            terminal, dist, volume = self.sortear_atendimento(b)
            t0 = env.now
            yield env.timeout(dist / b.velocidade)
            self.registrar(b, viagem, "navegando", f"Base-{terminal}", t0, 0.0)
            entregue, t0 = min(volume, b.carga), env.now
            yield env.timeout(entregue / b.vazao_bomba)
            b.carga -= entregue
            self.registrar(b, viagem, "bombeando", terminal, t0, entregue)
            t0 = env.now
            yield env.timeout(dist / b.velocidade)
            self.registrar(b, viagem, "navegando", f"{terminal}-Base", t0, 0.0)
            t0 = env.now
            with self.bercos.request() as req:
                self.fila_max = max(self.fila_max, len(self.bercos.queue))
                yield req
                self.registrar(b, viagem, "fila_base", "Base", t0, 0.0)
                self.ocupacao_max = max(self.ocupacao_max, self.bercos.count)
                carga_falta, t0 = b.capacidade - b.carga, env.now
                yield env.timeout(carga_falta / self.taxa_carga)
                b.carga = b.capacidade
                self.registrar(b, viagem, "carregando", "Base", t0, carga_falta)

    def simular(self):
        for b in self.barcacas:
            self.env.process(self.ciclo(b))
        self.env.run(until=self.horizonte_h)
        diag = {"ocupacao_max": self.ocupacao_max, "fila_max": self.fila_max,
                "carga_final": {b.id: b.carga for b in self.barcacas}, "p_destino": self.p_destino}
        return montar_log(self.registros, self.cenario), diag


def montar_log(registros, cenario):
    log = pd.DataFrame(registros, columns=COLUNAS_LOG)
    origem = pd.Timestamp(cenario["data_inicio"])
    for c in ("t_inicio", "t_fim"):
        log[c] = (origem + pd.to_timedelta(log[c], unit="h")).dt.round("us")
    log = log.sort_values(["id_barcaca", "t_inicio", "t_fim"], kind="stable").reset_index(drop=True)
    log["rep"] = log["rep"].astype(int)
    log["viagem"] = log["viagem"].astype(int)
    return log


def simular(frota, terminais, cenario, rep):
    return Frota(frota, terminais, cenario, rep).simular()


def gravar_log(log, caminho):
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    log.to_csv(caminho, index=False, date_format="%Y-%m-%d %H:%M:%S.%f")


def executar(pasta_entrada, pasta_saida, id_cenario=None):
    frota, terminais, cenario = carregar_parametros(pasta_entrada, id_cenario)
    logs, diags = [], []
    for rep in range(1, int(cenario["n_rep"]) + 1):
        log, diag = simular(frota, terminais, cenario, rep)
        logs.append(log)
        diags.append(diag)
    log = pd.concat(logs, ignore_index=True)
    gravar_log(log, Path(pasta_saida) / "log_barcacas.csv")
    return log, diags


if __name__ == "__main__":
    import sys
    log, _ = executar(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    print(len(log), "linhas de estado em", Path(sys.argv[2]) / "log_barcacas.csv")
