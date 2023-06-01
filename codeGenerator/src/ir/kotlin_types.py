# pylint: disable=abstract-method, useless-super-delegation,too-many-ancestors
import src.ir.ast as ast
import src.ir.builtins as bt
import src.ir.types as tp


class KotlinBuiltinFactory(bt.BuiltinFactory):
    def get_language(self):
        return "kotlin"

    def get_builtin(self):
        return KotlinBuiltin

    def get_void_type(self):
        return UnitType()

    def get_any_type(self):
        return AnyType()

    def get_number_type(self):
        return NumberType()

    def get_integer_type(self):
        return IntegerType()

    def get_byte_type(self):
        return ByteType()

    def get_short_type(self):
        return ShortType()

    def get_long_type(self):
        return LongType()

    def get_float_type(self):
        return FloatType()

    def get_double_type(self):
        return DoubleType()

    def get_big_decimal_type(self):
        return DoubleType()

    def get_big_integer_type(self):
        # FIXME
        return IntegerType()

    def get_boolean_type(self):
        return BooleanType()

    def get_char_type(self):
        return CharType()

    def get_string_type(self):
        return StringType()

    def get_array_type(self):
        return ArrayType()

    def get_iterator_type(self):
        return IteratorType()

    def get_function_type(self, nr_parameters=0):
        return FunctionType(nr_parameters)

    def get_nothing(self):
        return NothingType()

    def get_non_nothing_types(self):
        types = super().get_non_nothing_types()
        # types.extend([
        #     DoubleArray,
        #     FloatArray,
        #     LongArray,
        #     IntegerArray,
        #     ShortArray,
        #     ByteArray,
        #     CharArray,
        #     BooleanArray
        # ])
        return types


class KotlinBuiltin(tp.Builtin):
    def __str__(self):
        return str(self.name) + "(kotlin-builtin)"

    def is_primitive(self):
        return False


class AnyType(KotlinBuiltin, ):
    def __init__(self, name="Any"):
        super().__init__(name)

    def get_builtin_type(self):
        return bt.Any

    def get_class_declaration(self):
        return ast.ClassDeclaration(
            name=self.name,
            superclasses=[],
            class_type=ast.ClassDeclaration.REGULAR,
        )


class NothingType(KotlinBuiltin):
    def __init__(self, name="Nothing"):
        super().__init__(name)

    def is_subtype(self, other):
        return True

    def get_builtin_type(self):
        return bt.Nothing


class UnitType(AnyType):
    def __init__(self, name="Unit"):
        super().__init__(name)
        self.supertypes.append(AnyType())

    def get_builtin_type(self):
        return bt.Void


class NumberType(AnyType):
    def __init__(self, name="Number"):
        super().__init__(name)
        self.supertypes.append(AnyType())

    def get_builtin_type(self):
        return bt.Number

    def get_class_declaration(self):
        return ast.ClassDeclaration(
            name=self.name,
            superclasses=[ast.SuperClassInstantiation(class_type=AnyType())],
            class_type=ast.ClassDeclaration.REGULAR,
            functions=self.get_functions(),
        )

    def get_functions(self):
        functions = [
            ast.FunctionDeclaration("toByte", [], ByteType(), None, ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("toDouble", [], DoubleType(), None, ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("toFloat", [], FloatType(), None, ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("toInt", [], IntegerType(), None, ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("toShort", [], ShortType(), None, ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("toLong", [], LongType(), None, ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("toString", [], StringType(), None, ast.FunctionDeclaration.CLASS_METHOD),
        ]
        return functions


class IntegerType(NumberType):
    def __init__(self, name="Int"):
        super().__init__(name)
        self.supertypes.append(NumberType())

    def get_builtin_type(self):
        return bt.Integer

    def get_class_declaration(self):
        return ast.ClassDeclaration(
            name=self.name,
            superclasses=[ast.SuperClassInstantiation(class_type=NumberType())],
            class_type=ast.ClassDeclaration.REGULAR,
            functions=self.get_functions(),
        )


class ShortType(NumberType):
    def __init__(self, name="Short"):
        super().__init__(name)
        self.supertypes.append(NumberType())

    def get_builtin_type(self):
        return bt.Short

    def get_class_declaration(self):
        return ast.ClassDeclaration(
            name=self.name,
            superclasses=[ast.SuperClassInstantiation(class_type=NumberType())],
            class_type=ast.ClassDeclaration.REGULAR,
            functions=self.get_functions(),
        )


class LongType(NumberType):
    def __init__(self, name="Long"):
        super().__init__(name)
        self.supertypes.append(NumberType())

    def get_builtin_type(self):
        return bt.Long

    def get_class_declaration(self):
        return ast.ClassDeclaration(
            name=self.name,
            superclasses=[ast.SuperClassInstantiation(class_type=NumberType())],
            class_type=ast.ClassDeclaration.REGULAR,
            functions=self.get_functions(),
        )


class ByteType(NumberType):
    def __init__(self, name="Byte"):
        super().__init__(name)
        self.supertypes.append(NumberType())

    def get_builtin_type(self):
        return bt.Byte

    def get_class_declaration(self):
        return ast.ClassDeclaration(
            name=self.name,
            superclasses=[ast.SuperClassInstantiation(class_type=NumberType())],
            class_type=ast.ClassDeclaration.REGULAR,
            functions=self.get_functions(),
        )


class FloatType(NumberType):
    def __init__(self, name="Float"):
        super().__init__(name)
        self.supertypes.append(NumberType())

    def get_builtin_type(self):
        return bt.Float

    def get_class_declaration(self):
        return ast.ClassDeclaration(
            name=self.name,
            superclasses=[ast.SuperClassInstantiation(class_type=NumberType())],
            class_type=ast.ClassDeclaration.REGULAR,
            functions=self.get_functions(),
        )


class DoubleType(NumberType):
    def __init__(self, name="Double"):
        super().__init__(name)
        self.supertypes.append(NumberType())

    def get_builtin_type(self):
        return bt.Double

    def get_class_declaration(self):
        return ast.ClassDeclaration(
            name=self.name,
            superclasses=[ast.SuperClassInstantiation(class_type=NumberType())],
            class_type=ast.ClassDeclaration.REGULAR,
            functions=self.get_functions(),
        )


class CharType(AnyType):
    def __init__(self, name="Char"):
        super().__init__(name)
        self.supertypes.append(AnyType())

    def get_builtin_type(self):
        return bt.Char

    def get_class_declaration(self):
        return ast.ClassDeclaration(
            name=self.name,
            superclasses=[ast.SuperClassInstantiation(class_type=AnyType())],
            class_type=ast.ClassDeclaration.REGULAR,
            functions=self.get_functions()
        )

    def get_functions(self):
        return [ast.FunctionDeclaration("toString", [], StringType(), None, ast.FunctionDeclaration.CLASS_METHOD)]


class StringType(AnyType):
    def __init__(self, name="String"):
        super().__init__(name)
        self.supertypes.append(AnyType())

    def get_builtin_type(self):
        return bt.String

    def get_class_declaration(self):
        return ast.ClassDeclaration(
            name=self.name,
            superclasses=[ast.SuperClassInstantiation(class_type=AnyType())],
            class_type=ast.ClassDeclaration.REGULAR,
            functions=self.get_functions()
        )

    def get_functions(self):
        return [
            ast.FunctionDeclaration("toString", [], StringType(), None, ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("toLowerCase", [], StringType(), None, ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("toUpperCase", [], StringType(), None, ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("contains", [ast.ParameterDeclaration('other', StringType())], BooleanType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("replace", [ast.ParameterDeclaration('oldChar', CharType()),
                                                ast.ParameterDeclaration('newChar', CharType())], StringType(), None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
            ast.FunctionDeclaration("substring", [ast.ParameterDeclaration('beginIndex', IntegerType()),
                                                  ast.ParameterDeclaration('endIndex', IntegerType())], StringType(),
                                    None,
                                    ast.FunctionDeclaration.CLASS_METHOD),
        ]


class BooleanType(AnyType):
    def __init__(self, name="Boolean"):
        super().__init__(name)
        self.supertypes.append(AnyType())

    def get_builtin_type(self):
        return bt.Boolean

    def get_class_declaration(self):
        return ast.ClassDeclaration(
            name=self.name,
            superclasses=[ast.SuperClassInstantiation(class_type=AnyType())],
            class_type=ast.ClassDeclaration.REGULAR,
            functions=self.get_functions()
        )

    def get_functions(self):
        return [ast.FunctionDeclaration("toString", [], StringType(), None, ast.FunctionDeclaration.CLASS_METHOD)]


class ArrayType(tp.TypeConstructor, AnyType):
    def __init__(self, name="Array"):
        # In Kotlin, arrays are invariant.
        super().__init__(name, [tp.TypeParameter("T", variance=tp.Covariant)])
        self.supertypes.append(AnyType())


class IteratorType(tp.TypeConstructor, AnyType):
    def __init__(self, name="Iterator"):
        super().__init__(name, [tp.TypeParameter("T")])
        self.supertypes.append(AnyType())


class SpecializedArrayType(tp.TypeConstructor, AnyType):
    def __init__(self, name="Array"):
        # In Kotlin, arrays are invariant.
        super().__init__(name, [tp.TypeParameter("T")])
        self.supertypes.append(AnyType())


class FunctionType(tp.TypeConstructor, AnyType):
    def __init__(self, nr_type_parameters: int):
        name = "Function" + str(nr_type_parameters)
        # We can have decl-variance in Kotlin
        type_parameters = [
                              tp.TypeParameter("A" + str(i))  # , tp.Contravariant)
                              for i in range(1, nr_type_parameters + 1)
                          ] + [tp.TypeParameter("R")]  # , tp.Covariant)]
        self.nr_type_parameters = nr_type_parameters
        super().__init__(name, type_parameters)
        self.supertypes.append(AnyType())


### WARNING: use them only for testing ###
Any = AnyType()
Nothing = NothingType()
Unit = UnitType()
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

# Specialized arrays, see https://kotlinlang.org/spec/type-system.html#array-types
DoubleArray = SpecializedArrayType().new([Double])
FloatArray = SpecializedArrayType().new([Float])
LongArray = SpecializedArrayType().new([Long])
IntegerArray = SpecializedArrayType().new([Integer])
ShortArray = SpecializedArrayType().new([Short])
ByteArray = SpecializedArrayType().new([Byte])
CharArray = SpecializedArrayType().new([Char])
BooleanArray = SpecializedArrayType().new([Boolean])

NonNothingTypes = [Any, Number, Integer, Short, Long, Byte, Float,
                   Double, Char, String, Boolean, Array,
                   DoubleArray, FloatArray, LongArray, IntegerArray,
                   ShortArray, ByteArray, CharArray, BooleanArray]
