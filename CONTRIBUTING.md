# Guía de contribución — Mirror

## Flujo de trabajo

```
main  ←── PR con review ←── dev  ←── PR ←── feat/mi-feature
```

1. **Siempre parte de `dev`** para crear tu rama
2. Trabaja en tu rama con commits descriptivos
3. Abre un PR hacia `dev` cuando termines
4. Una vez que `dev` está estable, se abre un PR de `dev` → `main`

> **Nunca hagas push directo a `main` ni a `dev`.** Ambas ramas están protegidas.

---

## Naming de ramas

| Prefijo | Cuándo usarlo |
|---|---|
| `feat/` | Nueva funcionalidad |
| `fix/` | Corrección de bug |
| `chore/` | Mantenimiento, dependencias, config |
| `docs/` | Cambios solo en documentación |
| `refactor/` | Refactorización sin cambio de comportamiento |
| `hotfix/` | Corrección urgente que va directo a `main` |

**Formato:** `<tipo>/<descripcion-corta-en-kebab-case>`

```bash
git checkout dev
git pull origin dev
git checkout -b feat/emotion-chart
```

---

## Convención de commits

Seguimos [Conventional Commits](https://www.conventionalcommits.org/) de forma simplificada:

```
<tipo>(<scope opcional>): <descripción en imperativo>
```

**Ejemplos:**
```
feat(frontend): add emotion history chart
fix(whisper): handle empty audio file gracefully
chore: update FastAPI to 0.116.0
docs: add setup instructions for Windows
refactor(llm_service): extract prompt builder to separate function
```

**Tipos válidos:** `feat`, `fix`, `chore`, `docs`, `refactor`, `hotfix`, `test`

---

## Cómo abrir un Pull Request

1. Empuja tu rama: `git push origin feat/mi-feature`
2. Ve a GitHub → se mostrará el botón **"Compare & pull request"**
3. La plantilla de PR se cargará automáticamente — **llénala completa**
4. Asigna reviewers si el PR va a `main`
5. Los PRs hacia `dev` no requieren review, pero el Action de naming debe pasar

---

## Lo que NO debe ir en el repo

- `.env` con credenciales o rutas locales
- Archivos `data/chroma_db/`, `data/audio/`, `data/models/*.bin`
- El binario compilado de whisper.cpp
- Archivos de sistema: `.DS_Store`, `Thumbs.db`

Todo esto ya está en `.gitignore`.
