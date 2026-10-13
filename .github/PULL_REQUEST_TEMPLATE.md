<!--
  Título del PR (obligatorio, Conventional Commits):
  type(scope): descripción corta

  Ejemplos:
  feat(worker): agregar clasificación de reseñas con LLM
  fix(api): corregir validación de fechas
  docs(contributing): actualizar flujo de trabajo
-->

## Issue

Closes #

## Resumen del cambio

<!-- Qué cambia y por qué. Modo imperativo, en español,
     sin mayúscula inicial y sin punto final. -->

## Evidencia de verificación

<!-- Comandos ejecutados desde la raíz y su resultado.
     Pegá salida de terminal, capturas o link al workflow de CI. -->

```bash

```

## Impacto y riesgos

<!-- Qué se ve afectado, qué queda fuera de alcance,
     y si hay rollback posible. Si no aplica, escribir "Ninguno". -->

## Checklist

### Estándar del equipo

- [ ] El PR cierra un issue aprobado con `Closes #ID`
- [ ] El título sigue Conventional Commits: `type(scope): descripción corta`
- [ ] La descripción está en español, modo imperativo, sin mayúscula inicial ni punto final
- [ ] La rama sigue el formato `<type>/<issue-id>-descripcion-corta`
- [ ] No hice `push` directo a `main`

### Verificación

- [ ] Ejecuté los comandos aplicables desde la raíz: `pnpm check`, `pnpm lint`, `pnpm test`, `pnpm build`
- [ ] Los tests nuevos, si los hay, pasan
- [ ] No rompí funcionalidad existente

### Seguridad e higiene

- [ ] No commiteé tokens, `.env`, `project_ref` ni otras credenciales
- [ ] No commiteé artefactos generados (`node_modules/`, `.next/`, `__pycache__/`, CSVs)
- [ ] Los finales de línea son LF (regla `.gitattributes`)
- [ ] Documentación actualizada si cambió el comportamiento
