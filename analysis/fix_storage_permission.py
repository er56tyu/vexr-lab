"""Make the onboarding flow actually ask for gallery access on Android 12 and below.

The bug
-------
`MainActivity.getMissingPermissions()` gates the storage entry on the API level:

    :cond_2
    sget v1, Landroid/os/Build$VERSION;->SDK_INT:I
    const/16 v2, 0x21                 # 33
    if-lt v1, v2, :cond_4            # API < 33 -> skip the whole block
    ...
    const-string v1, "storage"
    invoke-static {v1}, La/wd1;->d(...)Z
    if-eqz v1, :cond_4
    const-string v1, "android.permission.READ_MEDIA_IMAGES"
    invoke-virtual {v0, v1}, Ljava/util/ArrayList;->add(...)Z
    :cond_4

`READ_MEDIA_IMAGES` only exists from API 33. On anything older the branch falls
straight through to `:cond_4`, so `READ_EXTERNAL_STORAGE` -- the only storage
permission that works below 33 -- is never added to the request list. The string
appears zero times in the whole of MainActivity.

Consequences observed on the lab handset (Android 12):

  * the onboarding prompt never mentions files, so the operator has no reason to
    grant anything
  * `runScanGallery$1` checks `READ_EXTERNAL_STORAGE` on that API level, finds it
    denied, and returns early after posting a `gallery_denied` beacon
  * `gallery` therefore produces no artifact until the permission is granted by
    hand in Settings

The manifest is already correct -- it declares `READ_EXTERNAL_STORAGE` with
`android:maxSdkVersion="32"` and `READ_MEDIA_IMAGES` unqualified. Only the
request path is broken.

The fix
-------
Add the missing else-branch: below API 33, request `READ_EXTERNAL_STORAGE` when
the config enables storage. Same guard style as the surrounding code.

    python3 -I fix_storage_permission.py <decoded-dir>
"""
from __future__ import annotations

import sys
from pathlib import Path

TARGET = Path("smali/com/VexR/app/MainActivity.smali")

ANCHOR = """    if-lt v1, v2, :cond_4

    .line 70
    .line 71
    const-string v1, "notification"
"""

# Keep `if-lt v1, v2, :cond_4` but retarget it to a new else-branch. The original
# fall-through path (notification + storage/READ_MEDIA_IMAGES) becomes the API>=33
# arm; the new label sits between the two arrays.
REPLACEMENT = """    if-lt v1, v2, :cond_low

    .line 70
    .line 71
    const-string v1, "notification"
"""

LOW_BLOCK = """
    # API>=33 already added READ_MEDIA_IMAGES above; skip over the low-API arm.
    goto :cond_4
    :cond_low
    const-string v1, "storage"
    invoke-static {v1}, La/wd1;->d(Ljava/lang/String;)Z
    move-result v1
    if-eqz v1, :cond_4
    const-string v1, "android.permission.READ_EXTERNAL_STORAGE"
    invoke-virtual {v0, v1}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z
"""

# `:cond_4` is reused elsewhere in the method, so anchor on the tail of the
# storage block instead of the bare label.
JOIN = """    const-string v1, "android.permission.READ_MEDIA_IMAGES"

    .line 93
    .line 94
    invoke-virtual {v0, v1}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z

    .line 95
    .line 96
    .line 97
    :cond_4
"""


def main() -> int:
    root = Path(sys.argv[1])
    path = root / TARGET
    if not path.exists():
        print(f"[!] not found: {path}")
        return 1

    src = path.read_text(encoding="utf-8")
    if src.count(ANCHOR) != 1:
        print(f"[!] anchor found {src.count(ANCHOR)} times, expected exactly 1")
        return 1

    src = src.replace(ANCHOR, REPLACEMENT, 1)

    # The new branch must be jumped over by the API>=33 arm; it goes right before
    # the join point both arms fall into (`:cond_4` after the storage block).
    if src.count(JOIN) != 1:
        print(f"[!] join anchor found {src.count(JOIN)} times, expected exactly 1")
        return 1
    src = src.replace(JOIN, JOIN.replace("    :cond_4\n", "") + LOW_BLOCK.lstrip("\n") + "\n    :cond_4\n", 1)

    path.write_text(src, encoding="utf-8")
    print(f"[+] {TARGET}: added READ_EXTERNAL_STORAGE request for API < 33")
    return 0


if __name__ == "__main__":
    sys.exit(main())
