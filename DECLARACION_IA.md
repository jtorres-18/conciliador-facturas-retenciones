# Declaración sobre el uso de inteligencia artificial generativa

> **BORRADOR: revisar antes de entregar.** Esta declaración describe cómo se construyó este repositorio con Claude. Debe quedar ajustada a lo que realmente hizo la persona que entrega (qué revisó, qué modificó, qué decidió).

**Sí se utilizó IA generativa.** Herramienta: **Claude (Anthropic)**, a través de Claude Code.

| Parte de la solución | Uso de la IA | Propósito |
|---|---|---|
| Análisis del caso | Explicación del negocio contable y tributario (IVA, retención, partida doble) y revisión de los CSV de ejemplo | Comprender el problema y detectar los casos que contienen los datos |
| Reglas de negocio (`backend/app/conciliador.py`) | Propuesta y escritura del código | Implementar las reglas del enunciado más algunas adicionales |
| API (`backend/app/main.py`) | Escritura del código | Exponer el servicio REST con manejo de errores |
| Pruebas del backend (`backend/tests/`) | Escritura del código | Verificar reglas y errores |
| Frontend Angular (`frontend/src/app/`) | Generación del proyecto con Angular CLI y escritura de componentes, servicio, estilos y pruebas | Pantalla de carga, resumen, tabla con filtro y mensajes de carga/error |
| `README.md` | Redacción | Documentar instalación, reglas, supuestos y limitaciones |
| `Presentacion_Conciliador.pptx` | Diseño y generación de las 5 diapositivas y de las notas del orador | Presentar el prototipo al equipo funcional |

**Verificación realizada:** se ejecutaron las pruebas automáticas del backend (31) y del frontend (4), y se probó el flujo completo en el navegador con los archivos de ejemplo, contrastando el resultado con una revisión independiente de los datos.

**Decisiones propias de quien entrega:** *(completar: por ejemplo, el tratamiento de las líneas contables en 0 como advertencia, elegido entre las opciones propuestas).*

**Revisión humana:** *(completar: qué partes del código se leyeron, se probaron o se modificaron a mano).*
