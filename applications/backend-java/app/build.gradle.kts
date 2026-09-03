plugins {
    kotlin("jvm") version "2.4.10"
    id("com.adarshr.test-logger") version "4.0.0"
    application
}

val kotlinVersion = "2.4.10"
val ktorVersion = "3.5.1"
val logbackVersion = "1.5.38"
val poiVersion = "5.5.1"
val jacksonVersion = "2.22.1"
val log4jToSlf4jVersion = "2.26.1"
val logstashEncoderVersion = "9.0"

repositories {
    mavenCentral()
}

dependencies {
    implementation(platform("org.jetbrains.kotlin:kotlin-bom:$kotlinVersion"))
    implementation("org.jetbrains.kotlin:kotlin-stdlib-jdk8")

    implementation("io.ktor:ktor-server-core:$ktorVersion")
    implementation("io.ktor:ktor-server-netty:$ktorVersion")
    implementation("io.ktor:ktor-server-call-logging:$ktorVersion")

    implementation("ch.qos.logback:logback-classic:$logbackVersion")
    implementation("net.logstash.logback:logstash-logback-encoder:$logstashEncoderVersion")
    implementation("org.apache.logging.log4j:log4j-to-slf4j:$log4jToSlf4jVersion")

    implementation("com.fasterxml.jackson.core:jackson-databind:$jacksonVersion")

    implementation("org.apache.poi:poi:$poiVersion")
    implementation("org.apache.poi:poi-ooxml:$poiVersion")

    testImplementation("io.ktor:ktor-server-test-host:${ktorVersion}")

    testImplementation("org.jetbrains.kotlin:kotlin-test:$kotlinVersion")
    testImplementation("org.jetbrains.kotlin:kotlin-test-junit:$kotlinVersion")
}

application {
    mainClass.set("fi.csc.varda.AppKt")
}

kotlin {
    jvmToolchain(25)
}

tasks {
    processResources {
        if (project.findProperty("env") != "prod") {
            exclude("app.prod.properties")
            rename("app.local.properties", "app.properties")
        } else {
            exclude("app.local.properties")
            rename("app.prod.properties", "app.properties")
        }
    }

    jar {
        manifest {
            // Update version code here
            attributes("Main-Class" to "fi.csc.varda.AppKt", "Implementation-Version" to "1.0.9")
        }

        // Create fat JAR
        // https://docs.gradle.org/current/userguide/working_with_files.html#sec:creating_uber_jar_example
        duplicatesStrategy = DuplicatesStrategy.EXCLUDE
        from(sourceSets.main.get().output)
        dependsOn(configurations.runtimeClasspath)
        from({
            configurations.runtimeClasspath.get().filter { it.name.endsWith("jar") }.map { zipTree(it) }
        })

        // https://stackoverflow.com/a/56242000
        exclude("META-INF/*.RSA", "META-INF/*.SF", "META-INF/*.DSA")
    }
}
