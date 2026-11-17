import logging, sys, zipfile, os
logging.disable(logging.CRITICAL)
sys.path.insert(0,'/home/arsham/vexr-lab/tools')
try:
    from loguru import logger; logger.remove()
except Exception: pass
from androguard.core.dex import DEX

RAILWAY = b"vexr-lab-c2-academic-production"
FOG = b"Fog_Key_99_VexR"
NKEY = b"VexR_Native_Key_2026"
TOK_OFF = b"VexR_Auth_99x_2026_Secured"
TOK_ACA = b"VexR_Lab_Academic_Token_2026"

apks = [
 "/home/arsham/vexr_lab.apk",
 "/home/arsham/OXYGPT/D_Kyt7_original.apk",
 "/home/arsham/OXYGPT/D_Kyt7_patched.apk",
 "/home/arsham/Downloads/Telegram Desktop/D_Kyt7.apk",
 "/home/arsham/vexr-lab/c2/D_Kyt7_lab.apk",
]

def xor_dec(data, key):
    return bytes(data[i]^key[i%len(key)] for i in range(len(data)))

for p in apks:
    if not os.path.exists(p): continue
    print("="*84)
    print(p)
    z = zipfile.ZipFile(p)
    dex = z.read('classes.dex')

    # stub detection: search for loadNativeLibrary bytecode pattern
    d2 = DEX(dex)
    stub = None
    for cls in d2.get_classes():
        if cls.get_name() != 'Lcom/VexR/app/utils/NativeSecurity;': continue
        for m in cls.get_methods():
            if m.get_name() == 'loadNativeLibrary':
                code = m.get_code()
                ins = list(code.get_bc().get_instructions()) if code else []
                stub = (len(ins)==1 and ins[0].get_name()=='return-void')
    print(f"  loadNativeLibrary stubbed : {stub}")

    # which tokens present (XOR with Fog key, any offset)
    hits = {}
    for name, t in (('offensive', TOK_OFF), ('academic', TOK_ACA)):
        found = False
        for off in range(len(FOG)):
            if t in xor_dec(dex, FOG[off:] + FOG[:off]):
                found = True; break
        if not found and t in dex: found = 'PLAINTEXT'
        hits[name] = found
    print(f"  tokens in dex             : {hits}")

    # app_config.bin token
    try:
        cfg = xor_dec(z.read('assets/app_config.bin'), NKEY)
        import re
        m = re.search(rb'"auth_token"\s*:\s*"([^"]*)"', cfg)
        print(f"  app_config auth_token     : {m.group(1).decode() if m else '?'}")
        m2 = re.search(rb'"domain"\s*:\s*"([^"]*)"', cfg)
        print(f"  app_config domain         : {m2.group(1).decode() if m2 else '?'}")
    except Exception as e:
        print("  app_config.bin            :", e)

    # url.txt
    try: print("  url.txt                   :", z.read('assets/url.txt').decode().strip())
    except Exception: print("  url.txt                   : <none>")

    # native lib contains railway?
    for n in z.namelist():
        if n.endswith('libvexr_native.so') and 'arm64' in n:
            so = z.read(n)
            # railway string is XORed in rodata with VexR_Native_Key_2026
            enc = bytes(RAILWAY[i]^NKEY[i%len(NKEY)] for i in range(len(RAILWAY)))
            print(f"  arm64 lib has railway URL : {enc in so}  (encoded)")
