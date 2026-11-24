"""Image decoding and the explicit, non-benchmark demo adapter."""
import warnings
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES=20*1024*1024
MAX_PIXELS=25_000_000
MIN_SIDE=16

def read_image(path, *, demo=False):
    path=Path(path)
    if demo and path.stat().st_size>MAX_BYTES: raise ValueError('Upload must be at most 20 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(path) as im:
                if im.format not in ('PNG','JPEG'): raise ValueError('Please upload a PNG or JPEG image.')
                if getattr(im,'n_frames',1)!=1: raise ValueError('Animated images are not supported.')
                if im.width*im.height>MAX_PIXELS: raise ValueError('Decoded image must be at most 25 million pixels.')
                if 'A' in im.getbands() or 'transparency' in im.info:
                    raise ValueError('Transparent images are not supported. Save an opaque RGB image first.')
                im=ImageOps.exif_transpose(im)
                if min(im.size)<MIN_SIDE: raise ValueError('Both image sides must be at least 16 pixels.')
                return im.convert('RGB').copy()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as e:
        raise ValueError('The image could not be decoded safely. Please upload a valid PNG or JPEG.') from e

def prepare_demo(image):
    original=image.size
    if max(original)>640:
        factor=640/max(original)
        size=tuple(max(1,int(round(v*factor))) for v in original)
        if min(size)<MIN_SIDE: raise ValueError('This aspect ratio becomes too narrow after resizing; crop the image first.')
        image=image.resize(size,Image.Resampling.LANCZOS)
    w,h=image.size
    meta={'original_size':list(original),'inference_size':[w,h], 'padding_right':(-w)%16,
          'padding_bottom':(-h)%16,'adapter':'demo-longedge640-lanczos-reflect16-v2'}
    return image,meta

def as_rgb_array(image):
    return np.asarray(image,dtype=np.uint8).copy()
