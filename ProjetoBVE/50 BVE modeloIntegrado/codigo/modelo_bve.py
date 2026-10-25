"""modelo_bve.py, FASE 3a: infraestructura de simulacion integrada SIN PCO.

Un unico simpy.Environment, creado en `simula`, compartido por navios, base y barcacas.
Ninguna clase crea su propio entorno (lo comprueba un test sobre el AST y otro que cuenta instancias).

NO incluye: PCO, asignacion de pedidos, rutas, replanificacion, perdidas de pedidos ni ninguna decision
operativa integrada. Las barcacas, tambien en el modo integrado, ejecutan solo el ciclo independiente D09
(destino sorteado por la propia barcaca): NO interactuan con los navios.

MODOS
  reproduccion_navios    Reproduce modelo_navios.simular: mismas semillas y mismo orden de sorteo.
  reproduccion_barcacas  Reproduce modelo_barcacas.simular: mismas semillas y mismo orden de sorteo.
  integrado_sin_pco      Navios y barcacas en el mismo entorno, sin interaccion operativa. Los navios conservan
                         sus semillas (su log coincide con reproduccion_navios). Las barcacas usan una raiz de
                         semillas SEPARADA, de modo que su log NO coincide con el de reproduccion_barcacas: es
                         legitimo y esperado. Solo admite una configuracion de prueba explicita (ver
                         cargar_config_prueba); nunca INT_D09 ni INT_PROPOSTA.

COMPONENTES (E = existente reutilizado sin cambios; A = adaptacion de codigo existente; N = nuevo)
  modelo_navios.Terminal, .sortear, .montar_log, .COLUNAS_LOG      E  importados, sin copia
  modelo_barcacas.Barcaca, .montar_log, .gravar_log                E  importados, sin copia
  Navio                                                            N  sustituye al dict `reg` de modelo_navios
  SimulacionNavios.generador / .proceso_navio                      A  de modelo_navios.simular (gerador_navios / navio);
                                                                      mismo orden de sorteo por flujo
  HooksNavios                                                      N  puntos de observacion; no alteran sorteos
  BaseCarga                                                        N  extrae Frota.bercos/taxa_carga/ocupacao_max/fila_max
  FlotaBVE                                                         A  de modelo_barcacas.Frota, pero recibe `env`
  FlotaBVE.ciclo_d09                                               A  copia literal de Frota.ciclo (compat. D09)
  construir_semillas, construir_semillas_legado_mezclado,
  identidad, estado_pool, detectar_colisiones                      N  aislamiento de flujos aleatorios
  EntradaSimulacion, entrada_modelo_navios, entrada_modelo_barcacas,
  cargar_config_prueba                                             N  configuracion
  simula, ResultadoSimulacion                                      N  funcion principal

CONSTRUCCION EXACTA DE SEMILLAS (numpy.random.SeedSequence)
  Navios (reproduccion_navios e integrado_sin_pco), por terminal i (0..M-1) en el orden de terminais:
      raiz  = SeedSequence([semente, rep])
      hijos = raiz.spawn(4*M);   terminal i usa hijos[4i:4i+4] = (chegada, compra, volume, operacao)
      -> identico a modelo_navios.simular.
  Barcacas, reproduccion_barcacas, por barcaca j (0..B-1) en el orden de frota:
      raiz  = SeedSequence([semente, rep])
      hijos = raiz.spawn(2*B);   barcaca j usa hijos[2j:2j+2] = (destino, volume)
      -> identico a modelo_barcacas.Frota.
  Barcacas, integrado_sin_pco, por barcaca j:
      SeedSequence([semente, rep, 1], spawn_key=(tipo, j))   con tipo 0=destino, 1=volume, 2=conexao,
      3=desconexao, 4=manobra_base (2..4 reservados para fases futuras; no se usan en 3a).
      La entropia [semente, rep, 1] difiere de la de navios [semente, rep]; ademas el flujo de cada barcaca
      no depende del tamano de la flota (la clave es (tipo, j) y no una posicion en spawn(2*B)).
  Por que hay colision en los modelos independientes: ambos llaman SeedSequence([semente, rep]).spawn(...)
  y el hijo k tiene la MISMA identidad (entropia, spawn_key=(k,)) en los dos: el flujo de llegadas de T1
  (hijo 0 de navios) y el de destino de la primera barcaca (hijo 0 de barcacas) son el mismo flujo.
"""
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import simpy

import modelo_barcacas as mb
import modelo_navios as mn

AQUI = Path(__file__).resolve().parent
RAIZ_REPO = AQUI.parent
HORAS_POR_DIA = mn.HORAS_POR_DIA
MODOS = ("reproduccion_navios", "reproduccion_barcacas", "integrado_sin_pco")
FLUJOS_NAVIO = ("chegada", "compra", "volume", "operacao")      # orden de modelo_navios.simular
TIPOS_FLUJO_BARCACA = {"destino": 0, "volume": 1, "conexao": 2, "desconexao": 3, "manobra_base": 4}
ESCENARIOS_PROHIBIDOS_EN_3A = {"INT_D09", "INT_PROPOSTA"}


class ModoNoPermitido(ValueError):
    pass


class ConfigPruebaInvalida(ValueError):
    pass


# =====================================================================================
# Semillas y aislamiento de flujos aleatorios (NUEVO)
# =====================================================================================
@dataclass
class Semillas:
    navios: list            # 4*M SeedSequence planas, en el orden de terminais (o [] si no hay navios)
    barcacas: list          # por barcaca: [SeedSequence destino, SeedSequence volume] (o [])
    nombres: dict           # nombre legible -> SeedSequence (para analizar colisiones)


def _nombres_navios(ids_terminales, hijos):
    return {f"navios/{t}/{f}": hijos[4 * i + k]
            for i, t in enumerate(ids_terminales) for k, f in enumerate(FLUJOS_NAVIO)}


def construir_semillas(modo, ids_terminales, ids_barcacas, semente, rep):
    """Unica funcion que construye semillas; `simula` la usa. Ver docstring del modulo."""
    if modo not in MODOS:
        raise ModoNoPermitido(f"modo desconocido: {modo}")
    semente, rep = int(semente), int(rep)
    navios, barcacas, nombres = [], [], {}
    if modo in ("reproduccion_navios", "integrado_sin_pco"):
        navios = np.random.SeedSequence([semente, rep]).spawn(4 * len(ids_terminales))
        nombres.update(_nombres_navios(ids_terminales, navios))
    if modo == "reproduccion_barcacas":
        hijos = np.random.SeedSequence([semente, rep]).spawn(2 * len(ids_barcacas))
        barcacas = [[hijos[2 * j], hijos[2 * j + 1]] for j in range(len(ids_barcacas))]
    elif modo == "integrado_sin_pco":
        barcacas = [[np.random.SeedSequence([semente, rep, 1], spawn_key=(TIPOS_FLUJO_BARCACA["destino"], j)),
                     np.random.SeedSequence([semente, rep, 1], spawn_key=(TIPOS_FLUJO_BARCACA["volume"], j))]
                    for j in range(len(ids_barcacas))]
    for j, b in enumerate(ids_barcacas):
        if barcacas:
            nombres[f"barcacas/{b}/destino"], nombres[f"barcacas/{b}/volume"] = barcacas[j]
    return Semillas(list(navios), barcacas, nombres)


def construir_semillas_legado_mezclado(ids_terminales, ids_barcacas, semente, rep):
    """Lo que ocurriria al meter los dos modelos independientes en un mismo entorno SIN separar raices.
    NO se usa en simula: existe para que un test permanente detecte la colision."""
    s = construir_semillas("reproduccion_navios", ids_terminales, ids_barcacas, semente, rep)
    b = construir_semillas("reproduccion_barcacas", ids_terminales, ids_barcacas, semente, rep)
    return {**s.nombres, **b.nombres}


def identidad(ss):
    """Identidad exacta de un flujo SeedSequence: (entropia, spawn_key). Dos flujos con la misma identidad
    son el mismo flujo aleatorio, sin necesidad de muestrear numeros."""
    return tuple(np.atleast_1d(ss.entropy).tolist()), tuple(ss.spawn_key)


def estado_pool(ss):
    """Estado de semilla derivado (512 bits). No consume el flujo."""
    return tuple(int(x) for x in ss.generate_state(8, np.uint64))


def detectar_colisiones(nombres):
    """Pares de flujos con la misma identidad o el mismo estado de semilla. Lista vacia = flujos separados."""
    vistos_id, vistos_pool, out = {}, {}, []
    for n, ss in nombres.items():
        for tabla, clave, motivo in ((vistos_id, identidad(ss), "misma identidad"), (vistos_pool, estado_pool(ss), "mismo estado de semilla")):
            if clave in tabla:
                out.append((tabla[clave], n, motivo))
            else:
                tabla[clave] = n
    return out


# =====================================================================================
# Entrada y configuracion (NUEVO)
# =====================================================================================
@dataclass
class EntradaSimulacion:
    id: str
    origen: str                      # "MODELO_INDEPENDIENTE" | "CONFIG_PRUEBA"
    terminais: pd.DataFrame
    frota: pd.DataFrame
    cenario: pd.Series
    n_bercos_base: int | None = None
    taxa_carga_base: float | None = None
    advertencias: list = field(default_factory=list)
    definitivo: bool = False


def entrada_modelo_navios(pasta, id_cenario=None):
    """Carga con el cargador existente de modelo_navios (terminais.csv + cenario.csv)."""
    ter, cen = mn.carregar_parametros(pasta, id_cenario)
    return EntradaSimulacion(str(cen["id_cenario"]), "MODELO_INDEPENDIENTE", ter, pd.DataFrame(), cen)


def entrada_modelo_barcacas(pasta, id_cenario=None):
    """Carga con el cargador existente de modelo_barcacas (frota.csv + terminais.csv + cenario.csv)."""
    frota, ter, cen = mb.carregar_parametros(pasta, id_cenario)
    return EntradaSimulacion(str(cen["id_cenario"]), "MODELO_INDEPENDIENTE", ter, frota, cen,
                             int(cen["n_bercos_base"]), float(cen["taxa_carga_base"]))


COLUMNAS_CONFIG_PRUEBA = ["id_cenario", "estado", "data_inicio", "horizonte", "n_rep", "semente", "fator_demanda",
                          "arq_terminais", "arq_frota", "n_bercos_base", "taxa_carga_base"]
ETIQUETAS_CONFIG = {"CONFIRMADO_DOC", "PROVISIONAL"}


def cargar_config_prueba(ruta=AQUI / "config_prueba_3a.csv", ruta_fuentes=AQUI / "config_prueba_3a_fuentes.csv"):
    """Unica via de entrada al modo integrado en 3a. Exige: id 'PRUEBA_*' (nunca INT_D09/INT_PROPOSTA),
    estado PRUEBA_PROVISIONAL, todas las columnas, y una etiqueta (CONFIRMADO_DOC o PROVISIONAL) con fuente
    por cada parametro. No hay valores por defecto: lo que falta es un error."""
    df = pd.read_csv(ruta, dtype=str, keep_default_na=False)
    faltan = [c for c in COLUMNAS_CONFIG_PRUEBA if c not in df.columns]
    if faltan:
        raise ConfigPruebaInvalida(f"columnas ausentes (no se rellenan): {faltan}")
    if len(df) != 1:
        raise ConfigPruebaInvalida("la configuracion de prueba debe tener exactamente una fila")
    f = df.iloc[0]
    if f["id_cenario"] in ESCENARIOS_PROHIBIDOS_EN_3A or not f["id_cenario"].startswith("PRUEBA_"):
        raise ConfigPruebaInvalida(f"id '{f['id_cenario']}' no permitido: el integrado de 3a solo admite 'PRUEBA_*'")
    if f["estado"] != "PRUEBA_PROVISIONAL":
        raise ConfigPruebaInvalida(f"estado '{f['estado']}' no permitido (se exige PRUEBA_PROVISIONAL)")
    vacios = [c for c in COLUMNAS_CONFIG_PRUEBA if f[c].strip() == ""]
    if vacios:
        raise ConfigPruebaInvalida(f"valores vacios (no se asume ningun valor): {vacios}")
    fu = pd.read_csv(ruta_fuentes, dtype=str, keep_default_na=False).set_index("parametro")
    pars = [c for c in COLUMNAS_CONFIG_PRUEBA if c not in ("id_cenario", "estado")]
    sin = [p for p in pars if p not in fu.index]
    if sin:
        raise ConfigPruebaInvalida(f"parametros sin etiqueta/fuente: {sin}")
    mal = {p: fu.loc[p, "etiqueta"] for p in pars if fu.loc[p, "etiqueta"] not in ETIQUETAS_CONFIG}
    if mal or any(fu.loc[p, "fuente"].strip() == "" for p in pars):
        raise ConfigPruebaInvalida(f"etiquetas invalidas o fuentes vacias: {mal}")
    rt, rf = RAIZ_REPO / f["arq_terminais"], RAIZ_REPO / f["arq_frota"]
    for r in (rt, rf):
        if not r.is_file():
            raise ConfigPruebaInvalida(f"archivo inexistente: {r}")
    ter, frota = pd.read_csv(rt), pd.read_csv(rf)
    if "dist_base" not in ter.columns:
        raise ConfigPruebaInvalida("arq_terminais sin columna dist_base")
    cen = pd.Series({"id_cenario": f["id_cenario"], "data_inicio": pd.Timestamp(f["data_inicio"]),
                     "horizonte": float(f["horizonte"]), "n_rep": int(f["n_rep"]), "semente": int(f["semente"]),
                     "fator_demanda": float(f["fator_demanda"])})
    adv = [f"{p}: PROVISIONAL ({fu.loc[p, 'fuente']})" for p in pars if fu.loc[p, "etiqueta"] == "PROVISIONAL"]
    return EntradaSimulacion(f["id_cenario"], "CONFIG_PRUEBA", ter, frota, cen,
                             int(f["n_bercos_base"]), float(f["taxa_carga_base"]), adv)


# =====================================================================================
# Navios (adaptacion de modelo_navios.simular)
# =====================================================================================
class Navio:
    """NUEVO. Sustituye al diccionario `reg` de modelo_navios; sus atributos son las columnas de log."""
    __slots__ = tuple(mn.COLUNAS_LOG)

    def __init__(self, id_cenario, rep, id_navio, id_classe, id_terminal, t_notificacao, comprador, volume_t):
        self.id_cenario, self.rep, self.id_navio = id_cenario, int(rep), id_navio
        self.id_classe, self.id_terminal, self.t_notificacao = id_classe, id_terminal, t_notificacao
        self.t_chegada = self.t_ini_manobra = self.t_ini_operacao = self.t_fim_operacao = self.t_fim_manobra = np.nan
        self.comprador, self.volume_t = comprador, volume_t

    def como_registro(self):
        return {c: getattr(self, c) for c in mn.COLUNAS_LOG}


@dataclass
class HooksNavios:
    """NUEVO. Observadores opcionales. Se llaman con (navio, env.now); no pueden alterar los sorteos."""
    al_notificar: object = None
    al_iniciar_operacion: object = None
    al_finalizar_operacion: object = None


class SimulacionNavios:
    """ADAPTACION de modelo_navios.simular: mismos procesos y mismo orden de sorteo en cada flujo
    (chegada -> compra -> volume solo si comprador; operacao al empezar la operacion)."""

    def __init__(self, env, terminais, cenario, rep, sementes, hooks=None):
        if len(sementes) != 4 * len(terminais):
            raise ValueError("se esperan 4 semillas por terminal")
        self.env, self.cenario, self.rep = env, cenario, int(rep)
        self.horizonte_h = float(cenario["horizonte"]) * HORAS_POR_DIA
        fator = float(cenario["fator_demanda"])
        self.hooks = hooks or HooksNavios()
        self.term = {}
        for i, (_, linha) in enumerate(terminais.iterrows()):
            self.term[linha["id_terminal"]] = mn.Terminal(env, linha, fator, sementes[4 * i:4 * i + 4])
        self.registros, self.todos, self.contador = [], [], 0

    def lanzar(self):
        for t in self.term.values():
            self.env.process(self.generador(t))

    def generador(self, t):
        env = self.env
        while True:
            yield env.timeout(t.rng_chegada.exponential(1.0 / t.taxa))
            if env.now >= self.horizonte_h:
                break
            self.contador += 1
            t.n_notificados += 1
            comprador = int(t.rng_compra.random() < t.prob_compra)
            volume = mn.sortear(t.rng_volume, t.dist_vol, *t.par_vol) if comprador else 0.0
            navio = Navio(self.cenario["id_cenario"], self.rep, f"N{self.contador:06d}", t.classe, t.id,
                          env.now, comprador, volume)
            self.todos.append(navio)
            if self.hooks.al_notificar:
                self.hooks.al_notificar(navio, env.now)
            env.process(self.proceso_navio(t, navio))

    def proceso_navio(self, t, navio):
        env = self.env
        yield env.timeout(t.antecedencia)
        navio.t_chegada = env.now
        t.N += 1
        t.N_max = max(t.N_max, t.N)
        with t.bercos.request() as req:
            t.fila_max = max(t.fila_max, len(t.bercos.queue))
            yield req
            navio.t_ini_manobra = env.now
            t.ocupacao_max = max(t.ocupacao_max, t.bercos.count)
            yield env.timeout(t.manobra)
            navio.t_ini_operacao = env.now
            if self.hooks.al_iniciar_operacion:
                self.hooks.al_iniciar_operacion(navio, env.now)
            yield env.timeout(mn.sortear(t.rng_operacao, t.dist_op, *t.par_op))
            navio.t_fim_operacao = env.now
            if self.hooks.al_finalizar_operacion:
                self.hooks.al_finalizar_operacion(navio, env.now)
            yield env.timeout(t.manobra)
            navio.t_fim_manobra = env.now
        t.N -= 1
        self.registros.append(navio)

    def resultados(self):
        term = self.term
        diag = {
            "horizonte_h": self.horizonte_h,
            "n_notificados": {k: t.n_notificados for k, t in term.items()},
            "ocupacao_max": {k: t.ocupacao_max for k, t in term.items()},
            "fila_max": {k: t.fila_max for k, t in term.items()},
            "N_max": {k: t.N_max for k, t in term.items()},
            "N_final": {k: t.N for k, t in term.items()},
            "n_registrados": len(self.registros),
            "n_total_notificados": self.contador,
            "notificados": mn.montar_log([n.como_registro() for n in self.todos], self.cenario),
        }
        return mn.montar_log([n.como_registro() for n in self.registros], self.cenario), diag


# =====================================================================================
# Base y barcacas (adaptacion de modelo_barcacas.Frota)
# =====================================================================================
class BaseCarga:
    """NUEVO. Recurso compartido de la base de carga (berços FIFO), extraido de Frota."""

    def __init__(self, env, n_bercos, taxa_carga):
        self.env = env
        self.bercos = simpy.Resource(env, capacity=int(n_bercos))
        self.taxa_carga = float(taxa_carga)
        self.ocupacao_max = 0
        self.fila_max = 0


class FlotaBVE:
    """ADAPTACION de modelo_barcacas.Frota. Diferencia esencial: recibe `env` y `base`; no crea ningun entorno.
    Solo ejecuta el ciclo D09 (destino sorteado por la propia barcaca). No hay PCO ni interaccion con navios."""

    def __init__(self, env, base, frota, terminais, cenario, rep, sementes_por_barcaca):
        if len(sementes_por_barcaca) != len(frota):
            raise ValueError("se esperan 2 semillas (destino, volume) por barcaca")
        self.env, self.base, self.cenario, self.rep = env, base, cenario, int(rep)
        self.terminais = terminais.reset_index(drop=True)
        prob = np.minimum(1.0, self.terminais["prob_compra"].to_numpy() * float(cenario["fator_demanda"]))
        pesos = self.terminais["taxa_chegada"].to_numpy() * prob
        self.p_destino = pesos / pesos.sum()
        self.barcacas = [mb.Barcaca(l, sementes_por_barcaca[j]) for j, (_, l) in enumerate(frota.iterrows())]
        self.registros = []

    def registrar(self, b, viagem, estado, local, t_inicio, volume):
        self.registros.append({"id_cenario": self.cenario["id_cenario"], "rep": self.rep, "id_barcaca": b.id,
                               "viagem": viagem, "estado": estado, "local": local, "t_inicio": t_inicio,
                               "t_fim": self.env.now, "carga_t": b.carga, "volume_t": volume})

    def sortear_atendimento(self, b):
        j = b.rng_destino.choice(len(self.terminais), p=self.p_destino)
        t = self.terminais.iloc[j]
        volume = mn.sortear(b.rng_volume, t["dist_volume"], t["vl_p1"], t["vl_p2"], t["vl_p3"])
        return t["id_terminal"], float(t["dist_base"]), volume

    def ciclo_d09(self, b):
        """Copia literal de modelo_barcacas.Frota.ciclo (mismo orden de operaciones y de sorteos)."""
        env, viagem, base = self.env, 0, self.base
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
            with base.bercos.request() as req:
                base.fila_max = max(base.fila_max, len(base.bercos.queue))
                yield req
                self.registrar(b, viagem, "fila_base", "Base", t0, 0.0)
                base.ocupacao_max = max(base.ocupacao_max, base.bercos.count)
                carga_falta, t0 = b.capacidade - b.carga, env.now
                yield env.timeout(carga_falta / base.taxa_carga)
                b.carga = b.capacidade
                self.registrar(b, viagem, "carregando", "Base", t0, carga_falta)

    def lanzar(self):
        for b in self.barcacas:
            self.env.process(self.ciclo_d09(b))

    def resultados(self):
        diag = {"ocupacao_max": self.base.ocupacao_max, "fila_max": self.base.fila_max,
                "carga_final": {b.id: b.carga for b in self.barcacas}, "p_destino": self.p_destino}
        return mb.montar_log(self.registros, self.cenario), diag


# =====================================================================================
# Funcion principal (NUEVO)
# =====================================================================================
@dataclass
class ResultadoSimulacion:
    modo: str
    id_cenario: str
    rep: int
    env: object
    log_navios: pd.DataFrame | None
    diag_navios: dict | None
    log_barcacas: pd.DataFrame | None
    diag_barcacas: dict | None
    semillas: Semillas
    componentes: dict
    advertencias: list
    definitivo: bool = False

    def identidades(self):
        return {n: identidad(s) for n, s in self.semillas.nombres.items()}


def simula(entrada, rep, modo, hooks_navios=None):
    """Crea el UNICO simpy.Environment, instancia los componentes que pide el modo, lo ejecuta y recoge logs."""
    if modo not in MODOS:
        raise ModoNoPermitido(f"modo desconocido: {modo}")
    if modo == "integrado_sin_pco":
        if entrada.origen != "CONFIG_PRUEBA":
            raise ModoNoPermitido("integrado_sin_pco solo admite una configuracion de prueba (cargar_config_prueba)")
        if entrada.id in ESCENARIOS_PROHIBIDOS_EN_3A:
            raise ModoNoPermitido(f"{entrada.id} no puede ejecutarse en 3a")
    cen = entrada.cenario
    con_navios = modo in ("reproduccion_navios", "integrado_sin_pco")
    con_barcacas = modo in ("reproduccion_barcacas", "integrado_sin_pco") and len(entrada.frota) > 0
    if modo == "reproduccion_barcacas" and len(entrada.frota) == 0:
        raise ModoNoPermitido("reproduccion_barcacas exige una flota")
    ids_ter = list(entrada.terminais["id_terminal"])
    ids_bar = list(entrada.frota["id_barcaca"]) if len(entrada.frota) else []
    sem = construir_semillas(modo, ids_ter, ids_bar, cen["semente"], rep)

    env = simpy.Environment()                         # <- UNICA creacion de entorno del modulo
    comp = {}
    if con_navios:
        comp["navios"] = SimulacionNavios(env, entrada.terminais, cen, rep, sem.navios, hooks_navios)
    if con_barcacas:
        if entrada.n_bercos_base is None or entrada.taxa_carga_base is None:
            raise ModoNoPermitido("faltan n_bercos_base y taxa_carga_base (no se asumen valores)")
        comp["base"] = BaseCarga(env, entrada.n_bercos_base, entrada.taxa_carga_base)
        comp["flota"] = FlotaBVE(env, comp["base"], entrada.frota, entrada.terminais, cen, rep, sem.barcacas)
    if "navios" in comp:
        comp["navios"].lanzar()
    if "flota" in comp:
        comp["flota"].lanzar()
    env.run(until=float(cen["horizonte"]) * HORAS_POR_DIA)

    log_n = diag_n = log_b = diag_b = None
    if "navios" in comp:
        log_n, diag_n = comp["navios"].resultados()
    if "flota" in comp:
        log_b, diag_b = comp["flota"].resultados()
    return ResultadoSimulacion(modo, entrada.id, int(rep), env, log_n, diag_n, log_b, diag_b, sem, comp,
                               list(entrada.advertencias))
