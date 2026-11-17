import sys, logging
sys.path.insert(0, '/home/arsham/vexr-lab/tools')
logging.disable(logging.CRITICAL)
try:
    from loguru import logger
    logger.remove()
except Exception:
    pass
from androguard.core.dex import DEX

TARGETS = {'getAuthToken', 'getAuthTokenNative', 'getSecretKey', 'getSecretKeyNative',
           'getBaseUrl', 'getBaseUrlNative', 'getKEY_SALT', 'KEY_SALT', 'AUTH_BYTES',
           'SECRET_BYTES', 'MASTER_KEY', 'HEADER_AUTH', 'URL_BYTES', 'CONFIG_NAME',
           'app_config', 'sudoport', 'url.txt', 'Fog_Key'}

with open('/tmp/apk_decode/classes.dex', 'rb') as f:
    dex = DEX(f.read())

print("=" * 72)
print("1) Method DEFINITIONS matching targets")
print("=" * 72)
for cls in dex.get_classes():
    cname = cls.get_name()
    for m in cls.get_methods():
        if m.get_name() in TARGETS:
            print(f"  DEF  {cname}->{m.get_name()}{m.get_descriptor()}")

print()
print("=" * 72)
print("2) Call sites / references matching targets")
print("=" * 72)
n = 0
for cls in dex.get_classes():
    cname = cls.get_name()
    for m in cls.get_methods():
        code = m.get_code()
        if not code:
            continue
        try:
            insns = list(code.get_bc().get_instructions())
        except Exception:
            continue
        for ins in insns:
            try:
                op = ins.get_output()
            except Exception:
                continue
            if any(t in op for t in TARGETS):
                print(f"  USE  {cname}->{m.get_name()}{m.get_descriptor()}")
                print(f"         {op.strip()}")
                n += 1
                break
print(f"\n(total {n} methods reference a target)")
