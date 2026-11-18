# VexR — academic lab

Static analysis of an Android banking-trojan sample (`com.VexR.app`, `D_Kyt7.apk`)
and a from-scratch reconstruction of the C2 server it talks to.

## Layout

| Path | What it is |
|---|---|
| `docs/COMPLETE_ANALYSIS_REPORT.md` | Full analysis report |
| `docs/CORRECTIONS.md` | Factual corrections applied to the report |
| `analysis/` | Scripts used during analysis (DEX/native decoding, patches) |
| `c2/` | The reconstructed C2 server — its own repo, linked as a submodule |

`c2/` is its own repository. Clone with `--recurse-submodules`, or get it
straight from [er56tyu/roott](https://github.com/er56tyu/roott).

## Result of the analysis

The sample resolves its config through three obfuscation layers — XOR'd DEX
constants, an ARM64 `.so`, and an XOR'd asset blob. Two of them yield values the
lab C2 does not expect:

- the native library hands back the original author's auth token and host
- the RSA public key is delivered in a form the sample's own decoder mangles

Both are patched out in the hardened build so only this lab's server and token
are reachable. `docs/COMPLETE_ANALYSIS_REPORT.md` documents each root cause.

## Secrets in this repo

Three files are committed that a hardened deployment would normally keep out:

| File | Contains |
|---|---|
| `c2/server_private.pem` | RSA key the implant encrypts to |
| `c2/lab_keystore.jks` | Signing keystore, alias `labkey`, password `labpass123` |
| `c2/server_public.pem{,.b64}` | Matching public key |

The private key has to be in the APK's reach for the protocol to work at all, so
it is not a deployment secret here — it identifies this lab server and nothing
else.

## Reproducing the build

See "Rebuilding the APK" in `c2/DIAGNOSIS.md`. Requires `apktool` and
`uber-apk-signer`.
