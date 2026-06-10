FROM node:20-alpine AS build

ARG NPM_REGISTRY_URL=https://registry.npmjs.org/

WORKDIR /app
COPY web/package.json web/package-lock.json* ./
RUN npm ci --registry "${NPM_REGISTRY_URL}"
COPY web/ ./
RUN npm run build

FROM nginx:1.27-alpine

COPY web/nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
