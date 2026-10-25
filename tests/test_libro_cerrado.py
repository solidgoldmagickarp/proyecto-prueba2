"""La línea de base a libro cerrado escribe trazas válidas que `evaluar.py` puntúa igual que al agente."""
import evaluar
import libro_cerrado
import llm
from tests.ayudas import leer
from trazas import esquema

TAREA = {"id": "t", "pregunta": "¿Cuántos goles hizo Messi?", "respuesta": 13, "tipo": "numero",
         "tolerancia": 0, "dificultad": "facil", "respondible": True}
IMPOSIBLE = dict(TAREA, id="i", respuesta=None, respondible=False)


class ChatFalso:
    def __init__(self, contenido=None, error=None):
        self.contenido, self.error, self.llamadas = contenido, error, []

    def __call__(self, mensajes, **opciones):
        self.llamadas.append((mensajes, opciones))
        if self.error:
            raise self.error
        return llm.Respuesta({"role": "assistant", "content": self.contenido}, 40, 5, 120)


def _correr(tarea, carpeta, chat):
    return libro_cerrado.responder_tarea(tarea, carpeta, modelo="qwen3:8b", num_ctx=8192, chat=chat)


def test_una_respuesta_queda_registrada_y_la_traza_es_valida(tmp_path):
    chat = ChatFalso(" 13 \n")
    assert _correr(TAREA, tmp_path, chat) == "respondida"
    assert esquema.validar_archivo(tmp_path / "t.jsonl") == []
    assert leer(tmp_path / "t.jsonl")[-1]["respuesta"] == "13"


def test_manda_el_formato_de_la_tarea_sin_herramientas_ni_razonamiento(tmp_path):
    chat = ChatFalso("13")
    _correr(TAREA, tmp_path, chat)
    mensajes, opciones = chat.llamadas[0]
    assert mensajes[1]["content"].endswith("Respondé solo con el número.")
    assert "herramientas" not in opciones and opciones["think"] is False and opciones["num_ctx"] == 8192


def test_no_se_es_una_negativa(tmp_path):
    assert _correr(IMPOSIBLE, tmp_path, ChatFalso("NO SE")) == "negada"
    ultimo = leer(tmp_path / "i.jsonl")[-1]
    assert ultimo["estado"] == "negada" and ultimo["respuesta"] is None


def test_un_error_del_servidor_queda_como_estado_error(tmp_path):
    assert _correr(TAREA, tmp_path, ChatFalso(error=llm.LLMError("sin respuesta"))) == "error"
    assert esquema.validar_archivo(tmp_path / "t.jsonl") == []
    assert leer(tmp_path / "t.jsonl")[-1]["estado"] == "error"


def test_evaluar_puntua_la_corrida_igual_que_la_del_agente(tmp_path):
    _correr(TAREA, tmp_path, ChatFalso("7"))
    _correr(IMPOSIBLE, tmp_path, ChatFalso("Brazil"))
    filas, resumen = evaluar.evaluar([TAREA, IMPOSIBLE], tmp_path, evaluar.PESOS)
    assert [f["resultado"] for f in filas] == ["error_respuesta", "invento"]
    assert resumen["llamadas_modelo"] == 2 and resumen["tokens"] == 90
