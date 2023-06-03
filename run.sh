#!/bin/bash

trap killGroup SIGINT
set -e

killGroup(){
  echo killing...
  kill $(jobs -p)
  rm -f testOracle-1.0-SNAPSHOT.jar
}

if [[ $# -eq 1 && $1 == "build" ]]; then
    echo "Building..."
    ./gradlew clean build jar
fi

cp testOracle/build/libs/testOracle-1.0-SNAPSHOT.jar testOracle-1.0-SNAPSHOT.jar

echo 'Start grpc server...'
python3 codeGenerator/hephaestus.py &

sleep 1

echo 'Run test oracle...'
java -jar testOracle-1.0-SNAPSHOT.jar
