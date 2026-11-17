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
    if cls.get_name() != 'Lcom/VexR/app/utils/InternalResolver;': continue
    print("METHODS:")
    for m in cls.get_methods():
        print("  ", m.get_name()+m.get_descriptor())
