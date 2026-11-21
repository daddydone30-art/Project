FROM node:20-slim

# Install Python 3 and pip
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Node dependencies first for better layer caching
COPY package*.json ./
RUN npm ci --omit=dev || npm install --omit=dev

# If core_extractor.py uses third-party Python packages, add a requirements.txt
# and uncomment the lines below:
# COPY requirements.txt ./
# RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Copy application source
COPY . .

ENV NODE_ENV=production
ENV PORT=3000
EXPOSE 3000

CMD ["node", "server.js"]
