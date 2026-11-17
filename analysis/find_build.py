import logging, sys, zipfile, os
logging.disable(logging.CRITICAL)
sys.path.insert(0,'/home/arsham/vexr-lab/tools')
try:
    from loguru import logger; logger.remove()
except Exception: pass
from androguard.core.dex import DEX

FOG = b"Fog_Key_99_VexR"
apks = [
 "/home/arsham/vexr_lab.apk",
 "/home/arsham/OXYGPT/D_Kyt7_original.apk",
 "/home/arsham/OXYGPT/D_Kyt7_patched.apk",
 "/home/arsham/Downloads/Telegram Desktop/D_Kyt7.apk",
 "/home/arsham/vexr-lab/c2/D_Kyt7_lab.apk",
]
for p in apks:
    if not os.path.exists(p): continue
    z = zipfile.ZipFile(p)
    dex = DEX(z.read('classes.dex'))
    url_bytes = token_bytes = None
    stub = None
    for cls in dex.get_classes():
        if cls.get_name() != 'Lcom/VexR/app/utils/InternalResolver;': continue
        for m in cls.get_methods():
            if m.get_name() != '<clinit>': continue
            code = m.get_code()
            payloads = []
            for ins in code.get_bc().get_instructions():
                if ins.get_name() == 'fill-array-data-payload':
                    payloads.append(ins.get_raw()[4:] if False else None)
            # use get_output to get the bytes
            blobs = []
            for ins in code.get_bc().get_instructions():
                if ins.get_name() == 'fill-array-data-payload':
                    try:
                        out = ins.get_output()
                        blobs.append(out)
                    except Exception: pass
    for cls in dex.get_classes():
        if cls.get_name() != 'Lcom/VexR/app/utils/NativeSecurity;': continue
        for m in cls.get_methods():
            if m.get_name() == 'loadNativeLibrary':
                code = m.get_code()
                ins = list(code.get_bc().get_instructions()) if code else []
                stub = (len(ins)==1 and ins[0].get_name()=='return-void')
    print("="*84)
    print(p)
    print("  loadNativeLibrary stubbed:", stub)
