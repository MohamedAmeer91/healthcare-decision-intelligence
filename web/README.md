# Web dashboard (dev branch)

A web view of the capstone results. It lives only in this folder; the capstone files (`part1.py` to `part4.py`, `outputs/`, the root `README.md`) are not changed and the root `requirements.txt` still needs only NumPy.

Every number shown comes from the committed `outputs/` files. The threshold explorer recomputes confusion cells and money cost from the same logistic model as `part2.py`.

## Two ways to use it

**1. Live (Flask)** - interactive, the threshold cost is calculated on the server:

```
pip install -r web/requirements.txt
python generate_data.py            # only if data/records.csv is missing
python part1.py && python part2.py && python part3.py && python part4.py
python web/app.py                  # open http://127.0.0.1:5000
```

API: `GET /api/health`, `GET /api/data`, `GET /api/threshold?tau=0.15&false_alarm=50&missed=400` (tau 0 to 1, costs 0 to 1,000,000; anything else returns HTTP 400).

**2. Static** - no server, no Python: open `web/static/index.html` in a browser (or host the `web/static` folder on any static host). The page then uses the bundled `data.js` and calculates the threshold explorer in the browser. The badge at the top shows which mode is active.

After re-running the Parts, refresh the bundled data with `python web/build_data.py` (rewrites `web/static/data.json` and `web/static/data.js`).

## Files

| File | Role |
|---|---|
| `app.py` | Flask app and API |
| `build_data.py` | Reads `outputs/` and the README memo, adds a 0.01-step threshold sweep |
| `static/index.html`, `style.css`, `app.js` | The pages (plain HTML, CSS and JavaScript, charts are inline SVG, no external libraries or links) |
| `static/data.js`, `data.json` | Bundled data for the static mode |

## Notes

- Colours use a colour-blind-safe set with a fixed order (segments A, B, C keep the same colour everywhere), with light and dark themes. The palette was chosen by hand, not run through a validator; every chart has a table view and hover text.
- Layout was tested by generating the pages with a scripted check (no errors, no missing values), not by screenshots.
- The data is synthetic and nothing here is clinical advice.
