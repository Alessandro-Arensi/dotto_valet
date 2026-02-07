# Dottò - PocketBase backend
# Build con binario ufficiale PocketBase (linux amd64)
FROM alpine:3.19

ARG PB_VERSION=0.36.2
RUN apk add --no-cache ca-certificates && \
    wget -q "https://github.com/pocketbase/pocketbase/releases/download/v${PB_VERSION}/pocketbase_${PB_VERSION}_linux_amd64.zip" -O /tmp/pb.zip && \
    unzip /tmp/pb.zip -d /usr/local/bin && \
    rm /tmp/pb.zip && \
    chmod +x /usr/local/bin/pocketbase

WORKDIR /app
COPY pb_migrations ./pb_migrations
COPY pb_hooks ./pb_hooks

# In runtime montiamo pb_data come volume; migrations sono in /app/pb_migrations
EXPOSE 8090
# In docker-compose montare pb_data, pb_migrations, pb_hooks; qui usiamo path standard
CMD ["/usr/local/bin/pocketbase", "serve", "--http=0.0.0.0:8090", "--dir=/pb_data", "--migrationsDir=/pb_migrations", "--hooksDir=/pb_hooks"]
