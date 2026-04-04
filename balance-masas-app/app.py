"""Entrypoint local para la app FastAPI."""

from __future__ import annotations

import uvicorn


def main() -> None:
    """Levanta la API FastAPI y sirve el frontend React compilado."""
    uvicorn.run("backend.api.main:app", host="0.0.0.0", port=8050, reload=True)


if __name__ == "__main__":
    main()
