"""Force the VexR lab build onto the academic C2, no matter what the native lib says.

`NativeSecurity` resolves three values through a native/Java split:

    getAuthToken()  -> isLoaded ? getAuthTokenNative() : InternalResolver.getToken()
    getBaseUrl()    -> isLoaded ? getBaseUrlNative()   : InternalResolver.getUrl()
    getSecretKey()  -> isLoaded ? getSecretKeyNative() : InternalResolver.getSecret()

The native branch is a liability for a lab build: it hands back the original
attacker token and the attacker base URL (https://tabahkar.shop). Rewriting each
getter to call the Java resolver unconditionally removes that branch entirely, so
neither the offensive token nor the attacker endpoint can be reached.

Run against an apktool-decoded tree:  python3 -I harden_native.py <decoded-dir>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

TARGET = Path("smali/com/VexR/app/utils/NativeSecurity.smali")

# (method signature, Java accessor that must always win)
GETTERS = [
    ("getAuthToken", "getToken"),
    ("getBaseUrl", "getUrl"),
    ("getSecretKey", "getSecret"),
]


def rewrite(src: str, method: str, fallback: str) -> tuple[str, bool]:
    """Replace a whole getter body with an unconditional call to the resolver."""
    pat = re.compile(
        r"\.method public final " + method + r"\(\)Ljava/lang/String;.*?\.end method",
        re.S,
    )
    m = pat.search(src)
    if not m:
        return src, False

    body = (
        f".method public final {method}()Ljava/lang/String;\n"
        f"    .locals 1\n"
        f"\n"
        f"    sget-object v0, Lcom/VexR/app/utils/InternalResolver;->INSTANCE:Lcom/VexR/app/utils/InternalResolver;\n"
        f"\n"
        f"    invoke-virtual {{v0}}, Lcom/VexR/app/utils/InternalResolver;->{fallback}()Ljava/lang/String;\n"
        f"\n"
        f"    move-result-object v0\n"
        f"\n"
        f"    return-object v0\n"
        f".end method"
    )
    return src[: m.start()] + body + src[m.end():], True


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    path = root / TARGET
    if not path.exists():
        print(f"[!] not found: {path}")
        return 1

    src = path.read_text(encoding="utf-8")
    ok = True
    for method, fallback in GETTERS:
        src, changed = rewrite(src, method, fallback)
        print(f"[{'+' if changed else '!'}] {method}() -> InternalResolver.{fallback}()")
        ok &= changed

    if not ok:
        print("[!] at least one getter was not rewritten; aborting")
        return 1

    path.write_text(src, encoding="utf-8")
    print(f"[+] wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
