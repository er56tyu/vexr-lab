"""Decode the XOR-obfuscated constant arrays out of InternalResolver.<clinit>."""
import logging
import sys
import zipfile

logging.disable(logging.CRITICAL)
sys.path.insert(0, '/home/arsham/vexr-lab/tools')
try:
    from loguru import logger
    logger.remove()
except Exception:
    pass

from androguard.core.dex import DEX

FOG = b"Fog_Key_99_VexR"
APKS = [
    "/home/arsham/vexr_lab.apk",
    "/home/arsham/OXYGPT/D_Kyt7_original.apk",
    "/home/arsham/OXYGPT/D_Kyt7_patched.apk",
    "/home/arsham/Downloads/Telegram Desktop/D_Kyt7.apk",
    "/home/arsham/vexr-lab/c2/D_Kyt7_lab.apk",
]

FIELDS = ['URL_BYTES', 'SECRET_BYTES', 'AUTH_BYTES', 'HEADER_AUTH', 'HEADER_UA',
          'CONFIG_NAME', 'K_PORT', 'K_WEB', 'K_PERMS', 'K_FORCE', 'K_HIDE']


def xor(data, key):
    return bytes(data[i] ^ key[i % len(key)] for i in range(len(data)))


def analyze(path):
    z = zipfile.ZipFile(path)
    dex = DEX(z.read('classes.dex'))
    out = {}
    stub = None
    for cls in dex.get_classes():
        if cls.get_name() == 'Lcom/VexR/app/utils/NativeSecurity;':
            for m in cls.get_methods():
                if m.get_name() == 'loadNativeLibrary':
                    code = m.get_code()
                    ins = list(code.get_bc().get_instructions()) if code else []
                    stub = len(ins) == 1 and ins[0].get_name() == 'return-void'
        if cls.get_name() != 'Lcom/VexR/app/utils/InternalResolver;':
            continue
        for m in cls.get_methods():
            if m.get_name() != '<clinit>':
                continue
            payloads = []
            for ins in m.get_code().get_bc().get_instructions():
                if ins.get_name() == 'fill-array-data-payload':
                    raw = ins.get_raw()
                    # payload layout: 2-byte ident + 2-byte width + 4-byte size + data
                    size = int.from_bytes(raw[4:8], 'little')
                    payloads.append(raw[8:8 + size])
            for name, blob in zip(FIELDS, payloads):
                out[name] = xor(blob, FOG).decode('utf-8', 'replace')
    try:
        cfg = xor(z.read('assets/app_config.bin'), b"VexR_Native_Key_2026")
        out['_app_config'] = cfg.decode('utf-8', 'replace')
    except Exception:
        out['_app_config'] = '<none>'
    try:
        out['_url.txt'] = z.read('assets/url.txt').decode().strip()
    except Exception:
        out['_url.txt'] = '<none>'
    out['_stub'] = stub
    return out


for p in APKS:
    try:
        r = analyze(p)
    except Exception as exc:
        print(p, "->", exc)
        continue
    print("=" * 84)
    print(p)
    print(f"  loadNativeLibrary stubbed : {r['_stub']}")
    print(f"  URL_BYTES                 : {r['URL_BYTES']}")
    print(f"  AUTH_BYTES                : {r['AUTH_BYTES']}")
    print(f"  SECRET_BYTES              : {r['SECRET_BYTES']}")
    print(f"  url.txt                   : {r['_url.txt']}")
    print(f"  app_config                : {r['_app_config'][:220]}")
