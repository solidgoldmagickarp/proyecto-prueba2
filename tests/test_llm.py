"""El cliente de Ollama, contra un servidor de mentira que registra lo que recibe."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import llm


class Servidor:
    def __init__(self):
        self.recibidos = []
        self.respuesta = (200, {"message": {"role": "assistant", "content": "hola"},
                                "prompt_eval_count": 12, "eval_count": 3, "done_reason": "stop"})
        servidor = self

        class Manejador(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _enviar(self, estado, cuerpo):
                datos = cuerpo.encode() if isinstance(cuerpo, str) else json.dumps(cuerpo).encode()
                self.send_response(estado)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(datos)

            def do_GET(self):
                if self.path == "/api/tags":
                    return self._enviar(200, {"models": [{"name": "qwen3:8b", "digest": "500a1f067a9f"}]})
                self._enviar(200, {"version": "9.9.9"})

            def do_POST(self):
                servidor.recibidos.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                self._enviar(*servidor.respuesta)

        self.http = HTTPServer(("127.0.0.1", 0), Manejador)
        threading.Thread(target=self.http.serve_forever, daemon=True).start()
        self.direccion = f"127.0.0.1:{self.http.server_port}"

    def cerrar(self):
        self.http.shutdown()


@pytest.fixture
def servidor(monkeypatch):
    activo = Servidor()
    monkeypatch.setenv("OLLAMA_HOST", activo.direccion)
    yield activo
    activo.cerrar()


def test_manda_num_ctx_y_pide_que_falle_en_lugar_de_recortar(servidor):
    llm.chat([{"role": "user", "content": "?"}], modelo="qwen3:8b", num_ctx=8192)
    [pedido] = servidor.recibidos
    assert pedido["options"] == {"num_ctx": 8192, "temperature": 0, "seed": 1337, "num_predict": 800}
    assert pedido["truncate"] is False and pedido["think"] is False and pedido["stream"] is False
    assert pedido["model"] == "qwen3:8b" and "tools" not in pedido


def test_manda_las_herramientas_cuando_hay(servidor):
    ficha = {"type": "function", "function": {"name": "calcular"}}
    llm.chat([], modelo="qwen3:8b", num_ctx=4096, herramientas=[ficha])
    assert servidor.recibidos[0]["tools"] == [ficha]


def test_devuelve_mensaje_contadores_y_duracion(servidor):
    respuesta = llm.chat([], modelo="qwen3:8b", num_ctx=4096)
    assert respuesta.mensaje["content"] == "hola"
    assert (respuesta.tokens_entrada, respuesta.tokens_salida) == (12, 3)
    assert isinstance(respuesta.duracion_ms, int) and respuesta.duracion_ms >= 0


def test_un_prompt_que_no_entra_es_context_overflow(servidor):
    servidor.respuesta = (400, {"error": "request (6170 tokens) exceeds the available context size (4096 tokens)"})
    with pytest.raises(llm.ContextOverflow) as error:
        llm.chat([], modelo="qwen3:8b", num_ctx=4096)
    assert error.value.estado == 400


def test_otro_error_del_servidor_es_llm_error_pero_no_overflow(servidor):
    servidor.respuesta = (500, {"error": "model runner has unexpectedly stopped"})
    with pytest.raises(llm.LLMError) as error:
        llm.chat([], modelo="qwen3:8b", num_ctx=4096)
    assert not isinstance(error.value, llm.ContextOverflow) and error.value.estado == 500


def test_una_respuesta_sin_contadores_no_se_completa_con_ceros(servidor):
    servidor.respuesta = (200, {"message": {"role": "assistant", "content": "hola"}})
    with pytest.raises(llm.LLMError, match="contadores"):
        llm.chat([], modelo="qwen3:8b", num_ctx=4096)


def test_servidor_apagado(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "127.0.0.1:1")
    with pytest.raises(llm.LLMError, match="sin respuesta"):
        llm.chat([], modelo="qwen3:8b", num_ctx=4096, timeout_s=2)


def test_version(servidor):
    assert llm.version() == "9.9.9"


def test_host_con_y_sin_esquema(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "10.0.0.5:11434")
    assert llm.host() == "http://10.0.0.5:11434"
    monkeypatch.setenv("OLLAMA_HOST", "http://otro:1")
    assert llm.host() == "http://otro:1"


def test_digest_del_modelo_descargado(servidor):
    assert llm.digest("qwen3:8b") == "500a1f067a9f"
    assert llm.digest("qwen3:4b") is None


def test_devuelve_la_razon_de_fin_que_informa_el_servidor(servidor):
    assert llm.chat([], modelo="qwen3:8b", num_ctx=4096).razon_fin == "stop"
    servidor.respuesta = (200, {"message": {"role": "assistant", "content": "cortado"},
                                "prompt_eval_count": 12, "eval_count": 800, "done_reason": "length"})
    assert llm.chat([], modelo="qwen3:8b", num_ctx=4096).razon_fin == "length"


def test_sin_done_reason_la_razon_de_fin_es_none(servidor):
    servidor.respuesta = (200, {"message": {"role": "assistant", "content": "x"},
                                "prompt_eval_count": 1, "eval_count": 1})
    assert llm.chat([], modelo="qwen3:8b", num_ctx=4096).razon_fin is None


def test_manda_el_esquema_de_salida_solo_cuando_se_pide(servidor):
    esquema = {"type": "object", "properties": {"respuesta": {"type": "string"}}, "required": ["respuesta"]}
    llm.chat([], modelo="qwen3:8b", num_ctx=4096)
    llm.chat([], modelo="qwen3:8b", num_ctx=4096, formato=esquema)
    sin, con = servidor.recibidos[-2:]
    assert "format" not in sin and con["format"] == esquema
