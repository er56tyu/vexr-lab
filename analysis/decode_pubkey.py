import logging, sys, base64
logging.disable(logging.CRITICAL)
sys.path.insert(0,'/home/arsham/vexr-lab/tools')
try:
    from loguru import logger; logger.remove()
except Exception: pass
from androguard.core.dex import DEX
with open('/tmp/apk_decode/classes.dex','rb') as f:
    dex = DEX(f.read())
KEY=b"VexR_2026"
for cls in dex.get_classes():
    if cls.get_name()!='La/sp0;': continue
    for m in cls.get_methods():
        if m.get_name()!='<clinit>': continue
        pl=[]
        for ins in m.get_code().get_bc().get_instructions():
            if ins.get_name()=='fill-array-data-payload':
                raw=ins.get_raw(); sz=int.from_bytes(raw[4:8],'little')
                pl.append(raw[8:8+sz])
        print("payload count:", len(pl))
        for i,p in enumerate(pl):
            dec=bytes(p[i2]^KEY[i2%len(KEY)] for i2 in range(len(p)))
            print(f"  [{i}] len={len(p)} -> {dec[:80]!r}")
