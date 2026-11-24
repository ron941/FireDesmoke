# Running the website and demo

## Project website

Visit [the project website](https://ron941.github.io/FireDesmoke/) to explore the saved comparisons. To preview it locally, run `python scripts/serve_site.py --port 8080` and open `http://127.0.0.1:8080/`.

## Upload-and-restore demo

Follow the [installation and weight setup](../README.md#quick-start), then run `firedesmoke demo --model firedesmoke --port 7860`. Open `http://127.0.0.1:7860/` on the same computer. Choose an example or upload an image, select **Restore image**, and download the result.

## Processing and privacy

PNG/JPEG uploads are limited to 20 MB and 25 million decoded pixels, with a
minimum side of 16 pixels. EXIF orientation is applied; images are converted to
RGB and resized only when the longest side exceeds 640 pixels. Output uses this
processing size. Transparent and animated images are rejected.

The fixed GPU model processes one request at a time, with up to eight queued
events. Completed uploads and outputs expire after one hour. No image is sent
to an external inference service, and images without a reference receive no
PSNR/SSIM score. Dense smoke can hide details that a single image cannot recover.
Both servers bind to `127.0.0.1` by default.
