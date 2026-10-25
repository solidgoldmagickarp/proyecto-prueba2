"""El esqueleto de agente.py corre limpio, escribe una traza válida y no responde nada."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

import correr_todas
import evaluar
from tests.ayudas import leer
from trazas import esquema
from trazas.registro import SinRegistro

RAIZ = Path(__file__).resolve().parent.parent


def _correr(*argumentos):
    return subprocess.run([sys.executable, str(RAIZ / "agente.py"), *argumentos], capture_output=True,
                          text=True, cwd=RAIZ, timeout=60,
                          env={"PATH": "", "SYSTEMROOT": "", "OLLAMA_HOST": "127.0.0.1:1"})


def test_el_esqueleto_termina_con_error_y_una_traza_valida(tmp_path):
    proceso = _correr("-p", "¿Cuántos?", "--tarea", "mun-001", "--log", str(tmp_path))
    assert proceso.returncode == 1 and "todavía no está implementado" in proceso.stderr
    ruta = tmp_path / "mun-001.jsonl"
    assert esquema.validar_archivo(ruta) == []
    eventos = leer(ruta)
    assert [e["evento"] for e in eventos] == ["corrida_inicio", "corrida_fin"]
    assert eventos[-1]["estado"] == "error" and eventos[-1]["respuesta"] is None


def test_la_traza_registra_la_configuracion_y_que_no_hubo_servidor(tmp_path):
    _correr("-p", "?", "--tarea", "t", "--log", str(tmp_path))
    inicio = leer(tmp_path / "t.jsonl")[0]
    assert inicio["modelo"] == "qwen3:8b"
    assert inicio["config"]["modelo"]["num_ctx"] == 8192
    assert inicio["config"]["ollama_version"] is None and inicio["config"]["modelo_digest"] is None


def test_sin_log_no_escribe_trazas(tmp_path):
    proceso = _correr("-p", "?")
    assert proceso.returncode == 1 and not list(tmp_path.iterdir())


def test_una_config_invalida_falla_antes_de_correr(tmp_path):
    roto = tmp_path / "roto.toml"
    roto.write_text("[modelo]\nnombre = 'qwen3:8b'\n", encoding="utf-8")
    proceso = _correr("-p", "?", "--config", str(roto))
    assert proceso.returncode != 0 and "falta" in proceso.stderr


def test_correr_todas_y_evaluar_de_punta_a_punta_con_el_esqueleto(tmp_path):
    tareas = json.loads(evaluar.TAREAS.read_text(encoding="utf-8"))[:4]
    carpeta = tmp_path / "corrida"
    for tarea in tareas:
        resultado = correr_todas.correr_tarea(tarea, carpeta, RAIZ / "agente.py", sys.executable, 60)
        assert resultado["estado"] == "fallo" and resultado["codigo"] == 1
    filas, resumen = evaluar.evaluar(tareas, carpeta, evaluar.PESOS)
    assert resumen["aciertos"] == 0
    assert {f["resultado"] for f in filas} == {"sin_respuesta"}


def test_sin_registro_acepta_eventos_y_no_escribe():
    assert SinRegistro().evento("corrida_inicio", modelo="x")["evento"] == "corrida_inicio"
