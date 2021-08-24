plugins {
    id("org.jetbrains.kotlin.jvm") version "1.5.10"
    id("com.adarshr.test-logger") version "3.0.0"
    application
}

repositories {
    mavenCentral()
}

dependencies {
    implementation(platform("org.jetbrains.kotlin:kotlin-bom"))
    implementation("org.jetbrains.kotlin:kotlin-stdlib-jdk8")

    implementation("com.google.guava:guava:30.1-jre")

    implementation("io.ktor:ktor-server-core:1.6.0")
    implementation("io.ktor:ktor-server-netty:1.6.0")
    implementation("ch.qos.logback:logback-classic:1.2.3")

    implementation("org.apache.poi:poi:5.0.0")
    implementation("org.apache.poi:poi-ooxml:5.0.0")

    testImplementation("io.ktor:ktor-server-test-host:1.6.0")
    testImplementation("org.jetbrains.kotlin:kotlin-test")
    testImplementation("org.jetbrains.kotlin:kotlin-test-junit")
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
            attributes(mapOf("Main-Class" to "fi.csc.varda.AppKt", "Implementation-Version" to "1.0.0"))
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
            jvmTarget = JavaVersion.VERSION_16.toString()
        }
    }
}
