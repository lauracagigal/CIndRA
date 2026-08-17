# CIndRA Climate Indicators

Atmosphere, ocean and tropical cyclone indicators for Pacific Island countries
and subregions.

## Jupyter Book

The book contains all national and regional notebooks listed in `_toc.yml`.
Notebook outputs are rendered from their saved state, so building the website
does not download or recompute the underlying climate datasets.

```bash
python -m pip install -r requirements-book.txt
jupyter-book build .
```

Open `_build/html/index.html` to inspect the result locally.

Pushes to `main` trigger `.github/workflows/deploy-book.yml`. To publish the
site, configure GitHub Pages to use **GitHub Actions** as its source in the
repository settings.
