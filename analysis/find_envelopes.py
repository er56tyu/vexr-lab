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
    for m in cls.get_methods():
        code = m.get_code()
        if not code: continue
        outs=[i.get_output() for i in code.get_bc().get_instructions()]
        if any('"v=3&d="' in o for o in outs):
            print("="*76)
            print(f"{cls.get_name()}->{m.get_name()}{m.get_descriptor()}")
