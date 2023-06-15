# pylint: disable=abstract-method, useless-super-delegation,too-many-ancestors
# pylint: disable=too-few-public-methods
from ordered_set import OrderedSet

import src.ir.ast as ast
import src.ir.builtins as bt
import src.ir.types as tp
from src.ir.types import Builtin


class JavaBuiltinFactory(bt.BuiltinFactory):

    def get_language(self):
        return "java"

    def get_builtin(self):
        return JavaBuiltin

    def get_void_type(self):
        return VoidType()

    def get_any_type(self):
        return ObjectType()

    def get_number_type(self):
        return NumberType()

    def get_integer_type(self):
        return IntegerType(primitive=False)

    def get_byte_type(self):
        return ByteType(primitive=False)

    def get_short_type(self):
        return ShortType(primitive=False)

    def get_long_type(self):
        return LongType(primitive=False)

    def get_float_type(self):
        return FloatType(primitive=False)

    def get_double_type(self):
        return DoubleType(primitive=False)

    def get_big_decimal_type(self):
        return DoubleType(primitive=False)

    def get_boolean_type(self):
        return BooleanType(primitive=False)

    def get_char_type(self):
        return CharType(primitive=False)

    def get_string_type(self):
        return StringType()

    def get_array_type(self):
        return ArrayType()

    def get_array_list_type(self):
        return ArrayListType()

    def get_iterator_type(self):
        return IteratorType()

    def get_big_integer_type(self):
        return IntegerType(primitive=False)

    def get_function_type(self, nr_parameters=0):
        return FunctionType(nr_parameters)

    def get_non_nothing_types(self):
        return super().get_non_nothing_types()

    def get_number_types(self):
        return super().get_number_types()


class JavaBuiltin(Builtin):

    def __init__(self, name, primitive):
        super().__init__(name)
        self.primitive = primitive

    def __str__(self):
        if not self.is_primitive():
            return str(self.name) + "(java-builtin)"
        return str(self.name).lower() + "(java-primitive)"

    def is_primitive(self):
        return False

    def box_type(self):
        raise NotImplementedError('box_type() must be implemented')


class ObjectType(JavaBuiltin):

    def __init__(self, name="Object"):
        super().__init__(name, False)

    def get_builtin_type(self):
        return bt.Any

    def box_type(self):
        return self

    def get_class_declaration(self):
        return ast.ClassDeclaration(
            name=self.name,
            superclasses=[],
            class_type=ast.ClassDeclaration.REGULAR,
        )


class VoidType(JavaBuiltin):

    def __init__(self, name="void", primitive=False):
        super().__init__(name, primitive)
        if not self.primitive:
            self.supertypes.append(ObjectType())
        else:
            self.supertypes = OrderedSet()

    def get_builtin_type(self):
        return bt.Void

    def box_type(self):
        return VoidType(self.name, primitive=False)


class NumberType(ObjectType):

    def __init__(self, name="Number"):
        super().__init__(name)
        self.supertypes.append(ObjectType())

    def get_builtin_type(self):
        return bt.Number

    def box_type(self):
        return self

    def get_class_declaration(self):
        return ast.ClassDeclaration(
            name=self.name,
            superclasses=[
                ast.SuperClassInstantiation(class_type=ObjectType())
            ],
            class_type=ast.ClassDeclaration.REGULAR,
            functions=self.get_functions())

    def get_functions(self):
        functions = [
            ast.FunctionDeclaration("byteValue", [], ByteType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("doubleValue", [], DoubleType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("floatValue", [], FloatType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("intValue", [], IntegerType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("shortValue", [], ShortType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("longValue", [], LongType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("toString", [], StringType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
        ]
        return functions


class IntegerType(NumberType):

    def __init__(self, name="Integer", primitive=False):
        super().__init__(name)
        self.primitive = primitive
        if not self.primitive:
            self.supertypes.append(NumberType())
        else:
            self.supertypes = OrderedSet()

    def get_builtin_type(self):
        return bt.Integer

    def box_type(self):
        return IntegerType(self.name, primitive=False)

    def is_assignable(self, other):
        assignable_types = (
            NumberType,
            IntegerType,
        )
        return self.is_subtype(other) or type(other) in assignable_types

    def get_name(self):
        if self.is_primitive():
            return "int"
        return super().get_name()

    def get_class_declaration(self):
        return ast.ClassDeclaration(
            name=self.name,
            superclasses=[
                ast.SuperClassInstantiation(class_type=NumberType())
            ],
            class_type=ast.ClassDeclaration.REGULAR,
            functions=self.get_functions())

    def get_binary_ops(self):
        return [
            (ast.ArithExpr, ast.Operator('+'), IntegerType()),
            (ast.ArithExpr, ast.Operator('-'), IntegerType()),
            (ast.ArithExpr, ast.Operator('*'), IntegerType()),
            (ast.ArithExpr, ast.Operator('/'), IntegerType()),
        ]


class ShortType(NumberType):

    def __init__(self, name="Short", primitive=False):
        super().__init__(name)
        self.primitive = primitive
        if not self.primitive:
            self.supertypes.append(NumberType())
        else:
            self.supertypes = OrderedSet()

    def get_builtin_type(self):
        return bt.Short

    def box_type(self):
        return ShortType(self.name, primitive=False)

    def is_assignable(self, other):
        assignable_types = (
            NumberType,
            ShortType,
        )
        return self.is_subtype(other) or type(other) in assignable_types

    def get_name(self):
        if self.is_primitive():
            return "short"
        return super().get_name()

    def get_class_declaration(self):
        return ast.ClassDeclaration(
            name=self.name,
            superclasses=[
                ast.SuperClassInstantiation(class_type=NumberType())
            ],
            class_type=ast.ClassDeclaration.REGULAR,
            functions=self.get_functions())

    def get_binary_ops(self):
        return [
            (ast.ArithExpr, ast.Operator('+'), IntegerType()),
            (ast.ArithExpr, ast.Operator('-'), IntegerType()),
            (ast.ArithExpr, ast.Operator('*'), IntegerType()),
            (ast.ArithExpr, ast.Operator('/'), IntegerType()),
        ]


class LongType(NumberType):

    def __init__(self, name="Long", primitive=False):
        super().__init__(name)
        self.primitive = primitive
        if not self.primitive:
            self.supertypes.append(NumberType())
        else:
            self.supertypes = OrderedSet()

    def get_builtin_type(self):
        return bt.Long

    def box_type(self):
        return LongType(self.name, primitive=False)

    def is_assignable(self, other):
        assignable_types = (
            NumberType,
            LongType,
        )
        return self.is_subtype(other) or type(other) in assignable_types

    def get_name(self):
        if self.is_primitive():
            return "long"
        return super().get_name()

    def get_class_declaration(self):
        return ast.ClassDeclaration(
            name=self.name,
            superclasses=[
                ast.SuperClassInstantiation(class_type=NumberType())
            ],
            class_type=ast.ClassDeclaration.REGULAR,
            functions=self.get_functions())

    # noinspection DuplicatedCode
    def get_binary_ops(self):
        return [
            (ast.ArithExpr, ast.Operator('+'), LongType()),
            (ast.ArithExpr, ast.Operator('-'), LongType()),
            (ast.ArithExpr, ast.Operator('*'), LongType()),
            (ast.ArithExpr, ast.Operator('/'), LongType()),
        ]


class ByteType(NumberType):

    def __init__(self, name="Byte", primitive=False):
        super().__init__(name)
        self.primitive = primitive
        if not self.primitive:
            self.supertypes.append(NumberType())
        else:
            self.supertypes = OrderedSet()

    def get_builtin_type(self):
        return bt.Byte

    def box_type(self):
        return ByteType(self.name, primitive=False)

    def is_assignable(self, other):
        assignable_types = (
            NumberType,
            ByteType,
        )
        return self.is_subtype(other) or type(other) in assignable_types

    def get_name(self):
        if self.is_primitive():
            return "byte"
        return super().get_name()

    def get_class_declaration(self):
        return ast.ClassDeclaration(
            name=self.name,
            superclasses=[
                ast.SuperClassInstantiation(class_type=NumberType())
            ],
            class_type=ast.ClassDeclaration.REGULAR,
            functions=self.get_functions())

    # noinspection DuplicatedCode
    def get_binary_ops(self):
        return [
            (ast.ArithExpr, ast.Operator('+'), IntegerType()),
            (ast.ArithExpr, ast.Operator('-'), IntegerType()),
            (ast.ArithExpr, ast.Operator('*'), IntegerType()),
            (ast.ArithExpr, ast.Operator('/'), IntegerType()),
        ]


class FloatType(NumberType):

    def __init__(self, name="Float", primitive=False):
        super().__init__(name)
        self.primitive = primitive
        if not self.primitive:
            self.supertypes.append(NumberType())
        else:
            self.supertypes = OrderedSet()

    def get_builtin_type(self):
        return bt.Float

    def box_type(self):
        return FloatType(self.name, primitive=False)

    def is_assignable(self, other):
        assignable_types = (
            NumberType,
            FloatType,
        )
        return self.is_subtype(other) or type(other) in assignable_types

    def get_name(self):
        if self.is_primitive():
            return "float"
        return super().get_name()

    def get_class_declaration(self):
        return ast.ClassDeclaration(
            name=self.name,
            superclasses=[
                ast.SuperClassInstantiation(class_type=NumberType())
            ],
            class_type=ast.ClassDeclaration.REGULAR,
            functions=self.get_functions())

    def get_binary_ops(self):
        return [
            (ast.ArithExpr, ast.Operator('+'), FloatType()),
            (ast.ArithExpr, ast.Operator('-'), FloatType()),
            (ast.ArithExpr, ast.Operator('*'), FloatType()),
            (ast.ArithExpr, ast.Operator('/'), FloatType()),
        ]

    def get_functions(self):
        functions = [
            ast.FunctionDeclaration("doubleValue", [], DoubleType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("floatValue", [], FloatType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("intValue", [], IntegerType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("longValue", [], LongType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("toString", [], StringType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
        ]
        return functions


class DoubleType(NumberType):

    def __init__(self, name="Double", primitive=False):
        super().__init__(name)
        self.primitive = primitive
        if not self.primitive:
            self.supertypes.append(NumberType())
        else:
            self.supertypes = OrderedSet()

    def get_builtin_type(self):
        return bt.Double

    def box_type(self):
        return DoubleType(self.name, primitive=False)

    def is_assignable(self, other):
        assignable_types = (
            NumberType,
            DoubleType,
        )
        return self.is_subtype(other) or type(other) in assignable_types

    def get_name(self):
        if self.is_primitive():
            return "double"
        return super().get_name()

    def get_class_declaration(self):
        return ast.ClassDeclaration(
            name=self.name,
            superclasses=[
                ast.SuperClassInstantiation(class_type=NumberType())
            ],
            class_type=ast.ClassDeclaration.REGULAR,
            functions=self.get_functions())

    def get_binary_ops(self):
        return [
            (ast.ArithExpr, ast.Operator('+'), DoubleType()),
            (ast.ArithExpr, ast.Operator('-'), DoubleType()),
            (ast.ArithExpr, ast.Operator('*'), DoubleType()),
            (ast.ArithExpr, ast.Operator('/'), DoubleType()),
        ]

    def get_functions(self):
        functions = [
            ast.FunctionDeclaration("doubleValue", [], DoubleType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("floatValue", [], FloatType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("intValue", [], IntegerType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("longValue", [], LongType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("toString", [], StringType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
        ]
        return functions


class CharType(ObjectType):

    def __init__(self, name="Character", primitive=False):
        super().__init__(name)
        self.primitive = primitive
        if not self.primitive:
            self.supertypes.append(ObjectType())
        else:
            self.supertypes = OrderedSet()

    def get_builtin_type(self):
        return bt.Char

    def box_type(self):
        return CharType(self.name, primitive=False)

    def get_name(self):
        if self.is_primitive():
            return "char"
        return super().get_name()

    def get_class_declaration(self):
        return ast.ClassDeclaration(
            name=self.name,
            superclasses=[
                ast.SuperClassInstantiation(class_type=ObjectType())
            ],
            class_type=ast.ClassDeclaration.REGULAR,
            functions=self.get_functions())

    def get_functions(self):
        return [
            ast.FunctionDeclaration("toString", [], StringType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD)
        ]


class StringType(ObjectType):

    def __init__(self, name="String"):
        super().__init__(name)
        self.supertypes.append(ObjectType())

    def get_builtin_type(self):
        return bt.String

    def box_type(self):
        return self

    def get_class_declaration(self):
        return ast.ClassDeclaration(
            name=self.name,
            superclasses=[
                ast.SuperClassInstantiation(class_type=ObjectType())
            ],
            class_type=ast.ClassDeclaration.REGULAR,
            functions=self.get_functions())

    def get_functions(self):
        functions = [
            ast.FunctionDeclaration("toString", [], StringType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("toLowerCase", [], StringType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("toUpperCase", [], StringType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration(
                "contains", [ast.ParameterDeclaration('other', StringType())],
                BooleanType(), None, ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("replace", [
                ast.ParameterDeclaration('oldChar', CharType()),
                ast.ParameterDeclaration('newChar', CharType())
            ], StringType(), None, ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("substring", [
                ast.ParameterDeclaration('beginIndex', IntegerType()),
                ast.ParameterDeclaration('endIndex', IntegerType())
            ], StringType(), None, ast.FunctionDeclaration.CLASS_METHOD),
        ]
        return functions

    def get_binary_ops(self):
        return [(ast.ArithExpr, ast.Operator('+'), StringType())]


class BooleanType(ObjectType):

    def __init__(self, name="Boolean", primitive=False):
        super().__init__(name)
        self.primitive = primitive
        if not self.primitive:
            self.supertypes.append(ObjectType())
        else:
            self.supertypes = []

    def get_builtin_type(self):
        return bt.Boolean

    def box_type(self):
        return BooleanType(self.name, primitive=False)

    def get_name(self):
        if self.is_primitive():
            return "boolean"
        return super().get_name()

    def get_class_declaration(self):
        return ast.ClassDeclaration(
            name=self.name,
            superclasses=[
                ast.SuperClassInstantiation(class_type=ObjectType())
            ],
            class_type=ast.ClassDeclaration.REGULAR,
            functions=self.get_functions())

    def get_functions(self):
        return [
            ast.FunctionDeclaration("toString", [], StringType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD)
        ]


class ArrayType(tp.TypeConstructor, ObjectType):

    def __init__(self, name="Array"):
        # In Java, arrays are covariant.
        super().__init__(name, [tp.TypeParameter("T", variance=tp.Covariant)])
        self.supertypes.append(ObjectType())


class IteratorType(tp.TypeConstructor, ObjectType):

    def __init__(self, name="java.util.Iterator"):
        super().__init__(name, [tp.TypeParameter("T")])
        self.supertypes.append(ObjectType())


class ArrayListType(tp.TypeConstructor, ObjectType):

    def __init__(self, name="java.util.ArrayList"):
        super().__init__(name, [tp.TypeParameter("T")])
        self.supertypes.append(ObjectType())


class FunctionType(tp.TypeConstructor, ObjectType):

    def __init__(self, nr_type_parameters: int):
        name = "Function" + str(nr_type_parameters)
        type_parameters = [
            tp.TypeParameter("A" + str(i))
            for i in range(1, nr_type_parameters + 1)
        ] + [tp.TypeParameter("R")]
        self.nr_type_parameters = nr_type_parameters
        super().__init__(name, type_parameters)
        self.supertypes.append(ObjectType())


### WARNING: use them only for testing ###
Object = ObjectType()
Void = VoidType()
Number = NumberType()
Integer = IntegerType()
Short = ShortType()
Long = LongType()
Byte = ByteType()
Float = FloatType()
Double = DoubleType()
Char = CharType()
String = StringType()
Boolean = BooleanType()
Array = ArrayType()
NonNothingTypes = [
    Object, Number, Integer, Short, Long, Byte, Float, Double, Char, String,
    Boolean, Array
]
