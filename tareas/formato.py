"""El formato de respuesta que se le pide al modelo según el tipo de cada tarea."""

FORMATO_POR_TIPO = {
    "numero": "Respondé solo con el número.",
    "fecha": "Respondé con una fecha AAAA-MM-DD.",
    "texto": "Respondé con una palabra o frase corta.",
    "lista": "Respondé con los elementos separados por punto y coma (;).",
}


def pregunta_con_formato(tarea: dict) -> str:
    return f"{tarea['pregunta']} {FORMATO_POR_TIPO[tarea['tipo']]}"
