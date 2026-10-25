# Licencias

## Datos: The Fjelstul World Cup Database

- Autor: Joshua C. Fjelstul, Ph.D. © 2023 Joshua C. Fjelstul, Ph.D.
- Repositorio: <https://www.github.com/jfjelstul/worldcup>, commit
  `35a8667f518b07469182ae16d35574dd0e7a00fb` (los `sha256` de cada archivo están en
  `datos/MANIFEST.json`).
- Licencia: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/legalcode).
- Modificaciones: `datos/descargar.py` convierte los CSV de `data-csv/` en una base SQLite
  (`datos/worldcup.sqlite`, que no se versiona). Los valores se conservan tal cual, incluidos los
  marcadores `not applicable` y `not available`; solo las columnas que son enteras en todas las filas se
  declaran `INTEGER`.

## Material derivado de los datos

`tareas/mundial_publicas.json` y `tareas/verificadores.py` contienen preguntas y respuestas calculadas
a partir de esos datos. Son una obra derivada y se distribuyen bajo **CC BY-SA 4.0**, con la atribución
de arriba. Las tareas que armes con datos de este corpus llevan la misma licencia (*share-alike*).

## Código

El resto del código está bajo licencia MIT: ver [LICENSE](LICENSE).
