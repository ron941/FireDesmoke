# FireDesmoke project website

`dist/` is the current static website: the research film, abstract, method diagram,
interactive comparisons, smoke transfer, results and data-access information.
The upload-and-restore GPU demo is a separate service.

## Local preview

From the repository root:

```bash
python scripts/serve_site.py --port 8080
```

The server binds to `127.0.0.1` and serves only the website assets. Open `http://127.0.0.1:8080/` on the same computer.

## Sources

The website is buildless: edit the HTML, CSS, JavaScript and data files in `dist/`. Scientific provenance accompanies the website data. See [template attribution](LICENSE-TEMPLATE.md).

Quantitative tables are generated from the author-supplied CSV files with `python scripts/build_results_snapshot.py`. The architecture figure is the current manuscript figure, not a relabelled earlier model.
