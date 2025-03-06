plugins {
    id("org.jetbrains.kotlin.jvm") version "1.9.22"
    id("com.adarshr.test-logger") version "4.0.0"
    application
}

repositories {
    mavenCentral()
}

dependencies {
    implementation(platform("org.jetbrains.kotlin:kotlin-bom"))
    implementation("org.jetbrains.kotlin:kotlin-stdlib-jdk8")

    implementation("com.google.guava:guava:33.0.0-jre")

    implementation("io.ktor:ktor-server-call-logging:2.3.7")
    implementation("io.ktor:ktor-server-core:2.3.7")
    implementation("io.ktor:ktor-server-netty:2.3.7")
    implementation("ch.qos.logback:logback-classic:1.4.14")
    implementation("ch.qos.logback.contrib:logback-json-classic:0.1.5")
    implementation("ch.qos.logback.contrib:logback-jackson:0.1.5")
    implementation("com.fasterxml.jackson.core:jackson-databind:2.16.1")

    implementation("org.apache.poi:poi:5.2.5")
    implementation("org.apache.poi:poi-ooxml:5.2.5")
    // POI Logback support https://poi.apache.org/components/logging.html
    implementation("org.apache.logging.log4j:log4j-to-slf4j:2.22.1")

    testImplementation("io.ktor:ktor-server-test-host:2.3.7")
    testImplementation("org.jetbrains.kotlin:kotlin-test:1.9.22")
    testImplementation("org.jetbrains.kotlin:kotlin-test-junit:1.9.22")
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
