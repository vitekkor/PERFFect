#!/bin/bash

echo "Build grpc server"

python3 -m grpc_tools.protoc \
--proto_path=../protobuf/ \
--python_out=./src/server \
--pyi_out=./src/server \
--grpc_python_out=./src/server \
../protobuf/server.proto
