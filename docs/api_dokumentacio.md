# API dokumentáció

Alap URL helyi futtatásnál: `http://localhost:8000`

## GET /health

Állapotellenőrzés. Visszaadja, hogy az API fut-e, van-e adatbázis, és elérhető-e az Ollama/Mistral.

Példa:

```bash
curl http://localhost:8000/health
```

## GET /grants

Visszaadja az összes feldolgozott felhívást.

```bash
curl http://localhost:8000/grants
```

## GET /grants/{call_code}

Egy konkrét felhívás lekérdezése felhíváskód alapján.

```bash
curl http://localhost:8000/grants/GINOP%20Plusz-1.2.1-21
```

## GET /search

Szűrés előleg, kockázati kategória, támogatástípus és konzorciumi lehetőség alapján.

```bash
curl "http://localhost:8000/search?risk_category=magas"
```

## GET /high-risk

Magas és kiemelt kockázatú felhívások lekérdezése.

```bash
curl http://localhost:8000/high-risk
```

## POST /classify

Tematikus kategorizálás. Alapértelmezetten offline kulcsszavas ZSC-helyettesítő logikát használ; `USE_HF_ZSC=1` esetén HuggingFace zero-shot pipeline is használható.

```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{"text":"KKV-k technológiai fejlesztését és eszközbeszerzését támogató felhívás."}'
```

## POST /intent

Felhasználói kérdés szándékának felismerése.

```bash
curl -X POST http://localhost:8000/intent \
  -H "Content-Type: application/json" \
  -d '{"text":"Mekkora az előleg és milyen kockázatok vannak?"}'
```

## POST /summarize

Mistral/Ollama alapú magyar összefoglaló készítése.

```bash
curl -X POST http://localhost:8000/summarize \
  -H "Content-Type: application/json" \
  -d '{"text":"A felhívás célja a mikro- és kisvállalkozások fejlesztése..."}'
```

## GET /monitoring/kpis

Monitoring KPI-k lekérdezése.

```bash
curl http://localhost:8000/monitoring/kpis
```

## Swagger

Böngészőben: `http://localhost:8000/docs`
