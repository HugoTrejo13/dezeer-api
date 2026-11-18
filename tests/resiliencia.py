"""Pruebas de resiliencia de Onda: comprueba que la app responde bien, que controla los errores
y que aguanta peticiones simultáneas.

Uso:
  .venv/bin/python tests/resiliencia.py URL               app normal
  .venv/bin/python tests/resiliencia.py URL --falla       con Deezer caído (deploy.sh -var deezer_url=...)
  .venv/bin/python tests/resiliencia.py URL --carga 50    cambia las peticiones simultáneas (30 por defecto)
"""

import argparse
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

parser = argparse.ArgumentParser(description="Pruebas de resiliencia de Onda")
parser.add_argument("url", help="por ejemplo http://localhost:8000 o la Function URL")
parser.add_argument("--falla", action="store_true", help="espera que Deezer esté caído")
parser.add_argument("--carga", type=int, default=30, help="peticiones simultáneas")
args = parser.parse_args()

client = httpx.Client(base_url=args.url.rstrip("/"), timeout=30)
results = []


def request(path: str) -> tuple[int | str, float]:
    start = time.perf_counter()
    try:
        status = client.get(path).status_code
    except httpx.HTTPError as exc:
        status = type(exc).__name__
    return status, (time.perf_counter() - start) * 1000


def check(scenario: str, path: str, *expected: int) -> None:
    status, ms = request(path)
    ok = status in expected
    results.append((scenario, path, "/".join(map(str, expected)), str(status), f"{ms:.0f} ms", ok))


def load(path: str, n: int) -> None:
    with ThreadPoolExecutor(max_workers=n) as pool:
        replies = list(pool.map(lambda _: request(path), range(n)))
    statuses = [s for s, _ in replies]
    times = sorted(ms for _, ms in replies)
    p95 = statistics.quantiles(times, n=20)[18] if n > 1 else times[0]
    summary = ", ".join(f"{s}×{statuses.count(s)}" for s in sorted(set(statuses), key=str))
    ok = all(s in (200, 429) for s in statuses)  # 429 = Lambda limita la carga en vez de caerse
    results.append((f"{n} peticiones simultáneas", path, "200/429", summary,
                    f"p50 {statistics.median(times):.0f} / p95 {p95:.0f} ms", ok))


unique = f"prueba-{int(time.time())}"  # búsqueda que nunca está en el caché

if not args.falla:
    check("Página principal", "/", 200)
    check("Primera petición (puede ser arranque en frío)", "/api/home", 200)
    check("Misma petición en caliente", "/api/home", 200)
    check("Búsqueda", "/api/search?q=queen", 200)
    check("Artista", "/api/artist/27", 200)
    check("Álbum", "/api/album/302127", 200)
    check("Audio: redirige a una URL fresca", "/api/preview/3135556", 307)
    check("Búsqueda vacía", "/api/search?q=", 422)
    check("Id que no es número", "/api/artist/abc", 422)
    check("Artista que no existe", "/api/artist/999999999", 404)
    load("/api/home", args.carga)
else:
    check("La página sigue arriba sin Deezer", "/", 200)
    check("Inicio: copia guardada o error controlado", "/api/home", 200, 502)
    check("Búsqueda nueva: error controlado", f"/api/search?q={unique}", 502)
    check("La validación sigue funcionando", "/api/search?q=", 422)
    for i in range(5):  # 5 errores en 5 min disparan la alarma onda-errores
        check(f"Error para la alarma {i + 1}/5", f"/api/search?q={unique}-{i}", 502)

widths = [max(len(str(row[i])) for row in results) for i in range(5)]
header = ("Escenario", "Ruta", "Esperado", "Obtenido", "Tiempo")
widths = [max(w, len(h)) for w, h in zip(widths, header)]
print("   " + "  ".join(h.ljust(w) for h, w in zip(header, widths)))
for *cols, ok in results:
    print(("✓  " if ok else "✗  ") + "  ".join(str(c).ljust(w) for c, w in zip(cols, widths)))

failed = sum(not ok for *_, ok in results)
print(f"\n{len(results) - failed}/{len(results)} pruebas correctas")
raise SystemExit(1 if failed else 0)
