# Pályázati felhívás kockázati elemző – beadandó kész verzió

Ez a csomag egy könnyen futtatható MLOps prototípus pályázati felhívások elemzésére.

A rendszer tartalmazza:

- PDF beolvasás és szövegkinyerés;
- strukturált mezőkinyerés;
- ZSC/HuggingFace jellegű tematikus kategorizálás;
- TF-IDF + Logistic Regression intent recognizer;
- Mistral/Ollama alapú magyar LLM összefoglaló;
- kockázati pontszámítás;
- SQLite adattárolás;
- FastAPI backend;
- Streamlit dashboard;
- Dockerfile és docker-compose;
- monitoring KPI-k;
- futtatható notebook;
- beadandó dokumentáció.

## Gyors indítás WSL/Ubuntu alatt

```bash
cd /mnt/c/Users/Kitti/OneDrive/Desktop/palyazat_fixed
source ~/venv/bin/activate
pip install -r requirements.txt
```

Ollama/Mistral ellenőrzés:

```bash
ollama list
ollama pull mistral
```

PDF-ek beolvasása első körben 3 felhívással:

```bash
PDF_LIMIT=3 python -m app.ingest
```

API indítása:

```bash
uvicorn app.api:app --reload --host 0.0.0.0 --port 8000
```

Streamlit indítása új terminálban:

```bash
cd /mnt/c/Users/Kitti/OneDrive/Desktop/palyazat_fixed
source ~/venv/bin/activate
streamlit run app/streamlit_app.py
```

Böngésző:

- Streamlit: `http://localhost:8501`
- API: `http://localhost:8000/docs`
- KPI-k: `http://localhost:8000/monitoring/kpis`

## Egyparancsos feldolgozás

```bash
./run_all.sh
```

Ez beolvassa a PDF-eket és kiírja a KPI riportot. Az API-t és a Streamlitet külön terminálban indítsd.

## Dokumentáció

- `docs/beadando_dokumentacio.md`: teljes beadandó szöveges dokumentáció.
- `docs/api_dokumentacio.md`: API dokumentáció.
- `docs/monitoring_kpi.md`: monitoring és KPI terv.
- `docs/uzemeltetesi_utmutato.md`: futtatási útmutató.
- `docs_kockazati_modell.md`: kockázati modell szakmai leírás.

## Notebook

Futtatható notebook:

```text
notebooks/demo.ipynb
```

A notebook a fő pipeline lépéseit demonstrálja.

## Docker

API konténer építése és futtatása:

```bash
docker compose up --build
```

WSL alatt az Ollama hoston is futhat. Ilyenkor az API az Ollama helyi endpointját használja.

## Környezeti változók

- `PDF_LIMIT=3`: hány PDF-et dolgozzon fel.
- `OLLAMA_MODEL=mistral`: használt LLM modell.
- `OLLAMA_TIMEOUT=600`: LLM timeout másodpercben.
- `LLM_INPUT_CHARS=9000`: Mistralnak átadott maximum karakter.
- `USE_HF_ZSC=0`: alapértelmezetten offline kategorizálás.

## Beadandó szempontok teljesítése

| Elvárás | Megvalósítás |
|---|---|
| Futtatható notebook | `notebooks/demo.ipynb` |
| Konténerizált API | `Dockerfile`, `docker-compose.yml` |
| Dokumentáció | `docs/` mappa |
| HuggingFace pipeline / ZSC | `app/zsc_classifier.py` |
| LLM használat | `app/llm_summary.py`, Ollama/Mistral |
| Intent recognizer | `app/intent_model.py` |
| Monitoring és KPI | `app/monitoring.py`, `/monitoring/kpis` |
| Prompt verziózás | `prompts/` mappa |
| Training set verziózás | `data/training/intent_examples.csv` |


## Keresők működése

A Streamlit oldalsávban három kulcsszavas kereső van:

- **Felhívás kód / cím:** a felhívás azonosítójában és címében keres.
- **Kedvezményezett:** a PDF-ből kinyert kedvezményezetti/jogosulti szövegrészben keres.
- **Tevékenység:** a PDF-ből kinyert támogatható tevékenységi szövegrészben, valamint címben és kedvezményezetti részben keres.

Ha egy PDF-ben a kedvezményezetti vagy tevékenységi fejezet nem volt gépileg jól kinyerhető, akkor a kereső arra nem ad találatot. A részletes felhívásnézetben látható, hogy a rendszer mit tudott kinyerni.
