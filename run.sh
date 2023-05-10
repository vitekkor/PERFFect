#!/bin/bash

trap killGroup SIGINT

killGroup(){
  echo killing...
  kill $(jobs -p)
  rm -f testOracle-1.0-SNAPSHOT.jar
}

cp testOracle/build/libs/testOracle-1.0-SNAPSHOT.jar testOracle-1.0-SNAPSHOT.jar

echo 'Start grpc server...'
python3 codeGenerator/hephaestus.py &

sleep 1

echo 'Run test oracle...'
java -jar testOracle-1.0-SNAPSHOT.jar
