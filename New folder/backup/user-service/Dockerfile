# syntax=docker/dockerfile:1.7

# Stage 1: Build & Extract (Giải nén JAR)
FROM maven:3.9.9-eclipse-temurin-17 AS build
WORKDIR /workspace

COPY pom.xml ./
COPY src ./src
# Build ra file JAR
RUN mvn -q -DskipTests package

# Giải nén file JAR ngay tại chỗ
RUN mkdir -p target/extracted && \
    java -Djarmode=layertools -jar target/*.jar extract --destination target/extracted

# Stage 2: Runtime (Chỉ copy các lớp đã giải nén)
FROM eclipse-temurin:17-jre
WORKDIR /app

# Copy các thư viện (ít thay đổi, tận dụng cache Docker cực tốt)
COPY --from=build /workspace/target/extracted/dependencies/ ./
COPY --from=build /workspace/target/extracted/spring-boot-loader/ ./
COPY --from=build /workspace/target/extracted/snapshot-dependencies/ ./
# Copy code ứng dụng (thường xuyên thay đổi)
COPY --from=build /workspace/target/extracted/application/ ./

EXPOSE 8083

# Chạy trực tiếp bằng JarLauncher (không cần giải nén lúc runtime)
ENTRYPOINT ["java", \
            "-XX:+TieredCompilation", \
            "-XX:TieredStopAtLevel=1", \
            "-Dspring.main.lazy-initialization=true", \
            "org.springframework.boot.loader.launch.JarLauncher"]