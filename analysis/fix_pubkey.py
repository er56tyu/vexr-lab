"""Restore the XOR contract that sp0.d expects from sp0.g / ky(5).

Original sample:
    ky(5)  -> Base64.decode(OBFUSCATED_BLOB)   // attacker key, XOR-encoded blob
    sp0.d  -> SecurityRuntime.decode(that)     // XOR with "VexR_2026"
           -> wg1.a(base64String)              // Base64.decode -> RSA PublicKey

The lab patch replaced the obfuscated blob with the plain Base64 DER of our key
but kept the surrounding Base64.decode, which broke the contract: sp0.d XORs the
raw DER bytes, wg1.a then receives non-ASCII garbage, throws, returns null, and
sp0 emits "&k=" with no value. The server consequently reports KeyError('k').

Fix: make ky(5) return the Base64 *text* bytes XOR-encoded with the same salt,
so SecurityRuntime.decode restores exactly the Base64 string wg1.a expects.

    python3 -I fix_pubkey.py <decoded-dir>
"""
from __future__ import annotations

import base64
import re
import sys
from pathlib import Path

SALT = b"VexR_2026"
KEY_PATH = Path("smali/a/ky.smali")
PUBKEY_B64_PATH = Path("server_public.pem.b64")


def xor(data: bytes, key: bytes = SALT) -> bytes:
    return bytes(data[i] ^ key[i % len(key)] for i in range(len(data)))


def main() -> int:
    root = Path(sys.argv[1])
    ky = root / KEY_PATH
    if not ky.exists():
        print(f"[!] not found: {ky}")
        return 1

    b64 = PUBKEY_B64_PATH.read_text().strip()
    obfuscated = xor(b64.encode())
    print(f"[*] public key {len(b64)} b64 chars -> {len(obfuscated)} obfuscated bytes")

    src = ky.read_text(encoding="utf-8")

    # Match the whole pswitch_1 branch (label through its return-object).
    pat = re.compile(
        r"(:pswitch_1\n)"
        r"\s*const-string\s+(?P<reg>[vp]\d+),\s*\"[^\"]*\"\n"
        r".*?"
        r"\s*return-object\s+(?P=reg)\n",
        re.S,
    )
    m = pat.search(src)
    if not m:
        print("[!] could not locate the pswitch_1 key branch in ky.smali")
        return 1

    reg = m.group("reg")
    literal = "".join(f"\\u{b:04x}" for b in obfuscated)
    body = (
        f":pswitch_1\n"
        f"    const-string {reg}, \"{literal}\"\n"
        f"\n"
        f"    .line 21\n"
        f"    .line 22\n"
        f"    const-string v0, \"UTF-8\"\n"
        f"\n"
        f"    invoke-static {{v0}}, Ljava/nio/charset/Charset;->forName(Ljava/lang/String;)Ljava/nio/charset/Charset;\n"
        f"\n"
        f"    move-result-object v0\n"
        f"\n"
        f"    invoke-virtual {{{reg}, v0}}, Ljava/lang/String;->getBytes(Ljava/nio/charset/Charset;)[B\n"
        f"\n"
        f"    move-result-object {reg}\n"
        f"\n"
        f"    return-object {reg}\n"
    )
    src = src[: m.start()] + body + src[m.end():]
    ky.write_text(src, encoding="utf-8")
    print("[+] ky.smali pswitch_1 now returns XOR(base64Key, \"VexR_2026\") as bytes")

    recovered = xor(obfuscated).decode()
    print(f"[+] round-trip: {recovered[:40]}...  matches={recovered == b64}")

    from cryptography.hazmat.primitives import serialization

    pub = serialization.load_der_public_key(base64.b64decode(recovered))
    print(f"[+] RSA key still valid: {pub.key_size} bits")
    return 0 if recovered == b64 else 1


if __name__ == "__main__":
    sys.exit(main())
