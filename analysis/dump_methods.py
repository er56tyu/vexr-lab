import sys, logging
sys.path.insert(0, '/home/arsham/vexr-lab/tools')
logging.disable(logging.CRITICAL)
try:
    from loguru import logger
    logger.remove()
except Exception:
    pass
from androguard.core.dex import DEX

WANT = {
 'Lcom/VexR/app/utils/NativeSecurity;': {'getAuthToken','getBaseUrl','getSecretKey','<clinit>'},
 'Lcom/VexR/app/utils/SecurityRuntime;': {'decode','encode','a','<clinit>'},
 'Lcom/VexR/app/utils/InternalResolver;': {'decode','getToken','getSecret','getUrl','getConfigName','getAuthHeader','<clinit>'},
}
with open('/tmp/apk_decode/classes.dex','rb') as f:
    dex = DEX(f.read())
for cls in dex.get_classes():
    cname = cls.get_name()
    if cname not in WANT: continue
    for m in cls.get_methods():
        if m.get_name() not in WANT[cname]: continue
        print("=" * 72)
        print(f"{cname}->{m.get_name()}{m.get_descriptor()}  access={m.get_access_flags_string()}")
        print("=" * 72)
        code = m.get_code()
        if not code:
            print("  <no code>"); continue
        for ins in code.get_bc().get_instructions():
            try:
                print("   ", ins.get_output().rstrip())
            except Exception as e:
                print("    ??", e)
        print()
