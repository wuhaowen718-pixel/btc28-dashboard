#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
比特28 实时开奖看板 —— 云端部署版（Render / Fly.io / 任何 Python 托管）
用 Flask 提供：
    /          看板页面
    /api/issues 开奖数据 JSON
"""
import json
import os
import ssl
import time
import gzip
import urllib.request

from flask import Flask, jsonify, send_from_directory

app = Flask(__name__, static_folder=os.path.dirname(os.path.abspath(__file__)))

BASE = 'https://pqlmtea2xl.hhdkz.com'
API_ISSUE = '/api/v1/lottery/sale/issue?gameId=140&gameRoomId=113&count=100&isFirst=1'
API_INDEX = '/api/v1/lottery/index?gameId=140&gameRoomId=113'

TOKEN = 'SGTpYZKmgMaRK1uyxh99uXh/rx0scPUCDFojYMuvJigoQ+fKYY2yneovo/gE0FRk'
TS = '1794936970815231'

HEADERS = {
    'versionCode': '125',
    'version': '1.2.5',
    'device': 'android',
    'timestamp': TS,
    'merid': '1051',
    'identifier': 'com.xsdfsdfss.yyeshdf',
    'customerUID': '4416380',
    'token': TOKEN,
    'mobileModel': 'XIAOMI 2512BPNDAC',
    'deviceVersion': 'Android 9',
    'Site-Code': 'a2',
    'Authorization': '5cbff709-c145-4568-b098-43a1daad3673',
    'line': 'line3',
    'User-Agent': 'okhttp/3.12.1',
    'Accept-Encoding': 'gzip',
}

_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE

_cache = {'payload': None, 'ts': 0}
CACHE_SEC = 8


def _get(path):
    req = urllib.request.Request(BASE + path, headers=HEADERS, method='GET')
    with urllib.request.urlopen(req, timeout=15, context=_ctx) as r:
        raw = r.read()
    try:
        return json.loads(gzip.decompress(raw).decode('utf-8'))
    except Exception:
        return json.loads(raw.decode('utf-8'))


def build_payload():
    now = time.time()
    if _cache['payload'] and now - _cache['ts'] < CACHE_SEC:
        return _cache['payload']

    issue, idx = {}, {}
    err = None
    try:
        issue = _get(API_ISSUE)
    except Exception as e:
        err = 'issue: %s' % e
    try:
        idx = _get(API_INDEX)
    except Exception as e:
        if not err:
            err = 'index: %s' % e

    data = issue.get('data') or {}
    idata = idx.get('data') or {}
    cur = data.get('currentIssue') or {}
    hist = data.get('historyIssue') or []

    items = []
    for it in hist:
        try:
            nums = [int(x) for x in it.get('code', [])]
            s = int(str(it.get('sum', '0')).lstrip('0') or 0)
        except Exception:
            continue
        items.append({
            'issue': str(it.get('issue', '')),
            'time': str(it.get('openTime', '')),
            'nums': nums,
            'sum': s,
            'dx': str(it.get('bigSmall', '')),
            'ds': str(it.get('singleEven', '')),
            'combo': str(it.get('bigSmallSingleEven', '')),
        })

    payload = {
        'ok': bool(items),
        'name': idata.get('name') or '比特28',
        'room': idata.get('roomName') or '',
        'saleStatus': idata.get('sale_status') or '',
        'members': idata.get('roomMemberCount'),
        'current': {
            'issue': str(cur.get('issue', '')),
            'stopTime': cur.get('stopTime'),
        },
        'count': len(items),
        'fetched_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'issues': items,
        'error': err,
    }
    _cache['payload'] = payload
    _cache['ts'] = now
    return payload


@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/issues')
def api_issues():
    resp = jsonify(build_payload())
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@app.route('/healthz')
def healthz():
    return 'ok'


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8899))
    app.run(host='0.0.0.0', port=port, debug=False)
