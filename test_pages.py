import urllib.request

pages = [
    '/',
    '/standings/drivers/',
    '/standings/constructors/',
    '/races/',
    '/analytics/',
    '/auth/login/',
    '/auth/signup/',
    '/partials/standings-mini/',
    '/partials/recent-results/',
    '/leaderboard/',
    '/predictions/',
]

for p in pages:
    try:
        r = urllib.request.urlopen('http://127.0.0.1:8000' + p)
        print(f'{p}: {r.status} ({len(r.read())} bytes)')
    except Exception as e:
        print(f'{p}: ERROR - {e}')
