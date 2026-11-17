import json, re, collections, sys

path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/livelog.json'
d = json.load(open(path))
entries = d.get('log', [])
print("entries:", len(entries))

ips = collections.Counter()
times = []
for e in entries:
    m = re.search(r'from ([\d.]+)', e['message'])
    if m:
        ips[m.group(1)] += 1
        times.append(e['ts'])

print("distinct rejected IPs:", len(ips))
for ip, c in ips.most_common(40):
    print(f"   {ip:16s} {c}")
if times:
    print("reject window:", min(times), "->", max(times))

auth = [e for e in entries
        if 'beacon action=' in e['message'] or 'file received' in e['message']]
print("authorized entries:", len(auth))
for e in auth[:10]:
    print("   ", e['ts'], e['message'])
