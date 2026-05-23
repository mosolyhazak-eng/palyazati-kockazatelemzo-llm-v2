# Monitoring és KPI terv

## Cél

A monitoring célja a feldolgozási pipeline, az adatminőség, az ML komponensek és az LLM komponens folyamatos ellenőrzése.

## Fő KPI-k

| KPI | Jelentés | Mérési mód | Beavatkozási küszöb |
|---|---|---|---|
| Feldolgozott PDF-ek száma | Pipeline aktivitás | `grants` rekordok száma | 0 rekord esetén hiba |
| Sikertelen feldolgozás | PDF vagy parsing hiba | log esemény | >10% esetén vizsgálat |
| Hiányzó felhíváskód | mezőkinyerési adatminőség | SQL COUNT | >5% esetén regex javítás |
| Hiányzó cím | mezőkinyerési adatminőség | SQL COUNT | >5% esetén parser javítás |
| Hiányzó előleg | pénzügyi adatminőség | SQL COUNT | >30% esetén manuális validálás |
| LLM timeout arány | Mistral stabilitás | log + summary szöveg | >20% esetén kisebb modell vagy timeout növelés |
| Kockázati kategóriák megoszlása | modell output drift | SQL GROUP BY | szokatlan eltolódásnál review |
| ZSC kategóriák megoszlása | tematikus drift | SQL GROUP BY | új kategóriaigény esetén label bővítés |
| Intent megoszlás | felhasználói igények változása | SQL GROUP BY / API log | új intent osztály létrehozása |

## Adatminőségi probléma esetén

1. A hiba bekerül a `logs/pipeline.log` fájlba.
2. A pipeline lehetőség szerint nem áll le.
3. Az érintett mező `ismeretlen`, `nincs adat` vagy `NULL` értéket kap.
4. A monitoring riport jelzi a problémát.
5. Kritikus hiba esetén újra kell futtatni a beolvasást javított parserrel.

## Modellmonitoring

Az intent modell esetében figyelni kell az alacsony predikciós bizonyosságot és az osztályeloszlás változását. A ZSC esetében figyelni kell, ha túl sok az `ismeretlen` kategória. Az LLM esetében figyelni kell a válaszidőt, timeoutot és azt, hogy magyar nyelvű, strukturált választ ad-e.

## Újratanítás

Újratanítás indokolt, ha új intent osztály jelenik meg, romlik a predikció minősége, vagy legalább 50–100 új validált kérdés összegyűlt.
