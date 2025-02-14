# Varda-Java

This application is used to encrypt Excel reports using Apache POI.

## Prerequisites

* Java 17 (OpenJDK)

## Development

You can start the application locally with:

```
gradlew run
```

### Testing

The application has one API:

#### `/upload`

An `xlsx`-file can be uploaded to this API as `multipart/form-data`.  
Field key of the `xlsx` file is optional. A password must be provided in a `password`-field.

After successful encryption an `xlsx`-file is returned.

## Deployment

The application can be built with:

```
gradlew build
```

An optional environment type can be provided, for example:

```
gradlew build -Penv=prod
```

Different flavors are:
1. local
2. prod

## Docker

Before you build the Docker image, make sure that line endings in `gradlew` are LF and not CRLF.  
You can build the image with:

```
docker build -t varda-java .
```

Run the container:

```
docker run -it -d --rm --name varda-java -p 8082:8080 --network varda-network --env VARDA_ENVIRONMENT_TYPE='local-dev-env' varda-java
```

The application can now be accessed in `http://localhost:8082`.  
`--network varda-network` option is important if you are also running backend in a container.
