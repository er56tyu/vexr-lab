import logging, sys, zipfile, base64
logging.disable(logging.CRITICAL)
sys.path.insert(0,'/home/arsham/vexr-lab/tools')
try:
    from loguru import logger; logger.remove()
except Exception: pass
from androguard.core.dex import DEX
SALT=b"VexR_2026"
z=zipfile.ZipFile('/home/arsham/vexr-lab/c2/D_Kyt7_lab_hardened.apk')
dex=DEX(z.read('classes.dex'))
want=open('/home/arsham/vexr-lab/c2/server_public.pem.b64').read().strip()
for cls in dex.get_classes():
    if cls.get_name()!='La/ky;': continue
    for m in cls.get_methods():
        if m.get_name()!='c': continue
        for ins in m.get_code().get_bc().get_instructions():
            o=ins.get_output()
            if 'const-string' in o and len(o)>200:
                lit=o.split('"',1)[1].rsplit('"',1)[0]
                bs=lit.encode('utf-8').decode('unicode_escape').encode('latin1')
                dec=bytes(bs[i]^SALT[i%len(SALT)] for i in range(len(bs))).decode('utf-8','replace')
                print("obf len:", len(bs))
                print("decoded:", dec[:60], "...")
                print("matches server key:", dec==want)
                break
