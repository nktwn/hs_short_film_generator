FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# запускаем vite dev-сервер
CMD ["npm", "run", "dev", "--", "--host", "--port", "5173"]

EXPOSE 5173