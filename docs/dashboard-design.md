# Dashboard design lock

Build directly from the brief's approved desktop command-center direction. The brief supplies the navy, cyan, teal and amber roles. The live Refero catalog did not return references; the design uses its bundled typography, color and accessibility guides and these public references.

| Decision | Reference | Rationale |
| --- | --- | --- |
| Short KPI row, one dominant trend, adjacent supporting panel | [Grafana dashboard guidance](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/best-practices/) | Keep volume, latency and availability legible at 1440 × 900. Let the reader drill from summary into evidence. |
| Show a label and unit alongside color; keep HR and pulse comparable, other channels separate | [IBM Design Language](https://www.ibm.com/design/language/data-visualization/overview/), [Adobe Spectrum](https://spectrum.adobe.com/page/color-for-data-visualization/) | Color cannot be the only indicator. Nulls remain gaps and may carry a separate missing-data marker. |
| Navy surfaces, compact system sans, tabular numbers, one cyan selection accent | User brief and Refero typography/color guides | Data should carry the visual emphasis. Teal labels verified evidence; amber labels replay or missingness, never a clinical alert. |
| Sidebar keeps run mode separate from page navigation; active replay offers pause, reset and step | User brief, Refero craft guidance | A lecturer can verify the source and control playback independently of filters. |
| Use real charts and one traceable workflow diagram as the visual assets | User brief | Do not present decorative waveforms or fabricated patient imagery as evidence. |
