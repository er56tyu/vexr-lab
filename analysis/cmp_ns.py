import logging, sys, zipfile, tempfile, os
logging.disable(logging.CRITICAL)
sys.path.insert(0,'/home/arsham/vexr-lab/tools')
try:
    from loguru import logger; logger.remove()
except Exception: pass
from androguard.core.dex import DEX

def show(apk, label):
    print("="*80)
    print(label)
    z = zipfile.ZipFile(apk)
    data = z.read('classes.dex')
    dex = DEX(data)
    for cls in dex.get_classes():
        if cls.get_name() != 'Lcom/VexR/app/utils/NativeSecurity;': continue
        for m in cls.get_methods():
            if m.get_name() not in ('loadNativeLibrary','<clinit>','<init>','getAuthToken'): continue
            code = m.get_code()
            print(f"\n  --- {m.get_name()}{m.get_descriptor()} ---")
            if not code:
                print("     <no code>"); continue
            off=0
            for ins in code.get_bc().get_instructions():
                raw=ins.get_raw()
                print(f"     {off:04x} {ins.get_name():24s} {ins.get_output().strip()}")
                off+=len(raw)

for apk, label in [
    ('/home/arsham/OXYGPT/D_Kyt7_original.apk', 'ORIGINAL'),
    ('/home/arsham/vexr-lab/c2/D_Kyt7_lab.apk',  'LAB (installed?)'),
]:
    show(apk, label)
