## Managing the Stracòt page assets

### What’s there

- `static/img/stracot-guide/official-logo.webp`: official logo, referenced directly from `layouts/stracot.html`.
- `static/img/stracot-guide/`: guide illustrations, six guide photo sets, and their WebP variants.
- `static/img/stracot-guide/manifest.json`: paths, dimensions and responsive variants used by the page generator.
- `static/img/stracot-guide/gallery/`: 480px and 960px WebP display copies of gallery photos.
- `static/img/stracot/`: 25 gallery JPEGs. These are the gallery sources and the images opened when someone clicks a gallery photo.

The guide photos currently use 640px and 1120px variants, except the overview, which uses 640px, 1000px and 1600px. The guide illustrations come from the Rollup PDF and use transparent WebP files.

### Add or remove a photo from the guide

1. Create the WebP file or responsive variants in `static/img/stracot-guide/`. For example, given a generic photo `photo`:

   ```bash
   for width in 640 1120; do
     magick "$photo" -auto-orient -colorspace sRGB -resize "${width}x>" \
       -strip -quality 76 -define webp:method=6 \
       "static/img/stracot-guide/${name}-${width}.webp"
   done
   ```

2. Update `static/img/stracot-guide/manifest.json` under `images` with the image paths, actual dimensions and `srcset` variants.
3. Add the image placeholder to `layouts/stracot.html` and its matching mapping in `processors/generate.py`. When removing a guide photo, remove those references and its manifest entry, then delete leftover WebP files.

### Add or remove a photo from the gallery

1. Add the JPEG to `static/img/stracot/`. The generator automatically includes image files in that folder in the gallery.
2. Create 480px and 960px WebP copies in `static/img/stracot-guide/gallery/` (using the same `magick` command as above, but with `480` and `960` widths).
3. Add an entry for the JPEG under `gallery` in `static/img/stracot-guide/manifest.json`, with the WebP paths, dimensions and `srcset`. The JPEG stays in `static/img/stracot/` as the full-size linked image.
4. To remove a gallery photo, remove its JPEG, manifest entry and WebP copies.

### Regenerate the pages

After changing assets, run:

```bash
python3 processors/generate.py
```
