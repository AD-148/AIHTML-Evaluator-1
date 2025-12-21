# Build Stage
# Build Stage
FROM node:20-slim as build

WORKDIR /app

COPY package.json ./
# Force fresh install
RUN npm install
# Explicitly pin esbuild to match host expectation
RUN npm install esbuild@0.25.12 --save-exact

COPY . .
# Fix permissions just in case
RUN chmod -R +x node_modules/.bin/
RUN npm run build

# Production Stage
FROM nginx:alpine

# Copy built assets from the previous stage
COPY --from=build /app/dist /usr/share/nginx/html

# Reset permissions (optional but good practice)
RUN chmod -R 755 /usr/share/nginx/html

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
