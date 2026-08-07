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
echo "→ 証明書の発行を待って https://monosashi.work を確認"
