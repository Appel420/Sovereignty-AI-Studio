FROM node:25-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --production
COPY server.js ./
EXPOSE 9899
CMD ["node", "server.js"]
