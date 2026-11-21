import heapq
import json
import string
from collections import deque


# =========================================================
# 1. TUTOR ADAPTATIVO PARA GRAFOS
# =========================================================

class TutorAdaptativo:
    """Perfila errores conceptuales del estudiante y adapta retos según el algoritmo."""

    def __init__(self):
        self.aciertos = 0
        self.errores = 0
        self.racha = 0
        self.nivel = 1
        self.errores_por_alg = {"BFS": 0, "DFS": 0, "Dijkstra": 0}
        self.trampa_dijkstra = False
        self.ultimo_mensaje = "Pulsa 'Paso >' para que te explique paso a paso, o cambia a 'Modo Oráculo' para ponerte a prueba."
        self.ultimo_tipo = "info"

    def registrar_acierto(self, algoritmo: str, nodo: str):
        self.aciertos += 1
        self.racha += 1
        if self.racha >= 3:
            self.trampa_dijkstra = False
            if self.nivel < 3:
                self.nivel += 1
            self.ultimo_mensaje = (
                f"Excelente: '{nodo}' era correcto. Racha de {self.racha} aciertos — "
                f"buen dominio en {algoritmo} (Nivel {self.nivel})."
            )
        else:
            self.ultimo_mensaje = f"Correcto: {algoritmo} elige '{nodo}'. Racha actual: {self.racha}."
        self.ultimo_tipo = "ok"

    def registrar_error(self, algoritmo: str, elegido: str, validos: list, costos: dict, desempate: str, min_costo=None):
        self.errores += 1
        self.racha = 0
        self.errores_por_alg[algoritmo] += 1
        self.ultimo_tipo = "error"

        if algoritmo == "Dijkstra":
            self.trampa_dijkstra = True
            c_elegido = costos.get(elegido, "∞")
            self.ultimo_mensaje = (
                f"Fallo en Dijkstra: elegiste '{elegido}' (d={c_elegido}), pero el menor costo acumulado "
                f"disponible es {min_costo} en {validos}. Tutor: preparé el 'Reto Adaptativo' (Grafo Trampa)."
            )
        elif algoritmo == "BFS":
            if desempate == "libre":
                self.ultimo_mensaje = (
                    f"Fallo en BFS (Libre): elegiste '{elegido}', pero aún faltan nodos del frente anterior "
                    f"en la Cola FIFO: {validos}. Vacía primero ese nivel."
                )
            else:
                self.ultimo_mensaje = (
                    f"Fallo en BFS (A→Z): elegiste '{elegido}', pero por orden alfabético salía {validos}."
                )
        else:
            if desempate == "libre":
                self.ultimo_mensaje = (
                    f"Fallo en DFS (Libre): elegiste '{elegido}', pero primero debes profundizar por los "
                    f"vecinos del tope de la Pila LIFO: {validos} antes de retroceder."
                )
            else:
                self.ultimo_mensaje = (
                    f"Fallo en DFS (A→Z): elegiste '{elegido}', pero en el tope de la Pila (A→Z) salía {validos}."
                )

    def precision(self) -> int:
        total = self.aciertos + self.errores
        return round((self.aciertos / total) * 100) if total > 0 else 100

    def recomendar_preset(self) -> tuple[str, str, bool]:
        if self.trampa_dijkstra or self.errores_por_alg["Dijkstra"] > 0:
            return ("trampa_dijkstra", "Dijkstra", True)
        if self.errores_por_alg["DFS"] > self.errores_por_alg["BFS"]:
            return ("laberinto_dfs", "DFS", False)
        if self.errores_por_alg["BFS"] > 0:
            return ("anillos_bfs", "BFS", False)
        return ("red_ospf", "Dijkstra", True)

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


# =========================================================
# 2. SIMULADOR PASO A PASO CON GUÍA DIDÁCTICA (BFS/DFS/DIJKSTRA)
# =========================================================

class SimuladorPasoAPaso:
    def __init__(self, grafo: dict, inicio: str, destino: str | None, algoritmo: str, usar_meta: bool, desempate: str):
        self.grafo = grafo
        self.inicio = inicio
        self.destino = destino if usar_meta else None
        self.algoritmo = algoritmo
        self.usar_meta = usar_meta
        self.desempate = desempate

        self.activo = True
        self.terminado = False
        self.sin_ruta = False
        self.paso = 0

        self.actual = None
        self.procesados = set()
        self.orden_visita = []
        self.padres = {inicio: None}
        self.ruta = []
        self.costo_total = 0
        self.unidad = "saltos"

        self.cola_grupos = deque()
        self.descubiertos_bfs = set()
        self.niveles_bfs = {}
        self.pila_grupos = []
        self.heap = []
        self.distancias = {}

        self.guia = {
            "titulo": "Preparando recorrido...",
            "que_paso": "",
            "como_seguir": "",
        }
        self._iniciar()

    def _iniciar(self):
        if self.algoritmo == "BFS":
            self.cola_grupos = deque([[self.inicio]])
            self.descubiertos_bfs = {self.inicio}
            self.niveles_bfs = {self.inicio: 0}
            self.unidad = "saltos"
        elif self.algoritmo == "DFS":
            self.pila_grupos = [[(self.inicio, None)]]
            self.unidad = "saltos (no garantiza óptimo)"
        else:
            self.heap = [(0, self.inicio)]
            self.distancias = {self.inicio: 0}
            self.unidad = "unidades de costo"

        self.avanzar()

    def _reconstruir_ruta(self) -> list:
        if not self.destino:
            return []
        ruta = []
        curr = self.destino
        while curr is not None:
            ruta.append(curr)
            curr = self.padres.get(curr)
        return list(reversed(ruta))

    def _limpiar_cola(self):
        while self.cola_grupos and not self.cola_grupos[0]:
            self.cola_grupos.popleft()

    def _limpiar_pila(self):
        while self.pila_grupos:
            self.pila_grupos[-1] = [(n, p) for n, p in self.pila_grupos[-1] if n not in self.procesados]
            if not self.pila_grupos[-1]:
                self.pila_grupos.pop()
            else:
                break

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

    def _pila_plana(self) -> list:
        vistos = set()
        desde_tope = []
        for grupo in reversed(self.pila_grupos):
            for nodo, _ in grupo:
                if nodo not in self.procesados and nodo not in vistos:
                    vistos.add(nodo)
                    desde_tope.append(nodo)
        return list(reversed(desde_tope))

    def _cola_plana(self) -> list:
        return [n for grupo in self.cola_grupos for n in grupo]

    def obtener_siguientes_validos(self) -> tuple[list, int | None]:
        if self.terminado:
            return ([], None)
        if self.algoritmo == "BFS":
            self._limpiar_cola()
            if not self.cola_grupos:
                return ([], None)
            frente = self.cola_grupos[0]
            return (list(frente), None) if self.desempate == "libre" else ([frente[0]], None)
        if self.algoritmo == "DFS":
            self._limpiar_pila()
            if not self.pila_grupos:
                return ([], None)
            tope = self.pila_grupos[-1]
            return ([n for n, _ in tope], None) if self.desempate == "libre" else ([tope[0][0]], None)
        self._limpiar_heap()
        limpio = self._estado_heap_limpio()
        if not limpio:
            return ([], None)
        min_c = limpio[0][0]
        return ([n for c, n in limpio if c == min_c], min_c)

    def _actualizar_guia_siguiente(self, titulo: str, que_paso: str):
        if self.terminado:
            if self.sin_ruta:
                como = f"La estructura quedó vacía sin llegar a '{self.destino}'. Conecta una unión en el editor y vuelve a probar."
            elif self.usar_meta:
                como = f"¡Listo! Siguiendo los padres desde '{self.destino}' hacia atrás reconstruimos la ruta: {' → '.join(self.ruta)}."
            else:
                como = f"¡Recorrido terminado! Visitamos los {len(self.orden_visita)} nodos alcanzables en el orden: {' → '.join(self.orden_visita)}."
            self.guia = {"titulo": titulo, "que_paso": que_paso, "como_seguir": como}
            return

        validos, min_c = self.obtener_siguientes_validos()
        if self.algoritmo == "BFS":
            if self.desempate == "libre":
                como = (
                    f"Mira el frente (izquierda) de la Cola FIFO: aún tienes {validos} en este lote. "
                    "Debes sacar cualquiera de ellos ANTES de pasar a los nodos descubiertos después."
                )
            else:
                como = (
                    f"Regla FIFO (primero en entrar, primero en salir): el nodo más a la izquierda de la Cola "
                    f"es '{validos[0]}'. Ese será el siguiente en salir."
                )
        elif self.algoritmo == "DFS":
            if self.desempate == "libre":
                como = (
                    f"Mira el tope (derecha) de la Pila LIFO: los vecinos más profundos pendientes son {validos}. "
                    "Elige cualquiera de ese bloque para seguir bajando antes de retroceder."
                )
            else:
                como = (
                    f"Regla LIFO (último en entrar, primero en salir): toma el elemento en el tope derecho "
                    f"de la Pila, que es '{validos[0]}'."
                )
        else:
            if len(validos) == 1:
                como = (
                    f"Compara los costos acumulados d(x) en el Min-Heap: el más pequeño es '{validos[0]}' con d={min_c}. "
                    "En Dijkstra siempre fijamos el nodo de menor costo acumulado."
                )
            else:
                como = (
                    f"Hay un empate en el menor costo acumulado (d={min_c}) entre {validos}. "
                    "Matemáticamente puedes elegir cualquiera de ellos en el siguiente paso."
                )
        self.guia = {"titulo": titulo, "que_paso": que_paso, "como_seguir": como}

    def avanzar(self, nodo_preferido: str | None = None):
        if self.terminado:
            return

        if self.algoritmo == "BFS":
            self._limpiar_cola()
            if not self.cola_grupos:
                self.terminado = True
                self.sin_ruta = self.usar_meta
                self._actualizar_guia_siguiente("Cola vacía", "No quedan más nodos por explorar.")
                return

            frente = self.cola_grupos[0]
            validos, _ = self.obtener_siguientes_validos()
            if nodo_preferido and nodo_preferido in validos:
                frente.remove(nodo_preferido)
                actual = nodo_preferido
            else:
                actual = frente.pop(0)
            self._limpiar_cola()

            self.actual = actual
            self.procesados.add(actual)
            self.orden_visita.append(actual)
            self.paso += 1
            nivel_act = self.niveles_bfs[actual]

            if self.usar_meta and actual == self.destino:
                self.terminado = True
                self.ruta = self._reconstruir_ruta()
                self.costo_total = len(self.ruta) - 1
                self._actualizar_guia_siguiente(
                    f"Paso {self.paso}: Meta '{actual}' alcanzada",
                    f"Sacamos '{actual}' (Nivel L{nivel_act}) de la Cola FIFO y coincide con la meta. Al explorar por capas, BFS garantiza el mínimo número de saltos ({self.costo_total}).",
                )
                return

            nuevos = [v for v in sorted(self.grafo[actual].keys()) if v not in self.descubiertos_bfs]
            for v in nuevos:
                self.descubiertos_bfs.add(v)
                self.padres[v] = actual
                self.niveles_bfs[v] = nivel_act + 1
            if nuevos:
                self.cola_grupos.append(nuevos)

            if self.paso == 1:
                desc = f"Arrancamos en '{actual}' (Nivel L0). "
            else:
                desc = f"Sacamos '{actual}' (Nivel L{nivel_act}) del frente de la Cola FIFO. "

            if nuevos:
                desc += f"Descubrimos sus vecinos nuevos {nuevos}, los marcamos en Nivel L{nivel_act + 1} y los metemos al FINAL de la Cola."
            else:
                desc += "Todos sus vecinos ya habían sido descubiertos antes, así que no se agrega nada nuevo a la Cola."

            self._limpiar_cola()
            if not self.cola_grupos:
                self.terminado = True
                self.sin_ruta = self.usar_meta
            self._actualizar_guia_siguiente(f"Paso {self.paso}: Visitando '{actual}' (L{nivel_act})", desc)

        elif self.algoritmo == "DFS":
            self._limpiar_pila()
            if not self.pila_grupos:
                self.terminado = True
                self.sin_ruta = self.usar_meta
                self._actualizar_guia_siguiente("Pila vacía", "No quedan más ramas por explorar.")
                return

            tope = self.pila_grupos[-1]
            validos, _ = self.obtener_siguientes_validos()
            if nodo_preferido and nodo_preferido in validos:
                idx = next(i for i, (n, _) in enumerate(tope) if n == nodo_preferido)
                actual, padre = tope.pop(idx)
            else:
                actual, padre = tope.pop(0)

            self.actual = actual
            self.procesados.add(actual)
            self.padres[actual] = padre
            self.orden_visita.append(actual)
            self.paso += 1

            if self.usar_meta and actual == self.destino:
                self.terminado = True
                self.ruta = self._reconstruir_ruta()
                self.costo_total = len(self.ruta) - 1
                self._actualizar_guia_siguiente(
                    f"Paso {self.paso}: Meta '{actual}' encontrada",
                    f"Sacamos '{actual}' del tope de la Pila LIFO y llegamos a la meta ({self.costo_total} saltos). Ojo: DFS encuentra una ruta válida, pero NO garantiza que sea la más corta.",
                )
                return

            nuevos = [(v, actual) for v in sorted(self.grafo[actual].keys()) if v not in self.procesados]
            if nuevos:
                self.pila_grupos.append(nuevos)

            nombres_nuevos = [n for n, _ in nuevos]
            if self.paso == 1:
                desc = f"Arrancamos en '{actual}'. "
            else:
                desc = f"Bajamos a '{actual}' desde '{padre}' (tope de la Pila LIFO). "

            if nombres_nuevos:
                desc += f"Apilamos sus vecinos sin visitar {nombres_nuevos} ENCIMA de la Pila para seguir profundizando por esa rama."
            else:
                desc += (
                    f"Callejón sin salida: '{actual}' no tiene vecinos sin visitar. "
                    "Aquí ocurre el RETROCESO (backtracking): volvemos al último nodo pendiente en la Pila."
                )

            self._limpiar_pila()
            if not self.pila_grupos:
                self.terminado = True
                self.sin_ruta = self.usar_meta
            self._actualizar_guia_siguiente(f"Paso {self.paso}: Profundizando en '{actual}'", desc)

        else:  # Dijkstra
            self._limpiar_heap()
            if not self.heap:
                self.terminado = True
                self.sin_ruta = self.usar_meta
                self._actualizar_guia_siguiente("Min-Heap vacío", "No quedan nodos alcanzables.")
                return

            validos, min_c = self.obtener_siguientes_validos()
            if nodo_preferido and nodo_preferido in validos:
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
            self.orden_visita.append(actual)
            self.paso += 1

            if self.usar_meta and actual == self.destino:
                self.terminado = True
                self.ruta = self._reconstruir_ruta()
                self.costo_total = costo_actual
                self._actualizar_guia_siguiente(
                    f"Paso {self.paso}: Meta '{actual}' asegurada (d={costo_actual})",
                    f"Al extraer '{actual}' del Min-Heap con d={costo_actual}, como todos los pesos son positivos, ninguna otra ruta puede ser más barata. Costo mínimo garantizado: {costo_actual}.",
                )
                return

            cambios = []
            descartados = []
            for vecino, peso in sorted(self.grafo[actual].items()):
                if vecino in self.procesados:
                    continue
                nuevo_costo = costo_actual + peso
                anterior = self.distancias.get(vecino)
                if anterior is None:
                    self.distancias[vecino] = nuevo_costo
                    self.padres[vecino] = actual
                    heapq.heappush(self.heap, (nuevo_costo, vecino))
                    cambios.append(f"{vecino}: {costo_actual}+{peso}={nuevo_costo} (nuevo)")
                elif nuevo_costo < anterior:
                    self.distancias[vecino] = nuevo_costo
                    self.padres[vecino] = actual
                    heapq.heappush(self.heap, (nuevo_costo, vecino))
                    cambios.append(f"{vecino}: {costo_actual}+{peso}={nuevo_costo} (mejora {anterior}→{nuevo_costo})")
                else:
                    descartados.append(f"{vecino}: {costo_actual}+{peso}={nuevo_costo} (no mejora {anterior})")

            desc = f"Fijamos '{actual}' con costo definitivo d={costo_actual}. "
            if cambios:
                desc += "Relajación de vecinos: " + "; ".join(cambios) + ". "
            if descartados:
                desc += "Descartados: " + "; ".join(descartados) + "."
            if not cambios and not descartados:
                desc += "Todos sus vecinos ya tienen su distancia definitiva cerrada."

            self._limpiar_heap()
            if not self.heap:
                self.terminado = True
                self.sin_ruta = self.usar_meta
            self._actualizar_guia_siguiente(f"Paso {self.paso}: Cerrando '{actual}' (d={costo_actual})", desc)

    def to_dict(self) -> dict:
        validos, min_c = self.obtener_siguientes_validos()
        if self.algoritmo == "BFS":
            est_nombre = "Cola (FIFO: sale izq. <- entra der.)"
            est_datos = [{"nodo": n, "texto": f"{n} (L{self.niveles_bfs.get(n, 0)})"} for n in self._cola_plana()]
            frontera = sorted(set(self._cola_plana()))
        elif self.algoritmo == "DFS":
            est_nombre = "Pila (LIFO: base izq. -> tope der.)"
            plana = self._pila_plana()
            est_datos = [{"nodo": n, "texto": n} for n in plana]
            frontera = sorted(set(plana))
        else:
            est_nombre = "Min-Heap (menor costo sale primero)"
            limpio = self._estado_heap_limpio()
            est_datos = [{"nodo": n, "texto": f"{n} (d={c})"} for c, n in limpio]
            frontera = sorted([n for _, n in limpio])

        costo_real_ruta = 0
        if len(self.ruta) > 1:
            costo_real_ruta = sum(self.grafo[self.ruta[i]][self.ruta[i + 1]] for i in range(len(self.ruta) - 1))

        aristas_arbol = [[self.padres[n], n] for n in self.orden_visita if self.padres.get(n) is not None]
        orden_mapa = {n: i + 1 for i, n in enumerate(self.orden_visita)}

        return {
            "activo": self.activo,
            "terminado": self.terminado,
            "sin_ruta": self.sin_ruta,
            "usar_meta": self.usar_meta,
            "paso": self.paso,
            "actual": self.actual,
            "procesados": sorted(self.procesados),
            "orden_visita": list(self.orden_visita),
            "orden_mapa": orden_mapa,
            "niveles_bfs": dict(self.niveles_bfs),
            "aristas_arbol": aristas_arbol,
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
            "guia": dict(self.guia),
        }


# =========================================================
# 3. CONTROLADOR DE GRAFOS
# =========================================================

class MotorGrafos:
    def __init__(self):
        self.grafo: dict[str, dict[str, int]] = {}
        self.posiciones: dict[str, list[float]] = {}
        self.inicio: str | None = None
        self.destino: str | None = None
        self.algoritmo: str = "BFS"
        self.modo_oraculo: bool = False
        self.usar_meta: bool = False
        self.desempate: str = "libre"
        self.titulo_escenario: str = "Grafo Base"
        self.sim: SimuladorPasoAPaso | None = None
        self.tutor = TutorAdaptativo()
        self.cargar_preset("base")

    def _guia_inicial(self) -> dict:
        if self.algoritmo == "BFS":
            return {
                "titulo": "Cómo funciona BFS (Búsqueda en Anchura)",
                "que_paso": "BFS explora el grafo por capas (L0, L1, L2...) usando una Cola FIFO e ignorando los pesos de las líneas.",
                "como_seguir": f"Pulsa 'Paso >' para iniciar en '{self.inicio or 'Inicio'}'. En cada paso verás qué vecinos entran al final de la Cola y cuál sale primero por la izquierda.",
            }
        if self.algoritmo == "DFS":
            return {
                "titulo": "Cómo funciona DFS (Búsqueda en Profundidad)",
                "que_paso": "DFS se mete lo más hondo posible por una rama usando una Pila LIFO. Cuando llega a un callejón sin salida, retrocede (backtracking).",
                "como_seguir": f"Pulsa 'Paso >' para arrancar en '{self.inicio or 'Inicio'}'. Fíjate cómo siempre extraemos el último bloque apilado a la derecha.",
            }
        return {
            "titulo": "Cómo funciona Dijkstra (Costo Mínimo)",
            "que_paso": "Dijkstra SÍ lee los pesos de cada unión. En cada paso elige el nodo no cerrado con menor distancia acumulada d(x) y revisa si pasar por él abarata a sus vecinos (relajación).",
            "como_seguir": f"Pulsa 'Paso >' para partir desde '{self.inicio or 'Inicio'}' con d=0. También puedes tocar cualquier línea del mapa para cambiar su peso en vivo.",
        }

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

    def seleccionar_modulo(self, alg: str):
        """Entrada dedicada desde el menú inicial de 4 opciones."""
        self.reiniciar_sim()
        self.modo_oraculo = False
        if alg == "BFS":
            self.algoritmo = "BFS"
            self.usar_meta = False
            self.cargar_preset("anillos_bfs")
        elif alg == "DFS":
            self.algoritmo = "DFS"
            self.usar_meta = False
            self.cargar_preset("laberinto_dfs")
        else:
            self.algoritmo = "Dijkstra"
            self.usar_meta = True
            self.cargar_preset("trampa_dijkstra")
        self.tutor.ultimo_mensaje = f"Módulo {self.algoritmo} listo. Pulsa 'Paso >' para aprender paso a paso o edita el mapa libremente."
        self.tutor.ultimo_tipo = "info"

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
            self.usar_meta = True
            if self.inicio == nombre:
                self.inicio = None

    def limpiar_todo(self):
        self.reiniciar_sim()
        self.grafo.clear()
        self.posiciones.clear()
        self.inicio = None
        self.destino = None
        self.titulo_escenario = "Lienzo Vacío"

    def configurar(self, algoritmo: str, modo_oraculo: bool, usar_meta: bool, desempate: str):
        if algoritmo in ("BFS", "DFS", "Dijkstra"):
            self.algoritmo = algoritmo
        self.modo_oraculo = bool(modo_oraculo)
        self.usar_meta = bool(usar_meta)
        if desempate in ("alfabetico", "libre"):
            self.desempate = desempate
        self.reiniciar_sim()

        if self.modo_oraculo:
            self.tutor.ultimo_mensaje = f"Modo Oráculo en {self.algoritmo}: pulsa 'Iniciar Reto' y toca en el mapa el siguiente nodo."
            self.tutor.ultimo_tipo = "info"
        else:
            self.tutor.ultimo_mensaje = f"Modo Guiado en {self.algoritmo}: pulsa 'Paso >' para ir viendo la explicación de cada paso."
            self.tutor.ultimo_tipo = "info"

    def iniciar_o_avanzar(self) -> dict:
        if not self.inicio:
            self.tutor.ultimo_mensaje = "Define primero un nodo de INICIO."
            self.tutor.ultimo_tipo = "error"
            return self.estado()
        if self.usar_meta and not self.destino:
            self.tutor.ultimo_mensaje = "Estás en 'Buscar Meta': fija un nodo META o cambia a 'Recorrido Completo'."
            self.tutor.ultimo_tipo = "error"
            return self.estado()

        if self.sim is None:
            self.sim = SimuladorPasoAPaso(
                self.grafo, self.inicio, self.destino, self.algoritmo, self.usar_meta, self.desempate
            )
            if self.modo_oraculo and not self.sim.terminado:
                self.tutor.ultimo_mensaje = (
                    f"Inicio '{self.inicio}' visitado (#1). Toca en el mapa qué nodo azul extraerá {self.algoritmo} ahora."
                )
                self.tutor.ultimo_tipo = "info"
        elif not self.modo_oraculo:
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
            self.tutor.ultimo_mensaje = f"'{nodo}' ya fue visitado. Toca un nodo azul de la frontera."
            self.tutor.ultimo_tipo = "info"
            return self.estado()
        if nodo not in sim_info["frontera"]:
            self.tutor.ultimo_mensaje = f"'{nodo}' aún no ha sido descubierto. Solo puedes elegir nodos azules."
            self.tutor.ultimo_tipo = "info"
            return self.estado()

        validos = sim_info["siguientes_validos"]
        if nodo in validos:
            self.tutor.registrar_acierto(self.algoritmo, nodo)
            self.sim.avanzar(nodo_preferido=nodo)
            if self.sim.terminado and not self.sim.sin_ruta:
                if self.usar_meta:
                    self.tutor.ultimo_mensaje += f" ¡Meta alcanzada: {' → '.join(self.sim.ruta)}!"
                else:
                    self.tutor.ultimo_mensaje += f" ¡Recorrido completo: {' → '.join(self.sim.orden_visita)}!"
        else:
            self.tutor.registrar_error(
                self.algoritmo, nodo, validos, sim_info["costos"], self.desempate, sim_info["min_costo"]
            )
        return self.estado()

    def comparar_todos(self) -> dict:
        if not self.inicio:
            return {"error": "Define al menos un nodo de INICIO para comparar."}
        if self.usar_meta and not self.destino:
            return {"error": "Fija una META o cambia a 'Recorrido Completo' para comparar."}

        resultados = []
        for alg in ("BFS", "DFS", "Dijkstra"):
            sim = SimuladorPasoAPaso(self.grafo, self.inicio, self.destino, alg, self.usar_meta, "alfabetico")
            while not sim.terminado:
                sim.avanzar()
            info = sim.to_dict()
            resultados.append({
                "algoritmo": alg,
                "encontro": not info["sin_ruta"],
                "ruta": info["ruta"],
                "orden_visita": info["orden_visita"],
                "saltos": max(0, len(info["ruta"]) - 1),
                "costo_real": info["costo_real_ruta"],
                "explorados": len(info["orden_visita"]),
            })

        if not self.usar_meta:
            veredicto = (
                "En Recorrido Completo los 3 visitan los mismos nodos alcanzables, pero en orden distinto: "
                "BFS avanza por capas, DFS baja a fondo por una rama y Dijkstra ordena por costo acumulado."
            )
            return {"modo": "recorrido", "resultados": resultados, "veredicto": veredicto}

        bfs_r, dfs_r, dij_r = resultados[0], resultados[1], resultados[2]
        if not dij_r["encontro"]:
            veredicto = "Grafo desconectado: ninguno de los 3 algoritmos pudo llegar a la meta."
        elif bfs_r["costo_real"] > dij_r["costo_real"]:
            ahorro = bfs_r["costo_real"] - dij_r["costo_real"]
            veredicto = (
                f"BFS ignoró los pesos y llegó en {bfs_r['saltos']} saltos con costo real {bfs_r['costo_real']}. "
                f"Dijkstra respetó los pesos y ahorró {ahorro} unidades (total {dij_r['costo_real']})."
            )
        else:
            veredicto = (
                f"BFS y Dijkstra empataron en costo ({dij_r['costo_real']}), "
                f"mientras DFS tomó {' → '.join(dfs_r['ruta'])} (costo {dfs_r['costo_real']})."
            )
        return {"modo": "meta", "resultados": resultados, "veredicto": veredicto}

    def cargar_preset(self, nombre: str):
        self.reiniciar_sim()
        if nombre == "adaptativo":
            preset_real, alg_rec, meta_rec = self.tutor.recomendar_preset()
            self.algoritmo = alg_rec
            self.modo_oraculo = True
            self.usar_meta = meta_rec
            self.cargar_preset(preset_real)
            self.tutor.ultimo_mensaje = (
                f"Reto Adaptativo para {alg_rec} ({self.titulo_escenario}). Pulsa 'Iniciar Reto' y resuélvelo."
            )
            self.tutor.ultimo_tipo = "info"
            return

        if nombre == "base":
            self.titulo_escenario = "Grafo Base"
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
            self.titulo_escenario = "Grafo Trampa (Menos saltos ≠ Menor costo)"
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
            self.algoritmo = "Dijkstra"
            self.usar_meta = True
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
            self.algoritmo = "Dijkstra"
            self.usar_meta = True
        elif nombre == "laberinto_dfs":
            self.titulo_escenario = "Árbol de Ramas (Backtracking DFS)"
            self.posiciones = {
                "A": [0.14, 0.50], "B": [0.36, 0.22], "C": [0.36, 0.78],
                "D": [0.62, 0.16], "E": [0.62, 0.42], "F": [0.64, 0.78], "G": [0.88, 0.78],
            }
            self.grafo = {
                "A": {"B": 1, "C": 1},
                "B": {"A": 1, "D": 1, "E": 1},
                "C": {"A": 1, "F": 1},
                "D": {"B": 1},
                "E": {"B": 1},
                "F": {"C": 1, "G": 1},
                "G": {"F": 1},
            }
            self.inicio, self.destino = "A", "G"
        elif nombre == "anillos_bfs":
            self.titulo_escenario = "Niveles Concéntricos (BFS)"
            self.posiciones = {
                "A": [0.14, 0.50], "B": [0.38, 0.22], "C": [0.38, 0.50],
                "D": [0.38, 0.78], "E": [0.66, 0.30], "F": [0.66, 0.70], "G": [0.88, 0.50],
            }
            self.grafo = {
                "A": {"B": 1, "C": 1, "D": 1},
                "B": {"A": 1, "E": 1},
                "C": {"A": 1, "E": 1, "F": 1},
                "D": {"A": 1, "F": 1},
                "E": {"B": 1, "C": 1, "G": 1},
                "F": {"C": 1, "D": 1, "G": 1},
                "G": {"E": 1, "F": 1},
            }
            self.inicio, self.destino = "A", "G"

    def estado(self) -> dict:
        sim_dict = self.sim.to_dict() if self.sim else None
        guia = sim_dict["guia"] if sim_dict else self._guia_inicial()
        return {
            "grafo": self.grafo,
            "posiciones": self.posiciones,
            "inicio": self.inicio,
            "destino": self.destino,
            "algoritmo": self.algoritmo,
            "modo_oraculo": self.modo_oraculo,
            "usar_meta": self.usar_meta,
            "desempate": self.desempate,
            "titulo_escenario": self.titulo_escenario,
            "sim": sim_dict,
            "guia": guia,
            "tutor": self.tutor.to_dict(),
        }


# =========================================================
# 4. MOTOR DIDÁCTICO DEL ALGORITMO DE EUCLIDES (MCD + PRÁCTICA)
# =========================================================

def euclides_extendido(a: int, b: int) -> tuple[int, int, int]:
    """Devuelve (mcd, x, y) tales que a*x + b*y = mcd."""
    if b == 0:
        return (a, 1, 0)
    mcd, x1, y1 = euclides_extendido(b, a % b)
    return (mcd, y1, x1 - (a // b) * y1)


class MotorEuclides:
    """Ejecuta y enseña paso a paso el Algoritmo de Euclides en Modo Guiado y Modo Práctica."""

    def __init__(self):
        self.a_orig = 252
        self.b_orig = 105
        self.cur_a = 252
        self.cur_b = 105
        self.modo_practica = False
        self.pasos = []
        self.terminado = False
        self.mcd = None
        self.bezout = None

        self.aciertos = 0
        self.errores = 0
        self.racha = 0
        self.mensaje_tutor = "Listo. Pulsa 'Siguiente Paso >' para aprender cómo dividir y desplazar, o pasa a 'Modo Práctica'."
        self.tipo_tutor = "info"
        self.guia = {}
        self.iniciar(252, 105, False)

    def iniciar(self, a: int, b: int, modo_practica: bool | None = None):
        a = abs(int(a))
        b = abs(int(b))
        if modo_practica is not None:
            self.modo_practica = bool(modo_practica)

        if a == 0 and b == 0:
            self.mensaje_tutor = "MCD(0, 0) no está definido. Ingresa al menos un número mayor que 0."
            self.tipo_tutor = "error"
            return

        self.a_orig = a
        self.b_orig = b
        self.cur_a = a
        self.cur_b = b
        self.pasos = []
        self.terminado = False
        self.mcd = None
        self.bezout = None

        if b == 0:
            self.terminado = True
            self.mcd = a
            g, x, y = euclides_extendido(a, 0)
            self.bezout = {"x": x, "y": y, "texto": f"{a}·({x}) + 0·({y}) = {g}"}
            self.guia = {
                "titulo": f"Caso base directo: MCD({a}, 0) = {a}",
                "que_paso": "Cuando el segundo número ya es 0, el Máximo Común Divisor es directamente el primer número.",
                "como_seguir": "Prueba con dos números positivos (como 252 y 105) para ver el ciclo completo de divisiones.",
            }
            return

        nota_orden = ""
        if a < b:
            nota_orden = (
                f" Fíjate que {a} es menor que {b}: en el paso 1 el cociente será 0 y el residuo será {a}, "
                "lo que automáticamente invertirá los números en el siguiente paso."
            )

        self.guia = {
            "titulo": f"Inicio: calcular MCD({a}, {b})",
            "que_paso": (
                f"Queremos el mayor entero que divide exactamente a {a} y {b} sin factorizar primos. "
                "La regla es: MCD(a, b) = MCD(b, a mod b)." + nota_orden
            ),
            "como_seguir": (
                f"Paso 1: Divide {a} entre {b}. Busca cuántas veces cabe {b} en {a} sin pasarte (cociente q) "
                "y calcula cuánto sobra (residuo r)."
            ),
        }
        self.mensaje_tutor = (
            f"Modo Práctica: divide {a} ÷ {b} y escribe el cociente q y el residuo r."
            if self.modo_practica
            else f"Modo Guiado listo para MCD({a}, {b}). Pulsa 'Siguiente Paso >'."
        )
        self.tipo_tutor = "info"

    def _registrar_paso(self, a: int, b: int, q: int, r: int):
        num = len(self.pasos) + 1
        paso = {
            "num": num,
            "a": a,
            "b": b,
            "q": q,
            "r": r,
            "producto": q * b,
            "ecuacion": f"{a} = {q} × {b} + {r}",
            "es_final": r == 0,
        }
        self.pasos.append(paso)

        explicacion_div = (
            f"Dividimos {a} ÷ {b}: cabe {q} veces porque {q} × {b} = {q * b}. "
            f"Al restar: {a} − {q * b} = {r} (residuo)."
        )

        if r == 0:
            self.terminado = True
            self.mcd = b
            g, x, y = euclides_extendido(self.a_orig, self.b_orig)
            self.bezout = {
                "x": x,
                "y": y,
                "texto": f"{self.a_orig}·({x}) + {self.b_orig}·({y}) = {g}",
            }
            extra_coprimos = " Como el MCD es 1, estos dos números son COPRIMOS (primos relativos)." if b == 1 else ""
            self.guia = {
                "titulo": f"Paso {num}: ¡Residuo 0! MCD = {b}",
                "que_paso": explicacion_div + f" Como el residuo dio 0, el algoritmo se detiene.{extra_coprimos}",
                "como_seguir": (
                    f"El último divisor distinto de cero fue {b}, así que MCD({self.a_orig}, {self.b_orig}) = {b}. "
                    f"Comprobación: {self.a_orig}÷{b}={self.a_orig // b} y {self.b_orig}÷{b}={self.b_orig // b} (ambas exactas)."
                ),
            }
        else:
            self.cur_a = b
            self.cur_b = r
            self.guia = {
                "titulo": f"Paso {num}: Residuo {r} ≠ 0 → Desplazamos",
                "que_paso": (
                    explicacion_div
                    + f" Como r = {r} no es cero, desplazamos los valores: el divisor anterior ({b}) pasa a ser el nuevo 'a', "
                    f"y el residuo ({r}) pasa a ser el nuevo 'b'."
                ),
                "como_seguir": (
                    f"Siguiente división (Paso {num + 1}): divide {self.cur_a} entre {self.cur_b} "
                    "para hallar su cociente y nuevo residuo."
                ),
            }

    def avanzar_guiado(self):
        if self.terminado:
            return
        q = self.cur_a // self.cur_b
        r = self.cur_a % self.cur_b
        self._registrar_paso(self.cur_a, self.cur_b, q, r)
        if self.terminado:
            self.mensaje_tutor = f"¡Terminado en {len(self.pasos)} pasos! MCD({self.a_orig}, {self.b_orig}) = {self.mcd}."
            self.tipo_tutor = "ok"
        else:
            self.mensaje_tutor = f"Desplazamiento listo: ahora calcula {self.cur_a} ÷ {self.cur_b}."
            self.tipo_tutor = "info"

    def verificar_practica(self, q_user: int, r_user: int):
        if self.terminado:
            return
        a, b = self.cur_a, self.cur_b
        q_real = a // b
        r_real = a % b
        q_user = int(q_user)
        r_user = int(r_user)

        if q_user == q_real and r_user == r_real:
            self.aciertos += 1
            self.racha += 1
            self._registrar_paso(a, b, q_real, r_real)
            if self.terminado:
                self.mensaje_tutor = (
                    f"¡Perfecto! Residuo 0: acabas de hallar MCD({self.a_orig}, {self.b_orig}) = {self.mcd} por tu cuenta."
                )
            else:
                self.mensaje_tutor = (
                    f"¡Correcto! {a} = {q_real}×{b} + {r_real}. Ahora desplazamos: divide {self.cur_a} entre {self.cur_b}."
                )
            self.tipo_tutor = "ok"
            return

        self.errores += 1
        self.racha = 0
        self.tipo_tutor = "error"

        if q_user != q_real and r_user != r_real:
            self.mensaje_tutor = (
                f"Revisa la división {a} ÷ {b}: busca cuántas veces cabe {b} en {a} sin pasarte. "
                f"Pista: {b} × {q_real} = {b * q_real}. Luego resta {a} − {b * q_real} para el residuo."
            )
        elif q_user != q_real:
            if q_user * b > a:
                self.mensaje_tutor = f"Te pasaste en el cociente: {q_user} × {b} = {q_user * b}, que es mayor que {a}. Prueba un número menor."
            else:
                self.mensaje_tutor = f"Te faltó en el cociente: con {q_user} sobra {a - q_user * b}, todavía cabe {b} al menos una vez más."
        else:
            self.mensaje_tutor = (
                f"¡El cociente ({q_real}) está perfecto! Solo falló la resta del residuo: "
                f"calcula {a} − ({q_real} × {b}) = {a} − {q_real * b}."
            )

    def dar_pista(self):
        if self.terminado:
            return
        a, b = self.cur_a, self.cur_b
        q_real = a // b
        self.mensaje_tutor = (
            f"Pista para {a} ÷ {b}: multiplica {b} × {q_real} = {b * q_real}. "
            f"¿Cuánto le falta a {b * q_real} para llegar a {a}?"
        )
        self.tipo_tutor = "info"

    def cargar_preset(self, preset: str):
        presets = {
            "clasico": (252, 105),
            "mediano": (1071, 462),
            "fibonacci": (89, 55),
            "coprimos": (35, 16),
            "rapido": (48, 18),
        }
        a, b = presets.get(preset, (252, 105))
        self.iniciar(a, b, self.modo_practica)

    def precision(self) -> int:
        total = self.aciertos + self.errores
        return round((self.aciertos / total) * 100) if total > 0 else 100

    def estado(self) -> dict:
        return {
            "a_orig": self.a_orig,
            "b_orig": self.b_orig,
            "cur_a": self.cur_a,
            "cur_b": self.cur_b,
            "modo_practica": self.modo_practica,
            "pasos": self.pasos,
            "terminado": self.terminado,
            "mcd": self.mcd,
            "bezout": self.bezout,
            "guia": self.guia,
            "tutor": {
                "aciertos": self.aciertos,
                "errores": self.errores,
                "racha": self.racha,
                "precision": self.precision(),
                "mensaje": self.mensaje_tutor,
                "tipo": self.tipo_tutor,
            },
        }


# =========================================================
# 5. PUENTE JSON PARA PYODIDE (GRAFOS + EUCLIDES)
# =========================================================

_motor = MotorGrafos()
_euclides = MotorEuclides()

# API Grafos
def api_estado(): return json.dumps(_motor.estado())
def api_seleccionar_modulo_grafo(alg): _motor.seleccionar_modulo(alg); return json.dumps(_motor.estado())
def api_agregar_nodo(nx, ny): _motor.agregar_nodo(nx, ny); return json.dumps(_motor.estado())
def api_mover_nodo(nombre, nx, ny): _motor.mover_nodo(nombre, nx, ny); return json.dumps(_motor.estado())
def api_eliminar_nodo(nombre): _motor.eliminar_nodo(nombre); return json.dumps(_motor.estado())
def api_agregar_arista(u, v, peso): _motor.agregar_arista(u, v, peso); return json.dumps(_motor.estado())
def api_eliminar_arista(u, v): _motor.eliminar_arista(u, v); return json.dumps(_motor.estado())
def api_fijar_inicio(nombre): _motor.fijar_inicio(nombre); return json.dumps(_motor.estado())
def api_fijar_destino(nombre): _motor.fijar_destino(nombre); return json.dumps(_motor.estado())
def api_limpiar_todo(): _motor.limpiar_todo(); return json.dumps(_motor.estado())
def api_configurar(alg, oraculo, usar_meta, desempate):
    _motor.configurar(alg, oraculo, usar_meta, desempate)
    return json.dumps(_motor.estado())
def api_avanzar(): return json.dumps(_motor.iniciar_o_avanzar())
def api_intentar_oraculo(nodo): return json.dumps(_motor.intentar_oraculo(nodo))
def api_reiniciar_sim(): _motor.reiniciar_sim(); return json.dumps(_motor.estado())
def api_cargar_preset(nombre): _motor.cargar_preset(nombre); return json.dumps(_motor.estado())
def api_comparar(): return json.dumps(_motor.comparar_todos())

# API Euclides
def api_euc_estado(): return json.dumps(_euclides.estado())
def api_euc_iniciar(a, b, practica): _euclides.iniciar(a, b, practica); return json.dumps(_euclides.estado())
def api_euc_avanzar(): _euclides.avanzar_guiado(); return json.dumps(_euclides.estado())
def api_euc_verificar(q, r): _euclides.verificar_practica(q, r); return json.dumps(_euclides.estado())
def api_euc_pista(): _euclides.dar_pista(); return json.dumps(_euclides.estado())
def api_euc_preset(nombre): _euclides.cargar_preset(nombre); return json.dumps(_euclides.estado())
