plugins {
    id("org.jetbrains.kotlin.jvm") version "1.6.10"
    id("com.adarshr.test-logger") version "3.1.0"
    application
}

repositories {
    mavenCentral()
}

dependencies {
    implementation(platform("org.jetbrains.kotlin:kotlin-bom"))
    implementation("org.jetbrains.kotlin:kotlin-stdlib-jdk8")

    implementation("com.google.guava:guava:31.0.1-jre")

    implementation("io.ktor:ktor-server-core:1.6.7")
    implementation("io.ktor:ktor-server-netty:1.6.7")
    implementation("ch.qos.logback:logback-classic:1.2.9")

    implementation("org.apache.poi:poi:5.1.0")
    implementation("org.apache.poi:poi-ooxml:5.1.0")

    testImplementation("io.ktor:ktor-server-test-host:1.6.7")
    testImplementation("org.jetbrains.kotlin:kotlin-test:1.6.7")
    testImplementation("org.jetbrains.kotlin:kotlin-test-junit:1.6.7")
}

application {
    mainClass.set("fi.csc.varda.AppKt")
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
            attributes(mapOf("Main-Class" to "fi.csc.varda.AppKt", "Implementation-Version" to "1.0.1"))
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
    compileKotlin {
        kotlinOptions {
            jvmTarget = JavaVersion.VERSION_17.toString()
        }
    }
}
