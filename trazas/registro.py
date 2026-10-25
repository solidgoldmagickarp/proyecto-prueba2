"""Escritor de trazas: una línea JSON por evento, con los campos comunes ya puestos."""
import datetime as dt
import json
from pathlib import Path


class SinRegistro:
    """Para correr sin `--log`: acepta los mismos eventos y no escribe nada."""

    def evento(self, evento: str, **campos) -> dict:
        return {"evento": evento, **campos}


class Registro:
    """Abre `<carpeta>/<tarea>.jsonl` de cero: una corrida nueva reemplaza la anterior de esa tarea."""

    def __init__(self, carpeta: Path, tarea: str | None, *, corrida: str | None = None,
                 agente: str | None = None, padre: str | None = None):
        self.carpeta = Path(carpeta)
        self.carpeta.mkdir(parents=True, exist_ok=True)
        self.corrida = corrida or self.carpeta.name
        self.tarea = tarea
        self.agente, self.padre = agente, padre
        self.ruta = self.carpeta / f"{tarea or 'libre'}.jsonl"
        self.ruta.write_text("", encoding="utf-8")

    def evento(self, evento: str, **campos) -> dict:
        registro = {"evento": evento, "ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds"),
                    "corrida": self.corrida, "tarea": self.tarea}
        if self.agente is not None:
            registro |= {"agente": self.agente, "padre": self.padre}
        registro |= campos
        with open(self.ruta, "a", encoding="utf-8") as archivo:
            archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
        return registro
