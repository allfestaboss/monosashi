#!/usr/bin/env bash
# shoken.monosashi.work を dx-fukuoka VPS に出す。
# 職種はパスで切るが、商圏モデルは同じ物差しで測っていないのでサブドメインに出す。
# デプロイ安全則: 他リポと同時に走らせない。VPSの空きメモリを見てから。
set -euo pipefail
cd "$(dirname "$0")"
HOST=dx-fukuoka-vps
NAME=monosashi-shoken

echo "== プリフライト =="
python3 build.py
[ -f dist-shoken/index.html ] || { echo "  dist-shoken/index.html が無い"; exit 1; }
FREE=$(ssh $HOST "free -m | awk '/^Mem:/{print \$7}'")
echo "  VPS の空きメモリ ${FREE}MB"
[ "$FREE" -lt 400 ] && { echo "  空きが少ない。他のデプロイが走っていないか確認してから。"; exit 1; }

echo "== 転送してビルド =="
ssh $HOST "mkdir -p /root/apps/monosashi-shoken"
# dist は**ディレクトリごと**送る（末尾スラッシュだと平たく展開されて COPY が落ちる）
rsync -az --delete dist-shoken/ $HOST:/root/apps/monosashi-shoken/dist/
rsync -az Dockerfile nginx.conf $HOST:/root/apps/monosashi-shoken/
ssh $HOST "cd /root/apps/monosashi-shoken && docker build -q -t ${NAME}:latest . && \
  docker rm -f ${NAME} 2>/dev/null; \
  docker run -d --name ${NAME} --restart unless-stopped --network npm_network ${NAME}:latest"

echo "== 疎通 =="
ssh $HOST "docker exec ${NAME} wget -qO- -S http://127.0.0.1/ 2>&1 | head -1"
echo "→ 次は NPM で shoken.monosashi.work のプロキシホストと証明書"
