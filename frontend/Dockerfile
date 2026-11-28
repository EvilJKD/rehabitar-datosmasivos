FROM node:24-alpine AS dependencies

WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN npm ci

FROM dependencies AS build
COPY . .
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html
EXPOSE 80
