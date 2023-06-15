import random
import time

import grpc.aio

from src import utils
from src.generators import Generator
from src.modules.logging import Logger
from src.server import server_pb2, server_pb2_grpc
from src.translators.java import JavaTranslator
from src.translators.kotlin import KotlinTranslator
import traceback


def generate_package_name():
    utils.randomUtil.reset_word_pool()
    packages = (utils.randomUtil.word(), utils.randomUtil.word())
    return packages


class GeneratorImpl(server_pb2_grpc.GeneratorServicer):
    TRANSLATORS = {
        'kotlin': KotlinTranslator,
        'java': JavaTranslator
    }
    _log: Logger = Logger("server_class")

    def generate_program(self, language, seed):
        packages = generate_package_name()
        utils.randomUtil.reset_word_pool()
        utils.randomUtil.reset_random(seed)
        translator = self.TRANSLATORS[language]('src.' + packages[0], {})
        logger = Logger("Generator")
        generator = Generator(language=language, logger=logger)
        try:
            program = generator.generate()
            text = utils.translate_program(translator, program)
            return text
        except Exception as exc:
            # This means that we have programming error in transformations
            err = str(traceback.format_exc())
            logger.log(err)
            return None

    async def generateKotlin(self, request: server_pb2.GenerateRequest, context: grpc.aio.ServicerContext):
        start_time = time.time()
        self._log.log(f"Incoming request to generate a Kotlin program: seed {request.seed}")
        text = self.generate_program(language="kotlin", seed=request.seed)
        self._log.log(f"Kotlin program generation completed successfully. Elapsed time {time.time() - start_time}ms")
        return server_pb2.Program(language="kotlin", text=text)

    async def generateJava(self, request: server_pb2.GenerateRequest, context: grpc.aio.ServicerContext):
        start_time = time.time()
        self._log.log(f"Incoming request to generate a Java program: seed {request.seed}")
        text = self.generate_program(language="java", seed=request.seed)
        self._log.log(f"Java program generation completed successfully. Elapsed time {time.time() - start_time}ms")
        return server_pb2.Program(language="java", text=text)
