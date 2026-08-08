#!/usr/bin/env bash
# NPM に monosashi.work のプロキシホストを作り、Let's Encrypt を取る。
# パスワードは見ない（/root/bin/npm-api が /root/npm/.npm-admin.env から読む）。
set -euo pipefail
ssh dx-fukuoka-vps '/root/bin/npm-api POST /nginx/proxy-hosts - <<JSON
{"domain_names":["monosashi.work","www.monosashi.work"],
 "forward_scheme":"http","forward_host":"monosashi-web","forward_port":80,
 "block_exploits":true,"caching_enabled":true,"allow_websocket_upgrade":false,
 "access_list_id":0,"certificate_id":"new","ssl_forced":true,"hsts_enabled":true,
 "http2_support":true,"advanced_config":"",
 "meta":{"letsencrypt_agree":true,"dns_challenge":false},"locations":[]}
JSON'
# **POST では SSL のフラグが効かない。** 証明書はリクエスト内で発行されるが、
# ssl_forced / hsts_enabled / http2_support は反映されず false のままになる
# （実際に http:// が 200 を返し続けた）。作成後に PUT で入れ直す。
HID=$(ssh dx-fukuoka-vps '/root/bin/npm-api GET /nginx/proxy-hosts 2>/dev/null | python3 -c "
import json,sys
for h in json.load(sys.stdin):
    if \"monosashi.work\" in h[\"domain_names\"]: print(h[\"id\"])
"')
ssh dx-fukuoka-vps "/root/bin/npm-api PUT /nginx/proxy-hosts/$HID '{\"ssl_forced\":true,\"hsts_enabled\":true,\"http2_support\":true}'" > /dev/null
echo "→ SSL強制・HSTS・HTTP/2 を有効化。https://monosashi.work を確認"
