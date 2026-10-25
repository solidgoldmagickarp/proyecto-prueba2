"""El runner corre un agente por tarea, y deja registrada la falla de uno que se cuelga o se cae."""
import json
import sys
from pathlib import Path

import pytest

import correr_todas
import evaluar
from tests.ayudas import leer
from trazas import esquema

RAIZ = Path(__file__).resolve().parent.parent

AGENTE_FALSO = '''
import argparse, sys, time
from pathlib import Path
from trazas.registro import Registro

parser = argparse.ArgumentParser()
parser.add_argument("-p"); parser.add_argument("--tarea"); parser.add_argument("--log")
parser.add_argument("--config")
args = parser.parse_args()
carpeta = Path(args.log)
(carpeta / f"{args.tarea}.pregunta.txt").write_text(args.p, encoding="utf-8")
(carpeta / f"{args.tarea}.corridas.txt").open("a").write("x")
if args.config:
    (carpeta / f"{args.tarea}.config.txt").write_text(args.config, encoding="utf-8")
if args.tarea == "t-nada":
    sys.exit(0)
registro = Registro(carpeta, args.tarea)
registro.evento("corrida_inicio", modelo="qwen3:8b", config={"num_ctx": 8192})
if args.tarea == "t-cuelga":
    time.sleep(30)
if args.tarea == "t-falla":
    sys.exit(3)
registro.evento("llamada_modelo", paso=1, modelo="qwen3:8b", num_ctx=8192, tokens_entrada=10,
                tokens_salida=2, duracion_ms=50)
registro.evento("corrida_fin", estado="respondida", respuesta="23", pasos=1)
'''


def _tarea(id_):
    return {"id": id_, "pregunta": "¿Cuántos?", "respuesta": 23, "tipo": "numero", "tolerancia": 0,
            "dificultad": "facil", "respondible": True}


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    agente = tmp_path / "agente_falso.py"
    agente.write_text(AGENTE_FALSO, encoding="utf-8")
    monkeypatch.setenv("PYTHONPATH", str(RAIZ))
    return agente, tmp_path / "trazas" / "corrida"


def _correr(tarea, entorno, timeout=20):
    agente, carpeta = entorno
    return correr_todas.correr_tarea(_tarea(tarea), carpeta, agente, sys.executable, timeout)


def test_una_tarea_normal(entorno):
    resultado = _correr("t-ok", entorno)
    carpeta = entorno[1]
    assert resultado["estado"] == "ok" and resultado["codigo"] == 0
    assert esquema.validar_archivo(carpeta / "t-ok.jsonl") == []


def test_agrega_el_formato_de_respuesta_a_la_pregunta(entorno):
    _correr("t-ok", entorno)
    pregunta = (entorno[1] / "t-ok.pregunta.txt").read_text(encoding="utf-8")
    assert pregunta == "¿Cuántos? Respondé solo con el número."


def test_un_agente_que_se_cuelga_se_corta_y_queda_registrado(entorno):
    resultado = _correr("t-cuelga", entorno, timeout=2)
    ruta = entorno[1] / "t-cuelga.jsonl"
    assert resultado["estado"] == "timeout"
    assert esquema.validar_archivo(ruta) == []
    fin = leer(ruta)[-1]
    assert fin["estado"] == "error" and fin["origen"] == "correr_todas" and "tope" in fin["motivo"]


def test_un_agente_que_se_cae_queda_registrado(entorno):
    resultado = _correr("t-falla", entorno)
    ruta = entorno[1] / "t-falla.jsonl"
    assert resultado["estado"] == "fallo" and resultado["codigo"] == 3
    assert esquema.validar_archivo(ruta) == []
    assert "código 3" in leer(ruta)[-1]["motivo"]


def test_un_agente_que_no_escribe_nada_no_deja_traza_inventada(entorno):
    resultado = _correr("t-nada", entorno)
    assert resultado["estado"] == "sin_traza" and not (entorno[1] / "t-nada.jsonl").exists()


def test_evaluar_distingue_cada_caso(entorno):
    for id_ in ("t-ok", "t-falla", "t-nada"):
        _correr(id_, entorno)
    tareas = [_tarea(i) for i in ("t-ok", "t-falla", "t-nada")]
    filas, _ = evaluar.evaluar(tareas, entorno[1], evaluar.PESOS)
    assert [f["resultado"] for f in filas] == ["acierto", "sin_respuesta", "sin_traza"]


def test_reanudar_saltea_las_tareas_con_traza_valida(entorno, tmp_path, monkeypatch, capsys):
    agente, carpeta = entorno
    archivo = tmp_path / "tareas.json"
    archivo.write_text(json.dumps([_tarea("t-ok")]), encoding="utf-8")
    argumentos = ["correr_todas.py", "--corrida", str(carpeta), "--tareas", str(archivo), "--agente", str(agente)]
    monkeypatch.setattr(sys, "argv", argumentos)
    correr_todas.main()
    monkeypatch.setattr(sys, "argv", argumentos + ["--reanudar"])
    correr_todas.main()
    assert "se saltea" in capsys.readouterr().out
    assert (carpeta / "t-ok.corridas.txt").read_text() == "x"


def test_pasa_el_config_alternativo_al_agente_solo_si_se_pide(entorno, tmp_path):
    agente, carpeta = entorno
    correr_todas.correr_tarea(_tarea("t-ok"), carpeta, agente, sys.executable, 20)
    assert not (carpeta / "t-ok.config.txt").exists()
    otro = tmp_path / "otro.toml"
    correr_todas.correr_tarea(_tarea("t-ok"), carpeta, agente, sys.executable, 20, config=otro)
    assert (carpeta / "t-ok.config.txt").read_text(encoding="utf-8") == str(otro)
