"""Validador del esquema de trazas (sección 7 del enunciado, ENUNCIADO.md).

Una traza es un archivo JSONL con un evento por línea. `validar_archivo` devuelve la lista de
problemas; vacía quiere decir que la traza es válida. Los eventos y campos que no están en la tabla
se aceptan y se ignoran: se pueden agregar, no sacar.
"""
import datetime as dt
import json
from pathlib import Path

CAMPOS_COMUNES = ("evento", "ts", "corrida", "tarea")


def _entero(valor, minimo=0) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool) and valor >= minimo


def _texto(valor) -> bool:
    return isinstance(valor, str) and valor != ""


def _texto_o_nulo(valor) -> bool:
    return valor is None or isinstance(valor, str)


def _booleano(valor) -> bool:
    return isinstance(valor, bool)


def _objeto(valor) -> bool:
    return isinstance(valor, dict)


def _objeto_o_texto(valor) -> bool:
    return isinstance(valor, (dict, str))


# evento -> {campo propio: (verificación, descripción del tipo esperado)}
EVENTOS = {
    "corrida_inicio": {"modelo": (_texto, "texto"), "config": (_objeto, "objeto")},
    "llamada_modelo": {"paso": (lambda v: _entero(v, 1), "entero desde 1"), "modelo": (_texto, "texto"),
                       "num_ctx": (lambda v: _entero(v, 1), "entero positivo"),
                       "tokens_entrada": (_entero, "entero"), "tokens_salida": (_entero, "entero"),
                       "duracion_ms": (_entero, "entero")},
    "reintento_modelo": {"paso": (lambda v: _entero(v, 1), "entero desde 1"), "motivo": (_texto, "texto"),
                         "intento": (lambda v: _entero(v, 1), "entero desde 1")},
    "llamada_herramienta": {"paso": (lambda v: _entero(v, 1), "entero desde 1"), "id": (_texto, "texto"),
                            "nombre": (_texto, "texto"),
                            "argumentos": (_objeto_o_texto, "objeto, o texto si el JSON vino roto")},
    "resultado_herramienta": {"paso": (lambda v: _entero(v, 1), "entero desde 1"), "id": (_texto, "texto"),
                              "ok": (_booleano, "booleano"), "truncado": (_booleano, "booleano"),
                              "caracteres": (_entero, "entero"), "duracion_ms": (_entero, "entero")},
    "corrida_fin": {"estado": (_texto, "texto"), "respuesta": (_texto_o_nulo, "texto o null"),
                    "pasos": (_entero, "entero")},
}


def _es_iso(valor) -> bool:
    if not isinstance(valor, str):
        return False
    try:
        dt.datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def leer_eventos(ruta: Path) -> tuple[list[tuple[int, dict]], list[str]]:
    """Devuelve los eventos con su número de línea, y los problemas de lectura."""
    eventos, problemas = [], []
    for numero, linea in enumerate(Path(ruta).read_text(encoding="utf-8").splitlines(), start=1):
        if not linea.strip():
            continue
        try:
            evento = json.loads(linea)
        except json.JSONDecodeError as error:
            problemas.append(f"línea {numero}: no es JSON ({error.msg})")
            continue
        if not isinstance(evento, dict):
            problemas.append(f"línea {numero}: el evento no es un objeto")
            continue
        eventos.append((numero, evento))
    return eventos, problemas


def _registra_num_ctx(config: dict) -> bool:
    """`num_ctx` suelto, o dentro de [modelo] como lo deja config.toml."""
    return "num_ctx" in config or (_objeto(config.get("modelo")) and "num_ctx" in config["modelo"])


def _campos(numero: int, evento: dict) -> list[str]:
    problemas = []
    for campo in CAMPOS_COMUNES:
        if campo not in evento:
            problemas.append(f"línea {numero}: falta el campo común «{campo}»")
    if "ts" in evento and not _es_iso(evento["ts"]):
        problemas.append(f"línea {numero}: «ts» no es una fecha ISO 8601")
    for campo, (verificar, esperado) in EVENTOS.get(evento.get("evento"), {}).items():
        if campo not in evento:
            problemas.append(f"línea {numero}: {evento['evento']} sin «{campo}»")
        elif not verificar(evento[campo]):
            problemas.append(f"línea {numero}: {evento['evento']}.{campo} debería ser {esperado}")
    if evento.get("evento") == "corrida_inicio" and _objeto(evento.get("config")) \
            and not _registra_num_ctx(evento["config"]):
        problemas.append(f"línea {numero}: corrida_inicio.config no registra num_ctx")
    return problemas


def _orden_y_pares(eventos: list[tuple[int, dict]]) -> list[str]:
    problemas = []
    ultimo_paso = 0
    llamadas: dict[tuple, tuple[int, dict]] = {}
    resultados: dict[tuple, int] = {}
    for numero, evento in eventos:
        paso = evento.get("paso")
        if _entero(paso, 1):
            if paso < ultimo_paso:
                problemas.append(f"línea {numero}: «paso» baja de {ultimo_paso} a {paso}")
            ultimo_paso = max(ultimo_paso, paso)
        clave = (evento.get("agente"), evento.get("id"))
        if evento.get("evento") == "llamada_herramienta" and _texto(evento.get("id")):
            if clave in llamadas:
                problemas.append(f"línea {numero}: el id «{evento['id']}» se repite en dos llamadas")
            llamadas.setdefault(clave, (numero, evento))
        elif evento.get("evento") == "resultado_herramienta" and _texto(evento.get("id")):
            if clave not in llamadas:
                problemas.append(f"línea {numero}: resultado del id «{evento['id']}» sin llamada previa")
            elif llamadas[clave][1].get("paso") != paso:
                problemas.append(f"línea {numero}: el resultado del id «{evento['id']}» es de otro paso "
                                 f"que su llamada")
            if clave in resultados:
                problemas.append(f"línea {numero}: el id «{evento['id']}» tiene dos resultados")
            resultados.setdefault(clave, numero)
    for clave, (numero, evento) in llamadas.items():
        if clave not in resultados:
            problemas.append(f"línea {numero}: la llamada «{evento['id']}» no tiene resultado")
    return problemas


def validar_eventos(eventos: list[tuple[int, dict]]) -> list[str]:
    if not eventos:
        return ["la traza está vacía"]
    problemas = []
    for numero, evento in eventos:
        problemas += _campos(numero, evento)
    nombres = [evento.get("evento") for _, evento in eventos]
    if nombres[0] != "corrida_inicio":
        problemas.append("el primer evento tiene que ser corrida_inicio")
    if nombres[-1] != "corrida_fin":
        problemas.append("el último evento tiene que ser corrida_fin")
    for nombre in ("corrida_inicio", "corrida_fin"):
        if nombres.count(nombre) != 1:
            problemas.append(f"tiene que haber exactamente un {nombre} y hay {nombres.count(nombre)}")
    for campo in ("corrida", "tarea"):
        valores = {evento.get(campo) for _, evento in eventos}
        if len(valores) > 1:
            problemas.append(f"el campo «{campo}» cambia dentro de la traza: {sorted(map(str, valores))}")
    return problemas + _orden_y_pares(eventos)


def validar_archivo(ruta: Path) -> list[str]:
    eventos, problemas = leer_eventos(ruta)
    return problemas + validar_eventos(eventos)
