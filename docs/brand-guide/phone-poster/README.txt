BenchMate phone poster

BenchMate-Phone-Poster.png: flat master artwork, 3600 x 3600 pixels.
BenchMate-Phone-Subway-Mockup.png: generated preview in the supplied subway scene.
poster.html: editable, self-contained poster source with embedded font and images.
home-screen-original.png: unchanged copy of the supplied 461 x 905 screenshot.
production.json: source treatment and rendering specifications.
review.html: local preview of the master artwork and subway mockup.

The flat poster retains the original brand vector paths and the original app
screenshot. Native HTML layout clips the screenshot to the iPhone's rounded
outer silhouette, excluding the exterior background. The screen has not been
redrawn, reconstructed or replaced. The original screenshot file remains intact.

Copy: Make something. / Guided projects. From idea to made.
Palette: cobalt #3155D9, pale cloud #F3F4F8, lime #D6E879.
The dithered ribbon comes from the existing brand guide asset library.

The built-in image_gen tool was first used for background removal. That cutout
changed screen details, so it is retained only as a generated reference and was
NOT used in the flat artwork. cutout-prompt.txt records that prompt.

The subway preview was generated using the built-in image_gen tool with the
original subway photograph and finished flat poster. mockup-prompt.txt contains
the exact prompt. It is a generated scene preview, not a pixel-preserving edit of
the full-resolution source photograph. Use the flat poster as the artwork master.
Physical print measurements and bleed were not supplied.

Rebuild from repository root:
  node docs/brand-guide/phone-poster/build-poster.mjs
