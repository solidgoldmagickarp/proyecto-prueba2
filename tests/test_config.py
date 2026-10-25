"""config.toml se carga, y una clave obligatoria que falta o está mal es un error."""
import copy

import pytest

import config as configuracion


@pytest.fixture
def base():
    return configuracion.cargar()


def test_el_config_del_kit_es_valido(base):
    assert base["modelo"]["nombre"] == "qwen3:8b" and base["modelo"]["num_ctx"] == 8192
    assert base["frenos"]["max_pasos"] == 14 and base["frenos"]["max_tokens"] == 80000


@pytest.mark.parametrize("seccion, clave", [("modelo", "num_ctx"), ("modelo", "think"), ("frenos", "max_pasos"),
                                            ("frenos", "max_tokens"), ("contexto", "tope_resultado_caracteres")])
def test_falta_una_clave_obligatoria(base, seccion, clave):
    roto = copy.deepcopy(base)
    del roto[seccion][clave]
    with pytest.raises(configuracion.ConfigError, match=clave):
        configuracion.validar(roto)


def test_falta_una_seccion(base):
    roto = copy.deepcopy(base)
    del roto["frenos"]
    with pytest.raises(configuracion.ConfigError, match="frenos"):
        configuracion.validar(roto)


@pytest.mark.parametrize("seccion, clave, valor", [("modelo", "num_ctx", "8192"), ("modelo", "num_ctx", True),
                                                   ("modelo", "think", 0), ("frenos", "max_pasos", 1.5)])
def test_tipo_equivocado(base, seccion, clave, valor):
    roto = copy.deepcopy(base)
    roto[seccion][clave] = valor
    with pytest.raises(configuracion.ConfigError, match="tipo equivocado"):
        configuracion.validar(roto)


def test_el_modelo_necesita_tag(base):
    roto = copy.deepcopy(base)
    roto["modelo"]["nombre"] = "qwen3"
    with pytest.raises(configuracion.ConfigError, match="tag"):
        configuracion.validar(roto)


def test_valores_no_positivos(base):
    roto = copy.deepcopy(base)
    roto["frenos"]["max_pasos"] = 0
    with pytest.raises(configuracion.ConfigError, match="positivos"):
        configuracion.validar(roto)


def test_las_claves_extra_se_aceptan(base):
    base["modelo"]["top_p"] = 0.9
    base["mi_seccion"] = {"x": 1}
    assert configuracion.validar(base) == base
