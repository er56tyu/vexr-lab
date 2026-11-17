import logging, sys
logging.disable(logging.CRITICAL)
sys.path.insert(0,'/home/arsham/vexr-lab/tools')
try:
    from loguru import logger; logger.remove()
except Exception: pass
from androguard.core.dex import DEX
with open('/tmp/apk_decode/classes.dex','rb') as f:
    dex = DEX(f.read())
for cls in dex.get_classes():
    if cls.get_name()!='La/sp0;': continue
    for m in cls.get_methods():
        if m.get_name()!='e': continue
        code=m.get_code(); off=0
        for ins in code.get_bc().get_instructions():
            raw=ins.get_raw()
            print(f"  {off:04x} {ins.get_name():24s} {ins.get_output().strip()}")
            off+=len(raw)
