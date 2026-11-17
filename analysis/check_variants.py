import logging, sys, zipfile
logging.disable(logging.CRITICAL)
sys.path.insert(0,'/home/arsham/vexr-lab/tools')
try:
    from loguru import logger; logger.remove()
except Exception: pass
from androguard.core.dex import DEX
FOG = b"Fog_Key_99_VexR"
FIELDS = ['URL_BYTES','SECRET_BYTES','AUTH_BYTES','HEADER_AUTH','HEADER_UA','CONFIG_NAME',
          'K_PORT','K_WEB','K_PERMS','K_FORCE','K_HIDE']
def xor(d,k): return bytes(d[i]^k[i%len(k)] for i in range(len(d)))
for p in ['/tmp/D_Kyt7_lab_rebuilt.apk','/tmp/D_Kyt7_lab_v2.apk','/home/arsham/vexr-lab/c2/D_Kyt7_lab.apk']:
    try:
        z=zipfile.ZipFile(p); dex=DEX(z.read('classes.dex'))
    except Exception as e:
        print(p,"->",e); continue
    stub=None; vals={}
    for cls in dex.get_classes():
        if cls.get_name()=='Lcom/VexR/app/utils/NativeSecurity;':
            for m in cls.get_methods():
                if m.get_name()=='loadNativeLibrary':
                    ins=list(m.get_code().get_bc().get_instructions()) if m.get_code() else []
                    stub = len(ins)==1 and ins[0].get_name()=='return-void'
        if cls.get_name()!='Lcom/VexR/app/utils/InternalResolver;': continue
        for m in cls.get_methods():
            if m.get_name()!='<clinit>': continue
            pl=[]
            for ins in m.get_code().get_bc().get_instructions():
                if ins.get_name()=='fill-array-data-payload':
                    raw=ins.get_raw(); size=int.from_bytes(raw[4:8],'little')
                    pl.append(raw[8:8+size])
            for n,b in zip(FIELDS,pl): vals[n]=xor(b,FOG).decode('utf-8','replace')
    print("="*80); print(p)
    print("  stubbed :", stub)
    print("  URL     :", vals.get('URL_BYTES'))
    print("  TOKEN   :", vals.get('AUTH_BYTES'))
