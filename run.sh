#!/bin/bash

trap killGroup SIGINT
set -e

grpcPID=-1

killGroup(){
  echo killing...
  kill $grpcPID
  rm -f testOracle-1.0-SNAPSHOT.jar
}

if [[ $# -eq 1 && $1 == "build" ]]; then
    echo "Building..."
    ./gradlew clean build jar
fi

cp testOracle/build/libs/testOracle-1.0-SNAPSHOT.jar testOracle-1.0-SNAPSHOT.jar

echo 'Start grpc server...'
python3 codeGenerator/hephaestus.py &
grpcPID=$!

sleep 1

echo 'Run test oracle...'
java -jar testOracle-1.0-SNAPSHOT.jar
