# Development Samples

The files are downloaded to `data/` (gitignored) by `python samples/fetch.py`. Sources and licenses are in `samples.json`.

| File | Role | License |
|---|---|---|
| `sfdph-wash-hands-en.webm` | Primary demo: 58 s narrated hand-washing demonstration, 1280×960 | CC BY 3.0, San Francisco Government Television ([Commons](https://commons.wikimedia.org/wiki/File:20200303_-_SFGovTV_-_SFDPH_WASH_HANDS_ENGLISH.webm)) |
| `cdc-ppe-hand-hygiene.webm` | Secondary: 20 s hand-hygiene clip | CC BY-SA 4.0, CDC ([Commons](https://commons.wikimedia.org/wiki/File:Donning_PPE-_Perform_Hand_Hygiene_CDC05.webm)) |
| `fda-food-code-2022.pdf` | SOP: §2-301.12 defines a five-step handwashing procedure and a 20-second minimum | US federal government work, public domain ([FDA](https://www.fda.gov/food/fda-food-code/food-code-2022)) |
| `bambu-x1-replace-nozzle-wiper.md` | SOP for the unstructured X1C sample: Bambu's official 4-step wiper replacement (power off, remove glass, one screw) | Copyright Bambu Lab; fetched for local testing, not redistributed ([wiki](https://wiki.bambulab.com/en/x1/maintenance/replace-nozzle-wiper)) |

The pairing deliberately gives the compliance stage something to check: a real procedure with an ordered list, a duration and named equipment, inside a 668-page manual where most text is irrelevant.

The CDC hand-hygiene guideline was considered as the SOP, but cdc.gov blocks scripted downloads, so it was not used.

## Unstructured Sample

The narrated, edited SFDPH video makes segmentation easy (the narrator says "Step 1", and scene cuts fall on step boundaries). The main test case is therefore an **uncut livestream**, used directly by URL with an excerpt:

| Source | Excerpt | Task | License |
|---|---|---|---|
| [Bambu Lab X1 Carbon Mod Install LIVE](https://www.youtube.com/watch?v=7787-1g8l4Y), Leckiestein | 49:00–62:30 (`ingest.start_s: 2940`, `end_s: 3750`) | Installing the SteinWipe nozzle-wiper mod inside an X1C, then confirming on the touchscreen | CC BY (YouTube) |

Candidates were screened for editing (scene cuts per minute in sampled windows) and for visible hands; edited tutorials were rejected.
