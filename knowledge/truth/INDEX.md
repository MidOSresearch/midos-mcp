# 📐 Truth INDEX — Verdades Empíricas Validadas

> **Capa**: 3 de 5 | **Criterio**: Sobrevivió contraste empírico, funciona en producción

## Criterio de Promoción (→ desde Skill/Knowledge)

Una verdad se promueve cuando cumple **los 3**:

1. **POR QUÉ**: Tiene causa documentada (no solo "qué" sino "por qué funciona")
2. **PARA QUÉ**: Tiene propósito claro (qué problema resuelve, en qué contexto)
3. **CONTRASTE**: Fue comparada contra el corpus y sobrevivió (no contradice, o si contradice, tiene evidencia superior)

## Criterio de Degradación (→ a Chunk o Descarte)

Una verdad **baja** cuando:

- Nueva evidencia la contradice con datos superiores
- El stack/contexto al que aplica ya no existe
- No tiene registro de uso en 90 días (nadie la consulta = no es útil)

> La verdad que nadie usa no es verdad — es trivia.

## Criterio de Promoción (→ a EUREKA)

Una verdad **sube** cuando demuestra mejora Kaizen/ROI medible. Ver [EUREKA/INDEX.md](../EUREKA/INDEX.md).

---

## Truth Patches (TP-XXX)

| TP-ID  | Verdad                                       | Por qué                                                         | Archivo                                                                           |
| ------ | -------------------------------------------- | --------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| TP-001 | Validar tokens antes de enviar prompt        | Truncamiento silencioso rompe la cadena                         | [EUREKA_CONTEXT_WINDOW_2026](../archive/deprecated_2026/truth_superseded_by_eureka/EUREKA_CONTEXT_WINDOW_2026.md) _(archived)_ |
| TP-002 | Comprimir antes de truncar                   | Truncar destruye contenido, comprimir lo preserva               | [EUREKA_PROMPT_COMPRESSION_2026](../EUREKA/EUREKA_PROMPT_COMPRESSION_2026.md)     |