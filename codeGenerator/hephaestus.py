#! /usr/bin/env python3
# pylint: disable=too-few-public-methods
import asyncio
import logging
import os
import shutil
import traceback

import grpc

from src import utils
from src.args import args as cli_args, validate_args
from src.generators import Generator
from src.modules.logging import Logger
from src.server import server_pb2_grpc, GeneratorImpl
from src.translators.java import JavaTranslator
from src.translators.kotlin import KotlinTranslator

TRANSLATORS = {
    'kotlin': KotlinTranslator,
    'java': JavaTranslator
}


def gen_program(pid, packages):
    """
    This function is responsible processing an iteration.

    It generates a program with a given id, it then applies a number of
    transformations, and finally it saves the resulting program into the
    given directory.

    The program belongs to the given packages.
    """
    utils.randomUtil.reset_word_pool()
    utils.randomUtil.reset_random()
    cli_args.language = 'kotlin'
    translator = TRANSLATORS[cli_args.language]('src.' + packages[0],
                                                cli_args.options['Translator'])
    if cli_args.log:
        logger = Logger(cli_args.name, cli_args.args.test_directory, pid, "Generator", pid)
    else:
        logger = None
    generator = Generator(language=cli_args.language, logger=logger)
    try:
        program = generator.generate()
        kotlin = utils.translate_program(translator, program)
        utils.randomUtil.reset_random()
        utils.randomUtil.reset_word_pool()
        cli_args.language = 'java'
        generator = Generator(language=cli_args.language, logger=logger)
        program2 = generator.generate()
        translator = TRANSLATORS[cli_args.language]('src.' + packages[0],
                                                    cli_args.options['Translator'])
        java = utils.translate_program(translator, program2)
        return program, kotlin, program2, java
    except Exception as exc:
        # This means that we have programming error in transformations
        err = str(traceback.format_exc())
        print(err)
        return None


def run():
    def process_program(pid, packages):
        return gen_program(pid, packages)

    utils.randomUtil.reset_word_pool()
    packages = (utils.randomUtil.word(), utils.randomUtil.word())
    utils.randomUtil.reset_random()
    res = []
    try:
        res.append(process_program(1, packages))
    except KeyboardInterrupt:
        pass
    path = os.path.join(cli_args.test_directory, 'tmp')
    if os.path.exists(path):
        shutil.rmtree(path)
    print()


def main():
    validate_args(cli_args)
    run()


async def serve():
    server = grpc.aio.server()
    server_pb2_grpc.add_GeneratorServicer_to_server(GeneratorImpl(), server)
    listen_addr = '[::]:50051'
    server.add_insecure_port(listen_addr)
    logging.info("Starting server on %s", listen_addr)
    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    if cli_args.debug:
        main()
    else:
        asyncio.run(serve())
