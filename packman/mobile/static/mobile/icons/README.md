# PackMate app icons — Pack 144 "Den Ring" (light)

| File | Use |
| --- | --- |
| `icon-512.png` | PWA icon, large |
| `icon-192.png` | PWA icon, standard |
| `icon-maskable-512.png` / `icon-maskable-192.png` | Android adaptive (safe-zone padded) |
| `apple-touch-icon.png` | iOS home screen, 180x180 |
| `favicon-32.png` | Browser tab |

Colors: plate `#ffffff` · ring `#c8202f` · numerals `#0b2a52` · type Archivo Black.
The manifest's `theme_color` and the `<meta name="theme-color">` in `index.html`
are both set to the ring red and must be kept in sync.

`apple-touch-icon.png` is intentionally flattened onto white (RGB, no alpha):
iOS ignores transparency and composites home-screen icons over black. Every
other file keeps its alpha channel; the maskable pair already has opaque white
corners so Android's mask has something to bite into.

These files are wired up through `{% static %}` in
`packman/mobile/templates/mobile/{index.html,manifest.webmanifest,sw.js}`.
Changing them requires bumping `VERSION` in `sw.js` so installed clients evict
the old cached copies.
