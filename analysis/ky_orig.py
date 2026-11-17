import logging, sys, zipfile
logging.disable(logging.CRITICAL)
sys.path.insert(0,'/home/arsham/vexr-lab/tools')
try:
    from loguru import logger; logger.remove()
except Exception: pass
from androguard.core.dex import DEX
for label, apk in [('ORIGINAL','/home/arsham/OXYGPT/D_Kyt7_original.apk'),
                   ('LAB','/home/arsham/vexr-lab/c2/D_Kyt7_lab.apk')]:
    z = zipfile.ZipFile(apk)
    dex = DEX(z.read('classes.dex'))
    print("="*70); print(label)
    for cls in dex.get_classes():
        if cls.get_name() != 'La/ky;': continue
        for m in cls.get_methods():
            if m.get_name() != 'c': continue
            for ins in m.get_code().get_bc().get_instructions():
                o = ins.get_output().strip()
                if 'const-string' in o and len(o) > 40:
                    print("  KEY:", o[:100], "...")
                elif any(k in o for k in ('Base64','getBytes','Charset','return-object')):
                    print("  ", o[:100])
