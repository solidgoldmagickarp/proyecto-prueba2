# Proyecto final — Construir y defender tu propio agente

**Inteligencia Artificial Generativa Avanzada y Sistemas Multi Agente · UTDT**

Grupos de hasta **4**. Enunciado publicado el **lunes 26/10/2026**, entrega el **domingo 29/11/2026**,
presentación oral en una fecha a definir, después de la última clase.

> Un agente se mide con su harness, sus trazas y una afirmación que se puede refutar con datos.
> Trabajamos con modelos abiertos sobre Ollama, Colab T4 o la máquina propia, sin APIs pagas.
>
> El **kit inicial** (herramientas, tareas públicas, evaluador y el esqueleto del agente) está en
> <https://github.com/solidgoldmagickarp/proyecto-final-ditella>. Para empezar, creá tu repositorio
> **privado** desde esa plantilla (*Use this template*); la sección 6 dice qué trae y el `README.md` del
> kit explica el primer día paso a paso.

---

## 1. De qué se trata

Cada grupo construye **un agente propio**: un programa que le cede al modelo la decisión del
próximo paso, le da herramientas sobre datos reales y se queda con todo lo demás (qué puede
elegir, cómo se ejecuta, cuándo se frena, qué vuelve a la ventana). Después lo **mide y lo defiende
en una presentación oral**.

El proyecto tiene cuatro bloques:

| Bloque | Qué hacés | Puntos |
|---|---|---|
| **1 · El loop** | Construís a mano el loop de un agente sobre los datos del Mundial, con herramientas, frenos y trazas | 20 |
| **2 · Tu agente** | Elegís un dominio, armás tus herramientas y tu conjunto de evaluación, y mostrás con mediciones que dos decisiones de diseño valieron la pena | 30 |
| **3 · Informe y registro de decisiones** | Una afirmación que se pueda refutar con datos, y una cuenta honesta de lo que pasó | 20 |
| **4 · Presentación oral** | Demo en vivo con la traza a la vista, y preguntas a cada integrante | 30 |

### Qué es nuevo y qué no

El Proyecto 2 (*Retrieval & Memory Lab*) ya cubrió RAG, memoria entre sesiones y el reparto de la
ventana de contexto. **Este proyecto no lo repite.** Podés usar recuperación o memoria como una
herramienta más de tu agente, pero no cuentan como la contribución del proyecto. Lo que se evalúa
es lo propio del agente:

- el diseño de las herramientas (pocas, ortogonales, bien descriptas) y el contrato con el modelo;
- el loop y sus frenos, y cómo falla el agente;
- negarse a responder cuando los datos no alcanzan, en lugar de inventar;
- decisiones de agente medidas: planificación, reflexión o verificación, varios agentes, guardrails
  o aprobación humana, qué herramientas cargar en cada paso;
- cómo se evalúa un agente: trazas, líneas de base, conclusiones que los datos sostienen.

### Cómo se evalúa

Como en el Proyecto 2: **cero puntos por tipear código**. Se evalúa qué decidiste construir, por
qué, y qué leíste en tus mediciones. Un grupo que hace menos, bien razonado y medido de verdad, saca
más que uno que hace todo a medias. Cada integrante tiene que poder explicar cualquier pieza del
sistema.

Les pedimos que el trabajo sea de todo el grupo. Si en las preguntas de la presentación resulta
evidente que algún integrante no participó o no entiende el proyecto, esa persona puede desaprobarlo,
aunque el resto del grupo lo haya hecho bien.

---

## 2. Cronograma

Hay **una sola entrega con nota**. Antes hay un único punto de control, sin nota.

| Hito | Contenido | Fecha |
|---|---|---|
| Publicación | Este enunciado y el kit inicial | lunes 26/10/2026 |
| Punto de control (sin nota) | Propuesta de dominio, una página (sección 5) | **domingo 15/11/2026** |
| **Entrega** | Repositorio, informe y registro de decisiones | **domingo 29/11/2026** |
| Presentación oral | Demo y defensa del grupo | a definir, después de la última clase |

La propuesta no se califica, pero hace falta que esté aprobada para usar un dominio propio: el
equipo docente la aprueba o la devuelve con cambios en la semana siguiente. **Podés entregarla
antes del 15/11**; se responde en orden de llegada. Sin propuesta aprobada, el grupo trabaja sobre
el Mundial con un conjunto de evaluación ampliado (sección 5).

**Ritmo sugerido**, sin entregas intermedias:

| Semana | Foco |
|---|---|
| 26/10 | Bloque 1: el loop sobre el Mundial |
| 2/11 | Bloque 1: frenos, trazas y evaluación; empezar a pensar el dominio |
| 9/11 | Propuesta de dominio; conjunto de evaluación del dominio |
| 16/11 | Bloque 2: tu agente y dos decisiones de diseño medidas |
| 23/11 | Mediciones, informe y presentación |

Antes de empezar, estimá cuánto tiempo y cuánto cómputo tiene tu grupo, y anotalo como primera
entrada de tu registro de decisiones (sección 8).

---

## 3. Reglas comunes

- **Grupos** de hasta 4 integrantes, los mismos para todo el proyecto.
- **Modelos abiertos solamente**, servidos por el grupo con Ollama. **Máximo 8B parámetros.** El
  modelo de referencia es `qwen3:8b`, con el tag fijado.
- **Nada de APIs pagas ni modelos comerciales dentro del agente**, tampoco como juez ni como
  respaldo. Los asistentes de código sí están permitidos (sección 9).
- **Los pesos no cambian.** No hay fine-tuning ni modelos más grandes: lo que se gana, se gana en
  el harness.
- **Versión de Ollama: 0.40.10**, la del kit. Con otra puede cambiar cómo se devuelven las llamadas a
  herramientas y cuánto tarda cada una; si usás otra, decilo en el informe.
- **API nativa de Ollama.** El endpoint `/v1` compatible con OpenAI no permite fijar `num_ctx` por
  llamada, y Ollama usa 4.096 tokens por defecto en una T4. Mandá `num_ctx` explícito en cada
  llamada, y registralo (sección 7).
- **Decodificación fija**: temperatura 0, semilla fija y modo de razonamiento (`think`) apagado.
  Podés cambiarlo si lo declarás y lo medís; lo que no se puede es no decirlo.
- **Hardware de referencia: Colab T4.** Los tiempos que reportes para comparar se miden ahí.
  Desarrollar en la máquina propia está bien.
- **Trazas obligatorias** con el esquema común (sección 7). Sin trazas no hay evidencia, y sin
  evidencia la afirmación no cuenta.
- **Datos:** públicos, con licencia que permita el uso, versión fijada. Nada de datos personales,
  privados ni de clientes. Los datos del Mundial son CC BY-SA 4.0: lo que derives de ellos lleva la
  misma licencia.
- **Registro de decisiones** (`decision_log.md`) desde el primer día.
- **Asistentes de código permitidos y declarados** (sección 9).

---

## 4. Bloque 1 — El loop (20 puntos)

**Objetivo:** construir a mano el loop de un agente y descubrir dónde se rompe.

### Qué se construye

Un programa `agente.py` que recibe una pregunta y la responde llamando herramientas sobre los datos
del Mundial (la *Fjelstul World Cup Database*, CC BY-SA 4.0, el corpus de la Clase 11):

```
uv run agente.py -p "¿Qué edad tenía el goleador del Mundial 1978 el día de la final?" --log trazas/mi_corrida
```

**Sin frameworks de agentes en este bloque.** Solo el cliente de Ollama y la biblioteca estándar.
LangChain y LangGraph pueden entrar en el Bloque 2.

El loop tiene que resolver, como mínimo:

1. **El ciclo:** llamar al modelo, ejecutar cada llamada a herramienta, devolver **un resultado por
   llamada** y repetir hasta que el modelo termine.
2. **El contrato de herramientas:** cada herramienta con su esquema JSON. El kit trae seis
   herramientas de partida (`herramientas/mundial.py`: `buscar_torneos`, `goleadores`,
   `buscar_jugador`, `goles`, `partidos`, `calcular`) y `terminar`. Podés cambiarlas, agregar o quitar, pero lo justificás.
3. **Salida mal formada:** JSON roto, una herramienta que no existe, argumentos del tipo
   equivocado. El agente no se cae: le devuelve el error al modelo y sigue.
4. **Herramientas que fallan:** excepciones, resultados vacíos, timeouts.
5. **Contexto:** los resultados largos se truncan o resumen antes de volver al modelo, con un
   `num_ctx` fijo.
6. **Reintentos** ante errores del servidor del modelo, con límite.
7. **Parada:** un tope de pasos y de tokens, y una herramienta `terminar(respuesta, motivo)`. Si la
   pregunta no se puede responder con los datos, el agente lo dice con `respuesta = null` y un
   motivo, en vez de inventar.
8. **Trazas** en JSONL con el esquema de la sección 7 cuando se pasa `--log`.

### Cómo se evalúa el loop

- **Tareas públicas** (`tareas/mundial_publicas.json`): 30 preguntas con respuesta exacta, en tres
  niveles de dificultad (13 fáciles, 10 medias, 7 difíciles). **Cuatro son imposibles a propósito**
  (los datos no alcanzan) y están marcadas con `respondible: false`. `tareas/verificadores.py`
  recalcula cada respuesta con SQL, sin pasar por el modelo.
- **Script de evaluación** (`uv run evaluar.py --corrida trazas/<corrida>`): compara las respuestas
  con las esperadas y suma tokens, costo, llamadas al modelo y tiempo a partir de las trazas.
  `uv run correr_todas.py --corrida trazas/<corrida>` corre las 30 tareas, una por proceso.
- **Libro cerrado** (`uv run libro_cerrado.py --corrida trazas/<corrida>`): las mismas preguntas
  sin herramientas. El modelo sabe de fútbol; lo que compra el agente es la respuesta correcta,
  verificable y con un "los datos no alcanzan" honesto. Medí eso, no solo si acierta.

Una pregunta imposible cuenta como acierto solo si el agente se niega a responderla. Inventar una
respuesta cuenta como error, igual que no responder una pregunta posible.

### Qué se mira en este bloque

| Componente | Puntos |
|---|---|
| Resultados sobre las tareas públicas, con trazas válidas | 8 |
| Decisiones de diseño del loop que no salen de este enunciado, cada una con su motivo | 6 |
| Un arreglo explicado: una tarea que fallaba, qué falló primero según la traza, qué cambiaron en el harness y por qué eso la arregló. Incluye una tarea que el agente se niega a responder, con la traza que muestra qué dato falta | 6 |

---

## 5. Bloque 2 — Tu agente (30 puntos)

**Objetivo:** un agente para un problema que elegís, con una evaluación que sostenga lo que
afirmás.

### Propuesta de dominio (punto de control, domingo 15/11, sin nota)

Una página (`propuesta.md`), que el equipo docente aprueba o devuelve con cambios:

1. **Problema:** quién tiene la necesidad y qué pregunta hoy no se puede responder bien.
2. **Datos:** fuente, licencia, tamaño y formato. Versión fijada.
3. **Herramientas:** al menos cuatro, con su firma. Al menos un tercio de las tareas tiene que
   necesitar dos llamadas encadenadas o más (si una sola consulta alcanza, no hace falta un agente).
4. **Dos decisiones de agente** que vas a medir (sección 5, «Qué construís»), y qué falla de tu
   agente espera arreglar cada una.
5. **Líneas de base:** al menos **libro cerrado** (el modelo sin herramientas) y **camino fijo**
   (un pipeline escrito de antemano, sin loop), con una nota de dónde fallan.
6. **Prueba de factibilidad:** cinco tareas del dominio probadas a mano con `qwen3:8b`, con lo que
   salió.
7. **Presupuesto y plan:** cuántas llamadas al modelo cuesta cada experimento, y qué recortarías
   primero.
8. **Afirmación tentativa:** qué esperan poder demostrar al final.

Quien no quiera elegir dominio, o no tenga la propuesta aprobada, trabaja sobre el Mundial: arma su
propio conjunto de evaluación con las mismas reglas de abajo y mide sus dos decisiones de diseño
sobre él.

### Qué construís

- **Un agente** con tu loop del Bloque 1 (o una versión en LangGraph, si tus decisiones lo piden),
  tus herramientas y tus trazas.
- **Dos decisiones de agente**, a elegir, **cada una medida contra el agente sin ella**:
  - planificación (*plan-and-execute*, ReWOO) o un workflow fijo para lo fácil;
  - reflexión o un verificador de la respuesta;
  - varios agentes con roles acotados (supervisor-trabajador, crítico);
  - guardrails o aprobación humana antes de una acción;
  - qué herramientas se cargan en cada paso, o servir herramientas por MCP;
  - otra que propongas y el equipo docente apruebe.

  La recuperación y la memoria pueden ser herramientas de tu agente, pero no cuentan como una de
  las dos.
- **Opcional, como meta ambiciosa de tu informe:** bajar costo o tiempo sin perder aciertos
  (el costo es la suma de tokens, entrada más salida, de cada llamada que cuenta el servidor, con
  peso 1,0 / 0,5 / 0,2 para `qwen3:8b` / `qwen3:4b-instruct` / `qwen3:1.7b` si usás los tres niveles);
  correr con un modelo chico (`qwen3:4b-instruct` o `qwen3:1.7b`); ejecutar herramientas en paralelo;
  caché de resultados. Ojo con el tag: `qwen3:4b` a secas escribe su razonamiento en la respuesta aunque
  apagues `think`, y se queda sin tokens antes de llamar a una herramienta. Los modelos chicos
  también llaman herramientas, pero fallan distinto que el de 8B (por ejemplo, a veces escriben la
  llamada a `terminar` como texto): si lo intentás, mirá primero con trazas qué hacen.

### El conjunto de evaluación

- **Al menos 15 tareas**, en un archivo con el mismo formato que `tareas/mundial_publicas.json`:

  ```json
  {
    "id": "dom-001",
    "pregunta": "...",
    "respuesta": 1978,
    "tipo": "numero",
    "tolerancia": 0,
    "dificultad": "media",
    "respondible": true
  }
  ```

  `tipo` es `numero`, `texto`, `lista` o `fecha`. `dificultad` es `facil`, `media` o `dificil`.
  Con `respondible: false`, `respuesta` es `null`.
- **Tres niveles de dificultad**, con al menos 3 tareas difíciles (tres llamadas encadenadas o
  más) y **al menos 3 imposibles** con los datos disponibles, pero verosímiles.
- **Corrección automática.** Las respuestas se comparan con un programa, no a ojo. Si una
  respuesta en texto libre no se puede comparar así, reformulá la tarea o usá un **juez local de
  hasta 8B, auditado** como en la Etapa 7a del Proyecto 2, y decilo en el informe.
- **Respuestas verificadas** contra los datos con un script incluido en el repositorio, no con el
  modelo.
- **Congelado antes de medir.** El conjunto se congela antes de que exista ningún resultado.
  Cualquier edición posterior es una entrada del registro de decisiones.
- **Si un modelo redactó tareas**, decís cuáles y cómo las verificó una persona.

### Qué se mira en este bloque

| Componente | Puntos |
|---|---|
| Problema y datos: una necesidad real, herramientas bien elegidas, licencia y versión fijadas | 6 |
| Conjunto de evaluación y líneas de base (libro cerrado y camino fijo) | 8 |
| Dos decisiones de agente, cada una con su medición de antes y de después, y una cota de ruido | 10 |
| Ejecución técnica: un harness que no dependa de una máquina, una tarea o una corrida | 6 |

---

## 6. Qué entrega el equipo docente

El kit inicial (<https://github.com/solidgoldmagickarp/proyecto-final-ditella>, MIT para el código y
CC BY-SA 4.0 para los datos) trae:

- `agente.py`: el esqueleto del agente. Lee y valida `config.toml`, abre la traza y escribe
  `corrida_inicio` y `corrida_fin`. **La función `bucle` está sin implementar: es el Bloque 1.**
- `llm.py`: una llamada a Ollama por la API nativa. Manda `num_ctx` siempre y puede restringir la
  salida a un esquema JSON. No reintenta: eso es tuyo.
- `herramientas/mundial.py`: las seis herramientas del Mundial sobre una base SQLite, sus esquemas
  JSON y `terminar`. `datos/descargar.py` baja los datos (versión fijada) y arma la base.
- `tareas/`: las 30 tareas públicas y los verificadores de sus respuestas.
- `correr_todas.py`, `evaluar.py`, `libro_cerrado.py`: correr las tareas, puntuarlas desde las
  trazas y medir la línea de base sin herramientas.
- `trazas/esquema.py` y `trazas/registro.py`: el validador del esquema de la sección 7 y el escritor
  de trazas.
- `colab/arranque.ipynb` y el `README.md` del kit: la puesta en marcha local y en Colab.

El kit no trae memoria, recuperación ni reparto de la ventana: eso fue el Proyecto 2.

---

## 7. Esquema de trazas

Una línea JSON por evento en `trazas/<corrida>/<tarea>.jsonl`. Campos comunes: `evento`, `ts` (ISO 8601),
`corrida`, `tarea`.

| Evento | Campos propios |
|---|---|
| `corrida_inicio` | `modelo`, `config` (objeto con la configuración del harness, incluidos `num_ctx`, temperatura, semilla y `think`) |
| `llamada_modelo` | `paso`, `modelo`, `num_ctx`, `tokens_entrada`, `tokens_salida`, `duracion_ms` |
| `reintento_modelo` | `paso`, `motivo`, `intento` |
| `llamada_herramienta` | `paso`, `id`, `nombre`, `argumentos` |
| `resultado_herramienta` | `paso`, `id`, `ok`, `truncado`, `caracteres`, `duracion_ms` |
| `corrida_fin` | `estado` (`respondida`, `negada`, `tope_pasos`, `tope_tokens`, `error`), `respuesta`, `pasos` |

Si tu agente tiene varios agentes, todo evento suma `agente` (un id) y `padre` (`null` para el
principal), y el costo y el tiempo cuentan **todas** las llamadas.

`id` empareja cada resultado con su llamada. Ollama lo entrega con cada llamada a herramienta; si
alguna vez falta, generalo vos: tiene que ser único dentro de la traza.

Se pueden agregar campos y eventos, pero no cambiar ni sacar los de la tabla: `evaluar.py` los lee
y valida cada traza con `trazas/esquema.py` antes de puntuarla. Una traza inválida no suma aciertos.

---

## 8. Registro de decisiones

`decision_log.md`, desde el primer día:

- el presupuesto que estimaste al principio y tu plan;
- qué probaste;
- qué recortaste y por qué (tiempo, VRAM, llamadas, beneficio conceptual).

Terminar en un lugar distinto de tu plan está bien y es esperable: decilo, y decí qué te hizo
cambiar de opinión. Cualquier edición del conjunto de evaluación congelado es una entrada.

---

## 9. Cómo trabajar con un asistente de código

El uso de asistentes de código está permitido y se espera. Estas pautas salen de un análisis de
reflexiones de estudiantes sobre su trabajo con un agente de código (ver Referencias):

1. **Definir qué cuenta como terminado.** Pedirle al asistente que separe qué intentó, qué corrió
   de verdad y qué queda sin verificar. Ojo cuando cambia la prueba para poder pasarla.
2. **Probar estados intermedios.** Un test que reproduce una corrida grabada puede esconder
   errores que solo aparecen en vivo: timeouts, cancelaciones, fallos al principio.
3. **Revisar el diff completo**, no solo lo que el asistente dice que cambió.
4. **Pedir interpretaciones antes de implementar.** «Costo total» o «tarea resuelta» pueden querer
   decir varias cosas. Escribir los requisitos como condiciones verificables.
5. **Experimentos chicos antes de decidir** un diseño cuyo comportamiento no conocen.
6. **Repartir archivos antes de trabajar en paralelo.** Dos agentes en el mismo directorio se pisan.

**Registros de desarrollo:** en `registros_desarrollo/` van las sesiones exportadas del asistente
que usaron, o un registro con los pedidos principales y qué se aceptó o se descartó de cada uno.

---

## 10. Informe, repositorio y presentación

### Informe (20 puntos, con el registro de decisiones)

`informe_final.md`, máximo cinco páginas más apéndices, con este orden:

1. **Problema y brecha:** el caso de uso, las líneas de base y qué no resuelven.
2. **Afirmación:** una frase que se pueda refutar con datos. Por ejemplo: «con una verificación
   antes de `terminar`, el agente baja de 6 a 2 las respuestas inventadas sobre las tareas
   imposibles, sin perder aciertos en las posibles».
3. **Diseño:** el harness final, con un diagrama, las herramientas y las decisiones que lo
   distinguen.
4. **Evaluación:** el conjunto, las líneas de base, las comparaciones controladas, la cota de ruido.
5. **Resultados**, incluidas las pérdidas y lo que no funcionó.
6. **Limitaciones:** en qué condiciones deja de valer la afirmación.
7. **Qué alcanzaron:** el objetivo mínimo, el esperado y el ambicioso de la propuesta, y cuál de
   los tres cumplieron.
8. **Uso de IA:** qué hizo el asistente y qué hizo el grupo.

Se evalúa en cuatro dimensiones de igual peso:

| Dimensión | Qué se mira |
|---|---|
| Problema y motivación | Pregunta clara, líneas de base probadas de verdad, brecha que se puede medir |
| Ejecución técnica | Harness sólido, que no dependa de una máquina, una tarea o una corrida |
| Evaluación | Líneas de base adecuadas, comparaciones controladas, conclusiones que los datos sostienen |
| Reporte | Afirmaciones claras, evidencia reproducible, cuenta honesta de limitaciones y resultados negativos |

Una idea que no funcionó puede llevarse casi todo el puntaje si el informe explica la distancia
entre lo esperado y lo medido.

### Repositorio

Tiene que permitir que otra persona reproduzca el resultado principal:

Es el repositorio que sale del kit, con lo tuyo agregado:

```
proyecto/
├── README.md              # instalación (uv), cómo correr cada bloque, versiones y hardware
├── agente.py              # tu loop del Bloque 1
├── config.toml
├── harness/               # opcional: el código del agente, si lo separás de agente.py
├── herramientas/          # las del Mundial y las de tu dominio
├── datos/                 # cómo se bajan los datos, con la versión fijada
├── tareas/                # tareas del Mundial y conjunto de evaluación del dominio
├── trazas/                # esquema.py y registro.py del kit, y una carpeta por corrida reportada
├── resultados/            # mediciones crudas (CSV) y scripts que generan cada gráfico
├── registros_desarrollo/
├── propuesta.md
├── decision_log.md
└── informe_final.md
```

Las carpetas de trazas de las corridas que reportás tienen que estar en el repositorio que entregás.

Canal de entrega: a confirmar al publicar.

### Presentación oral (30 puntos)

- **Doce minutos por grupo:** el problema, una demo en vivo con la traza a la vista, la medición
  central y la afirmación. El equipo docente elige una tarea del conjunto del grupo y suma una
  pregunta nueva, para ver el agente fuera de lo que ensayó.
- **Preguntas a integrantes elegidos al azar** sobre cualquier parte del sistema. Acá se verifica
  la comprensión conceptual: por qué está cada pieza y qué problema resuelve. Esta parte es
  individual: si un integrante no puede responder, su nota se ve afectada, y puede llegar a
  desaprobar el proyecto (sección 1).
- Fecha a definir, después de la última clase.

| Componente | Puntos |
|---|---|
| Claridad del problema y de la afirmación | 8 |
| Demo y evidencia | 10 |
| Respuestas a las preguntas | 12 |

---

## 11. Resumen de la nota

Todo se califica sobre la entrega del 29/11 y la presentación.

| Componente | Puntos |
|---|---|
| Bloque 1 · El loop | 20 |
| Bloque 2 · Tu agente | 30 |
| Informe y registro de decisiones | 20 |
| Presentación oral | 30 |
| **Total** | **100** |

Para aprobar el proyecto hace falta llegar a 60 sobre 100, como en los otros proyectos de la
materia.

---

## Referencias

- *Lessons for agentic coding from student projects*:
  <https://blog.cs2680.com/2026/assignment1/agentic-coding-lessons/>.
- J. C. Fjelstul, *The Fjelstul World Cup Database*, CC BY-SA 4.0:
  <https://github.com/jfjelstul/worldcup>.
