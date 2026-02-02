plugins {
    id("org.jetbrains.kotlin.jvm") version "2.1.20"
    id("com.adarshr.test-logger") version "4.0.0"
    application
}

repositories {
    mavenCentral()
}

val ktorVersion = "2.3.13"
val logbackContribVersion = "0.1.5"
val poiVersion = "5.4.1"
val kotlinVersion = "2.1.20" // Must match version in plugins (org.jetbrains.kotlin.jvm)

dependencies {
    implementation(platform("org.jetbrains.kotlin:kotlin-bom"))
    implementation("org.jetbrains.kotlin:kotlin-stdlib-jdk8")

    implementation("com.google.guava:guava:33.4.8-jre")

    implementation("io.ktor:ktor-server-call-logging:$ktorVersion")
    implementation("io.ktor:ktor-server-core:$ktorVersion")
    implementation("io.ktor:ktor-server-netty:$ktorVersion")
    implementation("ch.qos.logback:logback-classic:1.5.18")
    implementation("ch.qos.logback.contrib:logback-json-classic:$logbackContribVersion")
    implementation("ch.qos.logback.contrib:logback-jackson:$logbackContribVersion")
    implementation("com.fasterxml.jackson.core:jackson-databind:2.19.0")

    implementation("org.apache.poi:poi:$poiVersion")
    implementation("org.apache.poi:poi-ooxml:$poiVersion")
    // POI Logback support https://poi.apache.org/components/logging.html
    implementation("org.apache.logging.log4j:log4j-to-slf4j:2.24.3")

    testImplementation("io.ktor:ktor-server-test-host:$ktorVersion")
    testImplementation("org.jetbrains.kotlin:kotlin-test:$kotlinVersion")
    testImplementation("org.jetbrains.kotlin:kotlin-test-junit:$kotlinVersion")
}

application {
    mainClass.set("fi.csc.varda.AppKt")
}

kotlin {
    jvmToolchain(21)
}

tasks {
    processResources {
        if (!project.hasProperty("env") || project.property("env") != "prod") {
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
            attributes(mapOf("Main-Class" to "fi.csc.varda.AppKt", "Implementation-Version" to "1.0.6"))
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
