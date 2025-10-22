FROM node:20

WORKDIR /app

# Copy dependency files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy all frontend files
COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev"]

