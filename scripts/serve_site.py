"""Use the restricted local site handler; defaults to port 8080."""
import runpy,sys
from pathlib import Path
if __name__=='__main__':
    if '--port' not in sys.argv:sys.argv.extend(['--port','8080'])
    runpy.run_path(str(Path(__file__).resolve().parents[1]/'site'/'serve.py'),run_name='__main__')
