import numpy as np
import pytest
from PIL import Image
from firedesmoke.images import read_image,prepare_demo

def test_native_and_demo_geometry(tmp_path):
    p=tmp_path/'x.png';Image.new('RGB',(1001,751),(50,70,90)).save(p)
    im=read_image(p,demo=True);out,meta=prepare_demo(im)
    assert im.size==(1001,751) and out.size==(640,480)
    assert meta['padding_bottom']==0 and meta['padding_right']==0
    out,meta=prepare_demo(Image.new('RGB',(639,477)))
    assert out.size==(639,477) and meta['padding_right']==1 and meta['padding_bottom']==3

def test_exif_rotation(tmp_path):
    im=Image.new('RGB',(80,40));exif=im.getexif();exif[274]=6
    p=tmp_path/'x.jpg';im.save(p,exif=exif)
    assert read_image(p).size==(40,80)

@pytest.mark.parametrize('kind',['rgba','corrupt','tiny','gif','oversize'])
def test_reject_invalid(tmp_path,kind):
    p=tmp_path/'x.png'
    if kind=='rgba':Image.new('RGBA',(40,40)).save(p)
    elif kind=='corrupt':p.write_bytes(b'not an image')
    elif kind=='tiny':Image.new('RGB',(8,64)).save(p)
    elif kind=='gif':Image.new('RGB',(40,40)).save(p,format='GIF')
    else:p.write_bytes(b'0'*(20*1024*1024+1))
    with pytest.raises(ValueError):read_image(p,demo=True)

def test_no_upscale():
    assert prepare_demo(Image.new('RGB',(48,32)))[0].size==(48,32)
