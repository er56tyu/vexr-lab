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
    print("FIELDS:")
    for fl in cls.get_fields():
        print(f"  {fl.get_access_flags_string():26s} {fl.get_name()} {fl.get_descriptor()}")
    print("\nMETHODS:")
    for m in cls.get_methods():
        print(f"  {m.get_access_flags_string():26s} {m.get_name()}{m.get_descriptor()}")
