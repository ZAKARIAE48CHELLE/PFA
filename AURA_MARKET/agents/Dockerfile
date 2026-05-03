# Stage 1: Build the application
FROM maven:3.9.6-eclipse-temurin-17 AS build
WORKDIR /app

# Import TILAB SSL certificate to fix JADE dependency download
RUN keytool -printcert -rfc -sslserver jade.tilab.com:443 > /tmp/tilab.pem 2>/dev/null && \
    keytool -importcert -noprompt -keystore $JAVA_HOME/lib/security/cacerts -storepass changeit -alias tilab -file /tmp/tilab.pem || true

COPY pom.xml .

# Download and install jFuzzyLogic manually since it's not in Maven Central
RUN curl -L "https://sourceforge.net/projects/jfuzzylogic/files/jfuzzylogic/jFuzzyLogic_v3.0.jar/download" -o /tmp/jFuzzyLogic.jar && \
    mvn install:install-file -Dfile=/tmp/jFuzzyLogic.jar -DgroupId=net.sourceforge.jfuzzylogic -DartifactId=jfuzzylogic -Dversion=3.0 -Dpackaging=jar

COPY src ./src
RUN mvn clean package -DskipTests -Dmaven.wagon.http.ssl.insecure=true -Dmaven.wagon.http.ssl.allowall=true

# Stage 2: Run the application
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=build /app/target/*.jar app.jar
ENTRYPOINT ["java", "-jar", "app.jar"]
