# Representative interfaces of ErgoSight-Bench

These folders show representative pages of the benchmark as they are rendered under its display conditions.

| Folder | Content |
| --- | --- |
| `ds01_domains` | one generated page per HMI domain, on the desktop (D1) and the phone (D3) |
| `ds02_displays` | one page under all six display conditions, D1 desktop, D2 tablet, D3 phone, D4 reflow window, D5 deuteranopia, D6 daylight |
| `ds03_defects` | pages before and after the injection of each of the nine controlled defects |
| `ds04_repair` | pages generated as designed and after the repair loop |
| `ds05_generators` | one design brief rendered by the three generating models |
| `ds06_real` | real web pages |

D1 to D4 are laid out by Chromium at the physical parameters of the condition, D5 is the deuteranopia simulation of the tablet layout, and D6 is the 10,000 lx daylight simulation of the phone layout. Each `meta.json` lists the generator, the design brief, the style, and the violations measured per criterion and display condition. `selection.csv` lists every sample.
