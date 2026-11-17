import logging, sys, zipfile
logging.disable(logging.CRITICAL)
sys.path.insert(0,'/home/arsham/vexr-lab/tools')
try:
    from loguru import logger; logger.remove()
except Exception: pass
from androguard.core.dex import DEX

def dump(apk, label):
    z = zipfile.ZipFile(apk); dex = DEX(z.read('classes.dex'))
    for cls in dex.get_classes():
        if cls.get_name() != 'La/ky;': continue
        for m in cls.get_methods():
            if m.get_name() != 'c': continue
            print("="*70); print(label, "ky.c")
            for ins in m.get_code().get_bc().get_instructions():
                print("  ", ins.get_output().strip()[:130])

dump('/home/arsham/OXYGPT/D_Kyt7_original.apk','ORIGINAL')
dump('/home/arsham/vexr-lab/c2/D_Kyt7_lab.apk','LAB')
