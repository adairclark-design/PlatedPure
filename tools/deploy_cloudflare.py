"""
PlatedPure — Cloudflare Pages Direct Upload v2 (complete protocol).
Phase 1: POST to /assets/upload with actual file bytes (multipart)
Phase 2: POST to /deployments with manifest to create live deployment
"""
import os, hashlib, mimetypes, requests, json, base64

TOKEN      = "cfut_XpRiZHJ0nXYW08IuhfXPOlxdAczTTYEZDosFz62l05b1cbc7"
ACCOUNT_ID = "54a1e137e8cc02458998e3fdd16fae94"
PROJECT    = "platedpure-app"
DIST       = "/Users/adairclark/Desktop/AntiGravity/PlatedPure/web/dist"
BASE       = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/pages/projects/{PROJECT}"
HEADERS    = {"Authorization": f"Bearer {TOKEN}"}

def get_mime(path):
    mime, _ = mimetypes.guess_type(path)
    return mime or "application/octet-stream"

# ── Collect all files ─────────────────────────────────────────────────────────
manifest   = {}
files_data = {}
for root, _, fnames in os.walk(DIST):
    for f in fnames:
        full = os.path.join(root, f)
        rel  = "/" + os.path.relpath(full, DIST)
        data = open(full, "rb").read()
        sha  = hashlib.sha256(data).hexdigest()
        manifest[rel]   = sha
        files_data[sha] = (rel, full, data)

print(f"📁 {len(manifest)} files found\n")

# ── Phase 1: Request upload token (list of needed hashes + JWT) ──────────────
print("📡 Requesting upload token from CF...")
r = requests.post(
    f"{BASE}/deployments",
    headers=HEADERS,
    files={"manifest": (None, json.dumps(manifest), "application/json")}
)
resp = r.json()

# If CF returns no required_file_hashes, it means everything is natively cached and we're done.
if resp.get("success") and resp.get("result", {}).get("id"):
    result = resp.get("result", {})
    needed = result.get("required_file_hashes", [])
    if len(needed) == 0:
        print(f"✅ All chunks natively cached on Edge. Proceeding to finalize...")
    upload_jwt = result.get("jwt", TOKEN)
else:
    print(f"❌ Failed to request deployment: {resp}")
    exit(1)

print(f"📤 Need to upload {len(needed)} files...")

# ── Phase 2: Upload each required file ───────────────────────────────────────
UPLOAD_URL = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/pages/assets/upload"
for sha in needed:
    if sha not in files_data:
        print(f"  ⚠ Hash {sha[:8]} not found locally, skipping")
        continue
    rel, full, data = files_data[sha]
    mime = get_mime(full)
    upload_resp = requests.post(
        UPLOAD_URL,
        headers={"Authorization": f"Bearer {upload_jwt}"},
        files={sha: (os.path.basename(full), data, mime)}
    )
    status = upload_resp.json().get("success", False)
    print(f"  {'✅' if status else '❌'} {rel} ({len(data)/1024:.1f}kb)")

# ── Phase 3: Finalize the deployment ─────────────────────────────────────────
print("\n🚀 Finalizing deployment...")
final_r = requests.post(
    f"{BASE}/deployments",
    headers=HEADERS,
    files={"manifest": (None, json.dumps(manifest), "application/json")}
)
final = final_r.json()
print(json.dumps(final, indent=2))

if final.get("success"):
    dep = final["result"]
    print(f"\n✅ LIVE: https://platedpure-app.pages.dev")
    print(f"🔗 Preview: {dep.get('url')}")
