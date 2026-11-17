import logging, sys, zipfile
logging.disable(logging.CRITICAL)
sys.path.insert(0,'/home/arsham/vexr-lab/tools')
try:
    from loguru import logger; logger.remove()
except Exception: pass
from androguard.core.dex import DEX

for label, apk in [('ORIGINAL','/home/arsham/OXYGPT/D_Kyt7_original.apk'),
                   ('LAB','/home/arsham/vexr-lab/c2/D_Kyt7_lab.apk')]:
    z=zipfile.ZipFile(apk); dex=DEX(z.read('classes.dex'))
    print("="*66); print(label)
    for cls in dex.get_classes():
        if cls.get_name()!='La/sp0;': continue
        for m in cls.get_methods():
            if m.get_name()!='<clinit>': continue
            outs=[i.get_output() for i in m.get_code().get_bc().get_instructions()]
            for i,o in enumerate(outs):
                if 'La/ky;-><init>' in o:
                    print("  ky init:", outs[i-1].strip(), "->", o.strip()[:60])
