FROM maven:3.8.4-jdk-11

COPY app/ app/

CMD mvn test -f /app/pom.xml > output.txt 2> error.txt
#CMD mvn test -f /app/pom.xml