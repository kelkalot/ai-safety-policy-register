# Self-contained image with the app, the data and the current archive baked in.
# Build from the register folder:
#   docker build -f deploy/Dockerfile -t ai-safety-policy-register .
#   docker run -d -p 8080:80 --name ai-safety-policy-register ai-safety-policy-register
FROM nginx:1.27.4-alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
COPY assets/ /usr/share/nginx/html/assets/
COPY data/ /usr/share/nginx/html/data/
COPY archive/ /usr/share/nginx/html/archive/
