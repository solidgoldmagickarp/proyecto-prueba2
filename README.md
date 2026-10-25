# Kit del proyecto final

**IA Generativa Avanzada y Sistemas Multi-Agente** — Licenciatura en Tecnología Digital, Universidad
Torcuato Di Tella.

Este es el kit inicial del proyecto final. Trae las herramientas, las tareas, el evaluador y el
esqueleto de un agente que todavía no responde nada. **Lo que falta es el loop**: la función `bucle`
de [agente.py](agente.py) es tu trabajo. El resto es plomería: mueve datos, valida trazas y habla con
el servidor; ninguna pieza toma una decisión de diseño por vos.

El [enunciado](ENUNCIADO.md) dice qué se construye y cómo se evalúa. Este README dice cómo poner en marcha el kit.

## Qué hay acá

| Ruta | Qué es |
|---|---|
| [agente.py](agente.py) | **Tu loop.** Lee la configuración, abre la traza y llama a `bucle`, que está sin implementar |
| [config.toml](config.toml) | El modelo, `num_ctx`, los topes y el recorte de resultados. Se copia entera en cada traza |
| `herramientas/mundial.py` | Las seis herramientas del Mundial sobre SQLite, sus esquemas JSON (`FICHAS`) y `terminar` |
| `llm.py` | Una llamada a Ollama por la API nativa. Manda `num_ctx` siempre, puede restringir la salida a un esquema JSON (`formato`) y no reintenta: eso es tuyo |
| `datos/descargar.py` | Baja los CSV de la *Fjelstul World Cup Database* (commit fijado) y arma la base SQLite |
| `tareas/mundial_publicas.json` | 30 tareas del Mundial, con su respuesta |
| `tareas/verificadores.py` | Recalcula cada respuesta con SQL, sin pasar por el modelo ni por las herramientas |
| `correr_todas.py` | Corre `agente.py` una vez por tarea, cada una en su proceso y con un tope de tiempo |
| `evaluar.py` | Puntúa una corrida a partir de sus trazas: aciertos, tokens, costo y tiempo |
| `libro_cerrado.py` | Las mismas tareas con el modelo sin herramientas: la línea de base |
| `trazas/esquema.py`, `trazas/registro.py` | El validador del esquema de trazas y el escritor que usan todos |
| `colab/arranque.ipynb` | Deja Ollama, el modelo y los datos listos en una T4 de Colab |

## Primer día, paso a paso

1. **Creá tu repositorio.** En la página de este repositorio en GitHub, botón **Use this template** →
   *Create a new repository*, con visibilidad **Private**. No hagas un fork: un fork de un repositorio
   público es público.
2. **Clonalo a tu máquina:** `git clone https://github.com/<usuario>/<repo>.git`. El loop lo escribís
   ahí, en tu editor.
3. **Abrí `colab/arranque.ipynb`**, de una de dos maneras:
   - *En VS Code*, con la extensión de Colab: abrí la carpeta clonada y el cuaderno, y elegí
     *Select Kernel → Colab → New Colab Server* y una **T4**.
   - *En el sitio de Colab* (colab.research.google.com): *File → Upload notebook* y elegí
     `colab/arranque.ipynb` de tu carpeta clonada; después *Runtime → Change runtime type* y una **T4**.

   Elegí la T4 **antes** de correr nada: cambiarla después reemplaza la máquina.
4. **Creá un token de GitHub** para que Colab pueda bajar y subir tu repositorio. La sección 1 del
   cuaderno dice cómo (*Contents: Read and write*, solo tu repositorio, vencimiento corto). No lo pegues
   en ningún archivo.
5. **Corré las celdas en orden** (unos 10 minutos la primera vez). En la sección 1 poné tu usuario y el
   nombre del repositorio; el token se pide al correr la celda y no queda en el cuaderno.
6. **Ciclo de trabajo.** Escribís `bucle` en `agente.py`, hacés commit y push desde tu máquina, y en
   Colab volvés a correr la celda de la sección 1 (hace `git pull`) y después `correr_todas.py` y
   `evaluar.py`.
7. **Guardá las trazas.** La sección 6 del cuaderno las sube a GitHub desde Colab (`git add`,
   `git commit`, `git pull --rebase`, `git push`). En tu máquina, `git pull` las trae.

## Puesta en marcha

### Local

Necesitás [uv](https://docs.astral.sh/uv/) y [Ollama](https://ollama.com/download).

```bash
uv sync
uv run datos/descargar.py          # baja los CSV y arma datos/worldcup.sqlite
uv run pytest                      # tiene que dar todo en verde
ollama pull qwen3:8b               # el modelo de referencia, con el tag explícito
```

La versión de Ollama del kit es la **0.40.10**. Con otra puede cambiar cómo se devuelven las llamadas
a herramientas y cuánto tarda cada una; si usás otra, decilo en tu informe.

### En Colab (la T4, el entorno de referencia)

Los tiempos que reportes se miden ahí. Los pasos están en «Primer día» (arriba) y en las secciones del
cuaderno [colab/arranque.ipynb](colab/arranque.ipynb).

El disco de Colab se borra cuando se desconecta la máquina (unos 90 minutos inactiva, 12 horas como
máximo). Tus trazas y resultados tienen que salir de ahí antes: la sección 6 del cuaderno los sube a tu
repositorio. `correr_todas.py --reanudar` retoma una corrida sin repetir las tareas ya hechas.

## Cómo se usa

```bash
# una pregunta suelta, con traza
uv run agente.py -p "¿Cuántos goles hizo Messi en el Mundial 2014?" --log trazas/prueba

# las 30 tareas públicas, un proceso por tarea
uv run correr_todas.py --corrida trazas/mi_corrida
uv run evaluar.py --corrida trazas/mi_corrida          # escribe también resultados/mi_corrida.csv

# la línea de base: el modelo sin herramientas
uv run libro_cerrado.py --corrida trazas/libro_cerrado
uv run evaluar.py --corrida trazas/libro_cerrado
```

`correr_todas.py` le agrega a cada pregunta el formato de respuesta de su `tipo` («Respondé solo con
el número», etc.) y espera que `agente.py` responda con `terminar(respuesta, motivo)`. Con
`respuesta = None` el agente dice que los datos no alcanzan.

Antes de implementar `bucle`, corré `correr_todas.py` y `evaluar.py`: el esqueleto termina con estado
`error` en cada tarea y da 0 aciertos. Es el punto de partida.

## Lo que tenés que saber

- **`num_ctx` va explícito en cada llamada.** Ollama usa 4.096 tokens por defecto en una T4 y, si el
  prompt no entra, recorta en silencio y el modelo contesta igual. `llm.chat` manda `num_ctx` y pide
  que falle en lugar de recortar; si falla, levanta `llm.ContextOverflow`. El endpoint `/v1` compatible
  con OpenAI no permite fijar `num_ctx`: usá la API nativa.
- **Las tareas públicas traen la respuesta.** Sirven para medir tu loop, no para copiarlas. En la
  presentación se te pide una tarea que no ensayaste.
- **Los modelos chicos a veces escriben la llamada a `terminar` como texto**, por ejemplo `terminar("12", "...")`.
  Ollama no la reconoce como una llamada, y tu loop se queda sin respuesta aunque el modelo la tenía.
  Qué hacer en ese caso lo decidís vos: aparece en las trazas como una respuesta del modelo sin llamadas.
- **Una traza inválida o ausente no suma aciertos.** `evaluar.py` valida cada traza con
  `trazas/esquema.py` antes de leerla.
- **Los nombres de jugadores pueden ser ambiguos.** `goles("Ronaldo")` devuelve candidatos con su `id`;
  repetir el nombre no desambigua, el `id` sí.
- **Ningún modelo corrige las respuestas.** `evaluar.py` las compara con la esperada mediante un
  programa, nunca con un modelo como juez.

## Datos y licencias

Los datos del Mundial son la *Fjelstul World Cup Database* (CC BY-SA 4.0). Las tareas derivadas de
ellos llevan la misma licencia. El código es MIT. Detalle en [LICENCIAS.md](LICENCIAS.md).
