"""Build an isolated Windows package from source and installed dependencies.

Run with Python 3.12: build_payload.py --dependencies D:/EnglishOrbit --output D:/EnglishOrbitBuild/payload
No application data, provider sessions or user-created agent files are copied.
"""
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path

SOURCE=Path(__file__).resolve().parents[1]
MODULES='accounts avatar_gallery capture chat_view core design learning learning_ui main providers settings_ui toast_widgets ui'.split()

def build(dependencies, output):
    if output.exists():
        raise SystemExit('Use a fresh output folder; existing package will not be overwritten.')
    output.mkdir(parents=True)
    def copy(src,dst):
        if src.is_dir():shutil.copytree(src,dst,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.DS_Store'))
        else:dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    for module in MODULES:copy(SOURCE/(module+'.py'),output/(module+'.py'))
    for filename in ('login.ps1','deny-tools.toml','README.md','THIRD_PARTY.md'):
        copy(SOURCE/filename,output/filename)
    for folder in ('assets','chrome-extension'):copy(SOURCE/folder,output/folder)
    for filename in ('AGENT.md','mia.md','leo.md','emma.md'):
        copy(SOURCE/'agents'/filename,output/'agents'/filename)
    # A standalone CPython distribution, not a virtualenv tied to the builder PC.
    base=subprocess.check_output([str(dependencies/'.qt-env/Scripts/python.exe'),'-c','import sys;print(sys.base_prefix)'],text=True).strip()
    copy(Path(base),output/'runtime/python')
    site=dependencies/'.qt-env/Lib/site-packages'
    allowed=('PySide6','pyside6','shiboken6','psutil','uiautomation','comtypes')
    for path in site.iterdir():
        if path.name.startswith(allowed):copy(path,output/'runtime/python/Lib/site-packages'/path.name)
    copy(dependencies/'runtime/node',output/'runtime/node')
    copy(dependencies/'tools/node_modules',output/'tools/node_modules')
    for filename in ('package.json','package-lock.json'):copy(SOURCE/'tools'/filename,output/'tools'/filename)
    # Runtime source dependencies and notices remain available for replacement/inspection.
    manifest={str(p.relative_to(output)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
              for p in output.rglob('*') if p.is_file()}
    assert not any(p.startswith(('data/','cache/','backups/')) for p in manifest)
    (output/'build-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Clean payload:',len(manifest),'files')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--dependencies',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();build(args.dependencies.resolve(),args.output.resolve())
