"""Las herramientas del Mundial contra cifras verificadas en los datos."""
import datetime as dt

import pytest

from herramientas.mundial import FICHAS, FICHAS_POR_NOMBRE, HERRAMIENTAS, ORDEN_HERRAMIENTAS

pytestmark = pytest.mark.usefixtures("herramientas_con_db")


def test_argentina_campeon_tres_veces(herramientas_con_db):
    resultado = herramientas_con_db.buscar_torneos(campeon="Argentina")
    assert [t["torneo"] for t in resultado] == [1978, 1986, 2022]


def test_final_de_1978(herramientas_con_db):
    [torneo] = herramientas_con_db.buscar_torneos(anio=1978)
    assert torneo["final"] == "1978-06-25"
    assert torneo["campeon"] == "Argentina"


def test_1950_no_tiene_una_final(herramientas_con_db):
    [torneo] = herramientas_con_db.buscar_torneos(anio=1950)
    assert torneo["final"] is None


def test_sin_argumentos_son_los_masculinos(herramientas_con_db):
    assert len(herramientas_con_db.buscar_torneos()) == 22
    assert len(herramientas_con_db.buscar_torneos(femenino=True)) == 8


def test_campeon_sin_acentos_ni_mayusculas(herramientas_con_db):
    assert herramientas_con_db.buscar_torneos(campeon="argentina") == \
        herramientas_con_db.buscar_torneos(campeon="Argentina")


def test_torneos_sin_resultados_es_un_error(herramientas_con_db):
    assert "error" in herramientas_con_db.buscar_torneos(campeon="Atlantis")


@pytest.mark.parametrize("anio, jugador, goles", [(1978, "Mario Kempes", 6), (1986, "Gary Lineker", 6),
                                                  (2022, "Kylian Mbappé", 8)])
def test_goleador_del_torneo(herramientas_con_db, anio, jugador, goles):
    primero = herramientas_con_db.goleadores(anio)["goleadores"][0]
    assert (primero["jugador"], primero["goles"]) == (jugador, goles)


def test_goleadores_respeta_n(herramientas_con_db):
    assert len(herramientas_con_db.goleadores(2022, n=3)["goleadores"]) == 3


def test_empate_en_el_corte(herramientas_con_db):
    # 1986: Lineker 6 y, detrás, varios con 5.
    assert herramientas_con_db.goleadores(1986, n=1)["empate_en_el_corte"] is False
    assert herramientas_con_db.goleadores(1986, n=2)["empate_en_el_corte"] is True


def test_goleadores_de_un_anio_sin_mundial(herramientas_con_db):
    resultado = herramientas_con_db.goleadores(1942)
    assert "error" in resultado
    assert len(resultado["torneos_disponibles"]) == 30


def test_kempes_nacimiento_y_seleccion(herramientas_con_db):
    [kempes] = herramientas_con_db.buscar_jugador("Kempes")
    assert kempes["nacimiento"] == "1954-07-15"
    assert kempes["selecciones"] == ["Argentina"]
    assert 1978 in kempes["torneos"]


def test_nombre_sin_acentos(herramientas_con_db):
    assert herramientas_con_db.buscar_jugador("mbappe")[0]["jugador"] == "Kylian Mbappé"


def test_jugador_inexistente_es_un_error(herramientas_con_db):
    assert "error" in herramientas_con_db.buscar_jugador("Zzzzqqq")


def test_muchas_coincidencias_avisan_del_recorte(herramientas_con_db):
    resultado = herramientas_con_db.buscar_jugador("Silva")
    assert len(resultado) == 6
    assert "aviso" in resultado[-1]


def test_nacimiento_ausente_es_none(herramientas_con_db):
    from herramientas import mundial
    ausente = next(j for j in mundial._jugadores(str(mundial._ruta_db())) if j["nacimiento"] is None)
    assert mundial._ficha_jugador(ausente)["nacimiento"] is None


def test_messi_suma_13(herramientas_con_db):
    resultado = herramientas_con_db.goles("Messi")
    assert resultado["por_torneo"] == {"2006": 1, "2014": 4, "2018": 1, "2022": 7}
    assert resultado["total"] == 13


def test_goles_en_un_torneo(herramientas_con_db):
    assert herramientas_con_db.goles("Messi", torneo=2022)["goles"] == 7


def test_goles_en_un_torneo_que_no_jugo(herramientas_con_db):
    assert "error" in herramientas_con_db.goles("Messi", torneo=1930)


def test_goles_con_nombre_ambiguo_no_elige(herramientas_con_db):
    resultado = herramientas_con_db.goles("Silva")
    assert resultado["error"].startswith("ambiguo")
    assert len(resultado["candidatos"]) > 1


def test_goles_no_cuentan_los_goles_en_contra(herramientas_con_db):
    from herramientas import mundial
    autores = mundial._sql("SELECT DISTINCT player_id FROM goals WHERE own_goal = 1")
    assert autores, "la base debería tener goles en contra"
    comparados = 0
    for autor in autores:
        jugador = next(j for j in mundial._jugadores(str(mundial._ruta_db())) if j["id"] == autor["player_id"])
        resultado = mundial.goles(jugador["nombre"])
        if "error" in resultado:
            continue  # nombre ambiguo: no hay una sola respuesta que comparar
        esperado = mundial._sql("SELECT COUNT(*) AS n FROM goals WHERE player_id = ? AND own_goal = 0",
                                jugador["id"])[0]["n"]
        assert resultado["total"] == esperado
        comparados += 1
    assert comparados > 0


def test_goleadores_no_cuentan_los_goles_en_contra(herramientas_con_db):
    from herramientas import mundial
    for anio in mundial._anios_disponibles():
        ranking = mundial.goleadores(anio, n=10_000)["goleadores"]
        esperado = mundial._sql("SELECT COUNT(*) AS n FROM goals WHERE tournament_id = ? AND own_goal = 0",
                                mundial._id_torneo(anio))[0]["n"]
        assert sum(j["goles"] for j in ranking) == esperado, anio


def test_1986_tuvo_52_partidos(herramientas_con_db):
    assert len(herramientas_con_db.partidos(1986)) == 52


def test_partidos_tienen_los_campos_del_contrato(herramientas_con_db):
    campos = {"fecha", "etapa", "local", "visitante", "resultado", "penales", "estadio", "ciudad"}
    assert all(set(p) == campos for p in herramientas_con_db.partidos(2022))


def test_fechas_de_partidos_son_iso(herramientas_con_db):
    assert all(dt.date.fromisoformat(p["fecha"]) for p in herramientas_con_db.partidos(1978))


def test_penales_solo_en_las_definiciones(herramientas_con_db):
    final = [p for p in herramientas_con_db.partidos(2022) if p["etapa"] == "final"][0]
    assert final["penales"] is not None
    final_1978 = [p for p in herramientas_con_db.partidos(1978) if p["etapa"] == "final"][0]
    assert final_1978["penales"] is None


def test_calcular_suma(herramientas_con_db):
    assert herramientas_con_db.calcular("6 + 6 + 8") == {"resultado": 20}


def test_calcular_edad_de_kempes_en_la_final(herramientas_con_db):
    resultado = herramientas_con_db.calcular("1978-06-25 - 1954-07-15")
    assert resultado["anios_cumplidos"] == 23
    assert resultado["dias"] == (dt.date(1978, 6, 25) - dt.date(1954, 7, 15)).days


def test_calcular_division(herramientas_con_db):
    assert herramientas_con_db.calcular("7 / 2") == {"resultado": 3.5}


@pytest.mark.parametrize("expresion", ["1 / 0", "2 ** 1000000", "__import__('os')", "abs(-1)", "1 +",
                                       "2024-02-30 - 2024-01-01", "1954-07-15 - 1978-06-25"])
def test_calcular_rechaza_lo_que_no_puede(herramientas_con_db, expresion):
    assert "error" in herramientas_con_db.calcular(expresion)


def test_cada_ficha_es_coherente():
    assert [f["function"]["name"] for f in FICHAS] == ORDEN_HERRAMIENTAS
    for nombre, ficha in FICHAS_POR_NOMBRE.items():
        parametros = ficha["function"]["parameters"]
        assert parametros["additionalProperties"] is False
        assert set(parametros["required"]) <= set(parametros["properties"])
        assert all("description" in p for p in parametros["properties"].values())


def test_toda_herramienta_con_ficha_tiene_funcion():
    assert set(HERRAMIENTAS) == set(ORDEN_HERRAMIENTAS) - {"terminar"}


@pytest.mark.parametrize("nombre", ["Silva", "Ronaldo", "Rodríguez"])
def test_todo_candidato_ambiguo_se_puede_elegir_por_id(herramientas_con_db, nombre):
    candidatos = [c for c in herramientas_con_db.goles(nombre)["candidatos"] if "id" in c]
    assert len(candidatos) > 1
    for candidato in candidatos:
        elegido = herramientas_con_db.goles(candidato["id"])
        assert "error" not in elegido
        assert elegido["jugador"] == candidato["jugador"]


def test_ronaldo_brasileno_por_id_suma_15(herramientas_con_db):
    candidatos = herramientas_con_db.goles("Ronaldo")["candidatos"]
    [brasilenio] = [c for c in candidatos if c["selecciones"] == ["Brazil"]]
    assert herramientas_con_db.goles(brasilenio["id"])["total"] == 15


def test_id_inexistente_es_un_error(herramientas_con_db):
    assert "error" in herramientas_con_db.goles("P-00000")
    assert "error" in herramientas_con_db.buscar_jugador("P-00000")


def test_buscar_jugador_devuelve_el_id(herramientas_con_db):
    [kempes] = herramientas_con_db.buscar_jugador("Kempes")
    assert kempes["id"] == "P-35082"
    assert herramientas_con_db.buscar_jugador("P-35082")[0]["jugador"] == "Mario Kempes"


def test_el_error_de_ambiguedad_dice_como_resolverlo(herramientas_con_db):
    error = herramientas_con_db.goles("Ronaldo")["error"]
    assert "id" in error and "`jugador`" in error
