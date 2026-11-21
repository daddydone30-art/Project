FROM node:22-slim

RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package*.json ./
RUN npm install --omit=dev

COPY . .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

CMD ["node", "server.js"]
