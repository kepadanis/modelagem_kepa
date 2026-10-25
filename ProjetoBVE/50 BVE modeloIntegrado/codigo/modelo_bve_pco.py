"""modelo_bve_pco.py: modelo integrado da BVE (navios + barcaças + PCO) em UM único simpy.Environment.

REUTILIZADO sem cópia (módulos existentes do repositório):
  modelo_navios.Terminal / sortear / montar_log      geração de navios, berços e distribuições
  modelo_bve.SimulacionNavios / construir_semillas   processos dos navios com os mesmos sorteios do Lab 08
  prototipo_ventanas.PrevisorTerminal                janela de atendimento conhecida na notificação
  modelo_barcacas.montar_log / gravar_log            formato do log de barcaças (pré-aula 9)
NOVO neste módulo: Pedido, BarcacaPCO, PCO (rotina de programação), ModeloBVE (barcaças + base), função principal.

HIPÓTESES PROVISÓRIAS (nenhuma foi confirmada pelo professor; ver o relatório G112_D10):
  H1 (D-03) O PCO conhece a janela real [t_ini_operacao, t_fim_operacao] do navio no instante da notificação
            (previsor exato com sorteio antecipado da operação, "oráculo"). Premissa do modelo conceitual v1.1.
  H2        Pedido não programado numa rodada permanece na carteira e é reavaliado nas rodadas seguintes;
            é perdido quando a janela fecha sem início de atendimento (modelo conceitual, seção 3).
  H3 (D-04) Pedido já programado não é reatribuído a outra barcaça.
  H4 (D-07) Se a barcaça chega e o atendimento não cabe mais na janela, o pedido é perdido e a barcaça segue.
  H5 (D-05) Conexão e desconexão: constantes, valores em parametros_pco.csv (modelo conceitual/Dados: 1,5 h).
  H6 (D-06) Manobra na base: valor em parametros_pco.csv (sem dado em nenhum documento; adotado 0 h).
  H7        Previsão do PCO sem fila na base (como no modelo de referência do Lab 10).
Indicadores oficiais (definições do conceitual, seção 6): nível de serviço = pedidos atendidos / pedidos gerados;
utilização da barcaça = tempo fora de `ociosa` / tempo simulado; utilização do terminal de carga = tempo em
`carregando` / (berços x tempo simulado). O nível de serviço sobre pedidos resolvidos é apenas complementar.
Regra de programação (MVP pedido pelo grupo): rodadas nos horários de `horarios_programacao` do cenário,
pedidos ordenados por `regra_pco` (padrão menor_fim_janela), cada pedido vai à PRIMEIRA barcaça viável da
frota e cada barcaça recebe no máximo UM novo atendimento por rodada.
"""
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import simpy

import modelo_barcacas as mb
import modelo_bve as mv
import modelo_navios as mn
from prototipo_ventanas import PrevisorTerminal

EPS = 1e-9
HORAS_POR_DIA = mn.HORAS_POR_DIA
ESTADOS_BARCACA = ("ociosa", "fila_base", "carregando", "navegando", "aguardando_janela",
                   "conectando", "bombeando", "desconectando")
PARAMETROS_PCO = ("t_conexao", "t_desconexao", "t_manobra_base")
ESTADOS_PARAMETRO = {"CONFIRMADO_DOC", "HIPOTESE_PROVISORIA"}
REGRAS_PCO = ("menor_fim_janela", "ordem_aviso")
COLUNAS_CENARIO = ["id_cenario", "data_inicio", "horizonte", "n_rep", "semente", "fator_demanda", "n_bercos_base",
                   "taxa_carga_base", "horarios_programacao", "horizonte_programacao", "regra_pco"]
COLUNAS_PEDIDOS = ["id_cenario", "rep", "id_navio", "id_terminal", "volume_t", "t_notificacao", "t_ini_operacao",
                   "t_fim_operacao", "estado", "motivo", "id_barcaca", "t_programado", "t_fim_previsto",
                   "t_ini_bombeio", "t_fim_atendimento"]


class EntradaInvalida(ValueError):
    pass


# =====================================================================================
# Entradas: tudo é lido de arquivos, sem valores fixos no código
# =====================================================================================
@dataclass
class EntradaBVE:
    cenario: pd.Series
    terminais: pd.DataFrame
    frota: pd.DataFrame
    dist: dict
    par: dict
    par_tabela: pd.DataFrame
    horarios: list
    horizonte_prog_h: float
    regra_pco: str
    arquivos: dict = field(default_factory=dict)


def _horarios(txt):
    out = []
    for s in str(txt).split(";"):
        hh, mm = s.strip().split(":")
        out.append(int(hh) + int(mm) / 60.0)
    if not out or out != sorted(out) or not all(0 <= h < 24 for h in out):
        raise EntradaInvalida(f"horarios_programacao invalido: {txt}")
    return out


def carregar_entradas(arq_cenario, arq_terminais, arq_frota, arq_distancias, arq_pco, id_cenario=None):
    cen_df = pd.read_csv(arq_cenario, parse_dates=["data_inicio"])
    falta = [c for c in COLUNAS_CENARIO if c not in cen_df.columns]
    if falta:
        raise EntradaInvalida(f"colunas ausentes no cenario (nao sao preenchidas): {falta}")
    cen = cen_df.iloc[0] if id_cenario is None else cen_df.loc[cen_df["id_cenario"] == id_cenario].iloc[0]
    ter, frota = pd.read_csv(arq_terminais), pd.read_csv(arq_frota)
    if "dist_base" not in ter.columns:
        raise EntradaInvalida("terminais sem coluna dist_base")
    regra = str(cen["regra_pco"])
    if regra not in REGRAS_PCO:
        raise EntradaInvalida(f"regra_pco '{regra}' nao implementada; opcoes: {REGRAS_PCO}")
    d = pd.read_csv(arq_distancias)
    dist = {(r.origem, r.destino): float(r.distancia) for r in d.itertuples()}
    locais = ["Base"] + list(ter["id_terminal"])
    sem = [(a, b) for a in locais for b in locais if (a, b) not in dist]
    if sem:
        raise EntradaInvalida(f"distancias ausentes: {sem[:5]}")
    for _, l in ter.iterrows():
        if abs(dist[("Base", l["id_terminal"])] - float(l["dist_base"])) > 1e-9:
            raise EntradaInvalida(f"dist_base de {l['id_terminal']} difere da matriz de distancias")
    pt = pd.read_csv(arq_pco, dtype=str, keep_default_na=False)
    if list(pt.columns) != ["parametro", "valor", "estado", "fonte"]:
        raise EntradaInvalida("parametros_pco.csv deve ter as colunas parametro,valor,estado,fonte")
    pt = pt.set_index("parametro", drop=False)
    ausentes = [p for p in PARAMETROS_PCO if p not in pt.index]
    if ausentes:
        raise EntradaInvalida(f"parametros do PCO ausentes (nao ha valor padrao): {ausentes}")
    for p in PARAMETROS_PCO:
        if pt.loc[p, "estado"] not in ESTADOS_PARAMETRO or pt.loc[p, "fonte"].strip() == "" or pt.loc[p, "valor"].strip() == "":
            raise EntradaInvalida(f"parametro {p} sem valor, estado valido ou fonte")
    par = {p: float(pt.loc[p, "valor"]) for p in PARAMETROS_PCO}
    if min(par.values()) < 0:
        raise EntradaInvalida("parametros do PCO nao podem ser negativos")
    return EntradaBVE(cen, ter, frota, dist, par, pt.loc[list(PARAMETROS_PCO)].reset_index(drop=True),
                      _horarios(cen["horarios_programacao"]), float(cen["horizonte_programacao"]), regra,
                      {"cenario": str(arq_cenario), "terminais": str(arq_terminais), "frota": str(arq_frota),
                       "distancias": str(arq_distancias), "parametros_pco": str(arq_pco)})


# =====================================================================================
# Pedidos, barcaças e PCO
# =====================================================================================
@dataclass(eq=False)
class Pedido:
    """Pedido de combustível de um navio comprador; `t_ini`/`t_fim` é a janela conhecida pelo PCO (H1)."""
    id_navio: str
    id_terminal: str
    volume_t: float
    t_notificacao: float
    t_ini: float
    t_fim: float
    estado: str = "carteira"      # carteira, programado, em_atendimento, atendido, perdido
    motivo: str = ""
    barcaca: str = ""
    t_programado: float = np.nan
    t_fim_previsto: float = np.nan
    t_ini_bombeio: float = np.nan
    t_fim_atendimento: float = np.nan
    t_perdido: float = np.nan


class BarcacaPCO:
    """Agente passivo (como no modelo de referência): o PCO consulta status e grava a programação em `prox`."""

    def __init__(self, env, linha):
        self.id = linha["id_barcaca"]
        self.cap, self.vel = float(linha["capacidade"]), float(linha["velocidade"])
        self.bombeio, self.carga = float(linha["vazao_bomba"]), float(linha["carga_inicial"])
        # status previsto para o instante `prontidao` (consultado pelo PCO)
        self.prontidao, self.local, self.comb = 0.0, "Base", self.carga
        # programação (um único atendimento futuro por barcaça)
        self.prox = None
        self.acordar = env.event()
        # estado real e controle do log
        self.estado, self.local_log, self.t0, self.viagem = "ociosa", "Base", 0.0, 0


class PCO:
    """Rotina de programação do PCO (MVP): ver docstring do módulo. Os avisos chegam por `notificar`."""

    def __init__(self, env, barcacas, dist, par, horarios, horizonte_prog_h, regra):
        self.env, self.barcacas, self.dist, self.par = env, barcacas, dist, par
        self.horarios, self.H, self.regra = horarios, horizonte_prog_h, regra
        self.carteira, self.pedidos, self.rondas, self.decisoes = [], [], [], []

    def notificar(self, pedido):
        self.pedidos.append(pedido)
        self.carteira.append(pedido)

    def dur_servico(self, b, p):
        return self.par["t_conexao"] + p.volume_t / b.bombeio + self.par["t_desconexao"]

    def testar(self, b, p, t):
        """Viabilidade (como no modelo de referência): barcaça livre, combustível e janela."""
        if b.prox is not None:
            return None, "ocupada"
        if p.volume_t > b.comb + EPS:
            return None, "combustivel"
        chegada = max(b.prontidao, t) + self.dist[(b.local, p.id_terminal)] / b.vel
        termino = max(chegada, p.t_ini) + self.dur_servico(b, p)
        if termino > p.t_fim + EPS:
            return None, f"janela ({termino:.1f})"
        return termino, f"{termino:.1f}"

    def ordenar(self, lista):
        if self.regra == "menor_fim_janela":
            return sorted(lista, key=lambda p: (p.t_fim, -p.volume_t))
        return sorted(lista, key=lambda p: p.t_notificacao)

    def ronda(self, t):
        for p in self.carteira[:]:                    # janela fechada sem início de atendimento: perdido
            if p.t_fim <= t + EPS:
                p.estado, p.motivo, p.t_perdido = "perdido", "janela_fechou_sem_atendimento", p.t_fim
                self.carteira.remove(p)
        candidatos = self.ordenar([p for p in self.carteira if p.t_ini <= t + self.H + EPS])
        n_prog = 0
        for p in candidatos:
            testes, escolhida = [], None
            for b in self.barcacas:                   # ordem da frota: primeira barcaça viável
                termino, motivo = self.testar(b, p, t)
                testes.append((b.id, motivo))
                if termino is not None:
                    b.prox, p.estado, p.barcaca = p, "programado", b.id
                    p.t_programado, p.t_fim_previsto, escolhida = t, termino, b
                    self.carteira.remove(p)
                    if b.estado == "ociosa" and not b.acordar.triggered:
                        b.acordar.succeed()
                    n_prog += 1
                    break
            self.decisoes.append({"t_ronda": t, "id_navio": p.id_navio, "id_terminal": p.id_terminal,
                                  "volume_t": p.volume_t, "t_ini": p.t_ini, "t_fim": p.t_fim,
                                  "testes": " | ".join(f"{i}: {m}" for i, m in testes),
                                  "barcaca": escolhida.id if escolhida else ""})
        self.rondas.append({"t_ronda": t, "n_carteira": len(self.carteira) + n_prog,
                            "n_candidatos": len(candidatos), "n_programados": n_prog,
                            "n_sem_barcaca_viavel": len(candidatos) - n_prog})

    def processo(self):
        dia = 0
        while True:
            for h in self.horarios:
                t = dia * HORAS_POR_DIA + h
                if t > self.env.now:
                    yield self.env.timeout(t - self.env.now)
                self.ronda(self.env.now)
            dia += 1


class ModeloBVE:
    """Base de carga + barcaças + PCO. Recebe o `env` único: não cria nenhum Environment."""

    def __init__(self, env, entrada, rep):
        cen = entrada.cenario
        self.env, self.entrada, self.rep, self.cen = env, entrada, int(rep), cen
        self.dist, self.par = entrada.dist, entrada.par
        self.base = mv.BaseCarga(env, cen["n_bercos_base"], cen["taxa_carga_base"])
        self.barcacas = [BarcacaPCO(env, l) for _, l in entrada.frota.iterrows()]
        self.pco = PCO(env, self.barcacas, self.dist, self.par, entrada.horarios, entrada.horizonte_prog_h,
                       entrada.regra_pco)
        self.registros = []

    # ----- log no formato da pré-aula 9 (id_cenario, rep, id_barcaca, viagem, estado, local, t_inicio, t_fim, carga_t, volume_t)
    def _entrar(self, b, estado, local):
        b.estado, b.local_log, b.t0 = estado, local, self.env.now

    def _sair(self, b, volume=0.0, t_fim=None):
        self.registros.append({"id_cenario": self.cen["id_cenario"], "rep": self.rep, "id_barcaca": b.id,
                               "viagem": b.viagem, "estado": b.estado, "local": b.local_log, "t_inicio": b.t0,
                               "t_fim": self.env.now if t_fim is None else t_fim, "carga_t": b.carga,
                               "volume_t": volume})

    def fechar_estados(self, t):
        """Fecha em t (fim do horizonte) o estado em curso de cada barcaça, para que o log cubra todo o horizonte."""
        for b in self.barcacas:
            if b.t0 < t:
                self._sair(b, 0.0, t)

    def lancar(self):
        for b in self.barcacas:
            self.env.process(self.processo_barcaca(b))
        self.env.process(self.pco.processo())

    # ----- ciclo da barcaça (adaptado do modelo de referência do Lab 10 e do ciclo D09)
    def processo_barcaca(self, b):
        env = self.env
        while True:
            if b.cap - b.carga > EPS:
                yield from self.carregar(b)
            if b.prox is None:                         # sem atendimento programado: dorme até o PCO acordar
                b.prontidao, b.local, b.comb = env.now, "Base", b.carga
                b.acordar = env.event()
                self._entrar(b, "ociosa", "Base")
                yield b.acordar
                self._sair(b)
            b.viagem += 1
            pos = "Base"
            while b.prox is not None:                  # atende em sequência enquanto o PCO programar
                p, b.prox = b.prox, None
                yield from self.atender(b, p, pos)
                pos = p.id_terminal
            yield from self.voltar(b, pos)

    def carregar(self, b):
        env, base, tmb = self.env, self.base, self.par["t_manobra_base"]
        self._entrar(b, "fila_base", "Base")
        with base.bercos.request() as req:
            base.fila_max = max(base.fila_max, len(base.bercos.queue))
            yield req
            self._sair(b)
            base.ocupacao_max = max(base.ocupacao_max, base.bercos.count)
            falta = b.cap - b.carga
            dur = 2 * tmb + falta / base.taxa_carga
            b.prontidao, b.local, b.comb = env.now + dur, "Base", b.cap
            self._entrar(b, "carregando", "Base")
            yield env.timeout(dur)
            b.carga = b.cap
            self._sair(b, falta)

    def atender(self, b, p, pos):
        env, par = self.env, self.par
        t_nav = self.dist[(pos, p.id_terminal)] / b.vel
        dur = par["t_conexao"] + p.volume_t / b.bombeio + par["t_desconexao"]
        b.prontidao, b.local, b.comb = max(env.now + t_nav, p.t_ini) + dur, p.id_terminal, b.carga - p.volume_t
        self._entrar(b, "navegando", f"{pos}-{p.id_terminal}")
        yield env.timeout(t_nav)
        self._sair(b)
        inicio = max(env.now, p.t_ini)
        if inicio + dur > p.t_fim + EPS:               # H4: não cabe mais na janela, pedido perdido e a barcaça segue
            p.estado, p.motivo, p.t_perdido = "perdido", "nao_cabe_na_janela_ao_chegar", env.now
            b.prontidao, b.local, b.comb = env.now, p.id_terminal, b.carga
            return
        assert p.volume_t <= b.carga + EPS, "combustivel insuficiente apesar da viabilidade aprovada pelo PCO"
        if p.t_ini > env.now + EPS:
            self._entrar(b, "aguardando_janela", p.id_terminal)
            yield env.timeout(p.t_ini - env.now)
            self._sair(b)
        if par["t_conexao"] > 0:
            self._entrar(b, "conectando", p.id_terminal)
            yield env.timeout(par["t_conexao"])
            self._sair(b)
        p.estado, p.t_ini_bombeio = "em_atendimento", env.now
        self._entrar(b, "bombeando", p.id_terminal)
        yield env.timeout(p.volume_t / b.bombeio)
        b.carga -= p.volume_t
        self._sair(b, p.volume_t)
        if par["t_desconexao"] > 0:
            self._entrar(b, "desconectando", p.id_terminal)
            yield env.timeout(par["t_desconexao"])
            self._sair(b)
        p.estado, p.t_fim_atendimento = "atendido", env.now

    def voltar(self, b, pos):
        env, base = self.env, self.base
        t_nav = self.dist[(pos, "Base")] / b.vel
        falta = b.cap - b.carga
        b.prontidao = env.now + t_nav + (2 * self.par["t_manobra_base"] + falta / base.taxa_carga if falta > EPS else 0.0)
        b.local, b.comb = "Base", b.cap
        self._entrar(b, "navegando", f"{pos}-Base")
        yield env.timeout(t_nav)
        self._sair(b)


# =====================================================================================
# Função principal e indicadores
# =====================================================================================
@dataclass
class ResultadoBVE:
    indicadores: dict
    log_navios: pd.DataFrame
    log_barcacas: pd.DataFrame
    log_pedidos: pd.DataFrame
    rondas: pd.DataFrame
    decisoes: pd.DataFrame
    pedidos: list
    entrada: EntradaBVE
    env: object
    previsoes: dict
    arquivos_gravados: list


def _para_data(horas, origem):
    return (origem + pd.to_timedelta(pd.Series(horas, dtype=float), unit="h")).dt.round("us")


def montar_log_pedidos(pedidos, cen, rep):
    origem = pd.Timestamp(cen["data_inicio"])
    df = pd.DataFrame([{"id_cenario": cen["id_cenario"], "rep": int(rep), "id_navio": p.id_navio,
                        "id_terminal": p.id_terminal, "volume_t": p.volume_t, "t_notificacao": p.t_notificacao,
                        "t_ini_operacao": p.t_ini, "t_fim_operacao": p.t_fim, "estado": p.estado,
                        "motivo": p.motivo, "id_barcaca": p.barcaca, "t_programado": p.t_programado,
                        "t_fim_previsto": p.t_fim_previsto, "t_ini_bombeio": p.t_ini_bombeio,
                        "t_fim_atendimento": p.t_fim_atendimento} for p in pedidos], columns=COLUNAS_PEDIDOS)
    for c in [c for c in COLUNAS_PEDIDOS if c.startswith("t_")]:
        df[c] = _para_data(df[c].to_numpy(), origem).to_numpy()
    return df.sort_values("id_navio").reset_index(drop=True)


def calcular_indicadores(entrada, rep, semente, log_barcacas, pedidos, horizonte_h, n_navios, n_bercos_base):
    resolvidos = [p for p in pedidos if p.estado in ("atendido", "perdido")]
    atend = [p for p in resolvidos if p.estado == "atendido"]
    perd = [p for p in resolvidos if p.estado == "perdido"]
    motivos = pd.Series([p.motivo for p in perd], dtype=str).value_counts().to_dict()
    dur = (log_barcacas["t_fim"] - log_barcacas["t_inicio"]).dt.total_seconds() / 3600.0
    por_estado = dur.groupby([log_barcacas["id_barcaca"], log_barcacas["estado"]]).sum().unstack(fill_value=0.0)
    por_estado = por_estado.reindex(columns=list(ESTADOS_BARCACA), fill_value=0.0)
    util_b = 1.0 - por_estado["ociosa"] / horizonte_h        # tudo fora de `ociosa` conta como ocupada
    util_prod = (por_estado[["navegando", "conectando", "bombeando", "desconectando", "carregando"]].sum(axis=1)
                 / horizonte_h)
    espera_janela = por_estado["aguardando_janela"] / horizonte_h
    espera_fila = por_estado["fila_base"] / horizonte_h
    composicao = {"produtivo": float(util_prod.mean()), "espera_janela_no_terminal": float(espera_janela.mean()),
                  "espera_fila_base": float(espera_fila.mean()), "ociosa": float((por_estado["ociosa"] / horizonte_h).mean())}
    fila = dur[log_barcacas["estado"] == "fila_base"]
    return {
        "id_cenario": str(entrada.cenario["id_cenario"]), "rep": int(rep), "semente": int(semente),
        "horizonte_dias": float(entrada.cenario["horizonte"]), "n_barcacas": len(entrada.frota),
        "n_navios": int(n_navios), "n_pedidos": len(pedidos), "n_resolvidos": len(resolvidos),
        "n_atendidos": len(atend), "n_perdidos": len(perd),
        "n_em_aberto": len(pedidos) - len(resolvidos),
        # OFICIAL: atendidos / pedidos gerados (proposta e conceitual: "pedidos atendidos / pedidos"); os pedidos
        # ainda em aberto no fim do horizonte contam no denominador, como não atendidos.
        "nivel_servico": len(atend) / len(pedidos) if pedidos else float("nan"),
        # COMPLEMENTAR: exclui os pedidos ainda em aberto no fim do horizonte (cuja sorte não é conhecida).
        "nivel_servico_resolvidos": len(atend) / len(resolvidos) if resolvidos else float("nan"),
        "perdidos_por_motivo": motivos,
        "volume_demandado_t": float(sum(p.volume_t for p in resolvidos)),
        "volume_atendido_t": float(sum(p.volume_t for p in atend)),
        "volume_perdido_t": float(sum(p.volume_t for p in perd)),
        # OFICIAL (conceitual, seção 6): tempo fora de `ociosa` / tempo simulado (não há `fora de operação`).
        "utilizacao_barcacas_media": float(util_b.mean()),
        "utilizacao_barcacas": {k: float(v) for k, v in util_b.items()},
        "utilizacao_produtiva_barcacas_media": float(util_prod.mean()),
        # soma 1: produtivo (navegando, conectando, bombeando, desconectando, carregando) + espera na janela
        # + espera por berço na base + ociosa
        "composicao_tempo_barcacas": composicao,
        "tempo_por_estado_h": {k: {e: float(x) for e, x in r.items()} for k, r in por_estado.iterrows()},
        "utilizacao_terminal_carga": float(dur[log_barcacas["estado"] == "carregando"].sum()
                                           / (n_bercos_base * horizonte_h)),
        "espera_media_fila_base_h": float(fila.mean()) if len(fila) else 0.0,
        "espera_max_fila_base_h": float(fila.max()) if len(fila) else 0.0,
    }


def executar_bve(arq_cenario, arq_terminais, arq_frota, arq_distancias, arq_pco, semente,
                 gravar_logs=False, pasta_logs=None, id_cenario=None, rep=1):
    """Executa UMA replicação e devolve ResultadoBVE (logs em memória + indicadores)."""
    ent = carregar_entradas(arq_cenario, arq_terminais, arq_frota, arq_distancias, arq_pco, id_cenario)
    if gravar_logs and pasta_logs is None:
        raise ValueError("gravar_logs=True exige pasta_logs")
    cen = ent.cenario.copy()
    cen["semente"] = int(semente)
    horizonte_h = float(cen["horizonte"]) * HORAS_POR_DIA
    ids_ter = list(ent.terminais["id_terminal"])
    sem = mv.construir_semillas("reproduccion_navios", ids_ter, [], semente, rep)   # mesmas sementes do Lab 08

    env = simpy.Environment()                          # <- ÚNICO Environment da simulação integrada
    modelo = ModeloBVE(env, ent, rep)
    previsores = {l["id_terminal"]: PrevisorTerminal(l, sem.navios[4 * i + 3])
                  for i, (_, l) in enumerate(ent.terminais.iterrows())}
    previsoes = {}

    def ao_notificar(navio, t):                        # aviso de chegada ao PCO (H1: janela exata)
        prev = previsores[navio.id_terminal].notificar(t)        # todos os navios ocupam berço: sempre avança
        previsoes[navio.id_navio] = prev
        if navio.comprador:
            modelo.pco.notificar(Pedido(navio.id_navio, navio.id_terminal, float(navio.volume_t), t,
                                        prev["t_ini_operacao"], prev["t_fim_operacao"]))

    navios = mv.SimulacionNavios(env, ent.terminais, cen, rep, sem.navios, mv.HooksNavios(al_notificar=ao_notificar))
    navios.lanzar()
    modelo.lancar()
    env.run(until=horizonte_h)
    modelo.fechar_estados(env.now)
    for p in modelo.pco.carteira:                      # janela já fechada ao fim do horizonte: perdido
        if p.t_fim <= horizonte_h + EPS:
            p.estado, p.motivo, p.t_perdido = "perdido", "janela_fechou_sem_atendimento", p.t_fim
    log_n, _ = navios.resultados()
    log_b = mb.montar_log(modelo.registros, cen)
    log_p = montar_log_pedidos(modelo.pco.pedidos, cen, rep)
    ind = calcular_indicadores(ent, rep, semente, log_b, modelo.pco.pedidos, horizonte_h, navios.contador,
                               int(cen["n_bercos_base"]))
    gravados = []
    if gravar_logs:
        pasta = Path(pasta_logs)
        for nome, df in (("log_navios.csv", log_n), ("log_barcacas.csv", log_b), ("log_pedidos.csv", log_p)):
            mb.gravar_log(df, pasta / nome)
            gravados.append(str(pasta / nome))
    return ResultadoBVE(ind, log_n, log_b, log_p, pd.DataFrame(modelo.pco.rondas), pd.DataFrame(modelo.pco.decisoes),
                        modelo.pco.pedidos, ent, env, previsoes, gravados)


def simular_bve(arq_cenario, arq_terminais, arq_frota, arq_distancias, arq_pco, semente,
                gravar_logs=False, pasta_logs=None, id_cenario=None):
    """Função principal pedida no Lab 10: recebe os arquivos de entrada e a semente, grava os logs CSV só se
    `gravar_logs` for True e devolve os indicadores de desempenho."""
    return executar_bve(arq_cenario, arq_terminais, arq_frota, arq_distancias, arq_pco, semente,
                        gravar_logs, pasta_logs, id_cenario).indicadores
