from src.ir.kotlin_types import KotlinBuiltinFactory
from src.ir.java_types import JavaBuiltinFactory

BUILTIN_FACTORIES = {
    "kotlin": KotlinBuiltinFactory(),
    "java": JavaBuiltinFactory()
}
