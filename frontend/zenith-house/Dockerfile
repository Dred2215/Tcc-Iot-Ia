# Etapa 1 - Build com Node
FROM node:18 AS build
WORKDIR /app

ARG VITE_BACKEND_BASE_URL=http://localhost:8000
ARG VITE_WEBHOOK_BASE_URL=https://tcc-iot-n8n.dlivfa.easypanel.host/webhook
ARG VITE_WEBHOOK_TEST_BASE_URL=https://tcc-iot-n8n.dlivfa.easypanel.host/webhook-test
ARG VITE_WEBHOOK_MESSAGE_CHAT_RESPONSE=https://tcc-iot-n8n.dlivfa.easypanel.host/webhook/message_input
ARG VITE_REGISTER_WEBHOOK_URL=https://tcc-iot-n8n.dlivfa.easypanel.host/webhook/register-user
ARG VITE_VOICE_WS_BASE=wss://tcc-iot-backend-homolog.dlivfa.easypanel.host:8008
ARG VITE_VOICE_WS_PORT=8008

ENV VITE_BACKEND_BASE_URL=${VITE_BACKEND_BASE_URL}
ENV VITE_WEBHOOK_BASE_URL=${VITE_WEBHOOK_BASE_URL}
ENV VITE_WEBHOOK_TEST_BASE_URL=${VITE_WEBHOOK_TEST_BASE_URL}
ENV VITE_WEBHOOK_MESSAGE_CHAT_RESPONSE=${VITE_WEBHOOK_MESSAGE_CHAT_RESPONSE}
ENV VITE_REGISTER_WEBHOOK_URL=${VITE_REGISTER_WEBHOOK_URL}
ENV VITE_VOICE_WS_BASE=${VITE_VOICE_WS_BASE}
ENV VITE_VOICE_WS_PORT=${VITE_VOICE_WS_PORT}

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
