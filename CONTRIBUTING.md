# Contributing

Add a named text-to-image model or a distinct architecture release with a paper, official repository, model card or developer documentation. Keep checkpoint sizes, resolutions and quantizations under the same family unless the architecture changes substantially. See the [methodology](docs/methodology.md) for what is in scope.

1. Edit [data/models.json](data/models.json). Use a stable ID, one short architecture sentence, concise notes and primary-source metadata. Add a `description` for recent models: one short paragraph explaining the generation method, conditioning and controls, and intended use. Add `license` only when the repository or model card states it. Keep version-specific claims tied to primary sources. Follow an existing record for the complete schema.
2. Add a matching record to [data/figures.json](data/figures.json). Prefer the architecture figure from the primary source, not a sample grid. `python3 scripts/add_figure.py list <arxiv-id>` lists a paper's figures with their image URLs; `python3 scripts/add_figure.py fetch <id> --origin-url ... --source-url ... --locator "Figure N"` downloads it, converts it to PNG and prints the record with its SHA-256 checksum. For assembled panels or PDF crops, prepare the PNG yourself, pass it with `--file` and repeat `--origin-url` for every panel. Use `add_figure.py io` for a labeled input/output diagram when no suitable figure exists.
3. Regenerate and validate with Python 3.10 or newer:

   ```bash
   python3 scripts/catalog.py
   python3 scripts/catalog.py --check
   ```

The generator uses only the Python standard library. It checks metadata, duplicate entries, dates, licenses, asset checksums, the arXiv snapshot checksum, local links, anchors and generated-file consistency. Inspect new figures and rendered Markdown before sharing changes.

The optional `description` field appears on the README model card, the category architecture card and in [model descriptions](docs/model-descriptions.md). README cards use the architecture sentence when no separate description is provided.

The [2025+ arXiv collection](docs/t2i-arxiv-daily.md) requires a `description` and `github_status` (`author-linked` or `not-found`) for every included family. Keep the [screening ledger](data/t2i-arxiv-daily.json) in sync when correcting an imported record. `python3 scripts/fetch_arxiv.py` refreshes the snapshot: new papers arrive as `pending` rows and existing decisions are kept. New imports require a first paper submission from 2025 onward; an older paper's later revision does not qualify. `python3 scripts/catalog.py --check --strict` fails while any row is pending.

Do not infer architecture from a product name or API behavior, equate reference-image conditioning with image understanding, or treat a guidance or control method as a new model. Undated sources can remain undated. Repository timestamps are not release dates.

Submit corrections with the model ID and supporting source; attribution or removal requests should identify the affected asset. See the [figure notice](assets/architectures/FIGURE_NOTICE.md).
