import logging, sys, zipfile
logging.disable(logging.CRITICAL)
sys.path.insert(0,'/home/arsham/vexr-lab/tools')
try:
    from loguru import logger; logger.remove()
except Exception: pass
from androguard.core.dex import DEX
z=zipfile.ZipFile('/home/arsham/OXYGPT/D_Kyt7_original.apk')
dex=DEX(z.read('classes.dex'))
for cls in dex.get_classes():
    if cls.get_name()!='La/ky;': continue
    for m in cls.get_methods():
        if m.get_name()!='c': continue
        off=0
        for ins in m.get_code().get_bc().get_instructions():
            print(f"  {off:04x} {ins.get_name():22s} {ins.get_output().strip()[:120]}")
            off+=len(ins.get_raw())
