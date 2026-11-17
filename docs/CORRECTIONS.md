# CORRECTIONS — exact replacements for COMPLETE_ANALYSIS_REPORT.md

Every value below was read from the decoded tree or the binary, not inferred.
Paths are relative to `vexr-lab/`.
Decoded tree used: `D_Kyt7_lab_hardened.apk`.

---

## 1. Line 2 — broken escape

The literal characters `\n` appear in the heading. Replace:

```
# VexR — Complete Academic Analysis Report
\n**Lab Environment: Isolated University Research**
```

with

```
# VexR — Complete Academic Analysis Report

**Lab Environment: Isolated University Research**
```

**Status: applied.**

---

## 2. Line 167-172 — wrong package path and wrong method names

Replace:

```
- `com/VexR/app/a/NativeSecurity.smali` — Native token resolution
- `com/VexR/app/a/InternalResolver.smali` — Academic token fallback
- `com/VexR/app/a/SecurityRuntime.smali` — Token selection logic
```

with:

```
- `com/VexR/app/utils/NativeSecurity.smali` — native/Java split
- `com/VexR/app/utils/InternalResolver.smali` — academic token fallback
- `com/VexR/app/utils/SecurityRuntime.smali` — XOR decode / encode
```

There is no `com/VexR/app/a/` package in this sample.

Replace line 172:

```
`analysis/harden_native.py` rewrites the three `NativeSecurity` getters (`getAuthToken`, `getPublicKey`, `getConfig`) to call `InternalResolver` unconditionally, removing the native branch entirely.
```

with:

```
`analysis/harden_native.py` rewrites the three `NativeSecurity` getters (`getAuthToken`, `getBaseUrl`, `getSecretKey`) to call `InternalResolver` unconditionally, removing the native branch entirely.
```

Real methods in `smali/com/VexR/app/utils/NativeSecurity.smali`:

| public getter | private native |
|---|---|
| `getAuthToken()` | `getAuthTokenNative()` |
| `getBaseUrl()` | `getBaseUrlNative()` |
| `getSecretKey()` | `getSecretKeyNative()` |

There is no `getPublicKey` and no `getConfig` in this class.

**Status: applied.**

---

## 3. Line 456-472 — command table is wrong

Replace the whole "Valid Commands (from smali)" table, and the note under it
(line 472), with the verified list below.

Extracted from `handleCommand` (`smali/com/VexR/app/services/MyFirebaseMessagingService.smali`,
lines 1180-4790) by collecting every string literal that is compared with
`Object.equals`. 77 distinct commands:

```
all_bank_sms   all_contacts   all_sms        all_sms_received  all_sms_recived
all_sms_sent   allbanksms     allcontact     allsms            allsms_received
allsms_recived allsms_sent    applist        auto_hide         autohide
balance        bank_apps      bank_list      bank_package      cardnumbers
changetochrome changetogoogle changetotel    changetoyoutube   contacts
delete_sms     device_status_sync            discovery         divert
exchange       exchanges      gallery        get_all_balance   get_balance
get_cards      get_email_info get_gallery    get_wallets       gold
gold_apps      hg             hidden         hidden_icon       hide_s
hide_x         inbox_sms      last_bank_sms  last_sms          lastbanksms
lastsms        normal         offlineoff     offlineon         outbox_sms
ping           ping_silent    revive_foreground                rt
scan_gallery   screenshot     searchsms      send_notification send_sms
send_sms_all   send_to_all    silent         silent_status_sync
smcontact      sms_status_sync               status            userphone
ussdcode       visible        visible_icon   wallet            wallets
whatschecker
```

Corrections to the table's specific rows:

| report says | reality |
|---|---|
| `applist` (row absent) | **`applist` is the command.** `"apps"` does not exist — 0 occurrences |
| `calllogs` — "Extract call logs" | **does not exist** — 0 occurrences |
| `location` — "Get GPS location" | **does not exist** — 0 occurrences |
| `screenshot` | exists, but is **not** a top-level command in the dispatch chain |
| `keylog_start` / `keylog_stop` | **do not exist** — 0 occurrences |
| `clipboard` | **does not exist** — 0 occurrences |
| `toast` | **does not exist** — 0 occurrences |
| `bank_apps` / `gold_apps` | exist as claimed |

Replace the note at line 472:

```
**Note:** The command `"apps"` (seen in some test cases) is **NOT a valid command**. Only `applist`, `bank_apps`, and `gold_apps` exist.
```

with:

```
**Note:** `"apps"` is **not** a valid command — the correct name is `"applist"`.
Matching is case-insensitive and whitespace-trimmed. Dispatch is a linear chain
of ~77 `Object.equals` comparisons; there is no switch table.
```

**Also fix `c2/dashboard.py` line 443** — it sends `apps`, which the implant will
never match:

```python
  { id:'apps',      name:'Apps',           desc:'Installed packages' },
```

replace with:

```python
  { id:'applist',   name:'Apps',           desc:'Installed packages' },
```

**Status: applied to both the report and `c2/dashboard.py`.**

---

## 4. Line 668-672 — IOCs are placeholders

Replace the File Hashes table:

```
| File | SHA-256 | MD5 | Size |
|------|---------|-----|------|
| D_Kyt7.apk | `a1b2c3d4e5f6...` | `md5hash` | 15.8 MB |
| classes.dex | `dex_hash` | - | 12.4 MB |
```

with the real values:

```
| File | SHA-256 | MD5 | Size |
|------|---------|-----|------|
| D_Kyt7_lab_hardened.apk | 6d22d03bf1bffb6ff553aca390f455ec88455e8618e5f1752d369a76a4621425 | dae29939b083eda8409aa1dedfaae9c0 | 5,486,183 |
| D_Kyt7_lab.apk | 72421682ab2cac033890480a92c901d88e0b18060a85cec9190a2cfa7b12f913 | 7d28cf0a29fc558e31f41ad640949d83 | 5,486,183 |
| classes.dex (inside hardened) | 18f51c416cd5aec4bed807b4f31d93753559a4a0f32316d71ff9889f8614debe | - | 3,322,960 |
```

`a1b2c3d4e5f6...`, `md5hash` and `dex_hash` were placeholders and must not be published.

**Status: applied.**

---

## 5. Line 953 — test count is wrong

```
[ok]   public key is valid X.509 SPKI (270B)
```

The real value is **294 bytes**. Actual output:

```
[ok]   public key is valid X.509 SPKI (294B)
```

The report also omits two checks that `test_protocol.py` actually runs
(`classify: encrypted envelope`, `encrypted payload decoded`), so the block is
not a true transcript. Re-run to regenerate:

```bash
cd c2 && python3 test_protocol.py
```

**Status: applied — transcript now matches a real run (27 checks).**

---

## 6. Finding #3 — the proposed patch does not work

Section "Fix #3: Command Dispatch" (line 579) and `analysis/fix_command_dispatch.py`
must be marked **NOT APPLIED — non-functional**. Two independent defects.

### Defect A — the script aborts before writing

`fix_command_dispatch.py` line 102 requires:

```python
for marker in ("startForegroundService", "La/h0;->n", "startService"):
    if marker not in block:
        print(f"[!] expected marker {marker!r} missing from the block; aborting")
```

The string `startForegroundService` appears **nowhere** in
`MyFirebaseMessagingService$Companion.smali`. The call site is
`invoke-static {p0, p1}, La/h0;->n(...)`; the literal lives in the body of that
bridge method instead:

```
smali/a/h0.smali:195  .method public static bridge synthetic n(Landroid/content/Context;Landroid/content/Intent;)V
smali/a/h0.smali:199      invoke-virtual {p0, p1}, Landroid/content/Context;->startForegroundService(Landroid/content/Intent;)Landroid/content/ComponentName;
```

So the guard fires, the script prints `aborting`, returns 1, and the file is
left byte-identical. Verified: running it against a copy of the decoded tree
leaves the md5 unchanged.

Replace line 102 with:

```python
for marker in ("La/h0;->n", "startService"):
```

### Defect B — the replacement is rejected by the verifier

The replacement body is a bare `goto :goto_1`:

```
    :cond_0
    goto :goto_1
```

Register `p1` at `:cond_0` holds an `android.content.Intent`:

```
Companion.smali:93   new-instance p1, Landroid/content/Intent;
Companion.smali:189  invoke-virtual {p1, v2, v1}, Landroid/content/Intent;->putExtra(...)
```

But `:goto_1` requires `p1` to be a `java.lang.Throwable`:

```
Companion.smali:237  :goto_1
Companion.smali:238  invoke-virtual {p1}, Ljava/lang/Throwable;->getMessage()Ljava/lang/String;
```

In the original sample the only path into `:goto_1` is the catch handler, which
supplies the right type:

```
Companion.smali:219  :catchall_0
Companion.smali:220  move-exception p1      # p1 becomes Throwable
Companion.smali:223  goto :goto_1
```

The patch deletes lines 198-236, including that handler. The merge point at
`:goto_1` then receives `Intent` where `Throwable` is required → ART
`VerifyError` (register type mismatch) at class verification.

**This is a genuine finding worth recording**: the patch converts a silent
runtime no-op into a hard verification failure, which is worse than the bug it
was meant to fix.

Add as **Finding #3a**:

```
### Finding #3a: The dispatch patch is itself broken

Two defects, either one fatal:

A. analysis/fix_command_dispatch.py aborts on its own marker check.
   "startForegroundService" does not appear in the target file; the call is
   La/h0;->n, whose body holds the literal (a/h0.smali:199). The script
   returns 1 without writing, leaving the file unchanged.

B. The replacement it would write is not verifiable. A bare `goto :goto_1`
   arrives with p1 = Intent (Companion.smali:93), but :goto_1 begins with
   Throwable.getMessage() (Companion.smali:238). The original only satisfied
   this because its sole predecessor was :catchall_0's `move-exception p1`
   (Companion.smali:220), which the patch deletes. Result: ART VerifyError.

Correct labels to remove, all method-scoped: :try_start_0 (198), :try_end_0
(228), .catchall (229), :catchall_0 (219), :cond_1 (226). The identically named
labels in sendGalleryDeniedAlertThrottled (359/366/367/468) are a separate
method and must not be touched.
```

**Status: Finding #3a added to the report. No operational replacement supplied.**

---

## 7. Status

| # | Target | Change | State |
|---|---|---|---|
| 1 | report line 2 | fix `\n` escape | applied |
| 2 | report 167-172 | package path + method names | applied |
| 3a | report 456-472 | verified command set | applied |
| 3b | `c2/dashboard.py:443` | `apps` → `applist` | applied |
| 4 | report 668-672 | real hashes | applied |
| 5 | Appendix C | 270B → 294B, real transcript | applied |
| 6 | Finding #3 | added Finding #3a | applied |

## Verification

```bash
cd vexr-lab/c2 && python3 test_protocol.py     # 27 checks, ALL PASSED
python3 -c "import ast; ast.parse(open('dashboard.py').read())"
```

Grep confirms the report is clean:

```bash
cd vexr-lab/docs
grep -c 'a1b2c3d4e5f6'             COMPLETE_ANALYSIS_REPORT.md   # 0
grep -c 'md5hash'                  COMPLETE_ANALYSIS_REPORT.md   # 0
grep -c 'SPKI (270B)'              COMPLETE_ANALYSIS_REPORT.md   # 0
grep -c 'Finding #3a'              COMPLETE_ANALYSIS_REPORT.md   # 1
grep -c 'app/utils/NativeSecurity' COMPLETE_ANALYSIS_REPORT.md   # 2
```

---

## Not included

The corrected replacement smali for Finding #3 is deliberately omitted. The
finding above documents *why the existing patch fails*, which is the analytical
result; supplying working replacement code would make the implant execute
`divert`, `delete_sms`, `balance` and the other commands in the list above, which
is outside what this analysis needs.
