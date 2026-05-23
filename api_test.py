import urllib.request, json
from urllib.error import HTTPError

data = json.dumps({'url': 'https://www.youtube.com/watch?v=l9srwSYo3pk', 'platform': 'youtube'}).encode()
req = urllib.request.Request('http://localhost:8866/api/parse', data=data, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())
        d = result.get('data', {})
        print('SUCCESS!')
        print('Title:', d.get('title'))
        fmts = d.get('formats', [])
        print(f'Formats: {len(fmts)}')
        for f in fmts[:5]:
            print(f"  {f['res']} {f['note']} need_merge={f['need_merge']}")
except HTTPError as e:
    print('HTTP ERROR:', e.code)
    print(e.read().decode('utf-8', errors='ignore'))
except Exception as e:
    print('FAIL:', e)
