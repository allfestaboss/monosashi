# 静的サイトなので nginx だけ。ビルド成果物を焼き込む。
FROM nginx:1.27-alpine
COPY dist/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/conf.d/default.conf
