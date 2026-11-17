import logging, sys, zipfile, base64
logging.disable(logging.CRITICAL)
sys.path.insert(0,'/home/arsham/vexr-lab/tools')
try:
    from loguru import logger; logger.remove()
except Exception: pass
from androguard.core.dex import DEX

# Does the ORIGINAL (attacker) APK have the same structure?
z = zipfile.ZipFile('/home/arsham/OXYGPT/D_Kyt7_original.apk')
dex = DEX(z.read('classes.dex'))
for cls in dex.get_classes():
    if cls.get_name() != 'La/ky;': continue
    for m in cls.get_methods():
        if m.get_name() != 'c': continue
        outs = [i.get_output() for i in m.get_code().get_bc().get_instructions()]
        for o in outs:
            if 'Base64;->decode' in o or 'const-string' in o:
                print(" ", o.strip()[:120])
