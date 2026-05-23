# Beadandó dokumentáció – Pályázati felhívások kockázati elemző MLOps pipeline

## 1. Projekt bemutatása

A projekt célja egy olyan MLOps szemléletű, lokálisan futtatható elemző rendszer kialakítása, amely pályázati felhívások PDF dokumentumaiból strukturált adatokat nyer ki, tematikusan kategorizálja a felhívásokat, felismeri a felhasználói szándékot, Mistral/Ollama alapú magyar nyelvű LLM összefoglalót készít, majd egyszerű kockázati pontszámot és kockázati kategóriát rendel a felhívásokhoz.

A megoldás munkahelyi problémafelvetésre épül: a támogatási konstrukciók nagy száma és eltérő szabályozási logikája miatt az ellenőrzési szempontból releváns mezők azonosítása időigényes, ezért indokolt egy előszűrő és döntéstámogató prototípus kialakítása.

## 2. Architektúra

A rendszer fő komponensei:

1. PDF forrásadatok: `data/pdfs/`
2. Feldolgozó pipeline: `app/ingest.py`
3. Mezőkinyerés: `app/extractor.py`
4. ZSC kategorizáló: `app/zsc_classifier.py`
5. Intent recognizer: `app/intent_model.py`
6. LLM összefoglaló: `app/llm_summary.py`
7. Kockázati pontszámítás: `app/risk_model.py`
8. Adattárolás: SQLite `grants.db`
9. API: FastAPI `app/api.py`
10. Felhasználói felület: Streamlit `app/streamlit_app.py`
11. Monitoring: `app/monitoring.py`, `logs/pipeline.log`

A rendszer zárt/lokális környezetre készült. Az LLM hívás az Ollama szerveren keresztül történik, alapértelmezett modell: `mistral`.

## 3. Implementáció bemutatása

A pipeline a PDF-ekből szöveget nyer ki, majd reguláris kifejezésekkel és kulcsszavas szabályokkal kitölti a fő mezőket: felhíváskód, cím, keretösszeg, minimum és maximum támogatás, előleg, önerő, projektidő, konzorcium, kedvezményezetti kör. A ZSC komponens alapértelmezetten offline kulcsszavas besorolást alkalmaz, de `USE_HF_ZSC=1` környezeti változóval HuggingFace zero-shot pipeline is használható. Az intent recognizer TF-IDF + Logistic Regression modell, amely rövid magyar kérdések alapján szándékosztályt ad vissza. Az LLM komponens a teljes PDF helyett rövidített, releváns szövegrészt küld a Mistral modellnek, így stabilabban fut gyengébb gépen is.

## 4. API dokumentáció röviden

Az API a következő fő végpontokat tartalmazza:

- `GET /health`: állapotellenőrzés, adatbázis és Ollama elérhetőség.
- `GET /grants`: feldolgozott felhívások listája.
- `GET /grants/{call_code}`: egy felhívás lekérdezése.
- `GET /search`: szűrés előleg, kockázati kategória, támogatástípus és konzorcium alapján.
- `GET /high-risk`: magas és kiemelt kockázatú felhívások.
- `POST /classify`: tematikus kategorizálás.
- `POST /intent`: szándékfelismerés.
- `POST /summarize`: magyar LLM összefoglaló.
- `GET /monitoring/kpis`: monitoring KPI-k.

Részletesebb dokumentáció: `docs/api_dokumentacio.md`. Automatikus Swagger dokumentáció: `http://localhost:8000/docs`.

## 5. Training set bemutatása

A projekt kétféle adatforrást használ:

1. Nyers dokumentumok: `data/pdfs/` mappában tárolt pályázati felhívások.
2. Intent felismerő tanító példák: `data/training/intent_examples.csv`.

Az intent training set magyar nyelvű példamondatokat tartalmaz a következő osztályokra:

- `summary`: összefoglaló kérés.
- `indicator_analysis`: indikátor- és eredményességi elemzés.
- `financial_info`: pénzügyi adatok lekérdezése.
- `eligibility`: kedvezményezetti kör, jogosultság.
- `risk_analysis`: kockázati elemzés.

A training set jelenleg demonstrációs méretű, ezért a beadandóban prototípusként értelmezendő. Éles rendszerben a tanítópéldák számát bővíteni kell valós felhasználói kérdésekkel és validált címkékkel.

## 6. Training set és LLM promptok verziózása

A training set verziózása fájlszinten és Git verziózással történik. Javasolt struktúra:

- `data/training/intent_examples.csv`: aktuális tanítóállomány.
- `data/training/archive/intent_examples_YYYYMMDD.csv`: korábbi verziók.
- Git commit: minden tanítóadat-változás külön commitban.
- Git tag: beadandó vagy release állapot, például `v1.0-beadando`.

Az LLM promptok külön fájlban szerepelnek:

- `prompts/summary_v1.md`
- `prompts/risk_v1.md`
- `prompts/indicator_v1.md`

A prompt verzióját a dokumentáció és a kód is rögzíti. Új promptváltozat esetén új fájl készül, például `summary_v2.md`, a régi verziót nem írjuk felül.

## 7. Forráskódok és modellek tárolása

A forráskód tárolása Git repositoryban javasolt. A Python forráskód az `app/` mappában található. A konténerizációs állományok a projekt gyökerében vannak: `Dockerfile`, `docker-compose.yml`.

A modellek tárolása:

- Intent modell: `models/intent_model.joblib`, `models/intent_vectorizer.joblib`.
- LLM modell: Ollama modell store-ban, például `~/.ollama/models`.
- Adatbázis: `grants.db`, amely futtatással újra előállítható.

A nagy modelleket nem célszerű Gitben tárolni; ezek verzióját környezeti változóban és dokumentációban kell rögzíteni, például `OLLAMA_MODEL=mistral`.

## 8. Monitoring és loggolás

A monitoring célja, hogy látható legyen a pipeline stabilitása, az adatminőség és a modellkimenetek megbízhatósága. A logolás JSON sorok formájában történik a `logs/pipeline.log` fájlba.

Figyelt KPI-k:

- feldolgozott PDF-ek száma;
- sikeres és sikertelen feldolgozások száma;
- LLM elérhetőség és timeout aránya;
- hiányzó felhíváskódok aránya;
- hiányzó címek aránya;
- hiányzó előlegadatok aránya;
- kockázati kategóriák megoszlása;
- ZSC kategóriák megoszlása;
- intent kategóriák megoszlása.

A KPI-k lekérdezhetők az API-ból: `GET /monitoring/kpis`.

## 9. Data drift és adatminőségi problémák kezelése

Adatminőségi probléma lehet például:

- nem olvasható PDF;
- hiányzó felhíváskód;
- hiányzó pénzügyi adat;
- hibásan értelmezett százalék;
- LLM timeout;
- szokatlanul hosszú vagy rövid dokumentumszöveg;
- kategóriaeloszlás eltolódása.

Ha adatminőségi probléma jelentkezik, a rendszer nem áll le, hanem naplózza a hibát, az érintett mezőknél `nincs adat` vagy `ismeretlen` értéket alkalmaz, és a rekordot részlegesen menti. Kritikus hiba esetén a feldolgozás után a monitoring riport jelzi a beavatkozási igényt.

## 10. Modell monitorozása

Az intent modell monitorozása a predikált intent kategóriák eloszlásán és az alacsony bizonyosságú predikciókon alapulhat. A ZSC kategorizáló esetében a kategóriaeloszlás változása figyelhető. Az LLM komponens esetében a válaszidő, timeout arány és hiányzó válasz aránya fontos.

Éles rendszerben javasolt a felhasználói visszajelzések gyűjtése is: az összefoglaló hasznos volt-e, a kockázati besorolás szakmailag elfogadható-e, szükséges-e manuális korrekció.

## 11. Újratanítás logikája

Az intent modell újratanítása indokolt, ha:

- legalább 50–100 új, validált felhasználói kérdés összegyűlt;
- új intent osztály jelenik meg;
- romlik az intent pontossága;
- gyakori az `unknown` vagy téves predikció;
- új dokumentumtípusok kerülnek a rendszerbe.

Az újratanítás a `scripts/train_intent.py` futtatásával történik. A kimeneti modell a `models/` mappába kerül.

## 12. Konténerizáció

A rendszer Dockerrel is futtatható. Az API konténerizálását a `Dockerfile` biztosítja, a `docker-compose.yml` pedig az API szolgáltatást indítja. Az Ollama futtatható külön host szolgáltatásként vagy opcionálisan konténerben. WSL/Ubuntu környezetben egyszerűbb a hoston futó Ollama használata.

## 13. Összegzés

A beadandó egy teljes, futtatható MLOps prototípust mutat be: adatbeolvasás, feldolgozás, ML-alapú intent felismerés, HuggingFace jellegű ZSC kategorizálás, lokális LLM összefoglaló, API, dashboard, konténerizáció és monitoring. A rendszer a pályázati felhívások ellenőrzési célú előszűrését és vezetői szintű áttekintését támogatja.
