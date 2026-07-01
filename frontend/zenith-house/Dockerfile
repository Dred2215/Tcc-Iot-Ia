# Etapa 1 - Build com Node
FROM node:18 AS build
WORKDIR /app

ARG VITE_BACKEND_BASE_URL=http://localhost:8000
ARG VITE_LOCAL_BACKEND_PORT=8000

ENV VITE_BACKEND_BASE_URL=${VITE_BACKEND_BASE_URL}
ENV VITE_LOCAL_BACKEND_PORT=${VITE_LOCAL_BACKEND_PORT}

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Etapa 2 - Servir com Nginx
FROM nginx:alpine
RUN rm -rf /usr/share/nginx/html/*
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
