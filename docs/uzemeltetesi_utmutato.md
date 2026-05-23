# Üzemeltetési útmutató – gyors indítás

## 1. Projekt mappába lépés

```bash
cd /mnt/c/Users/Kitti/OneDrive/Desktop/palyazat_fixed
source ~/venv/bin/activate
```

## 2. Függőségek

```bash
pip install -r requirements.txt
```

## 3. Ollama/Mistral

```bash
ollama list
ollama pull mistral
```

Ha az Ollama már fut, az `ollama serve` parancs `address already in use` üzenete nem hiba.

## 4. PDF-ek beolvasása

```bash
PDF_LIMIT=3 python -m app.ingest
```

## 5. API indítása

```bash
uvicorn app.api:app --reload --host 0.0.0.0 --port 8000
```

## 6. Streamlit indítása új terminálban

```bash
cd /mnt/c/Users/Kitti/OneDrive/Desktop/palyazat_fixed
source ~/venv/bin/activate
streamlit run app/streamlit_app.py
```

## 7. Ellenőrző URL-ek

- Streamlit: `http://localhost:8501`
- API health: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`
- KPI-k: `http://localhost:8000/monitoring/kpis`
