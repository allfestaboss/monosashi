#!/usr/bin/env bash
# monosashi.work を dx-fukuoka VPS に出す。
# デプロイ安全則: 他リポと同時に走らせない。VPSの空きメモリを見てから。
set -euo pipefail
cd "$(dirname "$0")"
HOST=dx-fukuoka-vps
NAME=monosashi-web

echo "== プリフライト =="
python3 build.py
FREE=$(ssh $HOST "free -m | awk '/^Mem:/{print \$7}'")
echo "  VPS の空きメモリ ${FREE}MB"
[ "$FREE" -lt 400 ] && { echo "  空きが少ない。他のデプロイが走っていないか確認してから。"; exit 1; }
ssh $HOST "docker ps --format '{{.Names}}' | grep -q '^${NAME}$' && echo '  既存コンテナあり（置き換える）' || echo '  新規'"

echo "== 転送してビルド =="
ssh $HOST "mkdir -p /root/apps/monosashi"
# dist/ は**ディレクトリごと**送る。末尾スラッシュだと中身が平たく展開され、
# Dockerfile の COPY dist/ が「/dist が無い」で落ちる（実際に落ちた）。
rsync -az --delete dist/ $HOST:/root/apps/monosashi/dist/
rsync -az Dockerfile nginx.conf $HOST:/root/apps/monosashi/
ssh $HOST "cd /root/apps/monosashi && docker build -q -t ${NAME}:latest . && \
  docker rm -f ${NAME} 2>/dev/null; \
  docker run -d --name ${NAME} --restart unless-stopped --network npm_network ${NAME}:latest"

echo "== 疎通 =="
ssh $HOST "docker exec ${NAME} wget -qO- -S http://127.0.0.1/ 2>&1 | head -1"
echo "→ 次は NPM でプロキシホストと証明書。setup-npm.sh を実行"
