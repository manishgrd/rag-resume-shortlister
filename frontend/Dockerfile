FROM node:20-alpine

WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .

ENV VITE_API_BASE=http://localhost:7000
EXPOSE 5173
CMD ["npm", "run", "dev"]
