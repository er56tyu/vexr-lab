"""Re-encode assets/app_config.bin so every copy of the auth token agrees.

The blob is a repeating-XOR (key `VexR_Native_Key_2026`) over a JSON document.
The lab build left the original `auth_token` and `domain` in place, so this
rewrites both and re-encodes, keeping the byte length stable by padding the JSON
with spaces if the replacement is shorter (or failing loudly if it is longer).

    python3 -I reencode_config.py <decoded-dir> <token> <domain>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

KEY = b"VexR_Native_Key_2026"


def xor(data: bytes, key: bytes = KEY) -> bytes:
    return bytes(data[i] ^ key[i % len(key)] for i in range(len(data)))


def main() -> int:
    root = Path(sys.argv[1])
    token = sys.argv[2]
    domain = sys.argv[3]
    path = root / "assets/app_config.bin"

    raw = path.read_bytes()
    cfg = json.loads(xor(raw).decode("utf-8"))
    print(f"[*] before: auth_token={cfg.get('auth_token')!r} domain={cfg.get('domain')!r}")

    cfg["auth_token"] = token
    cfg["domain"] = domain

    plain = json.dumps(cfg, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(plain) > len(raw):
        print(f"[!] re-encoded blob is {len(plain)}B, original was {len(raw)}B; "
              f"cannot keep the file size stable")
        return 1
    plain = plain + b" " * (len(raw) - len(plain))

    path.write_bytes(xor(plain))
    print(f"[+] after : auth_token={token!r} domain={domain!r} ({len(raw)}B preserved)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
