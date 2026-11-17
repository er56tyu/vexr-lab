import logging, sys
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
        code=m.get_code(); off=0
        payloads=[]
        for ins in code.get_bc().get_instructions():
            raw=ins.get_raw()
            print(f"  {off:04x} {ins.get_name():24s} {ins.get_output().strip()[:110]}")
            if ins.get_name()=='fill-array-data-payload':
                sz=int.from_bytes(raw[4:8],'little'); payloads.append(raw[8:8+sz])
            off+=len(raw)
        print()
        for n,p in zip(('e','f'), payloads):
            dec = bytes(p[i]^KEY[i%len(KEY)] for i in range(len(p)))
            print(f"  field {n}: len={len(p)} -> {dec!r}")
