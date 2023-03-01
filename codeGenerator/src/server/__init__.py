import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.server import server_pb2 as server_pb2
from src.server import server_pb2_grpc
from src.server.sever_class import GeneratorImpl
