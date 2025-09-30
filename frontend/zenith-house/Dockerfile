# Etapa 1 - Build com Node
FROM node:18 AS build
WORKDIR /app

# Copia package.json e instala dependências
COPY package*.json ./
RUN npm install

# Copia todo o código e gera build
COPY . .
RUN npm run build

# Etapa 2 - Servir com Nginx
FROM nginx:alpine
# Remove arquivos padrão do Nginx
RUN rm -rf /usr/share/nginx/html/*

# Copia o build do React para a pasta do Nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Expor porta
EXPOSE 80

# Rodar Nginx
CMD ["nginx", "-g", "daemon off;"]
