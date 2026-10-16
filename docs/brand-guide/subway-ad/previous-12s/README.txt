BenchMate subway ad

Deliverables
- BenchMate-Subway-Mockup.mp4: 2000 x 1334, H.264, 30 fps, 12 seconds, silent.
- BenchMate-Ad-4114x780.mp4: flat artwork at the PSDT smart object's exact dimensions.
- review.html: local playback, downloads, and storyboard.
- ad.html: self-contained editable HTML/SVG motion source with embedded font and vector paths.

Copy: Guided projects. From idea to made.

Uses the current BenchMate_Brand_Guide.html construction animation: blueprint,
wireframe, detail points, then ordered-dither color fill. Original geometry and
construction timing are preserved. The final solid mark holds until 11.4 seconds,
then fades for 0.6 seconds before looping. Copy remains visible throughout.

The subway video uses the supplied AdobeStock_570926833.psdt background,
smart-object perspective corners, stored combined mask, and its White/Black
texture layers (linear burn and screen). It is a rendered video composite;
the original Photoshop template is unchanged. No edited layered PSDT is included.

Rebuild from the repository root:
  node docs/brand-guide/subway-ad/build-ad.mjs
  node docs/brand-guide/subway-ad/render-ad.mjs --preview
  node docs/brand-guide/subway-ad/render-ad.mjs
  python -m pip install --target .tmp-subway-python -r docs/brand-guide/subway-ad/requirements.txt
  python docs/brand-guide/subway-ad/composite.py

Requires Node, the repo's Playwright package, Chrome, FFmpeg, and Python.
composite.py reads the original PSDT from the supplied Downloads path.
production.json records the placement and output specifications.
