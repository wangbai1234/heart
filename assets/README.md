# Asset Library

This folder stores long-lived visual assets reconstructed from the UI design source pages in [`web/design/source`](/Users/wanglixun/heart/web/design/source).

Principles for this first pass:

- Preserve the original design language instead of redesigning the visuals.
- Export only reusable illustrations, backgrounds, character portraits, and effects.
- Skip ordinary UI components such as cards, buttons, tabs, inputs, borders, and icons.
- Prefer clean source crops from foundation pages when they are higher quality than screen-level crops.

Current export scope:

- `characters/`: circular character avatars with original glow retained.
- `backgrounds/`: reusable fantasy sky and scene backdrops.
- `illustrations/`: standalone hero-style visual elements such as the heart emblem and gift box.
- `effects/`: lightweight glow or sparkle overlays.
- `_meta/`: the extraction script and generated manifest.

To regenerate the library:

```bash
python3.11 assets/_meta/extract_ui_assets.py
```
