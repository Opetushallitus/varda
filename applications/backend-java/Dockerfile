FROM 105387356358.dkr.ecr.eu-west-1.amazonaws.com/ecr-public/docker/library/amazoncorretto:21-alpine

WORKDIR /app/

# Install dependencies first to leverage Docker caching
COPY *.gradle.* gradlew* ./
COPY gradle ./gradle/
COPY app/*.gradle.* ./app/
RUN ./gradlew app:dependencies
# Copy and build rest of the app
COPY . /app
RUN ./gradlew build --no-daemon -Penv=prod

# Install curl
RUN apk add --no-cache curl

# Kubernetes requires non-root user
USER 1001

EXPOSE 8080

CMD ["java", "-jar", "/app/app/build/libs/app.jar"]
