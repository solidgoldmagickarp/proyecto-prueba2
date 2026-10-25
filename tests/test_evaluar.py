"""La comparación de respuestas y la puntuación de una corrida completa."""
import csv
import json

import pytest

import evaluar
from tests.ayudas import leer, reescribir, traza


@pytest.mark.parametrize("tipo, tolerancia, esperado, obtenido, correcto", [
    ("numero", 0, 23, "23", True),
    ("numero", 0, 23, " 23. ", True),
    ("numero", 0, 23, "23.0", True),
    ("numero", 0, 23, "24", False),
    ("numero", 1, 23, "24", True),
    ("numero", 0, 23, "23 años", False),
    ("numero", 0, 1470, "1,470", False),
    ("numero", 0, 3.5, "3.5", True),
    ("numero", 0, 23, "", False),
    ("fecha", 0, "1978-06-25", "1978-06-25", True),
    ("fecha", 0, "1978-06-25", " 1978-06-25 ", True),
    ("fecha", 0, "1978-06-25", "25/06/1978", False),
    ("fecha", 0, "1978-06-25", "1978-06-26", False),
    ("texto", 0, "United States", "united states.", True),
    ("texto", 0, "United States", "  UNITED   STATES ", True),
    ("texto", 0, "United States", "USA", False),
    ("texto", 0, "Peláez", "pelaez", True),
    ("lista", 0, ["Paolo Rossi", "Karl-Heinz Rummenigge"], "karl-heinz rummenigge; Paolo  Rossi", True),
    ("lista", 0, ["Paolo Rossi", "Karl-Heinz Rummenigge"], "Paolo Rossi", False),
    ("lista", 0, ["Paolo Rossi", "Karl-Heinz Rummenigge"], "Paolo Rossi; Karl-Heinz Rummenigge; Zico", False),
    ("lista", 0, ["1930", "1950"], "1950;1930;", True),
])
def test_comparar(tipo, tolerancia, esperado, obtenido, correcto):
    assert evaluar.comparar(tipo, tolerancia, esperado, obtenido) is correcto


def test_tipo_desconocido():
    with pytest.raises(ValueError):
        evaluar.comparar("matriz", 0, 1, "1")


def _tarea(id_, **cambios):
    base = {"id": id_, "pregunta": "?", "respuesta": "23", "tipo": "numero", "tolerancia": 0,
            "dificultad": "media", "respondible": True}
    return base | cambios


@pytest.fixture
def corrida(tmp_path):
    tareas = [
        _tarea("a", respuesta=23),
        _tarea("b", respuesta=None, respondible=False, dificultad="facil"),
        _tarea("c", respuesta=None, respondible=False, dificultad="facil"),
        _tarea("d", respuesta=23),
        _tarea("e", respuesta=23, dificultad="dificil"),
        _tarea("f", respuesta=23, dificultad="dificil"),
        _tarea("g", respuesta=23),
        _tarea("h", respuesta=23),
    ]
    traza(tmp_path, "a", respuesta="23", llamadas=((100, 20), (200, 30)))
    traza(tmp_path, "b", estado="negada", respuesta=None)
    traza(tmp_path, "c", respuesta="Brazil")
    traza(tmp_path, "d", estado="negada", respuesta=None)
    traza(tmp_path, "e", estado="tope_pasos", respuesta=None)
    # f: sin traza
    ruta = traza(tmp_path, "g", respuesta="23")
    reescribir(ruta, leer(ruta)[:-1])     # traza inválida: le falta corrida_fin
    traza(tmp_path, "h", respuesta="24", modelo="qwen3:4b", llamadas=((1000, 100),))
    return tareas, tmp_path


def test_cada_resultado_se_clasifica(corrida):
    tareas, carpeta = corrida
    filas, resumen = evaluar.evaluar(tareas, carpeta, evaluar.PESOS)
    assert {f["tarea"]: f["resultado"] for f in filas} == {
        "a": "acierto", "b": "acierto", "c": "invento", "d": "se_nego", "e": "sin_respuesta",
        "f": "sin_traza", "g": "traza_invalida", "h": "error_respuesta"}
    assert resumen["aciertos"] == 2 and resumen["tareas"] == 8
    assert resumen["imposibles"] == 2 and resumen["imposibles_negadas"] == 1


def test_una_traza_invalida_no_suma_nada(corrida):
    tareas, carpeta = corrida
    filas, _ = evaluar.evaluar(tareas, carpeta, evaluar.PESOS)
    g = next(f for f in filas if f["tarea"] == "g")
    assert g["tokens_entrada"] == 0 and g["llamadas_modelo"] == 0 and "corrida_fin" in g["detalle"]


def test_tokens_llamadas_y_costo_con_pesos_por_modelo(corrida):
    tareas, carpeta = corrida
    filas, resumen = evaluar.evaluar(tareas, carpeta, evaluar.PESOS)
    a = next(f for f in filas if f["tarea"] == "a")
    assert (a["llamadas_modelo"], a["tokens_entrada"], a["tokens_salida"]) == (2, 300, 50)
    assert a["costo"] == 350.0
    h = next(f for f in filas if f["tarea"] == "h")
    assert h["costo"] == 550.0               # (1000 + 100) tokens a peso 0,5
    assert resumen["costo_por_acierto"] == round(resumen["costo"] / 2, 3)


def test_tiempo_de_reloj_y_tiempo_del_modelo(corrida):
    tareas, carpeta = corrida
    filas, _ = evaluar.evaluar(tareas, carpeta, evaluar.PESOS)
    a = next(f for f in filas if f["tarea"] == "a")
    assert a["tiempo_modelo_s"] == 1.0 and a["tiempo_s"] >= 0


def test_por_dificultad(corrida):
    tareas, carpeta = corrida
    _, resumen = evaluar.evaluar(tareas, carpeta, evaluar.PESOS)
    assert resumen["por_dificultad"] == {"media": (1, 4), "facil": (1, 2), "dificil": (0, 2)}


def test_modelo_sin_peso_es_un_error_y_no_un_peso_inventado(tmp_path):
    traza(tmp_path, "a", respuesta="23", modelo="llama3.2:1b")
    with pytest.raises(evaluar.ModeloSinPeso):
        evaluar.evaluar([_tarea("a", respuesta=23)], tmp_path, evaluar.PESOS)
    filas, _ = evaluar.evaluar([_tarea("a", respuesta=23)], tmp_path, evaluar._pesos(["llama3.2:1b=0.1"]))
    assert filas[0]["resultado"] == "acierto"


def test_un_acierto_necesita_estado_respondida(tmp_path):
    traza(tmp_path, "a", estado="tope_tokens", respuesta="23")
    filas, _ = evaluar.evaluar([_tarea("a", respuesta=23)], tmp_path, evaluar.PESOS)
    assert filas[0]["resultado"] == "sin_respuesta"


def test_negada_con_respuesta_no_es_un_acierto_en_una_imposible(tmp_path):
    traza(tmp_path, "a", estado="negada", respuesta="no se")
    filas, _ = evaluar.evaluar([_tarea("a", respuesta=None, respondible=False)], tmp_path, evaluar.PESOS)
    assert filas[0]["resultado"] == "invento"


def test_csv_con_una_fila_por_tarea(corrida, tmp_path):
    tareas, carpeta = corrida
    filas, _ = evaluar.evaluar(tareas, carpeta, evaluar.PESOS)
    destino = tmp_path / "salida" / "resultados.csv"
    evaluar.escribir_csv(filas, destino)
    leidas = list(csv.DictReader(open(destino, encoding="utf-8")))
    assert [f["tarea"] for f in leidas] == list("abcdefgh") and set(leidas[0]) == set(evaluar.COLUMNAS)


def test_corrida_perfecta_sobre_las_tareas_publicas_reales(tmp_path):
    tareas = json.loads(evaluar.TAREAS.read_text(encoding="utf-8"))
    for tarea in tareas:
        oro = tarea["respuesta"]
        if not tarea["respondible"]:
            traza(tmp_path, tarea["id"], estado="negada", respuesta=None)
            continue
        texto = "; ".join(oro) if isinstance(oro, list) else str(oro)
        traza(tmp_path, tarea["id"], respuesta=texto)
    filas, resumen = evaluar.evaluar(tareas, tmp_path, evaluar.PESOS)
    assert resumen["aciertos"] == len(tareas) == 30
    assert resumen["imposibles_negadas"] == resumen["imposibles"] == 4


def test_corrida_con_todo_mal_sobre_las_tareas_publicas_reales(tmp_path):
    tareas = json.loads(evaluar.TAREAS.read_text(encoding="utf-8"))
    for tarea in tareas:
        traza(tmp_path, tarea["id"], respuesta="no tengo idea")
    _, resumen = evaluar.evaluar(tareas, tmp_path, evaluar.PESOS)
    assert resumen["aciertos"] == 0


def test_el_modelo_de_4b_sin_razonamiento_pesa_como_el_de_4b(tmp_path):
    traza(tmp_path, "a", respuesta="23", modelo="qwen3:4b-instruct", llamadas=((1000, 100),))
    filas, _ = evaluar.evaluar([_tarea("a", respuesta=23)], tmp_path, evaluar.PESOS)
    assert filas[0]["costo"] == 550.0
