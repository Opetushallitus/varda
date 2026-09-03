FROM amazoncorretto:25-alpine

WORKDIR /app/

ENV JAVA_OPTS="--enable-native-access=ALL-UNNAMED"

# Install dependencies first to leverage Docker caching
COPY *.gradle.* gradlew* ./
COPY gradle ./gradle/
COPY app/*.gradle.* ./app/
RUN ./gradlew app:dependencies
# Copy and build rest of the app
COPY . /app
RUN ./gradlew build --no-daemon -Penv=prod

# Install curl and openssl
RUN apk add --no-cache curl openssl

# Create startup script
RUN echo '#!/bin/sh' > /app/start.sh && \
    echo 'if [ -f /tls/tls.crt ] && [ -f /tls/tls.key ]; then' >> /app/start.sh && \
    echo '  echo "Converting TLS certificates to keystore..."' >> /app/start.sh && \
    echo '  openssl pkcs12 -export -in /tls/tls.crt -inkey /tls/tls.key \' >> /app/start.sh && \
    echo '    -out /tmp/keystore.p12 -name tls -passout pass:temppassword' >> /app/start.sh && \
    echo 'fi' >> /app/start.sh && \
    echo 'exec java -jar /app/app/build/libs/app.jar "$@"' >> /app/start.sh && \
    chmod +x /app/start.sh

# Kubernetes requires non-root user
USER 1001

EXPOSE 8080

CMD ["/app/start.sh"]
