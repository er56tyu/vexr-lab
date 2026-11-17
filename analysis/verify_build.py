import logging, sys, zipfile, json
logging.disable(logging.CRITICAL)
sys.path.insert(0,'/home/arsham/vexr-lab/tools')
try:
    from loguru import logger; logger.remove()
except Exception: pass
from androguard.core.dex import DEX

FOG=b"Fog_Key_99_VexR"; NKEY=b"VexR_Native_Key_2026"
FIELDS=['URL_BYTES','SECRET_BYTES','AUTH_BYTES','HEADER_AUTH','HEADER_UA','CONFIG_NAME',
        'K_PORT','K_WEB','K_PERMS','K_FORCE','K_HIDE']
def xor(d,k): return bytes(d[i]^k[i%len(k)] for i in range(len(d)))

for p in ['/tmp/apk_build/D_Kyt7_lab_signed.apk']:
    z=zipfile.ZipFile(p); dex=DEX(z.read('classes.dex'))
    vals={}; getters={}
    for cls in dex.get_classes():
        if cls.get_name()=='Lcom/VexR/app/utils/InternalResolver;':
            for m in cls.get_methods():
                if m.get_name()!='<clinit>': continue
                pl=[]
                for ins in m.get_code().get_bc().get_instructions():
                    if ins.get_name()=='fill-array-data-payload':
                        raw=ins.get_raw(); sz=int.from_bytes(raw[4:8],'little')
                        pl.append(raw[8:8+sz])
                for n,b in zip(FIELDS,pl): vals[n]=xor(b,FOG).decode('utf-8','replace')
        if cls.get_name()=='Lcom/VexR/app/utils/NativeSecurity;':
            for m in cls.get_methods():
                if m.get_name() in ('getAuthToken','getBaseUrl','getSecretKey'):
                    outs=[i.get_output() for i in m.get_code().get_bc().get_instructions()]
                    native=[o for o in outs if 'Native()' in o]
                    java=[o for o in outs if 'InternalResolver' in o]
                    getters[m.get_name()]={'native_calls':len(native),'resolver_calls':len(java)}
    print("="*78); print(p)
    print("  URL_BYTES  :", vals.get('URL_BYTES'))
    print("  AUTH_BYTES :", vals.get('AUTH_BYTES'))
    print("  url.txt    :", z.read('assets/url.txt').decode().strip())
    cfg=json.loads(xor(z.read('assets/app_config.bin'),NKEY).decode())
    print("  cfg token  :", cfg['auth_token'])
    print("  cfg domain :", cfg['domain'])
    for k,v in getters.items(): print(f"  {k:14s}: {v}")
