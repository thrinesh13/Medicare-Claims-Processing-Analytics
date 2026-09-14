"""Build the claims analysis and execute its notebooks and checks."""
import os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
for folder in ['ipython','jupyter-runtime']:
    (ROOT/'work'/folder).mkdir(parents=True,exist_ok=True)
os.environ.setdefault('IPYTHONDIR',str(ROOT/'work/ipython'))
os.environ.setdefault('JUPYTER_RUNTIME_DIR',str(ROOT/'work/jupyter-runtime'))
for name in ['run_pipeline','build_notebooks','export_figures']:
    subprocess.run([sys.executable,str(ROOT/'scripts'/f'{name}.py')],check=True)
subprocess.run([sys.executable,'-m','pytest','tests','-q','-p','no:cacheprovider','--basetemp=work/pytest','--junitxml=results/tests.xml'],check=True)
