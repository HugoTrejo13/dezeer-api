import os
import time

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from mangum import Mangum

app = FastAPI(title="Onda")
deezer = httpx.Client(
    base_url=os.getenv("DEEZER_URL", "https://api.deezer.com"),  # cambiarla simula que Deezer se cae
    timeout=10,
    transport=httpx.HTTPTransport(retries=2),  # reintenta si falla la conexión
)

# Copias de las respuestas de Deezer; viven mientras la instancia de Lambda siga activa
cache: dict[str, tuple[float, dict]] = {}
FRESH = 300  # segundos que una copia se usa sin volver a preguntar a Deezer
BUSY = {4, 700}  # QUOTA y SERVICE_BUSY en la documentación de Deezer


@app.exception_handler(httpx.HTTPError)
def deezer_down(request: Request, exc: httpx.HTTPError):
    return JSONResponse({"detail": "No se pudo conectar con Deezer"}, 502)


def get(path: str, **params) -> dict:
    key = f"{path}?{sorted(params.items())}"
    saved = cache.get(key)
    if saved and time.time() - saved[0] < FRESH:
        return saved[1]
    try:
        data = deezer.get(path, params=params).raise_for_status().json()
        if data.get("error", {}).get("code") in BUSY:
            raise httpx.HTTPError(data["error"].get("message", "Deezer saturado"))
    except httpx.HTTPError as exc:
        if not saved:
            raise
        print(f"Deezer falló ({exc}); se usa la copia guardada de {key}")
        return saved[1]
    if error := data.get("error"):
        raise HTTPException(404 if error.get("code") == 800 else 502, error.get("message"))
    cache.pop(key, None)
    if len(cache) >= 200:
        cache.pop(next(iter(cache)))  # se va la copia más vieja
    cache[key] = (time.time(), data)
    return data


def tracks(items: list[dict]) -> list[dict]:
    return [
        {
            "id": t["id"],
            "title": t["title"],
            "artist": t["artist"]["name"],
            "artist_id": t["artist"]["id"],
            "album": t["album"]["title"],
            "album_id": t["album"]["id"],
            "cover": t["album"]["cover_medium"],
            "duration": t["duration"],
        }
        for t in items
        if t.get("preview")
    ]


def artists(items: list[dict]) -> list[dict]:
    return [{"id": a["id"], "title": a["name"], "cover": a["picture_medium"]} for a in items]


def albums(items: list[dict]) -> list[dict]:
    return [{"id": a["id"], "title": a["title"], "cover": a["cover_medium"]} for a in items]


@app.get("/api/home")
def home():
    chart = get("/chart", limit=12)
    return {
        "tracks": tracks(chart["tracks"]["data"]),
        "albums": albums(chart["albums"]["data"]),
        "artists": artists(chart["artists"]["data"]),
    }


@app.get("/api/search")
def search(q: str = Query(min_length=1)):
    return {
        "tracks": tracks(get("/search", q=q, limit=20)["data"]),
        "artists": artists(get("/search/artist", q=q, limit=6)["data"]),
    }


@app.get("/api/artist/{id}")
def artist(id: int):
    a = get(f"/artist/{id}")
    return {
        "title": a["name"],
        "cover": a["picture_big"],
        "fans": a["nb_fan"],
        "tracks": tracks(get(f"/artist/{id}/top", limit=20)["data"]),
        "albums": albums(get(f"/artist/{id}/albums", limit=12)["data"]),
    }


@app.get("/api/album/{id}")
def album(id: int):
    a = get(f"/album/{id}")
    return {
        "title": a["title"],
        "cover": a["cover_big"],
        "artist": a["artist"]["name"],
        "artist_id": a["artist"]["id"],
        "tracks": tracks(a["tracks"]["data"]),
    }


@app.get("/api/preview/{id}")
def preview(id: int):
    url = get(f"/track/{id}").get("preview")
    if not url:
        raise HTTPException(404, "Esta canción no tiene vista previa")
    return RedirectResponse(url)


app.mount("/", StaticFiles(directory="static", html=True))
handler = Mangum(app, lifespan="off")
