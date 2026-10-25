"""El validador de trazas acepta las válidas y señala cada tipo de problema."""
import pytest

from tests.ayudas import leer, reescribir, traza
from trazas import esquema


def _problemas(ruta):
    return esquema.validar_archivo(ruta)


def test_traza_valida(tmp_path):
    assert _problemas(traza(tmp_path, "t", llamadas=((10, 2), (30, 4), (50, 5)))) == []


def test_traza_valida_sin_herramientas(tmp_path):
    assert _problemas(traza(tmp_path, "t")) == []


def test_negada_es_valida(tmp_path):
    assert _problemas(traza(tmp_path, "t", estado="negada", respuesta=None)) == []


def test_estados_extra_y_eventos_desconocidos_se_aceptan(tmp_path):
    ruta = traza(tmp_path, "t", estado="sin_terminar", respuesta=None)
    eventos = leer(ruta)
    extra = dict(eventos[1], evento="nota_del_grupo", detalle="algo")
    reescribir(ruta, eventos[:2] + [extra] + eventos[2:])
    assert _problemas(ruta) == []


def test_campos_extra_se_aceptan(tmp_path):
    ruta = traza(tmp_path, "t")
    eventos = leer(ruta)
    eventos[1]["razonamiento"] = "texto libre"
    reescribir(ruta, eventos)
    assert _problemas(ruta) == []


def test_agente_y_padre_se_aceptan(tmp_path):
    ruta = traza(tmp_path, "t")
    eventos = [dict(e, agente="a1", padre=None) for e in leer(ruta)]
    reescribir(ruta, eventos)
    assert _problemas(ruta) == []


@pytest.mark.parametrize("campo", ["evento", "ts", "corrida", "tarea"])
def test_falta_un_campo_comun(tmp_path, campo):
    ruta = traza(tmp_path, "t")
    eventos = leer(ruta)
    del eventos[1][campo]
    reescribir(ruta, eventos)
    assert any(campo in p for p in _problemas(ruta))


def test_ts_que_no_es_iso(tmp_path):
    ruta = traza(tmp_path, "t")
    eventos = leer(ruta)
    eventos[1]["ts"] = "ayer a la tarde"
    reescribir(ruta, eventos)
    assert any("ISO" in p for p in _problemas(ruta))


@pytest.mark.parametrize("evento, campo", [("llamada_modelo", "tokens_entrada"), ("llamada_modelo", "num_ctx"),
                                           ("corrida_fin", "estado"), ("corrida_inicio", "config")])
def test_falta_un_campo_propio(tmp_path, evento, campo):
    ruta = traza(tmp_path, "t")
    eventos = leer(ruta)
    del next(e for e in eventos if e["evento"] == evento)[campo]
    reescribir(ruta, eventos)
    assert any(campo in p for p in _problemas(ruta))


@pytest.mark.parametrize("evento, campo, valor", [("llamada_modelo", "tokens_entrada", "100"),
                                                  ("llamada_modelo", "tokens_salida", -1),
                                                  ("llamada_modelo", "duracion_ms", True),
                                                  ("corrida_fin", "pasos", 1.5),
                                                  ("corrida_fin", "respuesta", 23)])
def test_tipo_equivocado(tmp_path, evento, campo, valor):
    ruta = traza(tmp_path, "t")
    eventos = leer(ruta)
    next(e for e in eventos if e["evento"] == evento)[campo] = valor
    reescribir(ruta, eventos)
    assert any(f"{evento}.{campo}" in p for p in _problemas(ruta))


def test_config_sin_num_ctx(tmp_path):
    ruta = traza(tmp_path, "t")
    eventos = leer(ruta)
    eventos[0]["config"] = {"temperatura": 0}
    reescribir(ruta, eventos)
    assert any("num_ctx" in p for p in _problemas(ruta))


def test_resultado_sin_llamada(tmp_path):
    ruta = traza(tmp_path, "t", llamadas=((10, 2), (30, 4)))
    eventos = [e for e in leer(ruta) if e["evento"] != "llamada_herramienta"]
    reescribir(ruta, eventos)
    assert any("sin llamada previa" in p for p in _problemas(ruta))


def test_llamada_sin_resultado(tmp_path):
    ruta = traza(tmp_path, "t", llamadas=((10, 2), (30, 4)))
    eventos = [e for e in leer(ruta) if e["evento"] != "resultado_herramienta"]
    reescribir(ruta, eventos)
    assert any("no tiene resultado" in p for p in _problemas(ruta))


def test_id_repetido(tmp_path):
    ruta = traza(tmp_path, "t", llamadas=((10, 2), (30, 4)))
    eventos = leer(ruta)
    llamada = next(e for e in eventos if e["evento"] == "llamada_herramienta")
    eventos.insert(eventos.index(llamada) + 1, dict(llamada))
    reescribir(ruta, eventos)
    assert any("se repite" in p for p in _problemas(ruta))


def test_dos_resultados_para_un_id(tmp_path):
    ruta = traza(tmp_path, "t", llamadas=((10, 2), (30, 4)))
    eventos = leer(ruta)
    resultado = next(e for e in eventos if e["evento"] == "resultado_herramienta")
    eventos.insert(eventos.index(resultado) + 1, dict(resultado))
    reescribir(ruta, eventos)
    assert any("dos resultados" in p for p in _problemas(ruta))


def test_resultado_de_otro_paso(tmp_path):
    ruta = traza(tmp_path, "t", llamadas=((10, 2), (30, 4), (50, 5)))
    eventos = leer(ruta)
    ultimo = [e for e in eventos if e["evento"] == "resultado_herramienta"][-1]
    ultimo["paso"] = 1
    reescribir(ruta, eventos)
    assert _problemas(ruta)


def test_dos_llamadas_a_la_vez_con_ids_distintos(tmp_path):
    ruta = traza(tmp_path, "t", llamadas=((10, 2), (30, 4)))
    eventos = leer(ruta)
    llamada = next(e for e in eventos if e["evento"] == "llamada_herramienta")
    resultado = next(e for e in eventos if e["evento"] == "resultado_herramienta")
    otra_llamada, otro_resultado = dict(llamada, id="call_b"), dict(resultado, id="call_b")
    posicion = eventos.index(llamada)
    eventos[posicion:posicion + 2] = [llamada, otra_llamada, resultado, otro_resultado]
    reescribir(ruta, eventos)
    assert _problemas(ruta) == []


def test_paso_que_baja(tmp_path):
    ruta = traza(tmp_path, "t", llamadas=((10, 2), (30, 4), (50, 5)))
    eventos = leer(ruta)
    [e for e in eventos if e["evento"] == "llamada_modelo"][-1]["paso"] = 1
    reescribir(ruta, eventos)
    assert any("«paso» baja" in p for p in _problemas(ruta))


def test_sin_corrida_inicio_o_sin_corrida_fin(tmp_path):
    ruta = traza(tmp_path, "t")
    eventos = leer(ruta)
    reescribir(ruta, eventos[1:])
    assert any("primer evento" in p for p in _problemas(ruta))
    reescribir(ruta, eventos[:-1])
    assert any("último evento" in p for p in _problemas(ruta))


def test_dos_corrida_fin(tmp_path):
    ruta = traza(tmp_path, "t")
    eventos = leer(ruta)
    reescribir(ruta, eventos + [eventos[-1]])
    assert any("exactamente un corrida_fin" in p for p in _problemas(ruta))


def test_la_tarea_cambia_dentro_de_la_traza(tmp_path):
    ruta = traza(tmp_path, "t")
    eventos = leer(ruta)
    eventos[1]["tarea"] = "otra"
    reescribir(ruta, eventos)
    assert any("«tarea» cambia" in p for p in _problemas(ruta))


def test_archivo_vacio_y_json_roto(tmp_path):
    vacio = tmp_path / "vacio.jsonl"
    vacio.write_text("", encoding="utf-8")
    assert _problemas(vacio) == ["la traza está vacía"]
    roto = traza(tmp_path, "t")
    roto.write_text(roto.read_text(encoding="utf-8") + "{no es json\n", encoding="utf-8")
    assert any("no es JSON" in p for p in _problemas(roto))


def test_el_registro_escribe_una_traza_valida_y_reemplaza_la_anterior(tmp_path):
    traza(tmp_path, "t", llamadas=((10, 2), (30, 4), (50, 5)))
    ruta = traza(tmp_path, "t")
    assert len(leer(ruta)) == 3
    assert _problemas(ruta) == []


def test_num_ctx_dentro_de_la_seccion_modelo(tmp_path):
    ruta = traza(tmp_path, "t")
    eventos = leer(ruta)
    eventos[0]["config"] = {"modelo": {"nombre": "qwen3:8b", "num_ctx": 8192}, "ollama_version": None}
    reescribir(ruta, eventos)
    assert _problemas(ruta) == []
