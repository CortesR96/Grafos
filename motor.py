import heapq
import json
import string
from collections import deque


class TutorAdaptativo:
    """Perfila errores conceptuales del estudiante y selecciona retos dirigidos."""

    def __init__(self):
        self.aciertos = 0
        self.errores = 0
        self.racha = 0
        self.nivel = 1
        self.errores_por_alg = {"BFS": 0, "DFS": 0, "Dijkstra": 0}
        self.trampa_dijkstra = False
        self.ultimo_mensaje = "Listo. Usa Modo Rayos X para observar o Modo Oráculo para evaluarte."
        self.ultimo_tipo = "info"  # info | ok | error

    def registrar_acierto(self, algoritmo: str, nodo: str):
        self.aciertos += 1
        self.racha += 1
        if self.racha >= 3:
            self.trampa_dijkstra = False
            if self.nivel < 3:
                self.nivel += 1
            self.ultimo_mensaje = (
                f"Excelente: '{nodo}' era correcto. Racha de {self.racha} aciertos — "
                f"dominio sólido en {algoritmo} (Nivel {self.nivel})."
            )
        else:
            self.ultimo_mensaje = f"Correcto: {algoritmo} expande '{nodo}'. Racha actual: {self.racha}."
        self.ultimo_tipo = "ok"

    def registrar_error(self, algoritmo: str, elegido: str, validos: list, costos: dict, min_costo=None):
        self.errores += 1
        self.racha = 0
        self.errores_por_alg[algoritmo] += 1
        self.ultimo_tipo = "error"

        if algoritmo == "Dijkstra":
            self.trampa_dijkstra = True
            c_elegido = costos.get(elegido, "∞")
            self.ultimo_mensaje = (
                f"Fallo en Dijkstra: elegiste '{elegido}' (costo acumulado {c_elegido}), "
                f"pero el mínimo disponible es {min_costo} en {validos}. "
                "Tutor: activé el 'Reto Adaptativo' (Grafo Trampa) para corregir el sesgo de saltos."
            )
        elif algoritmo == "BFS":
            self.ultimo_mensaje = (
                f"Fallo en BFS: elegiste '{elegido}', pero debía salir {validos}. "
                "Recuerda la Cola (FIFO): siempre sale el nodo que entró primero, nivel por nivel."
            )
        else:
            self.ultimo_mensaje = (
                f"Fallo en DFS: elegiste '{elegido}', pero debía salir {validos}. "
                "Recuerda la Pila (LIFO): siempre sale el último nodo apilado en la rama más profunda."
            )

    def precision(self) -> int:
        total = self.aciertos + self.errores
        return round((self.aciertos / total) * 100) if total > 0 else 100

    def recomendar_preset(self) -> tuple[str, str]:
        """Devuelve (preset_id, algoritmo_sugerido) según la debilidad real del usuario."""
        if self.trampa_dijkstra or self.errores_por_alg["Dijkstra"] > 0:
            return ("trampa_dijkstra", "Dijkstra")
        if self.errores_por_alg["DFS"] > self.errores_por_alg["BFS"]:
            return ("laberinto_dfs", "DFS")
        if self.errores_por_alg["BFS"] > 0:
            return ("anillos_bfs", "BFS")
        return ("red_ospf", "Dijkstra")

    def to_dict(self) -> dict:
        return {
            "aciertos": self.aciertos,
            "errores": self.errores,
            "racha": self.racha,
            "nivel": self.nivel,
            "precision": self.precision(),
            "errores_por_alg": dict(self.errores_por_alg),
            "trampa_dijkstra": self.trampa_dijkstra,
            "mensaje": self.ultimo_mensaje,
            "tipo": self.ultimo_tipo,
        }


class SimuladorPasoAPaso:
    """Máquina de estados determinista para BFS, DFS y Dijkstra con soporte de empates."""

    def __init__(self, grafo: dict, inicio: str, destino: str, algoritmo: str):
        self.grafo = grafo
        self.inicio = inicio
        self.destino = destino
        self.algoritmo = algoritmo

        self.activo = True
        self.terminado = False
        self.sin_ruta = False
        self.paso = 0

        self.actual = None
        self.procesados = set()
        self.padres = {inicio: None}
        self.ruta = []
        self.costo_total = 0
        self.unidad = "saltos"

        # Estructuras internas reales
        self.cola = deque()
        self.descubiertos_bfs = set()
        self.pila = []
        self.heap = []
        self.distancias = {}

        self._iniciar()

    def _iniciar(self):
        if self.algoritmo == "BFS":
            self.cola = deque([self.inicio])
            self.descubiertos_bfs = {self.inicio}
            self.unidad = "saltos"
        elif self.algoritmo == "DFS":
            self.pila = [(self.inicio, None)]
            self.unidad = "saltos (no garantiza óptimo)"
        else:
            self.heap = [(0, self.inicio)]
            self.distancias = {self.inicio: 0}
            self.unidad = "unidades de costo"

        # Expandimos automáticamente el nodo inicial para mostrar la primera frontera real
        self.avanzar()

    def _reconstruir_ruta(self) -> list:
        ruta = []
        curr = self.destino
        while curr is not None:
            ruta.append(curr)
            curr = self.padres.get(curr)
        return list(reversed(ruta))

    def _pila_limpia(self) -> list:
        """Devuelve la pila activa (base -> tope) sin nodos procesados ni copias obsoletas."""
        vistos = set()
        activa_rev = []
        for nodo, _ in reversed(self.pila):
            if nodo not in self.procesados and nodo not in vistos:
                vistos.add(nodo)
                activa_rev.append(nodo)
        return list(reversed(activa_rev))

    def _limpiar_tope_pila(self):
        while self.pila and self.pila[-1][0] in self.procesados:
            self.pila.pop()

    def _limpiar_heap(self):
        while self.heap and (
            self.heap[0][1] in self.procesados
            or self.heap[0][0] > self.distancias.get(self.heap[0][1], float("inf"))
        ):
            heapq.heappop(self.heap)

    def _estado_heap_limpio(self) -> list:
        mejores = {}
        for c, n in self.heap:
            if n not in self.procesados and c == self.distancias.get(n):
                mejores[n] = c
        return sorted([(c, n) for n, c in mejores.items()])

    def obtener_siguientes_validos(self) -> tuple[list, int | None]:
        if self.terminado:
            return ([], None)
        if self.algoritmo == "BFS":
            return ([self.cola[0]] if self.cola else [], None)
        if self.algoritmo == "DFS":
            self._limpiar_tope_pila()
            return ([self.pila[-1][0]] if self.pila else [], None)
        self._limpiar_heap()
        limpio = self._estado_heap_limpio()
        if not limpio:
            return ([], None)
        min_c = limpio[0][0]
        return ([n for c, n in limpio if c == min_c], min_c)

    def avanzar(self, nodo_preferido: str | None = None):
        if self.terminado:
            return

        if self.algoritmo == "BFS":
            if not self.cola:
                self.terminado = True
                self.sin_ruta = True
                return
            actual = self.cola.popleft()
            self.actual = actual
            self.procesados.add(actual)
            self.paso += 1

            if actual == self.destino:
                self.terminado = True
                self.ruta = self._reconstruir_ruta()
                self.costo_total = len(self.ruta) - 1
                return

            for vecino in sorted(self.grafo[actual].keys()):
                if vecino not in self.descubiertos_bfs:
                    self.descubiertos_bfs.add(vecino)
                    self.padres[vecino] = actual
                    self.cola.append(vecino)

            if not self.cola:
                self.terminado = True
                self.sin_ruta = True

        elif self.algoritmo == "DFS":
            self._limpiar_tope_pila()
            if not self.pila:
                self.terminado = True
                self.sin_ruta = True
                return
            actual, padre = self.pila.pop()
            self.actual = actual
            self.procesados.add(actual)
            self.padres[actual] = padre
            self.paso += 1

            if actual == self.destino:
                self.terminado = True
                self.ruta = self._reconstruir_ruta()
                self.costo_total = len(self.ruta) - 1
                return

            for vecino in sorted(self.grafo[actual].keys(), reverse=True):
                if vecino not in self.procesados:
                    self.pila.append((vecino, actual))

            self._limpiar_tope_pila()
            if not self.pila:
                self.terminado = True
                self.sin_ruta = True

        else:  # Dijkstra
            self._limpiar_heap()
            if not self.heap:
                self.terminado = True
                self.sin_ruta = True
                return

            validos, min_c = self.obtener_siguientes_validos()
            if nodo_preferido and nodo_preferido in validos:
                # Respeta la elección válida del estudiante en caso de empate
                for i, (c, n) in enumerate(self.heap):
                    if c == min_c and n == nodo_preferido:
                        self.heap.pop(i)
                        heapq.heapify(self.heap)
                        costo_actual, actual = c, n
                        break
            else:
                costo_actual, actual = heapq.heappop(self.heap)

            self.actual = actual
            self.procesados.add(actual)
            self.paso += 1

            if actual == self.destino:
                self.terminado = True
                self.ruta = self._reconstruir_ruta()
                self.costo_total = costo_actual
                return

            for vecino, peso in self.grafo[actual].items():
                if vecino in self.procesados:
                    continue
                nuevo_costo = costo_actual + peso
                if nuevo_costo < self.distancias.get(vecino, float("inf")):
                    self.distancias[vecino] = nuevo_costo
                    self.padres[vecino] = actual
                    heapq.heappush(self.heap, (nuevo_costo, vecino))

            self._limpiar_heap()
            if not self.heap:
                self.terminado = True
                self.sin_ruta = True

    def to_dict(self) -> dict:
        validos, min_c = self.obtener_siguientes_validos()
        if self.algoritmo == "BFS":
            est_nombre = "Cola (FIFO: sale izq. <- entra der.)"
            est_datos = list(self.cola)
            frontera = sorted(set(self.cola))
        elif self.algoritmo == "DFS":
            est_nombre = "Pila (LIFO: base -> tope der.)"
            est_datos = self._pila_limpia()
            frontera = sorted(set(est_datos))
        else:
            est_nombre = "Min-Heap (menor costo sale primero)"
            limpio = self._estado_heap_limpio()
            est_datos = [f"{n}({c})" for c, n in limpio]
            frontera = sorted([n for _, n in limpio])

        costo_real_ruta = 0
        if len(self.ruta) > 1:
            costo_real_ruta = sum(
                self.grafo[self.ruta[i]][self.ruta[i + 1]] for i in range(len(self.ruta) - 1)
            )

        return {
            "activo": self.activo,
            "terminado": self.terminado,
            "sin_ruta": self.sin_ruta,
            "paso": self.paso,
            "actual": self.actual,
            "procesados": sorted(self.procesados),
            "frontera": frontera,
            "estructura_nombre": est_nombre,
            "estructura_estado": est_datos,
            "costos": dict(self.distancias),
            "siguientes_validos": validos,
            "min_costo": min_c,
            "ruta": self.ruta,
            "costo_total": self.costo_total,
            "costo_real_ruta": costo_real_ruta,
            "unidad": self.unidad,
        }


class MotorGrafos:
    """Controlador principal del grafo, presets, comparador y tutor."""

    def __init__(self):
        self.grafo: dict[str, dict[str, int]] = {}
        self.posiciones: dict[str, list[float]] = {}  # Coordenadas normalizadas 0..1
        self.inicio: str | None = None
        self.destino: str | None = None
        self.algoritmo: str = "Dijkstra"
        self.modo_oraculo: bool = False
        self.titulo_escenario: str = "Terreno Base"
        self.sim: SimuladorPasoAPaso | None = None
        self.tutor = TutorAdaptativo()
        self.cargar_preset("base")

    def _siguiente_etiqueta(self) -> str:
        for letra in string.ascii_uppercase:
            if letra not in self.grafo:
                return letra
        i = 1
        while True:
            for letra in string.ascii_uppercase:
                cand = f"{letra}{i}"
                if cand not in self.grafo:
                    return cand
            i += 1

    def reiniciar_sim(self):
        self.sim = None

    # ---------- CRUD seguro del grafo ----------

    def agregar_nodo(self, nx: float, ny: float):
        self.reiniciar_sim()
        etiqueta = self._siguiente_etiqueta()
        self.posiciones[etiqueta] = [round(float(nx), 4), round(float(ny), 4)]
        self.grafo[etiqueta] = {}
        if self.inicio is None:
            self.inicio = etiqueta
        elif self.destino is None and etiqueta != self.inicio:
            self.destino = etiqueta
        self.titulo_escenario = "Grafo Personalizado"

    def mover_nodo(self, nombre: str, nx: float, ny: float):
        if nombre in self.posiciones:
            self.posiciones[nombre] = [round(float(nx), 4), round(float(ny), 4)]

    def eliminar_nodo(self, nombre: str):
        if nombre not in self.grafo:
            return
        self.reiniciar_sim()
        # Limpieza en cascada para evitar aristas fantasma
        for vecino in list(self.grafo[nombre].keys()):
            self.grafo[vecino].pop(nombre, None)
        del self.grafo[nombre]
        del self.posiciones[nombre]
        if self.inicio == nombre:
            self.inicio = None
        if self.destino == nombre:
            self.destino = None
        self.titulo_escenario = "Grafo Personalizado"

    def agregar_arista(self, u: str, v: str, peso: int):
        if u not in self.grafo or v not in self.grafo or u == v:
            return
        peso_int = max(1, min(999, int(peso)))
        self.reiniciar_sim()
        self.grafo[u][v] = peso_int
        self.grafo[v][u] = peso_int
        self.titulo_escenario = "Grafo Personalizado"

    def eliminar_arista(self, u: str, v: str):
        if u not in self.grafo or v not in self.grafo:
            return
        self.reiniciar_sim()
        self.grafo[u].pop(v, None)
        self.grafo[v].pop(u, None)
        self.titulo_escenario = "Grafo Personalizado"

    def fijar_inicio(self, nombre: str):
        if nombre in self.grafo:
            self.reiniciar_sim()
            self.inicio = nombre
            if self.destino == nombre:
                self.destino = None

    def fijar_destino(self, nombre: str):
        if nombre in self.grafo:
            self.reiniciar_sim()
            self.destino = nombre
            if self.inicio == nombre:
                self.inicio = None

    def limpiar_todo(self):
        self.reiniciar_sim()
        self.grafo.clear()
        self.posiciones.clear()
        self.inicio = None
        self.destino = None
        self.titulo_escenario = "Lienzo Vacío"

    # ---------- Control de simulación y Modo Oráculo ----------

    def configurar(self, algoritmo: str, modo_oraculo: bool):
        if algoritmo in ("BFS", "DFS", "Dijkstra"):
            self.algoritmo = algoritmo
        self.modo_oraculo = bool(modo_oraculo)
        self.reiniciar_sim()
        if self.modo_oraculo:
            self.tutor.ultimo_mensaje = (
                f"Modo Oráculo en {self.algoritmo}: pulsa 'Iniciar Reto' y toca en el mapa el siguiente nodo."
            )
            self.tutor.ultimo_tipo = "info"

    def iniciar_o_avanzar(self) -> dict:
        if not self.inicio or not self.destino:
            self.tutor.ultimo_mensaje = "Define primero un nodo de INICIO y uno de META."
            self.tutor.ultimo_tipo = "error"
            return self.estado()

        if self.sim is None:
            self.sim = SimuladorPasoAPaso(self.grafo, self.inicio, self.destino, self.algoritmo)
            if self.modo_oraculo and not self.sim.terminado:
                self.tutor.ultimo_mensaje = (
                    f"Inicio '{self.inicio}' expandido. Toca en el mapa qué nodo de la frontera azul "
                    f"extraerá {self.algoritmo} ahora."
                )
                self.tutor.ultimo_tipo = "info"
        else:
            if not self.modo_oraculo:
                self.sim.avanzar()
        return self.estado()

    def intentar_oraculo(self, nodo: str) -> dict:
        if not self.modo_oraculo:
            return self.estado()
        if self.sim is None:
            self.iniciar_o_avanzar()
            return self.estado()
        if self.sim.terminado:
            return self.estado()

        sim_info = self.sim.to_dict()
        if nodo in sim_info["procesados"]:
            self.tutor.ultimo_mensaje = f"'{nodo}' ya está cerrado/visitado. Toca un nodo azul de la frontera."
            self.tutor.ultimo_tipo = "info"
            return self.estado()

        if nodo not in sim_info["frontera"]:
            self.tutor.ultimo_mensaje = f"'{nodo}' aún no ha sido descubierto. Solo puedes elegir nodos de la frontera azul."
            self.tutor.ultimo_tipo = "info"
            return self.estado()

        validos = sim_info["siguientes_validos"]
        if nodo in validos:
            self.tutor.registrar_acierto(self.algoritmo, nodo)
            self.sim.avanzar(nodo_preferido=nodo)
            if self.sim.terminado and not self.sim.sin_ruta:
                self.tutor.ultimo_mensaje += f" ¡Meta alcanzada: {' -> '.join(self.sim.ruta)}!"
        else:
            self.tutor.registrar_error(
                self.algoritmo, nodo, validos, sim_info["costos"], sim_info["min_costo"]
            )
        return self.estado()

    # ---------- Comparador simultáneo ----------

    def comparar_todos(self) -> dict:
        if not self.inicio or not self.destino:
            return {"error": "Define un nodo de INICIO y uno de META para comparar los 3 algoritmos."}

        resultados = []
        for alg in ("BFS", "DFS", "Dijkstra"):
            sim = SimuladorPasoAPaso(self.grafo, self.inicio, self.destino, alg)
            while not sim.terminado:
                sim.avanzar()
            info = sim.to_dict()
            resultados.append({
                "algoritmo": alg,
                "encontro": not info["sin_ruta"],
                "ruta": info["ruta"],
                "saltos": max(0, len(info["ruta"]) - 1),
                "costo_real": info["costo_real_ruta"],
                "explorados": len(info["procesados"]),
            })

        # Diagnóstico automático del comparador
        bfs_r, dfs_r, dij_r = resultados[0], resultados[1], resultados[2]
        if not dij_r["encontro"]:
            veredicto = "Grafo desconectado: ninguno de los 3 algoritmos pudo llegar a la meta."
        elif bfs_r["costo_real"] > dij_r["costo_real"]:
            ahorro = bfs_r["costo_real"] - dij_r["costo_real"]
            veredicto = (
                f"Aquí se ve la clave: BFS encontró ruta en {bfs_r['saltos']} saltos pero pagó costo {bfs_r['costo_real']}. "
                f"Dijkstra ahorró {ahorro} unidades de costo (total {dij_r['costo_real']})."
            )
        else:
            veredicto = (
                f"En este grafo BFS y Dijkstra empataron en costo ({dij_r['costo_real']}), "
                f"mientras DFS exploró {dfs_r['explorados']} nodos con costo {dfs_r['costo_real']}."
            )

        return {"resultados": resultados, "veredicto": veredicto}

    # ---------- Presets y Reto Adaptativo ----------

    def cargar_preset(self, nombre: str):
        self.reiniciar_sim()

        if nombre == "adaptativo":
            preset_real, alg_rec = self.tutor.recomendar_preset()
            self.algoritmo = alg_rec
            self.modo_oraculo = True
            self.cargar_preset(preset_real)
            self.tutor.ultimo_mensaje = (
                f"Reto Adaptativo generado para {alg_rec} ({self.titulo_escenario}). "
                "Pulsa 'Iniciar Reto' y resuélvelo tocando los nodos."
            )
            self.tutor.ultimo_tipo = "info"
            return

        if nombre == "base":
            self.titulo_escenario = "Terreno Base"
            self.posiciones = {
                "A": [0.12, 0.50], "B": [0.35, 0.22], "C": [0.35, 0.78],
                "D": [0.64, 0.25], "E": [0.64, 0.75], "F": [0.88, 0.50],
            }
            self.grafo = {
                "A": {"B": 4, "C": 2},
                "B": {"A": 4, "C": 1, "D": 5},
                "C": {"A": 2, "B": 1, "E": 7},
                "D": {"B": 5, "F": 3},
                "E": {"C": 7, "F": 1},
                "F": {"D": 3, "E": 1},
            }
            self.inicio, self.destino = "A", "F"

        elif nombre == "trampa_dijkstra":
            self.titulo_escenario = "Grafo Trampa (Menos saltos != Menor costo)"
            self.posiciones = {
                "A": [0.12, 0.65], "B": [0.28, 0.24], "C": [0.50, 0.18],
                "D": [0.72, 0.24], "E": [0.88, 0.65],
            }
            self.grafo = {
                "A": {"B": 2, "E": 25},
                "B": {"A": 2, "C": 3},
                "C": {"B": 3, "D": 2},
                "D": {"C": 2, "E": 4},
                "E": {"A": 25, "D": 4},
            }
            self.inicio, self.destino = "A", "E"

        elif nombre == "red_ospf":
            self.titulo_escenario = "Red OSPF (Latencia en ms)"
            self.posiciones = {
                "A": [0.10, 0.50], "B": [0.32, 0.20], "C": [0.32, 0.80],
                "D": [0.54, 0.50], "E": [0.72, 0.20], "F": [0.72, 0.80], "G": [0.90, 0.50],
            }
            self.grafo = {
                "A": {"B": 8, "C": 2, "D": 15},
                "B": {"A": 8, "D": 3, "E": 4},
                "C": {"A": 2, "D": 4, "F": 9},
                "D": {"A": 15, "B": 3, "C": 4, "E": 6, "F": 2},
                "E": {"B": 4, "D": 6, "G": 3},
                "F": {"C": 9, "D": 2, "G": 5},
                "G": {"E": 3, "F": 5},
            }
            self.inicio, self.destino = "A", "G"

        elif nombre == "laberinto_dfs":
            self.titulo_escenario = "Ramas y Retroceso (Backtracking DFS)"
            self.posiciones = {
                "A": [0.14, 0.50], "B": [0.36, 0.22], "C": [0.36, 0.78],
                "D": [0.62, 0.16], "E": [0.62, 0.42], "F": [0.64, 0.78], "G": [0.88, 0.78],
            }
            self.grafo = {
                "A": {"B": 2, "C": 3},
                "B": {"A": 2, "D": 2, "E": 2},
                "C": {"A": 3, "F": 3},
                "D": {"B": 2},
                "E": {"B": 2},
                "F": {"C": 3, "G": 2},
                "G": {"F": 2},
            }
            self.inicio, self.destino = "A", "G"

        elif nombre == "anillos_bfs":
            self.titulo_escenario = "Niveles Concéntricos (BFS)"
            self.posiciones = {
                "A": [0.14, 0.50], "B": [0.38, 0.22], "C": [0.38, 0.50],
                "D": [0.38, 0.78], "E": [0.66, 0.30], "F": [0.66, 0.70], "G": [0.88, 0.50],
            }
            self.grafo = {
                "A": {"B": 5, "C": 5, "D": 5},
                "B": {"A": 5, "E": 4},
                "C": {"A": 5, "E": 4, "F": 4},
                "D": {"A": 5, "F": 4},
                "E": {"B": 4, "C": 4, "G": 3},
                "F": {"C": 4, "D": 4, "G": 3},
                "G": {"E": 3, "F": 3},
            }
            self.inicio, self.destino = "A", "G"

    def estado(self) -> dict:
        return {
            "grafo": self.grafo,
            "posiciones": self.posiciones,
            "inicio": self.inicio,
            "destino": self.destino,
            "algoritmo": self.algoritmo,
            "modo_oraculo": self.modo_oraculo,
            "titulo_escenario": self.titulo_escenario,
            "sim": self.sim.to_dict() if self.sim else None,
            "tutor": self.tutor.to_dict(),
        }


# =========================================================
# PUENTE JSON PARA PYODIDE (CERO FUGAS DE MEMORIA)
# =========================================================

_motor = MotorGrafos()

def api_estado(): return json.dumps(_motor.estado())
def api_agregar_nodo(nx, ny): _motor.agregar_nodo(nx, ny); return json.dumps(_motor.estado())
def api_mover_nodo(nombre, nx, ny): _motor.mover_nodo(nombre, nx, ny); return json.dumps(_motor.estado())
def api_eliminar_nodo(nombre): _motor.eliminar_nodo(nombre); return json.dumps(_motor.estado())
def api_agregar_arista(u, v, peso): _motor.agregar_arista(u, v, peso); return json.dumps(_motor.estado())
def api_eliminar_arista(u, v): _motor.eliminar_arista(u, v); return json.dumps(_motor.estado())
def api_fijar_inicio(nombre): _motor.fijar_inicio(nombre); return json.dumps(_motor.estado())
def api_fijar_destino(nombre): _motor.fijar_destino(nombre); return json.dumps(_motor.estado())
def api_limpiar_todo(): _motor.limpiar_todo(); return json.dumps(_motor.estado())
def api_configurar(alg, oraculo): _motor.configurar(alg, oraculo); return json.dumps(_motor.estado())
def api_avanzar(): return json.dumps(_motor.iniciar_o_avanzar())
def api_intentar_oraculo(nodo): return json.dumps(_motor.intentar_oraculo(nodo))
def api_reiniciar_sim(): _motor.reiniciar_sim(); return json.dumps(_motor.estado())
def api_cargar_preset(nombre): _motor.cargar_preset(nombre); return json.dumps(_motor.estado())
def api_comparar(): return json.dumps(_motor.comparar_todos())
