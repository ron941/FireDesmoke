"""Check actual decoded title holds, including the final frame, on both exports.
Run: python site/tests/check_film_loop.py [film_directory]
Requires ffmpeg, ffprobe, NumPy. No network or model inference.
"""
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'dist/film'
reports=[]
for resolution in ('1080p','720p'):
 p=root/f'FireDesmoke_loop_{resolution}.mp4'
 info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]))
 s=info['streams'][0];count=int(s['nb_frames'])
 assert count==1986 and abs(float(info['format']['duration'])-66.2)<.001
 # Test start/end of both holds, plus the boundary entering the final hold.
 indices=[0,44,1940,1941,1985]
 select='+'.join(f'eq(n,{i})' for i in indices)
 raw=subprocess.check_output(['ffmpeg','-v','error','-threads','4','-i',str(p),'-vf',f"select='{select}',scale=192:108",'-vsync','0','-pix_fmt','rgb24','-f','rawvideo','-'])
 frames=np.frombuffer(raw,dtype=np.uint8).reshape(len(indices),108,192,3).astype(float)
 diffs=[float(np.abs(f-frames[0]).mean()) for f in frames]
 assert max(diffs)<2,(resolution,dict(zip(indices,diffs)))
 reports.append({'resolution':resolution,'frames':count,'duration':66.2,'hold_frame_indices':indices,'mean_pixel_difference_0_255':diffs})
print(json.dumps(reports,indent=2))
