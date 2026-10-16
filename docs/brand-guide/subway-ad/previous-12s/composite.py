"""Composite the ad using the PSDT's native placement, mask, and texture layers."""
import sys, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'.tmp-subway-python'))
import numpy as np
import cv2
from PIL import Image
from psd_tools import PSDImage
OUT=Path(__file__).resolve().parent
TEMPLATE=Path(r'C:\Users\alexx\Downloads\AdobeStock_570926833.psdt')
p=PSDImage.open(TEMPLATE)
layer=p[1]
W,H=2000,1334
scale=W/p.width
bg=np.array(p[0].topil().convert('RGB').resize((W,H),Image.Resampling.LANCZOS))
corners=np.array(layer.smart_object.transform_box,dtype=np.float32).reshape(4,2)*scale
x0,y0=340,330
x1,y1=1630,775
rw,rh=x1-x0,y1-y0
matrix=cv2.getPerspectiveTransform(np.float32([[0,0],[4114,0],[4114,780],[0,780]]),np.float32(corners-[x0,y0]))
mask_image=Image.new('L',p.size)
mask_image.paste(layer.mask.topil(layer_sized=True),(layer.left,layer.top))
mask=np.array(mask_image.resize((W,H),Image.Resampling.LANCZOS))[y0:y1,x0:x1,None]/255.
textures=[]
for l in p[2]:
    im=Image.new('RGBA',p.size)
    im.paste(l.topil(),(l.left,l.top))
    a=np.array(im.resize((W,H),Image.Resampling.LANCZOS))[y0:y1,x0:x1].astype(np.float32)/255
    textures.append((l.name,a[:,:,:3],a[:,:,3:4]))
base=bg[y0:y1,x0:x1].astype(np.float32)/255
def composite(ad):
    warped=cv2.warpPerspective(ad,matrix,(rw,rh),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE).astype(np.float32)/255
    area=base*(1-mask)+warped*mask
    for name,rgb,alpha in textures:
        blend=np.maximum(0,area+rgb-1) if name=='White' else 1-(1-area)*(1-rgb)
        area=area*(1-alpha)+blend*alpha
    result=bg.copy();result[y0:y1,x0:x1]=np.clip(area*255+.5,0,255).astype(np.uint8)
    return result
for t in ['1.3','3.6','5','6.7','9']:
    Image.fromarray(composite(np.array(Image.open(OUT/f'ad-{t}s.png').convert('RGB')))).save(OUT/f'mockup-{t}s.jpg',quality=96)
metadata={'template':str(TEMPLATE),'templateSize':p.size,'artworkSize':[4114,780],'mockupSize':[W,H],'perspectiveCorners':np.array(layer.smart_object.transform_box).reshape(4,2).tolist(),'mask':'PSDT stored combined layer mask','textures':[{'name':l.name,'blend':str(l.blend_mode),'opacity':l.opacity} for l in p[2]],'fps':30,'durationSeconds':12,'copy':'Guided projects. From idea to made.','motion':'Exact SVG setup and construction timing extracted from BenchMate_Brand_Guide.html; final hold extended and 0.6-second loop fade added'}
(OUT/'production.json').write_text(json.dumps(metadata,indent=2))
if '--preview' in sys.argv: sys.exit(0)
video=cv2.VideoCapture(str(OUT/'BenchMate-Ad-4114x780.mp4'))
assert video.isOpened()
cmd=['ffmpeg','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','30','-i','-','-an','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/'BenchMate-Subway-Mockup.mp4')]
with open(OUT/'encode.log','w') as log:
    encoder=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=log)
    frames=0
    while True:
        ok,frame=video.read()
        if not ok:break
        encoder.stdin.write(composite(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)).tobytes())
        frames+=1
        if frames%60==0:print(f'Composited {frames}/360 frames',flush=True)
    encoder.stdin.close();assert encoder.wait()==0
video.release();assert frames==360,frames
print('Finished subway video using native PSDT placement and textures')
