"""
This file includes the program generator.

Context:
    The context is composed of three types of declarations:
        * VariableDeclaration
        * FunctionDeclaration
        * ClassDeclaration
    In the generator, we add declarations to the context after creating their
    AST Nodes because only then we have generated all their values.
    This introduces an issue when we want to look up the context when
    creating subnodes. To solve this issue, we generate artificial nodes in
    `gen_func_decl` and `gen_class_decl`, which we delete before returning
    from those functions.

TODO: describe the generation steps.

TODOs:
    * Use a probabilities table.
"""
# pylint: disable=too-many-instance-attributes,too-many-arguments,dangerous-default-value
import functools
from collections import defaultdict
from copy import deepcopy
from typing import Tuple, List, Callable

from ordered_set import OrderedSet

from src import utils as ut
from src.generators import generators as gens
from src.generators import utils as gu
from src.generators.config import cfg
from src.ir import BUILTIN_FACTORIES
from src.ir import ast, types as tp, type_utils as tu
from src.ir.builtins import BuiltinFactory
from src.ir.context import Context
from src.modules.logging import Logger, log


# noinspection PyUnresolvedReferences,PyTypeChecker,PyArgumentList
class Generator:

    def __init__(self, language=None, options=None, logger=None):
        assert language is not None, "You must specify the language"
        self.language = language
        self.logger: Logger = logger
        # noinspection PyTypeChecker
        self.context: typing.Optional[Context] = None
        self.bt_factory: BuiltinFactory = BUILTIN_FACTORIES[language]
        self.depth = 1
        self._vars_in_context = defaultdict(lambda: 0)
        self._new_from_class = None
        self.namespace = ('global', )
        self.enable_pecs = False
        self.disable_variance_functions = True

        # This flag is used for Java lambdas where local variables references
        # must be final.
        self._inside_java_lambda = False
        self._inside_func_body = False

        self.function_type = type(self.bt_factory.get_function_type())
        self.function_types = self.bt_factory.get_function_types(
            cfg.limits.max_functional_params)

        self.ret_builtin_types = self.bt_factory.get_non_nothing_types()
        self.builtin_types = self.ret_builtin_types + \
                             [self.bt_factory.get_void_type()]

        # In some case we need to use two namespaces. One for having access
        # to variables from scope, and one for adding new declarations.
        # In most cases one namespace is enough, but in cases like
        # `generate_expr` in `_gen_func_params_with_default` we need both
        # namespaces. To use one namespace we must model scope better.
        # Almost always declaration_namespace is set to None to be ignored
        self.declaration_namespace = None
        self.int_stream = iter(range(1, 10000))
        self._in_super_call = False
        # We use this data strcuture to store blacklisted classes, i.e.,
        # classes that are incomplete (we do not have the information regarding
        # their fields and functions yet). So, we avoid instantiating these
        # classes or using them as supertypes, because we do not have the
        # complete informations about them.
        self._blacklisted_classes: OrderedSet = OrderedSet()
        self.fa = 0
        self.loopExpr = 0
        self.allow_bottom_consts = True

    ### Entry Point Generators ###

    def generate(self, context=None) -> ast.Program:
        """Generate a program.

        It first generates a number `n` top-level declarations,
        and then it generates the main function.
        """
        self.context = context or Context()
        for _ in ut.randomUtil.range(cfg.limits.min_top_level,
                                     cfg.limits.max_top_level):
            self.gen_top_level_declaration()
        self.generate_main_func()
        return ast.Program(self.context, self.language)

    def gen_class_for_bottom_constant(self, super_class: ast.ClassDeclaration,
                                      cls_type, type_var_map):
        class_name = gu.gen_identifier('capitalize')
        initial_namespace = self.namespace
        self.namespace = ast.GLOBAL_NAMESPACE + (class_name, )
        initial_depth = self.depth
        self.depth = 2
        cls = ast.ClassDeclaration(class_name,
                                   class_type=ast.ClassDeclaration.REGULAR,
                                   superclasses=[],
                                   type_parameters=[],
                                   is_final=True,
                                   fields=[],
                                   functions=[])
        self._add_node_to_parent(ast.GLOBAL_NAMESPACE, cls)
        self._blacklisted_classes.add(class_name)

        con_args = None if super_class.is_interface() else []
        prev_super_call = self._in_super_call
        self._in_super_call = True
        for f in super_class.fields:
            field_type = tp.substitute_type(f.get_type(), type_var_map)
            con_args.append(self.generate_expr(field_type, only_leaves=True))
        self._in_super_call = prev_super_call
        super_cls_info = gu.SuperClassInfo(
            super_class, type_var_map,
            ast.SuperClassInstantiation(cls_type, con_args))

        cls.superclasses = [super_cls_info.super_inst]
        cls.supertypes = [c.class_type for c in cls.superclasses]
        cls.fields = self.gen_class_fields(cls, super_cls_info)

        cls.functions = self.gen_class_functions(cls, super_cls_info)
        self._blacklisted_classes.remove(class_name)
        self.namespace = initial_namespace
        self.depth = initial_depth
        return cls

    def gen_top_level_declaration(self):
        """Generate a top-level declaration and add it in the context.

        Top-level declarations are defined in the global scope.
        Top-level declarations can be:

        * Variable Declarations
        * Class Declarations
        * Function Declarations

        NOTE that a top-level declaration can generate more top-level
        declarations.
        """
        candidates = [
            self.gen_variable_decl,
            self.gen_class_decl,
            self.gen_func_decl,
        ]
        gen_func = ut.randomUtil.choice(candidates)
        gen_func()

    # noinspection PyTypeChecker
    def generate_main_func(self) -> ast.FunctionDeclaration:
        """Generate the main function.
        """

        t_constructor = self.bt_factory.get_array_type()
        type_arg = self.bt_factory.get_string_type()
        args = ast.ParameterDeclaration(
            'args', tp.ParameterizedType(t_constructor, [type_arg]))
        self.allow_bottom_consts = False
        return self.gen_func_decl(self.bt_factory.get_void_type(),
                                  class_is_final=True,
                                  func_name='main',
                                  params=[args])

    def generate_loop_expr(self, already_in_main: list):
        """
        Generate a new loop. One of the three is for, while, do-while.
        Iterations can be either using a variable or iterating through a collection.
        :param already_in_main: a list of declarations that already exist in the parent block
        :return: ast.LoopExpr
        """
        res = []
        iterable_types = self._get_iterable_types()
        random_type_to_iterate = ut.randomUtil.choice(iterable_types)
        initial_depth = self.depth
        initial_namespace = self.namespace
        self.namespace = self.namespace + (f'loop_{self.loopExpr}', )
        self.loopExpr += 1
        self.depth += 1
        if self.depth >= cfg.limits.max_depth:  # gen simple body for loop
            body = self.gen_loop_body_from_existing()
        else:
            body = self._gen_func_body(self.bt_factory.get_void_type())
        body.is_func_block = False
        body.body = [
            decl for decl in body.body if decl not in already_in_main
            and not isinstance(decl, ast.Constant)
        ]
        etype = self.bt_factory.get_string_type()
        string_var = self.find_existing_variable(etype, allow_final=False)
        string_concat = False
        if not string_var:  # if not string var in context found generate a new one
            tmp_namespace = self.namespace
            self.namespace = initial_namespace
            string_var = self.gen_variable_decl(etype, only_leaves=True)
            string_var.is_final = False
            self.namespace = tmp_namespace
        if ut.randomUtil.bool(0.69):  # generate string concat inside loop
            string_concat = True
            old_vars = self.context.get_vars(self.namespace, glob=False)
            bin_op = self.get_bt_operation_generators(etype)[0](etype)
            new_vars = self.context.get_vars(self.namespace, glob=False)
            new_vars = [v for k, v in new_vars.items() if k not in old_vars]
            body.body.extend(new_vars)
            body.body.append(ast.Assignment(string_var.name, bin_op))

        if isinstance(random_type_to_iterate, tp.ParameterizedType
                      ):  # generate an iteration loop over an array
            array_expr = self.gen_array_expr(random_type_to_iterate,
                                             array_list=True)
            if ut.randomUtil.bool(0.43):  # for loop
                loop_expr = ast.ForExpr.IterableExpr(
                    array_expr, ast.Variable(gu.gen_identifier('lower')))
                loop = ast.ForExpr(body, loop_expr)
            else:  # generate while or do-while loop
                array_ = self.gen_variable_decl(random_type_to_iterate,
                                                expr=array_expr)
                iterator_call = ast.FunctionCall("iterator", [])
                iterator = self.gen_variable_decl(tp.ParameterizedType(
                    self.bt_factory.get_iterator_type(),
                    array_expr.array_type.type_args),
                                                  expr=iterator_call)
                iterator_call.receiver = ast.Variable(array_.name)
                cond = ast.FunctionCall("hasNext", [],
                                        ast.Variable(iterator.name))
                if ut.randomUtil.bool(0.43):  # while loop
                    loop = ast.WhileExpr(body, cond)
                else:
                    loop = ast.DoWhileExpr(body, cond)
                res.append(array_)
                res.append(iterator)
        else:  # generate an iteration loop over a variable
            if ut.randomUtil.bool(0.43):  # for loop
                left_bound = gens.gen_integer_constant(
                    left_bound=0, expr_type=random_type_to_iterate)
                right_bound = gens.gen_integer_constant(
                    left_bound=1000000,
                    right_bound=
                    10000000,  # ut.randomUtil.integer(int(left_bound.literal), 100)
                    expr_type=random_type_to_iterate)
                loop_expr = ast.ForExpr.RangeExpr(
                    ast.Variable(gu.gen_identifier('lower')), left_bound,
                    right_bound)
                loop = ast.ForExpr(body, loop_expr)
            else:  # generate while or do-while loop
                i = self.gen_variable_decl(
                    random_type_to_iterate,
                    expr=gens.gen_integer_constant(
                        left_bound=0, expr_type=random_type_to_iterate))
                i.is_final = False
                cond = ast.ComparisonExpr(
                    ast.Variable(i.name),
                    gens.gen_integer_constant(
                        left_bound=ut.randomUtil.integer(
                            int(i.expr.literal), 100),
                        expr_type=random_type_to_iterate),
                    ut.randomUtil.choice(
                        ast.ComparisonExpr.VALID_OPERATORS[self.language]))
                increment = ast.IncDecExpr(ast.Variable(i.name),
                                           ast.IncDecExpr.ALL_OPERATORS[0])
                body.body.append(increment)
                if ut.randomUtil.bool(0.43):
                    loop = ast.WhileExpr(body, cond)
                else:
                    loop = ast.DoWhileExpr(body, cond)
                res.append(i)
        res.append(loop)
        self.depth = initial_depth
        self.namespace = initial_namespace
        if string_concat:  # prevent the compiler from optimizing string concatenation
            length = ".length" if self.language == 'kotlin' else '.length()'
            res.append(
                ast.FunctionCall(
                    'System.out.println',
                    [ast.CallArgument(ast.Variable(string_var.name + length))
                     ]))
        return res

    def _get_iterable_types(self) -> list[tp.Type]:
        """
        Returns a list of iterable types that includes built-in types, user-defined types, and primitive data types
        :return: a list of iterable types
        """
        builtin_types: list[tp.Type] = [
            x for x in self.get_types() if hasattr(x, 'type_args')
        ]
        usr_types = \
            [
                c.get_type()
                for c in self.context.get_classes(self.namespace).values()
            ]
        primitives = [self.bt_factory.get_integer_type()]
        iterable_types: list[tp.Type] = [
            tp.ParameterizedType(self.bt_factory.get_array_list_type(), [t])
            for t in usr_types
        ]
        iterable_types = iterable_types + builtin_types + primitives
        return iterable_types

    ### Generators ###

    ##### Declarations #####
    # FunctionDeclaration, ParameterDeclaration, ClassDeclaration,
    # FieldDeclaration, and VariableDeclaration

    def _remove_unused_type_params(self, type_params, params, ret_type):
        """
        Remove function's type parameters that are not included in its
        signature.
        """

        def get_type_vars(t):
            if t.is_type_var():
                return [t]
            return getattr(t, "get_type_variables",
                           lambda x: [])(self.bt_factory)

        replaced = {}
        all_type_vars = []
        param_types = [p.get_type() for p in params]
        for t in param_types + [ret_type]:
            all_type_vars.extend(get_type_vars(t))

        for t_param in list(type_params):
            if t_param in all_type_vars:
                continue
            bound = t_param.get_bound_rec(self.bt_factory)
            type_vars = get_type_vars(t)
            if any(t in replaced for t in type_vars):
                bound = None
            if bound is None:
                bound = self.bt_factory.get_any_type()

            replaced[t_param] = bound
            self.context.remove_type(self.namespace, t_param.name)
            type_params.remove(t_param)

        for t_param in type_params:
            if t_param.bound:
                t_param.bound = tp.substitute_type(t_param.bound, replaced)

    def gen_func_decl(self,
                      etype: tp.Type = None,
                      not_void=False,
                      class_is_final=False,
                      func_name: str = None,
                      params: List[ast.ParameterDeclaration] = None,
                      abstract=False,
                      is_interface=False,
                      type_params: List[tp.TypeParameter] = None,
                      namespace=None) -> ast.FunctionDeclaration:
        """Generate a function declaration.

        This method is responsible for generating all types of function/methods,
        i.e. functions, class methods, nested functions. Furthermore, it also
        generates parameterized functions.

        Args:
            etype: expected return type.
            not_void: do not return void.
            class_is_final: function of a final class.
            func_name: function name.
            params: list of parameter declarations.
            abstract: function of an abstract class.
            is_interface: function of an interface.
            type_params: list of type parameters for parameterized function.
            namespace: set explicit namespace.

        Returns:
            A function declaration node.
        """
        func_name = func_name or gu.gen_identifier('lower')

        initial_namespace = self.namespace
        if namespace:
            self.namespace = namespace + (func_name, )
        else:
            self.namespace += (func_name, )
        initial_depth = self.depth
        self.depth += 1
        # Check if this function we want to generate is a class method, by
        # checking the name of the outer namespace. If we are in class then
        # the outer namespace begins with capital letter.
        class_method = (False if len(self.namespace) < 2 else
                        self.namespace[-2][0].isupper())
        can_override = abstract or is_interface or (class_method
                                                    and not class_is_final
                                                    and ut.randomUtil.bool())
        # Check if this function we want to generate is a nested functions.
        # To do so, we want to find if the function is directly inside the
        # namespace of another function.
        nested_function = (len(self.namespace) > 1
                           and self.namespace[-2] != 'global'
                           and self.namespace[-2][0].islower())

        prev_inside_java_lamdba = self._inside_java_lambda
        self._inside_java_lambda = nested_function
        # Type parameters of functions cannot be variant.
        # Also note that at this point, we do not allow a conflict between
        # type variable names of class and type variable names of functions.
        # TODO consider being less conservative.
        if not nested_function:
            if type_params is not None:
                for t_p in type_params:
                    # We add the types to the context.
                    self.context.add_type(self.namespace, t_p.name, t_p)
            else:
                # Type parameters of parameterized functions can be neither
                # covariant nor contravariant.
                type_params = self.gen_type_params(
                    with_variance=False,
                    blacklist=self._get_type_variable_names(),
                    for_function=True
                ) if ut.randomUtil.bool(prob=cfg.prob.parameterized_functions) \
                    else []

        else:
            # Nested functions cannot be parameterized (
            # at least in Groovy, Java), because they are modeled as lambdas.
            type_params = []
        if params is not None:
            for p in params:
                self._add_node_to_parent(self.namespace, p)
        else:
            params = (self._gen_func_params() if
                      (ut.randomUtil.bool(prob=0.25) or is_interface) else
                      self._gen_func_params_with_default())
        ret_type = self._get_func_ret_type(params, etype, not_void=not_void)
        if is_interface or (abstract and ut.randomUtil.bool()):
            body, inferred_type = None, None
        else:
            # If we are going to generate a non-abstract method, we generate
            # a temporary body as a placeholder.
            body = ast.BottomConstant(ret_type)
        self._remove_unused_type_params(type_params, params, ret_type)
        func = ast.FunctionDeclaration(
            func_name,
            params,
            ret_type,
            body,
            func_type=(ast.FunctionDeclaration.CLASS_METHOD
                       if class_method else ast.FunctionDeclaration.FUNCTION),
            is_final=not can_override,
            inferred_type=None,
            type_parameters=type_params,
        )
        self._add_node_to_parent(self.namespace[:-1], func)
        for p in params:
            self.context.add_var(self.namespace, p.name, p)

        if func.body is not None:
            body = self._gen_func_body(ret_type)
        func.body = body

        self._inside_java_lambda = prev_inside_java_lamdba
        self.depth = initial_depth
        self.namespace = initial_namespace
        return func

    # Where

    def _gen_func_params_with_default(self) -> List[ast.ParameterDeclaration]:
        """Generate function parameters that may include one with default.

        It will generate at most one parameter with a default value.
        """
        has_default = False
        params = []
        for _ in range(ut.randomUtil.integer(0, cfg.limits.fn.max_params)):
            param = self.gen_param_decl()
            if not has_default:
                has_default = ut.randomUtil.bool()
            if has_default:
                prev_decl_namespace = self.declaration_namespace
                self.declaration_namespace = self.namespace
                prev_namespace = self.namespace
                self.namespace = self.namespace[:-1]
                expr = self.generate_expr(param.get_type(), only_leaves=True)
                self.namespace = prev_namespace
                self.declaration_namespace = prev_decl_namespace
                param.default = expr
            params.append(param)
        return params

    def gen_param_decl(self, etype=None) -> ast.ParameterDeclaration:
        """Generate a function Parameter Declaration.

        Args:
            etype: Parameter type.
        """
        name = gu.gen_identifier('lower')
        if etype and etype.is_wildcard():
            bound = etype.get_bound_rec()
            param_type = bound or self.select_type(exclude_covariants=True)
        else:
            param_type = etype or self.select_type(exclude_covariants=True)
        param = ast.ParameterDeclaration(name, param_type)
        return param

    def gen_class_decl(
            self,
            field_type: tp.Type = None,
            fret_type: tp.Type = None,
            not_void: bool = False,
            type_params: List[tp.TypeParameter] = None,
            class_name: str = None,
            signature: tp.ParameterizedType = None) -> ast.ClassDeclaration:
        """Generate a class declaration.

        It generates all type of classes (regular, abstract, interface),
        and it can also generate parameterized classes.

        Args:
            field_type: At least one field will have this type.
            fret_type: At least one function will return this type.
            not_void: Do not generate functions that return void.
            type_params: List with type parameters.
            class_name: Class name.
            signature: Generate at least one function with the given signature.

        Returns:
            A class declaration node.
        """
        class_name = class_name or gu.gen_identifier('capitalize')
        initial_namespace = self.namespace
        self.namespace += (class_name, )
        initial_depth = self.depth
        self.depth += 1
        class_type = gu.select_class_type(field_type is not None)
        is_final = ut.randomUtil.bool() and class_type == \
                   ast.ClassDeclaration.REGULAR
        type_params = type_params or self.gen_type_params()
        cls = ast.ClassDeclaration(class_name,
                                   class_type=class_type,
                                   superclasses=[],
                                   type_parameters=type_params,
                                   is_final=is_final,
                                   fields=[],
                                   functions=[])
        self._add_node_to_parent(ast.GLOBAL_NAMESPACE, cls)
        self._blacklisted_classes.add(class_name)

        super_cls_info = self._select_superclass(
            class_type == ast.ClassDeclaration.INTERFACE)
        if super_cls_info:
            cls.superclasses = [super_cls_info.super_inst]
            cls.supertypes = [c.class_type for c in cls.superclasses]
        if not cls.is_interface():
            self.gen_class_fields(cls, super_cls_info, field_type)

        self.gen_class_functions(cls, super_cls_info, not_void, fret_type,
                                 signature)
        self._blacklisted_classes.remove(class_name)
        self.namespace = initial_namespace
        self.depth = initial_depth
        return cls

    # Where

    def _select_superclass(self, only_interfaces: bool) -> gu.SuperClassInfo:
        """
        Select a superclass for a class.

        Args:
            only_interfaces: select an interface.

        Returns:
            SuperClassInfo object which includes: the super class declaration,
                its TypeVarMap, and a SuperClassInstantiation for the selected
                class.
        """

        current_cls = self.namespace[-1]

        def is_cls_candidate(cls):
            # A class should not inherit from itself to avoid circular
            # dependency problems.
            if cls.name == current_cls:
                return False
            if cls.name in self._blacklisted_classes:
                return False
            return not cls.is_final and (cls.is_interface()
                                         if only_interfaces else True)

        class_decls = [
            c for c in self.context.get_classes(self.namespace).values()
            if is_cls_candidate(c)
        ]
        if not class_decls:
            return None
        class_decl = ut.randomUtil.choice(class_decls)
        if class_decl.is_parameterized():
            cls_type, type_var_map = tu.instantiate_type_constructor(
                class_decl.get_type(),
                self.get_types(exclude_covariants=True,
                               exclude_contravariants=True,
                               exclude_arrays=True),
                enable_pecs=self.enable_pecs,
                disable_variance_functions=self.disable_variance_functions,
                only_regular=True,
            )
        else:
            cls_type, type_var_map = class_decl.get_type(), {}
        con_args = None if class_decl.is_interface() else []
        prev_super_call = self._in_super_call
        self._in_super_call = True
        for f in class_decl.fields:
            field_type = tp.substitute_type(f.get_type(), type_var_map)
            con_args.append(self.generate_expr(field_type, only_leaves=True))
        self._in_super_call = prev_super_call
        return gu.SuperClassInfo(
            class_decl, type_var_map,
            ast.SuperClassInstantiation(cls_type, con_args))

    # And

    def gen_class_fields(
            self,
            curr_cls: ast.ClassDeclaration,
            super_cls_info: gu.SuperClassInfo,
            field_type: tp.Type = None) -> List[ast.FieldDeclaration]:
        """Generate fields for a class.

        It also adds the fields in the context.

        Args:
            curr_cls: Current class declaration.
            super_cls_info: SuperClassInstantiation for curr_cls
            field_type: At least one field will have this type.

        Returns:
            A list of field declarations
        """
        max_fields = cfg.limits.cls.max_fields - 1 if field_type \
            else cfg.limits.cls.max_fields
        fields = []
        if field_type:
            fields.append(self.gen_field_decl(field_type, curr_cls.is_final))
        if not super_cls_info:
            for _ in range(ut.randomUtil.integer(0, max_fields)):
                fields.append(
                    self.gen_field_decl(class_is_final=curr_cls.is_final))
        else:
            overridable_fields = super_cls_info.super_cls \
                .get_overridable_fields()
            k = ut.randomUtil.integer(0,
                                      min(max_fields, len(overridable_fields)))
            if overridable_fields:
                chosen_fields = ut.randomUtil.sample(overridable_fields, k=k)
                for f in chosen_fields:
                    field_type = tp.substitute_type(
                        f.get_type(), super_cls_info.type_var_map)
                    new_f = self.gen_field_decl(field_type,
                                                curr_cls.is_final,
                                                add_to_parent=False)
                    new_f.name = f.name
                    new_f.override = True
                    new_f.is_final = f.is_final
                    fields.append(new_f)
                    self._add_node_to_parent(self.namespace, new_f)
                max_fields = max_fields - len(chosen_fields)
            if max_fields < 0:
                return fields
            for _ in range(ut.randomUtil.integer(0, max_fields)):
                fields.append(
                    self.gen_field_decl(class_is_final=curr_cls.is_final))
        return fields

    # Where

    def _add_node_to_class(self, cls, node):
        if isinstance(node, ast.FunctionDeclaration):
            cls.functions.append(node)
            return

        if isinstance(node, ast.FieldDeclaration):
            cls.fields.append(node)
            return

        assert False, ('Trying to put a node in class other than a function',
                       ' and a field')

    def _add_node_to_parent(self, parent_namespace, node):
        node_type = {
            ast.FunctionDeclaration: self.context.add_func,
            ast.ClassDeclaration: self.context.add_class,
            ast.VariableDeclaration: self.context.add_var,
            ast.FieldDeclaration: self.context.add_var,
            ast.ParameterDeclaration: self.context.add_var,
            ast.Lambda: self.context.add_lambda,
        }
        if parent_namespace == ast.GLOBAL_NAMESPACE:
            node_type[type(node)](parent_namespace, node.name, node)
            return
        parent = self.context.get_decl(parent_namespace[:-1],
                                       parent_namespace[-1])
        if parent and isinstance(parent, ast.ClassDeclaration):
            self._add_node_to_class(parent, node)

        node_type[type(node)](parent_namespace, node.name, node)

    # And

    def gen_class_functions(
        self,
        curr_cls,
        super_cls_info,
        not_void=False,
        fret_type=None,
        signature: tp.ParameterizedType = None
    ) -> List[ast.FunctionDeclaration]:
        """Generate methods for a class.

        If the method has a superclass, then it will try to implement any
        method that must be implemented (e.g., abstract methods in regular
        classes).

        Args:
            curr_cls: Current Class declaration
            super_cls_info: SuperClassInstantiation for curr_cls
            not_void: Do not create methods that return void.
            fret_type: At least one method will return this type.
            signature: Generate at least one function with the given signature.
        """
        funcs = []
        max_funcs = cfg.limits.cls.max_funcs - 1 if fret_type \
            else cfg.limits.cls.max_funcs
        max_funcs = max_funcs - 1 if signature else max_funcs
        abstract = not curr_cls.is_regular()
        if fret_type:
            funcs.append(
                self.gen_func_decl(fret_type,
                                   not_void=not_void,
                                   class_is_final=curr_cls.is_final,
                                   abstract=abstract,
                                   is_interface=curr_cls.is_interface()))
        if signature:
            ret_type, params = self._gen_ret_and_paramas_from_sig(signature)
            funcs.append(
                self.gen_func_decl(ret_type,
                                   params=params,
                                   not_void=not_void,
                                   class_is_final=curr_cls.is_final,
                                   abstract=abstract,
                                   is_interface=curr_cls.is_interface()))
        if not super_cls_info:
            for _ in range(ut.randomUtil.integer(0, max_funcs)):
                funcs.append(
                    self.gen_func_decl(not_void=not_void,
                                       class_is_final=curr_cls.is_final,
                                       abstract=abstract,
                                       is_interface=curr_cls.is_interface()))
        else:
            abstract_funcs = []
            class_decls = self.context.get_classes(self.namespace).values()
            if curr_cls.is_regular():
                abstract_funcs = super_cls_info.super_cls \
                    .get_abstract_functions(class_decls)
                for f in abstract_funcs:
                    funcs.append(
                        self._gen_func_from_existing(
                            f, super_cls_info.type_var_map, curr_cls.is_final,
                            curr_cls.is_interface()))
                max_funcs = max_funcs - len(abstract_funcs)
            overridable_funcs = super_cls_info.super_cls \
                .get_overridable_functions()
            abstract_funcs = {f.name for f in abstract_funcs}
            overridable_funcs = [
                f for f in overridable_funcs if f.name not in abstract_funcs
            ]
            len_over_f = len(overridable_funcs)
            if len_over_f > max_funcs:
                return funcs
            k = ut.randomUtil.integer(0, min(max_funcs, len_over_f))
            chosen_funcs = ([] if not max_funcs or curr_cls.is_interface() else
                            ut.randomUtil.sample(overridable_funcs, k=k))
            for f in chosen_funcs:
                funcs.append(
                    self._gen_func_from_existing(f,
                                                 super_cls_info.type_var_map,
                                                 curr_cls.is_final,
                                                 curr_cls.is_interface()))
            max_funcs = max_funcs - len(chosen_funcs)
            if max_funcs < 0:
                return funcs
            for _ in range(ut.randomUtil.integer(0, max_funcs)):
                funcs.append(
                    self.gen_func_decl(not_void=not_void,
                                       class_is_final=curr_cls.is_final,
                                       abstract=abstract,
                                       is_interface=curr_cls.is_interface()))
        return funcs

    # And

    def _gen_func_from_existing(self, func: ast.FunctionDeclaration,
                                type_var_map: tu.TypeVarMap,
                                class_is_final: bool,
                                is_interface: bool) -> ast.FunctionDeclaration:
        """Generate a method that overrides an existing method.

        Args:
            func: Method to override.
            type_var_map: TypeVarMap of func
            class_is_final: is current class final.
            is_interface: is current class an interface.

        Returns:
            A function declaration.
        """
        params = deepcopy(func.params)
        type_params, substituted_type_params = \
            self._gen_type_params_from_existing(func, type_var_map)
        type_param_names = [t.name for t in type_params]
        ret_type = func.ret_type
        for p in params:
            sub = False
            sub_type_map = {
                k: v
                for k, v in type_var_map.items()
                if k.name not in type_param_names
            }
            old = p.get_type()
            p.param_type = tp.substitute_type(p.get_type(), sub_type_map)
            sub = old != p.get_type()
            if not sub:
                p.param_type = tp.substitute_type(p.get_type(),
                                                  substituted_type_params)
            p.default = None
        sub = False
        sub_type_map = {
            k: v
            for k, v in type_var_map.items() if k.name not in type_param_names
        }
        old = ret_type
        ret_type = tp.substitute_type(ret_type, sub_type_map)
        sub = old != ret_type
        if not sub:
            ret_type = tp.substitute_type(ret_type, substituted_type_params)
        new_func = self.gen_func_decl(func_name=func.name,
                                      etype=ret_type,
                                      not_void=False,
                                      class_is_final=class_is_final,
                                      params=params,
                                      is_interface=is_interface,
                                      type_params=type_params)
        if func.body is None:
            new_func.is_final = False
        new_func.override = True
        return new_func

    # Where

    def _gen_type_params_from_existing(
            self, func: ast.FunctionDeclaration,
            type_var_map) -> (List[tp.TypeParameter], tu.TypeVarMap):
        """Gen type parameters for a function that overrides a parameterized
            function.

        Args:
            func: Function to override.
            type_var_map: TypeVarMap of func.

        Returns:
            A list of available type parameters, and TypeVarMap for the type
            parameters of func
        """
        if not func.type_parameters:
            return [], {}
        substituted_type_params = {}
        curr_type_vars = self._get_type_variable_names()
        func_type_vars = [t.name for t in func.type_parameters]
        class_type_vars = [
            t for t in curr_type_vars if t not in func_type_vars
        ]
        blacklist = func_type_vars + curr_type_vars + list(type_var_map.keys())
        new_type_params = []
        for t_param in func.type_parameters:
            # Here, we substitute the bound of an overriden parameterized
            # function based on the type arguments of the superclass.
            new_type_param = deepcopy(t_param)
            if t_param.name in curr_type_vars:
                # The child class contains a type variable that has the
                # same name with a type variable of the overriden function.
                # So we change the name of the function's type variable to
                # avoid the conflict.
                new_name = ut.randomUtil.caps(blacklist=blacklist)
                func_type_vars.append(new_name)
                blacklist.append(new_name)
                new_type_param.name = new_name
                substituted_type_params[t_param] = new_type_param

            if new_type_param.bound is not None:
                sub = False
                sub_type_map = {
                    k: v for k, v in type_var_map.items()
                    if k.name not in func_type_vars \
                       or k.name not in class_type_vars
                }
                old = new_type_param.bound
                bound = tp.substitute_type(new_type_param.bound, sub_type_map)
                sub = old != bound

                if not sub:
                    bound = tp.substitute_type(bound, substituted_type_params)
                new_type_param.bound = bound
            new_type_params.append(new_type_param)
        return new_type_params, substituted_type_params

    def gen_field_decl(self,
                       etype=None,
                       class_is_final=True,
                       add_to_parent=True) -> ast.FieldDeclaration:
        """Generate a class Field Declaration.

        Args:
            etype: Field type.
            class_is_final: Is the class final.
            add_to_parent: add node to parent (default True)
        """
        name = gu.gen_identifier('lower')
        can_override = not class_is_final and ut.randomUtil.bool()
        is_final = ut.randomUtil.bool()
        field_type = etype or self.select_type(exclude_contravariants=True,
                                               exclude_covariants=not is_final,
                                               exclude_function_types=True)
        field = ast.FieldDeclaration(name,
                                     field_type,
                                     is_final=is_final,
                                     can_override=can_override)
        if add_to_parent:
            self._add_node_to_parent(self.namespace, field)
        return field

    def gen_variable_decl(self,
                          etype=None,
                          only_leaves=False,
                          expr=None) -> ast.VariableDeclaration:
        """Generate a Variable Declaration.

        Args:
            etype: the type of the variable.
            only_leaves: do not generate new leaves except from `expr`.
            expr: an expression to assign to the variable.

        Returns:
            A Variable Declaration
        """
        var_type = etype if etype else self.select_type()
        initial_depth = self.depth
        self.depth += 1
        # NOTE maybe we should disable sam coercion for Kotlin
        # the following code does not compile
        # fun interface FI { fun foo(p: Int): Long }
        # var v: FI = {x: Int -> x.toLong()}
        old_allow_bottom_const = self.allow_bottom_consts
        if self.namespace == ast.GLOBAL_NAMESPACE:
            self.allow_bottom_consts = False

        expr = expr or self.generate_expr(
            var_type, only_leaves, sam_coercion=True)
        self.depth = initial_depth
        is_final = ut.randomUtil.bool()
        # We cannot set ? extends X as the type of a variable.
        vtype = var_type.get_bound_rec() if var_type.is_wildcard() else \
            var_type
        var_name = gu.gen_identifier('lower')
        var_decl = ast.VariableDeclaration(var_name,
                                           expr=expr,
                                           is_final=is_final,
                                           var_type=vtype,
                                           inferred_type=var_type)
        self._add_node_to_parent(self.namespace, var_decl)
        self.allow_bottom_consts = old_allow_bottom_const
        return var_decl

    ##### Expressions #####

    def _get_class_attributes(self, class_decl, attr_name):
        class_decls = self.context.get_classes(self.namespace).values()
        if attr_name == 'functions':
            return class_decl.get_callable_functions(class_decls)
        return class_decl.get_all_fields(class_decls)

    def generate_expr(self,
                      expr_type: tp.Type = None,
                      only_leaves=False,
                      subtype=True,
                      exclude_var=False,
                      gen_bottom=False,
                      sam_coercion=False) -> ast.Expr:
        """Generate an expression.

        This function could produce new nodes external to the generated
        expression as a side effect. For instance, it could generate new
        variable declarations.

        Args:
            expr_type: The type that the expression should have.
            only_leaves: do not generate new leaves except from `expr`.
            subtype: The type of the generated expression could be a subtype
                of `expr_type`.
            exclude_var: if this option is false, then it could assign the
                generated expression into a variable, and return that
                variable reference.
            gen_bottom: Generate a bottom constant.
            sam_coercion: Enable sam coercion.

        Returns:
            The generated expression.
        """
        if self.depth >= cfg.limits.max_depth and self.allow_bottom_consts:
            if tu.is_builtin(expr_type, self.bt_factory):
                gen_bottom = False
                only_leaves = True
                exclude_var = False
                sam_coercion = False
            else:
                return ast.BottomConstant(expr_type)
        if gen_bottom:
            only_leaves = True
            exclude_var = False
            sam_coercion = False
            if self.allow_bottom_consts:
                return ast.BottomConstant(expr_type)
        find_subtype = (expr_type and subtype
                        and expr_type != self.bt_factory.get_void_type()
                        and ut.randomUtil.bool())
        expr_type = expr_type or self.select_type()
        if find_subtype:
            subtypes = tu.find_subtypes(expr_type,
                                        self.get_types(),
                                        include_self=True,
                                        concrete_only=True)
            old_type = expr_type
            expr_type = ut.randomUtil.choice(subtypes)
            msg = "Found subtype of {}: {}".format(old_type, expr_type)
            log(self.logger, msg)
        generators = self.get_generators(expr_type,
                                         only_leaves,
                                         subtype,
                                         exclude_var,
                                         sam_coercion=sam_coercion)
        existing_expr = self.find_existing_variable(expr_type)
        if existing_expr and ut.randomUtil.bool(0.7):
            expr = existing_expr
        else:
            expr = ut.randomUtil.choice(generators)(expr_type)
        # Make a probablistic choice, and assign the generated expr
        # into a variable, and return that variable reference.
        gen_var = (not only_leaves
                   and expr_type != self.bt_factory.get_void_type()
                   and self._vars_in_context[self.namespace]
                   < cfg.limits.max_var_decls and ut.randomUtil.bool())
        if gen_var:
            self._vars_in_context[self.namespace] += 1
            var_decl = self.gen_variable_decl(expr_type,
                                              only_leaves,
                                              expr=expr)
            expr = ast.Variable(var_decl.name)
        return expr

    def find_existing_variable(self,
                               expr_type: tp.Type = None,
                               allow_final=True):
        """
        Find existing variable in context with expr_type
        :param expr_type: type of variable
        :param allow_final: if false returns only non-final variables
        :return: variable with type expr_type
        """
        if expr_type is None:
            return None
        _vars = self.context.get_vars(self.namespace, glob=False)
        matched_vars = []
        for key, var in _vars.items():
            if isinstance(
                    var,
                    ast.FieldDeclaration) and var.field_type == expr_type and (
                        not var.is_final or allow_final):
                if self._inside_java_lambda and not allow_final:
                    continue
                matched_vars.append(ast.Variable(var.name))
            if isinstance(var, ast.ParameterDeclaration
                          ) and var.param_type == expr_type and allow_final:
                matched_vars.append(ast.Variable(var.name))
            if isinstance(var, ast.VariableDeclaration
                          ) and var.var_type == expr_type and (not var.is_final
                                                               or allow_final):
                if self._inside_java_lambda and not allow_final:
                    if len(
                            self.context.get_namespaces_decls(
                                self.namespace, var.name, 'vars',
                                glob=False)) == 0:
                        continue
                matched_vars.append(ast.Variable(var.name))
        if len(matched_vars) != 0:
            return ut.randomUtil.choice(matched_vars)
        return None

    def get_bt_operation_generators(self, etype: tp.Type):
        """
        Get generators for builtins
        :param etype: builtin type
        :return: list of lambda expressions that return a binary operation on built-in types
        """
        if not hasattr(etype, 'get_binary_ops'):
            return []
        var_in_context = self.find_existing_variable(etype)
        if var_in_context is None:
            return []
        generators = []
        for op in etype.get_binary_ops():
            if (len(op)) == 3:
                op = op + (False, )
            op_class, operation, ret_type, cast = op
            if ret_type == etype:
                binary_op_generator = lambda x, et=etype, op_cl=op_class, oper=operation, rt=ret_type: op_cl(
                    self.generate_expr(et), self.generate_expr(et), oper
                ) if not cast else ast.ClassCast(
                    op_cl(self.generate_expr(et), self.generate_expr(et), oper
                          ), rt)
                generators.append(binary_op_generator)
        return generators

    def gen_loop_body_from_existing(self) -> ast.Block:
        """
        Generate loop body from existing variable declarations.
        May generate new varDecl with builtin types.
        Body contains only func calls.
        :return: ast.Block - new loop body
        """
        _vars = self.context.get_vars(self.namespace, glob=False)
        new_vars = []
        for _ in ut.randomUtil.range(0, cfg.limits.max_var_decls):
            name = gu.gen_identifier('lower')
            etype = ut.randomUtil.choice([
                bt for bt in self.ret_builtin_types
                if len(bt.get_class_declaration().functions) != 0
            ])
            generator = self.get_generators(etype, True, True, False)[0]
            var = ast.VariableDeclaration(name,
                                          generator(etype),
                                          is_final=ut.randomUtil.bool(),
                                          var_type=etype)
            _vars[name] = var
            new_vars.append(var)
        func_calls = []
        for _, var in _vars.items():
            if isinstance(var, ast.FieldDeclaration):
                etype = var.field_type
                func_calls.extend(
                    self.process_etype(etype, ast.Variable(var.name)))
            if isinstance(var, ast.VariableDeclaration):
                etype = var.var_type
                func_calls.extend(
                    self.process_etype(etype, ast.Variable(var.name)))
            if isinstance(var, ast.ParameterDeclaration):
                etype = var.param_type
                func_calls.extend(
                    self.process_etype(etype, ast.Variable(var.name)))
        func_calls = ut.randomUtil.sample(
            func_calls, min(len(func_calls), cfg.limits.max_var_decls))
        return ast.Block(body=new_vars + func_calls)

    def process_etype(self, etype, receiver):
        """
        Get function calls for target etype
        :param etype: function's type-carrier
        :param receiver: function reciever
        :return: list of func calls
        """
        if isinstance(etype, tp.SimpleClassifier):
            decl_type = self.context.get_classes(
                ('global', )).get(etype.name, None)
            if decl_type is None:
                return []
            return self.get_class_functions_calls(decl_type, receiver)
        if tu.is_builtin(etype, self.bt_factory):
            decl_type = etype.get_class_declaration()
            return self.get_class_functions_calls(decl_type, receiver)
        return []

    def get_class_functions_calls(self, class_decl, receiver):
        """
        Get function calls for target class_decl
        :param class_decl: function's class_decl-carrier
        :param receiver: function reciever
        :return: list of func calls
        """
        func_calls = []
        for func in class_decl.functions:
            if all([p.default is not None for p in func.params]):
                args = [ast.CallArgument(p.default) for p in func.params]
                func_call = ast.FunctionCall(func.name,
                                             args,
                                             receiver=receiver)
                func_calls.append(func_call)
        return func_calls

    # pylint: disable=unused-argument
    def gen_assignment(self,
                       expr_type: tp.Type,
                       only_leaves=False,
                       subtype=True) -> ast.Assignment:
        """Generate an assignment expressions.

        Args:
            expr_type: The value that the assignment expression should hold.
            only_leaves: do not generate new leaves except from `expr`.
            subtype: The type of the generated expression could be a subtype
                of `expr_type`.
        """
        # Get all all non-final variables for performing the assignment.
        variables = self._get_assignable_vars()
        initial_depth = self.depth
        self.depth += 1
        if not variables:
            # Ok, it's time to find a class with non-final fields,
            # generate an object of this class, and perform the assignment.
            res = self._get_classes_with_assignable_fields()
            if res:
                expr_type, field = res
                variables = [(self.generate_expr(expr_type, only_leaves,
                                                 subtype), field)]
        if not variables:
            # Nothing of the above worked, so generate a 'var' variable,
            # and perform the assignment
            etype = self.select_type(exclude_covariants=True,
                                     exclude_contravariants=True)
            self._vars_in_context[self.namespace] += 1
            # If there are not variable declarations that match our criteria,
            # we have to create a new variable declaration.
            var_decl = self.gen_variable_decl(etype, only_leaves)
            var_decl.is_final = False
            var_decl.var_type = var_decl.get_type()
            self.depth = initial_depth
            return ast.Assignment(
                var_decl.name,
                self.generate_expr(var_decl.get_type(), only_leaves, subtype))
        receiver, variable = ut.randomUtil.choice(variables)
        self.depth = initial_depth
        gen_bottom = (variable.get_type().is_wildcard()
                      or (variable.get_type().is_parameterized()
                          and variable.get_type().has_wildcards()))
        return ast.Assignment(
            variable.name,
            self.generate_expr(variable.get_type(),
                               only_leaves,
                               subtype,
                               gen_bottom=gen_bottom),
            receiver=receiver,
        )

    # Where

    def _get_assignable_vars(self) -> List[ast.Variable]:
        """Get all non-final variables in context.

        Note that variables inside lambdas in Java should be either final, or
        effectively final.
        """
        variables = []
        for var in self.context.get_vars(self.namespace).values():
            if self._inside_java_lambda:
                continue
            if not getattr(var, 'is_final', True):
                variables.append((None, var))
                continue
            var_type = self._get_var_type_to_search(var.get_type())
            if not var_type:
                continue
            if isinstance(getattr(var_type, 't_constructor', None),
                          self.function_type):
                continue
            cls, type_var_map = self._get_class(var_type)
            for field in cls.fields:
                # Ok here we create a new field whose type corresponds
                # to the type argument with which the class 'c' is
                # instantiated.
                field_sub = ast.FieldDeclaration(field.name,
                                                 field_type=tp.substitute_type(
                                                     field.get_type(),
                                                     type_var_map))
                if not field.is_final:
                    variables.append((ast.Variable(var.name), field_sub))
        return variables

    # And

    def _get_classes_with_assignable_fields(self):
        """Get classes with non-final fields.

        Returns:
            A list that contains tuples of expressions that produce objects
            of a class, and field declarations.
        """
        classes = []
        class_decls = self.context.get_classes(self.namespace).values()
        for c in class_decls:
            for field in c.fields:
                if not field.is_final:
                    classes.append((c, field))
        assignable_types = []
        for c, f in classes:
            t, type_var_map = c.get_type(), {}
            if t.is_type_constructor():
                variance_choices = {
                    t_param: (False, True)
                    for t_param in t.type_parameters
                }
                t, type_var_map = tu.instantiate_type_constructor(
                    t,
                    self.get_types(exclude_arrays=True),
                    variance_choices=variance_choices,
                    disable_variance_functions=self.disable_variance_functions,
                    enable_pecs=self.enable_pecs)
                # Ok here we create a new field whose type corresponds
                # to the type argument with which the class 'c' is
                # instantiated.
                f = ast.FieldDeclaration(f.name,
                                         field_type=tp.substitute_type(
                                             f.get_type(), type_var_map))
            assignable_types.append((t, f))

        if not assignable_types:
            return None
        return ut.randomUtil.choice(assignable_types)

    def gen_field_access(self,
                         etype: tp.Type,
                         only_leaves=False,
                         subtype=True) -> ast.FieldAccess:
        """Generate a field access expression.

        Args:
            etype: The value that the field access should return.
            only_leaves: do not generate new leaves except from `expr`.
            subtype: The type of the generated expression could be a subtype
                of `expr_type`.
        """
        initial_depth = self.depth
        self.depth += 1
        objs = self._get_matching_objects(etype, subtype, 'fields')
        if not objs:
            type_f = self._get_matching_class(etype,
                                              subtype=subtype,
                                              attr_name='fields')
            if type_f is None:
                type_f = self._gen_matching_class(
                    etype,
                    'fields',
                    not_void=True,
                )
            receiver = self.generate_expr(type_f.receiver_t, only_leaves)
            objs.append(
                gu.AttrReceiverInfo(receiver, None, type_f.attr_decl, None))
        objs = [(obj.receiver_expr, obj.attr_decl) for obj in objs]
        receiver, attr = ut.randomUtil.choice(objs)
        self.depth = initial_depth
        return ast.FieldAccess(receiver, attr.name)

    def gen_variable(self,
                     etype: tp.Type,
                     only_leaves=False,
                     subtype=True) -> ast.Variable:
        """Generate a variable.

        First, it searches for all variables in the scope. In case it doesn't
        find any variable of etype, then it generates one.

        Args:
            etype: The type that the variable should have.
            only_leaves: do not generate new leaves except from `expr`.
            subtype: The type of the generated variable could be a subtype
                of `expr_type`.
        """
        # Get all variables declared in the current namespace or
        # the outer namespace.
        variables = self.context.get_vars(self.namespace).values()
        old_allow_bottom_const = self.allow_bottom_consts
        if self.namespace == ast.GLOBAL_NAMESPACE:
            self.allow_bottom_consts = False
        # Case where we want only final variables
        # Or variables declared in the nested function
        if self._inside_java_lambda:
            variables = list(
                filter(
                    lambda v: (getattr(v, 'is_final', False) or v not in self.
                               context.get_vars(self.namespace[:-1]).values()),
                    variables))
        # If we need to use a variable of a specific types, then filter
        # all variables that match this specific type.
        if subtype:
            fun = lambda v, t: v.get_type().is_assignable(t)
        else:
            fun = lambda v, t: v.get_type() == t
        variables = [v for v in variables if fun(v, etype)]
        if not variables:
            return self.generate_expr(etype,
                                      only_leaves=only_leaves,
                                      subtype=subtype,
                                      exclude_var=True)
        varia = ut.randomUtil.choice([v.name for v in variables])
        self.allow_bottom_consts = old_allow_bottom_const
        return ast.Variable(varia)

    def gen_array_expr(self,
                       expr_type: tp.Type,
                       only_leaves=False,
                       subtype=True,
                       array_list=False) -> ast.ArrayExpr:
        """Generate an array expression

        Args:
            expr_type: The type of the array
            only_leaves: do not generate new leaves except from `expr`.
            subtype: The type of the generated array could be a subtype
                of `expr_type`.
        """
        arr_len = ut.randomUtil.integer(0, 3)
        etype = expr_type.type_args[0]
        # if tu.is_builtin(etype, self.bt_factory) and ut.randomUtil.bool():
        #     arr_len = ut.randomUtil.integer(3, 10)
        exprs = [
            self.generate_expr(etype, only_leaves=only_leaves, subtype=subtype)
            for _ in range(arr_len)
        ]
        if array_list:
            return ast.ArrayListExpr(expr_type.to_variance_free(), arr_len,
                                     exprs)
        # An array expression (i.e., emptyArray<T>(), arrayOf<T>) cannot
        # take wildcards.
        return ast.ArrayExpr(expr_type.to_variance_free(), arr_len, exprs)

    # pylint: disable=unused-argument
    def gen_equality_expr(self,
                          expr_type=None,
                          only_leaves=False) -> ast.EqualityExpr:
        """Generate an equality expression

        It generates two additional expression for performing the comparison
        between them.

        Args:
            expr_type: exists for compatibility reasons.
            only_leaves: do not generate new leaves except from `expr`.
        """
        initial_depth = self.depth
        self.depth += 1
        exclude_function_types = True
        etype = self.select_type(exclude_function_types=exclude_function_types)
        op = ut.randomUtil.choice(
            ast.EqualityExpr.VALID_OPERATORS[self.language])
        e1 = self.generate_expr(etype, only_leaves, subtype=False)
        e2 = self.generate_expr(etype, only_leaves, subtype=False)
        self.depth = initial_depth
        return ast.EqualityExpr(e1, e2, op)

    # pylint: disable=unused-argument
    def gen_logical_expr(self,
                         expr_type=None,
                         only_leaves=False) -> ast.LogicalExpr:
        """Generate a logical expression

        It generates two additional expression for the logical expression.

        Args:
            expr_type: exists for compatibility reasons.
            only_leaves: do not generate new leaves except from `expr`.
        """
        initial_depth = self.depth
        self.depth += 1
        op = ut.randomUtil.choice(
            ast.LogicalExpr.VALID_OPERATORS[self.language])
        e1 = self.generate_expr(self.bt_factory.get_boolean_type(),
                                only_leaves)
        e2 = self.generate_expr(self.bt_factory.get_boolean_type(),
                                only_leaves)
        self.depth = initial_depth
        return ast.LogicalExpr(e1, e2, op)

    # pylint: disable=unused-argument
    def gen_comparison_expr(self,
                            expr_type=None,
                            only_leaves=False) -> ast.ComparisonExpr:
        """Generate a comparison expression

        It generates two additional expression for performing the comparison
        between them.
        It supports only built-in types.

        Args:
            expr_type: exists for compatibility reasons.
            only_leaves: do not generate new leaves except from `expr`.
        """
        valid_types = [
            self.bt_factory.get_string_type(),
            self.bt_factory.get_boolean_type(),
            self.bt_factory.get_double_type(),
            self.bt_factory.get_char_type(),
            self.bt_factory.get_float_type(),
            self.bt_factory.get_integer_type(),
            self.bt_factory.get_byte_type(),
            self.bt_factory.get_short_type(),
            self.bt_factory.get_long_type(),
            self.bt_factory.get_big_decimal_type(),
            self.bt_factory.get_big_integer_type(),
        ]
        number_types = self.bt_factory.get_number_types()
        e2_types = {
            self.bt_factory.get_string_type():
            [self.bt_factory.get_string_type()],
            self.bt_factory.get_boolean_type():
            [self.bt_factory.get_boolean_type()],
            self.bt_factory.get_double_type():
            number_types,
            self.bt_factory.get_big_decimal_type():
            number_types,
            self.bt_factory.get_char_type(): [self.bt_factory.get_char_type()],
            self.bt_factory.get_float_type():
            number_types,
            self.bt_factory.get_integer_type():
            number_types,
            self.bt_factory.get_big_integer_type():
            number_types,
            self.bt_factory.get_byte_type():
            number_types,
            self.bt_factory.get_short_type():
            number_types,
            self.bt_factory.get_long_type():
            number_types
        }
        initial_depth = self.depth
        self.depth += 1
        op = ut.randomUtil.choice(
            ast.ComparisonExpr.VALID_OPERATORS[self.language])
        e1_type = ut.randomUtil.choice(valid_types)
        e2_type = ut.randomUtil.choice(e2_types[e1_type])
        e1 = self.generate_expr(e1_type, only_leaves)
        e2 = self.generate_expr(e2_type, only_leaves)
        self.depth = initial_depth
        return ast.ComparisonExpr(e1, e2, op, e1_type)

    def gen_conditional(self,
                        etype: tp.Type,
                        only_leaves=False,
                        subtype=True) -> ast.Conditional:
        """Generate a conditional expression.

        It generates 3 sub expressions, one for each branch, and one for
        the conditional.

        Args:
            etype: type for each sub expression.
            only_leaves: do not generate new leaves except from `expr`.
            subtype: The type of the sub expressions could be a subtype of
                `etype`.
        """
        initial_depth = self.depth
        self.depth += 3
        cond = self.generate_expr(self.bt_factory.get_boolean_type(),
                                  only_leaves)

        if subtype:
            subtypes = tu.find_subtypes(etype,
                                        self.get_types(),
                                        include_self=True,
                                        concrete_only=True)
            true_type = ut.randomUtil.choice(subtypes)
            false_type = ut.randomUtil.choice(subtypes)
            tmp_t = ut.randomUtil.choice(subtypes)
            # Find which of the given types is the supertype.
            cond_type = functools.reduce(
                lambda acc, x: acc
                if x.is_subtype(acc) else x, [true_type, false_type], tmp_t)
        else:
            true_type, false_type, cond_type = etype, etype, etype
        true_expr = self.generate_expr(true_type, only_leaves, subtype=False)
        false_expr = self.generate_expr(false_type, only_leaves, subtype=False)
        self.depth = initial_depth

        # Note that this an approximation of the type of the whole conditional.
        # To properly estimate the type of conditional, we need to implememnt
        # the LUB algorithm.
        # Note the type passed in conditional may be imprecise in the following
        # scenario:
        # class A
        # class B extends A
        # class C extends B
        # class D extends B
        #
        # gen_conditional with type A
        # true branch type C
        # false branch type D
        #
        # The type will assign to the conditional will be A, but the correct
        # one is B.
        return ast.Conditional(cond, true_expr, false_expr, cond_type)

    def gen_is_expr(self,
                    expr_type: tp.Type,
                    only_leaves=False,
                    subtype=True) -> ast.Conditional:
        """Generate an is expression.

        If it cannot detect a subtype for the expr_type, then it just generates
        a new expression of expr_type.

        Args:
            expr_type: type to smart cast.
            only_leaves: do not generate new leaves except from `expr`.
            subtype: The type of the sub expressions could be a subtype of
                `expr_type`.

        Returns:
            A conditional with is.
        """

        def _get_extra_decls(namespace):
            return [
                v for v in self.context.get_declarations(
                    namespace, only_current=True).values()
                if (isinstance(v, (ast.VariableDeclaration,
                                   ast.FunctionDeclaration)))
            ]

        final_vars = [
            v for v in self.context.get_vars(self.namespace).values() if (
                # We can smart cast local variables that are final, have
                # explicit types, and are not overridable.
                isinstance(v, ast.VariableDeclaration)
                and getattr(v, 'is_final', True) and not v.is_type_inferred
                and not getattr(v, 'can_override', True))
        ]
        if not final_vars:
            return self.generate_expr(expr_type,
                                      only_leaves=True,
                                      subtype=subtype)
        prev_depth = self.depth
        self.depth += 3
        var = ut.randomUtil.choice(final_vars)
        var_type = var.get_type()
        subtypes = tu.find_subtypes(var_type,
                                    self.get_types(),
                                    include_self=False,
                                    concrete_only=True)
        subtypes = self._filter_subtypes(subtypes, var_type)
        if not subtypes:
            return self.generate_expr(expr_type,
                                      only_leaves=True,
                                      subtype=subtype)

        subtype = ut.randomUtil.choice(subtypes)
        initial_decls = _get_extra_decls(self.namespace)
        prev_namespace = self.namespace
        self.namespace += ('true_block', )
        # Here, we create a 'virtual' variable declaration inside the
        # namespace of the block corresponding to the true branch. This
        # variable has the same name with the variable that appears in
        # the left-hand side of the 'is' expression, but its type is the
        # selected subtype.
        self.context.add_var(
            self.namespace, var.name,
            ast.VariableDeclaration(var.name,
                                    ast.BottomConstant(var.get_type()),
                                    var_type=subtype))
        true_expr = self.generate_expr(expr_type)
        # We pop the variable from context. Because it's no longer used.
        self.context.remove_var(self.namespace, var.name)
        extra_decls_true = [
            v for v in _get_extra_decls(self.namespace)
            if v not in initial_decls
        ]
        if extra_decls_true:
            true_expr = ast.Block(extra_decls_true + [true_expr],
                                  is_func_block=False)
        self.namespace = prev_namespace + ('false_block', )
        false_expr = self.generate_expr(expr_type,
                                        only_leaves=only_leaves,
                                        subtype=subtype)
        extra_decls_false = [
            v for v in _get_extra_decls(self.namespace)
            if v not in initial_decls
        ]
        if extra_decls_false:
            false_expr = ast.Block(extra_decls_false + [false_expr],
                                   is_func_block=False)
        self.namespace = prev_namespace
        self.depth = prev_depth
        return ast.Conditional(ast.Is(ast.Variable(var.name), subtype),
                               true_expr, false_expr, expr_type)

    # Where

    def _filter_subtypes(self, subtypes, initial_type):
        """Filter out types that cannot be smart casted.

        The types that cannot be smart casted are Type Variables and
        Parameterized Types. The only exception is Kotlin in which we can
        smart cast parameterized types.
        """
        new_subtypes = []
        for t in subtypes:
            if t.is_type_var():
                continue
            # if self.language != 'kotlin':
            #     # We can't check the instance of a parameterized type due
            #     # to type erasure. The only exception is Kotlin, see below.
            #     if not t.is_parameterized():
            #         new_subtypes.append(t)
            #     continue

            # In Kotlin, you can smart cast a parameterized type like the
            # following.

            # class A<T>
            # class B<T> extends A<T>
            # fun test(x: A<String>) {
            #   if (x is B) {
            #      // the type of x is B<String> here.
            #   }
            # }
            if t.is_parameterized():
                t_con = t.t_constructor
                if t_con.is_subtype(initial_type):
                    continue
            new_subtypes.append(t)
        return new_subtypes

    def gen_lambda(self,
                   etype: tp.Type = None,
                   not_void=False,
                   params: List[ast.ParameterDeclaration] = None,
                   only_leaves=False) -> ast.Lambda:
        """Generate a lambda expression.

        Lambdas have shadow names that we can use them in the context to
        retrieve them.

        Args:
            etype: return type of the lambda.
            not_void: the lambda should not return void.
            params: parameters for the lambda.
        """
        if self.declaration_namespace:
            namespace = self.declaration_namespace
        else:
            namespace = self.namespace

        initial_namespace = self.namespace
        shadow_name = "lambda_" + str(next(self.int_stream))
        self.namespace += (shadow_name, )
        initial_depth = self.depth
        self.depth += 1

        prev_inside_java_lamdba = self._inside_java_lambda
        self._inside_java_lambda = True

        params = params if params is not None else self._gen_func_params()
        param_types = [p.param_type for p in params]
        for p in params:
            self.context.add_var(self.namespace, p.name, p)
        ret_type = self._get_func_ret_type(params, etype, not_void=not_void)
        signature = tp.ParameterizedType(
            self.bt_factory.get_function_type(len(params)),
            param_types + [ret_type])
        res = ast.Lambda(shadow_name, params, ret_type, None, signature)
        self.context.add_lambda(initial_namespace, shadow_name, res)
        body = self._gen_func_body(ret_type)
        res.body = body

        self.depth = initial_depth
        self.namespace = initial_namespace
        self._inside_java_lambda = prev_inside_java_lamdba

        return res

    def gen_func_call(self,
                      etype: tp.Type,
                      only_leaves=False,
                      subtype=True) -> ast.FunctionCall:
        """Generate a function call.

        The function call could be either a normal function call, or a function
        call from a function reference.
        Note that this function may generate a new function/class as a side
        effect.

        Args:
            etype: the type that the function call should return.
            only_leaves: do not generate new leaves except from `expr`.
            subtype: The returned type could be a subtype of `etype`.

        Returns:
            A function call.
        """
        if ut.randomUtil.bool(cfg.prob.func_ref_call):
            ref_call = self._gen_func_call_ref(etype, only_leaves, subtype)
            if ref_call:
                return ref_call
            # NOTE we could use _gen_func_call to generate function references
            # for producing function calls, but then we should always cast them.
        return self._gen_func_call(etype, only_leaves, subtype)

    # gen_func_call Where

    def _gen_func_call(self,
                       etype: tp.Type,
                       only_leaves=False,
                       subtype=True) -> ast.FunctionCall:
        """Generate a function call.

        Args:
            etype: the type that the function call should return.
            only_leaves: do not generate new leaves except from `expr`.
            subtype: The returned type could be a subtype of `etype`.
        """
        log(self.logger, "Generating function call of type {}".format(etype))
        funcs = self._get_matching_function_declarations(etype, subtype)
        if not funcs:
            msg = "No compatible functions in the current scope for type {}"
            log(self.logger, msg.format(etype))
            type_fun = self._get_matching_class(etype,
                                                subtype=subtype,
                                                attr_name='functions')
            if type_fun is None:
                msg = "No compatible classes for type {}"
                log(self.logger, msg.format(etype))
                # Here, we generate a function or a class containing a function
                # whose return type is 'etype'.
                type_fun = self._gen_matching_func(etype, not_void=True)
            receiver = (None if type_fun.receiver_t is None else
                        self.generate_expr(type_fun.receiver_t, only_leaves))
            funcs.append(
                gu.AttrReceiverInfo(receiver, type_fun.receiver_inst,
                                    type_fun.attr_decl, type_fun.attr_inst))

        rand_func = ut.randomUtil.choice(funcs)
        receiver = rand_func.receiver_expr
        params_map = rand_func.receiver_inst
        func = rand_func.attr_decl
        func_type_map = rand_func.attr_inst

        params_map.update(func_type_map or {})

        msg = ("Selected callee method {}: type {}; receiver {}; "
               "TypeVarMap {}".format(func.name, etype, receiver, params_map))
        log(self.logger, msg)
        args = []
        initial_depth = self.depth
        self.depth += 1
        for param in func.params:
            expr_type = tp.substitute_type(param.get_type(), params_map)
            gen_bottom = expr_type.is_wildcard() or (
                expr_type.is_parameterized() and expr_type.has_wildcards())
            if not param.vararg:
                arg = self.generate_expr(expr_type,
                                         only_leaves,
                                         gen_bottom=gen_bottom)
                if not param.default:
                    args.append(ast.CallArgument(arg))
                else:
                    if self.language == 'java':  # java hasn't default params
                        args.append(ast.CallArgument(arg))
                    # if self.language == 'kotlin' and ut.randomUtil.bool():
                    # Randomly skip some default arguments.
                    #    args.append(ast.CallArgument(arg, name=param.name))
            else:
                # This param is a vararg, so provide a random number of
                # arguments.
                for _ in range(ut.randomUtil.integer(0, 3)):
                    args.append(
                        ast.CallArgument(
                            self.generate_expr(expr_type.type_args[0],
                                               only_leaves,
                                               gen_bottom=gen_bottom)))
        self.depth = initial_depth
        type_args = ([] if not func.is_parameterized() else [
            func_type_map[t_param] for t_param in func.type_parameters
        ])
        return ast.FunctionCall(func.name, args, receiver, type_args=type_args)

    # Where

    def _gen_func_call_ref(self,
                           etype: tp.Type,
                           only_leaves=False,
                           subtype=False) -> ast.FunctionCall:
        """Generate a function call from a reference.

        This function searches for variables and receivers in current scope.

        Args:
            etype: the type that the function call should return.
            only_leaves: do not generate new leaves except from `expr`.
            subtype: The returned type could be a subtype of `etype`.
        """
        # Tuple of signature, name, receiver
        refs = []
        # Search for function references in current scope
        variables = self.context.get_vars(self.namespace).values()
        if self._inside_java_lambda:
            variables = list(
                filter(
                    lambda v: (getattr(v, 'is_final', False) or
                               (v not in self.context.get_vars(
                                   self.namespace[:-1]).values())), variables))
        for var in variables:
            var_type = var.get_type()
            if not getattr(var_type, 'is_function_type', lambda: False)():
                continue
            ret_type = var_type.type_args[-1]
            if (subtype
                    and ret_type.is_assignable(etype)) or ret_type == etype:
                refs.append((var_type, var.name, None))

        if not refs:
            # Detect receivers
            objs = self._get_matching_objects(etype,
                                              subtype,
                                              'fields',
                                              signature=False,
                                              func_ref=True)
            refs = [(tp.substitute_type(obj.attr_decl.get_type(),
                                        obj.receiver_inst), obj.attr_decl.name,
                     obj.receiver_expr) for obj in objs]

        if not refs:
            return None

        signature, name, receiver = ut.randomUtil.choice(refs)

        # Generate arguments
        args = []
        initial_depth = self.depth
        self.depth += 1
        for param_type in signature.type_args[:-1]:
            gen_bottom = param_type.is_wildcard() or (
                param_type.is_parameterized() and param_type.has_wildcards())
            arg = self.generate_expr(param_type,
                                     only_leaves,
                                     gen_bottom=gen_bottom,
                                     sam_coercion=False)
            args.append(ast.CallArgument(arg))
        self.depth = initial_depth
        return ast.FunctionCall(name,
                                args,
                                receiver=receiver,
                                is_ref_call=True)

    # pylint: disable=unused-argument
    def gen_new(self,
                etype: tp.Type,
                only_leaves=False,
                subtype=True,
                sam_coercion=False):
        """Create a new object of a given type.

        This could be:
            * Function type
            * SAM type
            * Parameterized Type
            * Simple Classifier Type

        Args:
            etype: the type for which we want to create an object
            only_leaves: do not generate new leaves except from `expr`.
            subtype: The type could be a subtype of `etype`.
            sam_coercion: Apply sam coercion if possible.
        """

        if getattr(etype, 'is_function_type', lambda: False)():
            return self._gen_func_ref_lambda(etype, only_leaves=only_leaves)

        # Apply SAM coercion
        if (sam_coercion and tu.is_sam(self.context, etype)
                and ut.randomUtil.bool(cfg.prob.sam_coercion)):
            type_var_map = tu.get_type_var_map_from_ptype(etype)
            sam_sig_etype = tu.find_sam_fun_signature(
                self.context,
                etype,
                self.bt_factory.get_function_type,
                type_var_map=type_var_map)
            if sam_sig_etype:
                return self._gen_func_ref_lambda(sam_sig_etype,
                                                 only_leaves=only_leaves)

        class_decl = self._get_subclass(etype, subtype)
        if isinstance(etype, tp.ParameterizedType):
            etype = etype.to_variance_free()
        news = {
            self.bt_factory.get_any_type():
            ast.New(self.bt_factory.get_any_type(), args=[]),
            self.bt_factory.get_void_type():
            ast.New(self.bt_factory.get_void_type(), args=[])
        }
        con = news.get(etype)
        if con is not None:
            return con

        # No class was found corresponding to the given type. Probably,
        # the given type is a type parameter. So, if this type parameter has
        # a bound, generate a value of this bound. Otherwise, generate a bottom
        # value.
        if class_decl is None or etype.name in self._blacklisted_classes:
            t = etype
            # If the etype corresponds to a type variable not belonging to
            # to the current namespace, then create a bottom constant
            # whose type is unknown. This means that the corresponding
            # translator won't perform cast on this constant.
            if etype.is_type_var() and (
                    etype.name not in self._get_type_variable_names()):
                t = None
            if class_decl and class_decl.is_final:
                class_decl.is_final = False

            if isinstance(etype, tp.ParameterizedType):
                decl_type = self.context.get_classes(('global', ))[etype.name]
                cls_type = etype
                type_var_map = {}
                for (i,
                     type_) in enumerate(etype.t_constructor.type_parameters):
                    type_var_map[type_] = etype.type_args[i]
                new_class = self.gen_class_for_bottom_constant(
                    decl_type, cls_type, type_var_map)
                initial_depth = self.depth
                self.depth += 1
                args = []
                prev = self._new_from_class
                self._new_from_class = None
                for field in new_class.fields:
                    expr_type = tp.substitute_type(field.get_type(), {})
                    args.append(
                        self.generate_expr(expr_type,
                                           only_leaves,
                                           subtype=False,
                                           sam_coercion=True))
                self._new_from_class = prev
                self.depth = initial_depth
                return ast.New(new_class.get_type(), args)
            if isinstance(etype, tp.WildCardType) and tu.is_builtin(
                    etype.bound, self.bt_factory):
                return self.gen_builtin_const(etype.bound)
            if isinstance(etype, tp.SimpleClassifier):
                decl_type = self.context.get_classes(('global', ))[etype.name]
                cls_type = etype
                type_var_map = {}
                new_class = self.gen_class_for_bottom_constant(
                    decl_type, cls_type, type_var_map)
                initial_depth = self.depth
                self.depth += 1
                args = []
                prev = self._new_from_class
                self._new_from_class = None
                for field in new_class.fields:
                    expr_type = tp.substitute_type(field.get_type(), {})
                    args.append(
                        self.generate_expr(expr_type,
                                           only_leaves,
                                           subtype=False,
                                           sam_coercion=True))
                self._new_from_class = prev
                self.depth = initial_depth
                return ast.New(new_class.get_type(), args)
            return ast.BottomConstant(t)

        if etype.is_type_constructor():
            etype, _ = tu.instantiate_type_constructor(
                etype,
                self.get_types(),
                disable_variance_functions=self.disable_variance_functions,
                enable_pecs=self.enable_pecs)
        if class_decl.is_parameterized() and (class_decl.get_type().name
                                              != etype.name):
            etype, _ = tu.instantiate_type_constructor(
                class_decl.get_type(),
                self.get_types(),
                disable_variance_functions=self.disable_variance_functions,
                enable_pecs=self.enable_pecs)
        # If the matching class is a parameterized one, we need to create
        # a map mapping the class's type parameters with the corresponding
        # type arguments as given by the `etype` variable.
        type_param_map = ({} if not class_decl.is_parameterized() else {
            t_p: etype.type_args[i]
            for i, t_p in enumerate(class_decl.type_parameters)
        })
        initial_depth = self.depth
        self.depth += 1
        args = []
        prev = self._new_from_class
        self._new_from_class = None
        for field in class_decl.fields:
            expr_type = tp.substitute_type(field.get_type(), type_param_map)
            # Generate a bottom value, if we are in this case:
            # class A(val x: A)
            # Generating a bottom constants prevents us from infinite loops.
            gen_bottom = expr_type.name == etype.name or (
                self.depth > (cfg.limits.max_depth * 2)
                and not expr_type.is_primitive())
            args.append(
                self.generate_expr(expr_type,
                                   only_leaves,
                                   subtype=False,
                                   gen_bottom=gen_bottom,
                                   sam_coercion=True))
        self._new_from_class = prev
        self.depth = initial_depth
        new_type = class_decl.get_type()
        if class_decl.is_parameterized():
            new_type = new_type.new(etype.type_args)
        return ast.New(new_type, args)

    def gen_builtin_const(self, t: tp.Type) -> ast.Constant:
        const_gen = self.get_generators(t,
                                        only_leaves=True,
                                        subtype=False,
                                        exclude_var=False,
                                        sam_coercion=False)
        if t == self.bt_factory.get_any_type() and len(const_gen) == 1:
            return const_gen[0](t)
        if len(const_gen) == 1:
            return const_gen[0](t)

    # Where

    def _get_subclass(self,
                      etype: tp.Type,
                      subtype=True) -> ast.ClassDeclaration:
        """"Find a subclass that is a subtype of the given type and is a
        regular class.

        Args:
            etype: the type for which we are searching for subclasses.
            subtype: The type could be a subtype of `etype`.
        """
        class_decls = self.context.get_classes(self.namespace).values()
        # Get all classes that are subtype of the given type, and there
        # are regular classes (no interfaces or abstract classes).
        subclasses = []
        for c in class_decls:
            if c.class_type != ast.ClassDeclaration.REGULAR:
                continue
            if c.is_parameterized():
                t_con = getattr(etype, 't_constructor', None)
                if c.get_type() == t_con or (subtype and
                                             c.get_type().is_subtype(etype)):
                    subclasses.append(c)
            else:
                if c.get_type() == etype or (subtype and
                                             c.get_type().is_subtype(etype)):
                    subclasses.append(c)
        if not subclasses:
            return None
        # FIXME what happens if subclasses is empty?
        # it may happens due to ParameterizedType with TypeParameters as targs
        return ut.randomUtil.choice(
            [s for s in subclasses if s.name == etype.name] or subclasses)

    # And

    def _gen_func_ref_lambda(self, etype: tp.Type, only_leaves=False):
        """Generate a function reference or a lambda for a given signature.

        Args:
            etype: signature

        Returns:
            ast.Lambda or ast.FunctionReference
        """
        # We are unable to produce function references in super calls.
        if ut.randomUtil.bool(cfg.prob.func_ref) and not self._in_super_call:
            func_ref = self._gen_func_ref(etype, only_leaves=only_leaves)
            if func_ref:
                return func_ref

        # Generate Lambda
        ret_type, params = self._gen_ret_and_paramas_from_sig(etype, True)
        return self.gen_lambda(etype=ret_type,
                               params=params,
                               only_leaves=only_leaves)

    # Where

    def _gen_func_ref(self,
                      etype: tp.Type,
                      only_leaves=False) -> List[ast.FunctionReference]:
        """Generate a function reference.

        1. Functions in current scope and global scope, or methods that have
            a receiver in current scope.
        2. Create receiver for a function reference.
        3. Create a new function.

        Args:
            etype: signature for function reference
        """
        # Get function references from functions in the current scope or
        # methods that have a receiver in the current scope.
        refs = []
        funcs = self._get_matching_function_declarations(etype,
                                                         False,
                                                         signature=True)
        for func in funcs:
            if func.attr_decl.name == self.namespace[-1]:
                continue
            refs.append(
                ast.FunctionReference(func.attr_decl.name, func.receiver_expr,
                                      etype))

        if refs:
            return ut.randomUtil.choice(refs)

        ref = None
        # NOTE a maximum recursion error may occur.
        # Get function references from methods of classes.
        # ie create receiver
        type_fun = self._get_matching_class(etype,
                                            subtype=False,
                                            attr_name='functions',
                                            signature=True)

        # Generate a matching function.
        if not type_fun:
            type_fun = self._gen_matching_func(etype,
                                               not_void=True,
                                               signature=True)

        if type_fun:
            receiver = (None if type_fun.receiver_t is None else
                        self.generate_expr(type_fun.receiver_t,
                                           only_leaves=only_leaves))
            ref = ast.FunctionReference(type_fun.attr_decl.name, receiver,
                                        etype)

        return ref

    ### Standard API of Generator ###

    def get_generators(self,
                       expr_type: tp.Type,
                       only_leaves: bool,
                       subtype: bool,
                       exclude_var: bool,
                       sam_coercion=False) -> List[Callable]:
        """Get candidate generators for the given type.

        Args:
            expr_type: targeted type.
            only_leaves: do not generate new leaves except from `expr`.
            subtype: The type of the generated expression could be a subtype
                of `expr_type`.
            exclude_var: if this option is false, then it could assign the
                generated expression into a variable, and return that
                variable reference.
            sam_coercion: Enable sam coercion.

        Returns:
            A list of generator functions
        """

        def gen_variable(etype):
            return self.gen_variable(etype, only_leaves, subtype)

        def gen_fun_call(etype):
            return self.gen_func_call(etype,
                                      only_leaves=only_leaves,
                                      subtype=subtype)

        # Do not generate new nodes in context.
        leaf_canidates = [
            lambda x: self.gen_new(
                x, only_leaves, subtype, sam_coercion=sam_coercion),
        ]
        constant_candidates = {
            self.bt_factory.get_number_type().name:
            (lambda x: gens.gen_integer_constant(self.bt_factory.
                                                 get_number_type())),
            self.bt_factory.get_integer_type().name:
            (lambda x: gens.gen_integer_constant(self.bt_factory.
                                                 get_integer_type())),
            self.bt_factory.get_big_integer_type().name:
            (lambda x: gens.gen_integer_constant(self.bt_factory.
                                                 get_big_integer_type())),
            self.bt_factory.get_byte_type().name:
            (lambda x: gens.gen_integer_constant(self.bt_factory.get_byte_type(
            ))),
            self.bt_factory.get_short_type().name:
            (lambda x: gens.gen_integer_constant(self.bt_factory.
                                                 get_short_type())),
            self.bt_factory.get_long_type().name:
            (lambda x: gens.gen_integer_constant(self.bt_factory.get_long_type(
            ))),
            self.bt_factory.get_float_type().name:
            (lambda x: gens.gen_real_constant(self.bt_factory.get_float_type())
             ),
            self.bt_factory.get_double_type().name:
            gens.gen_real_constant,
            self.bt_factory.get_big_decimal_type().name:
            gens.gen_real_constant,
            self.bt_factory.get_char_type().name:
            gens.gen_char_constant,
            self.bt_factory.get_string_type().name:
            gens.gen_string_constant,
            self.bt_factory.get_boolean_type().name:
            gens.gen_bool_constant,
            self.bt_factory.get_array_type().name:
            (lambda x: self.gen_array_expr(x, only_leaves, subtype=subtype)),
        }
        binary_ops = {
            self.bt_factory.get_boolean_type(): [
                lambda x: self.gen_logical_expr(x, only_leaves),
                lambda x: self.gen_equality_expr(only_leaves),
                lambda x: self.gen_comparison_expr(only_leaves)
            ],
        }
        other_candidates = [
            lambda x: self.gen_field_access(x, only_leaves, subtype), lambda x:
            self.gen_conditional(x, only_leaves=only_leaves, subtype=subtype),
            lambda x: self.gen_is_expr(
                x, only_leaves=only_leaves, subtype=subtype), gen_fun_call,
            gen_variable
        ]

        if expr_type == self.bt_factory.get_void_type():
            # The assignment operator in Java evaluates to the assigned value.
            # if self.language == 'java':
            #    return [gen_fun_call]
            return [
                gen_fun_call, lambda x: self.gen_assignment(x, only_leaves)
            ]

        if self.depth >= cfg.limits.max_depth or only_leaves:
            gen_con = constant_candidates.get(expr_type.name)
            if gen_con is not None:
                return [gen_con]
            gen_var = (self._vars_in_context.get(self.namespace,
                                                 0) < cfg.limits.max_var_decls
                       and not only_leaves and not exclude_var)
            if gen_var:
                # Decide if we can generate a variable.
                # If the maximum numbers of variables in a specific context
                # has been reached, or we have previously declared a variable
                # of a specific type, then we should avoid variable creation.
                leaf_canidates.append(gen_variable)
            return leaf_canidates
        con_candidate = constant_candidates.get(expr_type.name)
        binary_ops_canidates = self.get_bt_operation_generators(expr_type)
        if con_candidate is not None:
            candidates = [con_candidate] + binary_ops.get(expr_type, [])
            if not exclude_var:
                candidates.append(gen_variable)
        else:
            candidates = leaf_canidates
        return other_candidates + candidates + binary_ops_canidates

    def get_types(self,
                  ret_types=True,
                  exclude_arrays=False,
                  exclude_covariants=False,
                  exclude_contravariants=False,
                  exclude_type_vars=False,
                  exclude_function_types=False) -> List[tp.Type]:
        """Get all available types.

        Including user-defined types, built-ins, and function types.
        Note that this may include Type Constructors.

        Args:
            ret_types: use non-nothing built-in types (use this option if you
                want to generate a return type).
            exclude_arrays: exclude array types.
            exclude_covariants: exclude covariant type parameters.
            exclude_contravariants: exclude contravariant type parameters.
            exclude_type_vars: exclude type variables.
            exclude_function_types: exclude function types.

        Returns:
            A list of available types.
        """
        usr_types = [
            c.get_type()
            for c in self.context.get_classes(self.namespace).values()
        ]
        if self.depth >= cfg.limits.max_depth:
            usr_types = []
        type_params = []
        if not exclude_type_vars:
            for t_param in self.context.get_types(self.namespace).values():
                variance = getattr(t_param, 'variance', None)
                if exclude_covariants and variance == tp.Covariant:
                    continue
                if exclude_contravariants and variance == tp.Contravariant:
                    continue
                type_params.append(t_param)

        if type_params and ut.randomUtil.bool():
            return type_params

        builtins = list(
            self.ret_builtin_types if ret_types else self.builtin_types)
        if exclude_arrays:
            builtins = [
                t for t in builtins
                if t.name != self.bt_factory.get_array_type().name
            ]
        if exclude_function_types:
            return usr_types + builtins
        return usr_types + builtins + self.function_types

    def select_type(self,
                    ret_types=True,
                    exclude_arrays=False,
                    exclude_covariants=False,
                    exclude_contravariants=False,
                    exclude_function_types=False) -> tp.Type:
        """Select a type from the all available types.

        It will always instantiating type constructors to parameterized types.

        Args:
            ret_types: use non-nothing built-in types (use this option if you
                want to generate a return type).
            exclude_arrays: exclude array types.
            exclude_covariants: exclude covariant type parameters.
            exclude_contravariants: exclude contravariant type parameters.
            exclude_function_types: exclude function types.

        Returns:
            Returns a type.
        """
        types = self.get_types(ret_types=ret_types,
                               exclude_arrays=exclude_arrays,
                               exclude_covariants=exclude_covariants,
                               exclude_contravariants=exclude_contravariants,
                               exclude_function_types=exclude_function_types)
        stype = ut.randomUtil.choice(types)
        if stype.is_type_constructor():
            exclude_type_vars = stype.name == self.bt_factory.get_array_type(
            ).name
            stype, _ = tu.instantiate_type_constructor(
                stype,
                self.get_types(exclude_arrays=True,
                               exclude_covariants=True,
                               exclude_contravariants=True,
                               exclude_type_vars=exclude_type_vars,
                               exclude_function_types=exclude_function_types),
                enable_pecs=self.enable_pecs,
                disable_variance_functions=self.disable_variance_functions,
                variance_choices={})
            msg = "Instantiating type constructor {}".format(stype)
            log(self.logger, msg)
        return stype

    def gen_type_params(self,
                        count: int = None,
                        with_variance=False,
                        blacklist: List[str] = None,
                        for_function=False) -> List[tp.TypeParameter]:
        """Generate a list containing type parameters

        Args:
            count: number of type parameters, if none it randomly select the
                number of type parameters.
            with_variance: enable variance
            blacklist: a list of type parameter names
            for_function: create type parameters for parameterized functions
        """
        if not count and ut.randomUtil.bool():
            return []
        if cfg.limits.max_type_params == 0:
            return []
        type_params = []
        type_param_names = blacklist or []
        variances = [tp.Invariant, tp.Covariant, tp.Contravariant]
        limit = (
            # In case etype is Function3<T1, T2, T3, F_N>
            4 if count == 4 and cfg.limits.max_type_params < 4 else
            cfg.limits.max_type_params)
        for _ in range(ut.randomUtil.integer(count or 1, limit)):
            name = ut.randomUtil.caps(blacklist=type_param_names)
            type_param_names.append(name)
            if for_function:
                # OK we do this trick for type parameters corresponding to
                # functions in order to avoid conflicts with type variables
                # of classes. TODO: consider being less conservative.
                name = "F_" + name
            variance = None
            if with_variance and ut.randomUtil.bool():
                variance = ut.randomUtil.choice(variances)
            bound = None
            if ut.randomUtil.bool(cfg.prob.bounded_type_parameters):
                exclude_covariants = variance == tp.Contravariant or for_function
                exclude_contravariants = True
                bound = self.select_type(
                    exclude_arrays=True,
                    exclude_covariants=exclude_covariants,
                    exclude_contravariants=exclude_contravariants)
                if bound.is_primitive():
                    bound = bound.box_type()
            type_param = tp.TypeParameter(name, variance=variance, bound=bound)
            # Add type parameter to context.
            self.context.add_type(self.namespace, type_param.name, type_param)
            type_params.append(type_param)
        return type_params

    ### Internal helper functions ###

    def _get_type_variable_names(self) -> List[str]:
        """Get the name of type variables that are in place in the current
        namespace.
        """
        return list(self.context.get_types(self.namespace).keys())

    def _get_func_ret_type(self,
                           params: List[ast.ParameterDeclaration],
                           etype: tp.Type,
                           not_void=False) -> tp.Type:
        """Get return type for a function or lambda.

        Args:
            params: function parameters.
            etype: use this type as the return type
            not_void: do not return void
        """
        if etype is not None:
            return etype
        param_types = [
            p.param_type for p in params
            if getattr(p.param_type, 'variance', None) != tp.Contravariant
        ]
        if param_types and ut.randomUtil.bool():
            return ut.randomUtil.choice(param_types)
        return self.select_type(exclude_contravariants=True)

    def _get_class(
            self,
            etype: tp.Type) -> Tuple[ast.ClassDeclaration, tu.TypeVarMap]:
        """Find the class declaration for a given type.
        """
        # Get class declaration based on the given type.
        if tu.is_builtin(etype, self.bt_factory):
            return etype.get_class_declaration(), {}
        class_decls = self.context.get_classes(self.namespace).values()
        for c in class_decls:
            cls_type = c.get_type()
            t_con = getattr(etype, 't_constructor', None)
            # or t == t_con: If etype is a parameterized type (i.e.,
            # getattr(etype, 't_constructor', None) != None), we need to
            # get the class corresponding to its type constructor.
            if cls_type.name == etype.name or cls_type == t_con:
                if c.is_parameterized():
                    type_var_map = {
                        t_param: etype.type_args[i]
                        for i, t_param in enumerate(c.type_parameters)
                    }
                else:
                    type_var_map = {}
                return c, type_var_map
        return None

    def _get_var_type_to_search(self, var_type: tp.Type) -> tp.TypeParameter:
        """Get the type that we want to search for.

        We exclude:
            * built-ins
            * type variables/wildcards without bounds
            * type variables/wildcards with bounds to a type variable

        Args:
            var_type: The type of the variable.

        Returns:
            var_type or None
        """
        # We are only interested in variables of class types.
        if tu.is_builtin(var_type, self.bt_factory):
            try:
                var_type.get_class_declaration()
                return var_type
            except Exception:
                return None
        if var_type.is_type_var() or var_type.is_wildcard():
            args = [] if var_type.is_wildcard() else [self.bt_factory]
            bound = var_type.get_bound_rec(*args)
            if not bound or tu.is_builtin(bound,
                                          self.bt_factory) or (isinstance(
                                              bound, tp.TypeParameter)):
                return None
            var_type = bound
        return var_type

    def _get_vars_of_function_types(self, etype: tp.Type):
        """Get a variable or a field access whose type is a function type.

        Args:
            etype: function signature

        Returns:
            ast.Variable or ast.FieldAccess
        """
        refs = []

        # Get variables without receivers
        variables = list(self.context.get_vars(self.namespace).values())
        if self._inside_java_lambda:
            variables = list(
                filter(
                    lambda v: (getattr(v, 'is_final', False) or
                               (v not in self.context.get_vars(
                                   self.namespace[:-1]).values())), variables))
        variables += list(
            self.context.get_vars(('global', ), only_current=True).values())
        for var_decl in variables:
            var_type = var_decl.get_type()
            var = ast.Variable(var_decl.name)
            if var_type == etype:
                refs.append(var)

        # field accesses
        objs = self._get_matching_objects(etype,
                                          False,
                                          'fields',
                                          func_ref=True,
                                          signature=True)
        for obj in objs:
            refs.append(ast.FieldAccess(obj.receiver_expr, obj.attr_decl.name))

        return refs

    # helper generators

    def _gen_func_params(self) -> List[ast.ParameterDeclaration]:
        """Generate parameters for a function or for a lambda.
        """
        params = []
        arr_index = None
        vararg_found = False
        vararg = None
        for i in range(ut.randomUtil.integer(0, cfg.limits.fn.max_params)):
            param = self.gen_param_decl()
            # If the type of the parameter is an array consider make it
            # a vararg.
            if not vararg_found and self._can_vararg_param(param) and (
                    ut.randomUtil.bool()):
                param.vararg = True
                arr_index = i
                vararg = param
                vararg_found = True
            params.append(param)
        len_p = len(params)
        # If one of the parameters is a vararg, then place it to the back.
        if arr_index is not None and arr_index != len_p - 1:
            params[len_p - 1], params[arr_index] = vararg, params[len_p - 1]
        return params

    # Where

    def _can_vararg_param(self, param: ast.ParameterDeclaration) -> bool:
        """Check if a parameter can be vararg.
        """
        return False  # FIXME: vararg support is disabled for some reason (code equivalence)
        # if self.language == 'kotlin':
        #     # TODO theosotr Can we do this in a better way? without hardcode?
        #     # Actually in Kotlin, the type of varargs is Array<out T>.
        #     # So, until we add support for use-site variance, we support
        #     # varargs for 'primitive' types only which kotlinc treats them
        #     # as specialized arrays.
        #     t_constructor = getattr(param.get_type(), 't_constructor', None)
        #     return isinstance(t_constructor, kt.SpecializedArrayType)
        # # A vararg is actually a syntactic sugar for a parameter whose type
        # # is an array of something.
        # return param.get_type().name == 'Array'

    def _gen_func_body(self, ret_type: tp.Type):
        """Generate the body of a function or a lambda.

        Args:
            ret_type: Return type of the function

        Returns:
            ast.Block or ast.Expr
        """
        expr_type = (self.select_type(ret_types=False) if ret_type
                     == self.bt_factory.get_void_type() else ret_type)
        old_inside_func_body = self._inside_func_body
        self._inside_func_body = True
        expr = self.generate_expr(expr_type)
        if isinstance(
                expr,
            (ast.FieldAccess, ast.Conditional, ast.Variable,
             ast.FunctionReference, ast.ArrayExpr, ast.Lambda,
             ast.BinaryOp)) and ret_type == self.bt_factory.get_void_type():
            var_decl = ast.VariableDeclaration(
                f'variableDeclaration_{self.fa}',
                expr=expr,
                is_final=False,
                var_type=expr_type)
            self.fa += 1
            # self._add_node_to_parent(self.namespace, var_decl)
            expr = var_decl
        decls = list(
            self.context.get_declarations(self.namespace, True).values())
        var_decls = [
            d for d in decls if not isinstance(d, ast.ParameterDeclaration)
        ]
        if not var_decls and ret_type != self.bt_factory.get_void_type():
            # The function does not contain any declarations and its return
            # type is not Unit. So, we can create an expression-based function.
            body = expr if ut.randomUtil.bool(cfg.prob.function_expr) else \
                ast.Block([expr])
        else:
            exprs, decls = self._gen_side_effects()
            if ut.randomUtil.bool(
            ):  # probabilistic choice whether to generate a cycle in the body of this function
                loop_expr = self.generate_loop_expr(decls)

                # Get all variable declarations in current context, excluding parameter declarations
                decls_in_context = {
                    k: v
                    for k, v in self.context.get_vars(
                        self.namespace, only_current=True).items()
                    if not isinstance(v, ast.ParameterDeclaration)
                }
                # Get all variable declarations in func body, including those declared in loop_expr and decls
                decls_in_body = [
                    expr for expr in exprs
                    if isinstance(expr, ast.VariableDeclaration)
                ] + decls + [
                    _var for _var in loop_expr
                    if isinstance(_var, ast.VariableDeclaration)
                ]

                # Get all variable declarations in loop
                decls_in_loop = [
                    _var for _var in [
                        _var for _var in loop_expr
                        if isinstance(_var, ast.LoopExpr)
                    ][0].body.body if isinstance(_var, ast.VariableDeclaration)
                ]

                #  Get all variable declarations in loop context (i.e., variables defined in a parent loop)
                decls_in_loop_context = {
                    decl.name: decl
                    for decl, namespace in self.context._namespaces.items()
                    if isinstance(decl, ast.VariableDeclaration)
                    and namespace[:-1] == self.namespace
                    and namespace[-1].__contains__('loop')
                }

                # Get all variable declarations in loop context that are not already in decls_in_body or decls_in_loop
                decls_in_loop_to_add = {
                    k: decl
                    for k, decl in decls_in_loop_context.items()
                    if decl not in decls_in_loop and decl not in decls_in_body
                }
                decls_in_context.update(decls_in_loop_to_add)
                # Get all variable declarations in decls_in_context that are not already in decls_in_body
                decls_to_add = {
                    k: v
                    for k, v in decls_in_context.items()
                    if v not in decls_in_body
                }
                # Add new variables to decls
                for var in decls_to_add.values():
                    decls.append(var)
                # Create a new Block with updated declarations and expressions
                body = ast.Block(decls + exprs + loop_expr + [expr])
            else:
                body = ast.Block(decls + exprs + [expr])
        self._inside_func_body = old_inside_func_body
        return body

    # Where

    def _gen_side_effects(
            self) -> Tuple[List[ast.Expr], List[ast.Declaration]]:
        """Generate expressions with side-effects for function bodies.

        Example side-effects: assignment, variable declaration, etc.
        """
        exprs = []
        # old_allow_bottom_consts = self.allow_bottom_consts
        # self.allow_bottom_consts = True
        for _ in range(ut.randomUtil.integer(0,
                                             cfg.limits.fn.max_side_effects)):
            expr_type = self.select_type(ret_types=True)
            expr = self.generate_expr(expr_type)
            if isinstance(expr,
                          (ast.FieldAccess, ast.Conditional, ast.Variable,
                           ast.FunctionReference, ast.ArrayExpr, ast.Lambda,
                           ast.BinaryOp, ast.Constant)):
                var_decl = ast.VariableDeclaration(
                    name=gu.gen_identifier('lower'),
                    expr=expr,
                    is_final=False,
                    var_type=expr_type)
                # self._add_node_to_parent(self.namespace, var_decl)
                expr = var_decl
            if expr:
                exprs.append(expr)
        # These are the new declarations that we created as part of the side-
        # effects.
        decls = self.context.get_declarations(self.namespace, True).values()
        decls = [
            d for d in decls if not isinstance(d, ast.ParameterDeclaration)
        ]
        # self.allow_bottom_consts = old_allow_bottom_consts
        return exprs, decls

    def _gen_ret_and_paramas_from_sig(self, etype, inside_lambda=False) -> \
        Tuple[tp.Type, List[ast.ParameterDeclaration]]:
        """Generate parameters from signature and return them along with return
        type.

        Args:
            etype: signature type
            inside_lambda: true if we want to generate parameters for a lambda
        """
        prev_inside_java_lamdba = False
        if inside_lambda:
            prev_inside_java_lamdba = self._inside_java_lambda
            self._inside_java_lambda = True  # self.language == "java"
        params = [self.gen_param_decl(et) for et in etype.type_args[:-1]]
        if inside_lambda:
            self._inside_java_lambda = prev_inside_java_lamdba
        ret_type = etype.type_args[-1]
        return ret_type, params

    # Matching functions

    def _get_matching_objects(
            self,
            etype: tp.Type,
            subtype: bool,
            attr_name: str,
            func_ref: bool = False,
            signature: bool = False) -> List[gu.AttrReceiverInfo]:
        """Get objects that have an attribute of attr_name that is/return etype.

        This function essentially searches for variables containing objects
        whose class has either a field of a specific value or a function that
        return a particular value.

        As for func_ref and signatures there are the following scenarios:

        1. func_ref = True and signature = False and attr_name = fields
            -> find function references that return etype
        2. func_ref = False and signature = True and attr_name = functions
            -> find functions that have the given signature
        2. func_ref = True and signature = True and attr_name = fields
            -> find functions references that return etype (etype is signature)

        Args:
            etype: the targeted type that we are searching. Functions should
                return that type.
            subtype: The type of matching attribute could be a subtype of
                `etype`.
            attr_name: 'fields' or 'functions'
            func_ref: look for function reference variables
            signature: etype is a signature.

        Returns:
            AttrReceiverInfo
        """
        fun_type_var_map = {}
        decls = []
        variables = self.context.get_vars(self.namespace).values()
        if self._inside_java_lambda:
            variables = list(
                filter(
                    lambda v: (getattr(v, 'is_final', False) or
                               (v not in self.context.get_vars(
                                   self.namespace[:-1]).values())), variables))
        for var in variables:
            var_type = self._get_var_type_to_search(var.get_type())
            if not var_type:
                continue
            if isinstance(getattr(var_type, 't_constructor', None),
                          self.function_type):
                continue
            cls, type_map_var = self._get_class(var_type)
            for attr in self._get_class_attributes(cls, attr_name):
                attr_type = tp.substitute_type(attr.get_type(), type_map_var)
                if attr_type == self.bt_factory.get_void_type():
                    continue
                if func_ref:
                    if not getattr(attr_type, 'is_function_type',
                                   lambda: False)():
                        continue

                if attr_name == 'functions':
                    fun_type_var_map = {}
                    if attr.is_parameterized():
                        func_type_var_map = tu.unify_types(
                            etype, attr.get_type(), self.bt_factory)
                        if not func_type_var_map:
                            continue
                        # Here we do the following. The retrieved attribute
                        # is a parameterized function. So, we need to
                        # instantiate it with some type arguments. However,
                        # note that if the matching object belongs to a
                        # parameterized class, we need to consider the
                        # following case:
                        #
                        # A<T> {
                        #   fun <X: T> foo(): X
                        # }
                        # val a = new A<String>()
                        # a.foo() -> here the type argument of the function
                        # `foo` should be a subtype of String, as the type of
                        # the receiver is A<String> and as a result the bound
                        # type variable X is String.
                        type_var_bounds = {}
                        for t_param in attr.type_parameters:
                            bound = t_param.bound
                            if bound is None:
                                continue
                            if bound.has_type_variables():
                                # Substitute the bound of the function type
                                # parameter with type assignment map of the
                                # receiver class.
                                bound = tp.substitute_type(bound, type_map_var)
                                if func_type_var_map.get(t_param,
                                                         bound) != bound:
                                    continue
                                if bound.is_wildcard():
                                    type_var_bounds = None
                                    break
                                if not bound.has_type_variables():
                                    type_var_bounds[t_param] = bound
                        if type_var_bounds is None:
                            continue
                        type_var_bounds.update(type_map_var)
                        type_var_bounds.update(fun_type_var_map)
                        fun_type_var_map = tu.instantiate_parameterized_function(
                            attr.type_parameters,
                            self.get_types(),
                            type_var_map=type_var_bounds,
                            only_regular=True)
                    else:
                        fun_type_var_map = {}
                    type_map_var.update(fun_type_var_map)

                if not self._is_sigtype_compatible(
                        attr, etype, type_map_var, signature and not func_ref,
                        subtype, lambda x, y:
                    (tp.substitute_type(x.get_type(), y).type_args[-1]
                     if not signature and func_ref else tp.substitute_type(
                         x.get_type(), y))):
                    continue
                if getattr(attr, 'type_parameters', None):

                    decls.append(
                        gu.AttrReceiverInfo(ast.Variable(var.name),
                                            type_map_var, attr,
                                            fun_type_var_map))
                else:
                    decls.append(
                        gu.AttrReceiverInfo(ast.Variable(var.name),
                                            type_map_var, attr, None))
        return decls

    def _get_matching_function_declarations(
            self,
            etype: tp.Type,
            subtype: bool,
            signature=False) -> List[gu.AttrReceiverInfo]:
        """Get all available function declarations.

        This function searches functions in the current scope that return
        `etype`, and then it also searches for receivers whose class has a
        function that return `etype` (a function with a specific signature
        type).

        Args:
            etype: the return type for the function to find
                return that type.
            subtype: The return type of the function could be a subtype of
                `etype`.
            signature: etype is a signature.
        """
        functions = []
        is_nested_function = (self.namespace != ast.GLOBAL_NAMESPACE
                              and self.namespace[-2].islower()
                              and self.namespace[-2] != 'global')
        # First find all top-level functions or methods included
        # in the current class.
        msg = ("Searching for function declarations that match type {};"
               " checking signature {}")
        log(self.logger, msg.format(etype, signature))
        for func in self.context.get_funcs(self.namespace).values():
            # The receiver object for this kind of functions is None.
            if func.get_type() == self.bt_factory.get_void_type():
                continue

            if is_nested_function and func.name in self.namespace:
                # Here, we disallow recursive calls because it may lead to
                # recursive call on lambda expressions.
                continue
            if is_nested_function and signature:
                # Here we disallow nested functions to be used as function
                # references
                continue
            if func.is_parameterized() and func.is_class_method():
                # TODO: Consider being less conservative.
                # The problem is when the class method is parameterized,
                # the receiver is parameterized, and the type parameters
                # of functions have bounds corresponding to the type parameters
                # of class.
                continue

            type_var_map = {}
            if func.is_parameterized():
                func_type_var_map = tu.unify_types(etype, func.get_type(),
                                                   self.bt_factory)
                if not func_type_var_map:
                    continue
                func_type_var_map = tu.instantiate_parameterized_function(
                    func.type_parameters,
                    self.get_types(),
                    type_var_map=func_type_var_map,
                    only_regular=True)
                type_var_map.update(func_type_var_map)

            if not self._is_sigtype_compatible(func, etype, type_var_map,
                                               signature, subtype):
                continue

            # Nice to have:  add `this` explicitly as the receiver in methods
            # of current class.
            functions.append(gu.AttrReceiverInfo(None, {}, func, type_var_map))
        return functions + self._get_matching_objects(
            etype, subtype, 'functions', signature=signature)

    def _gen_matching_func(self,
                           etype: tp.Type,
                           not_void=False,
                           signature=False) -> gu.AttrAccessInfo:
        """ Generate a function or a class containing a function whose return
        type is 'etype'.

        Args:
            etype: the targeted return type.
            not_void: do not create functions that return void.
            signature: etype is a signature.
        """
        # Randomly choose to generate a function or a class method.
        gen_method = (
            ut.randomUtil.bool() or
            # We avoid generating nested functions that we are going to use
            # as function references.
            signature)
        if not gen_method:
            initial_namespace = self.namespace
            # If the given type 'etype' is a type parameter, then the
            # function we want to generate should be in the current namespace,
            # so that the type parameter is accessible.
            self.namespace = (
                self.namespace if
                (ut.randomUtil.bool() or etype.has_type_variables())
                and not self._inside_func_body else ast.GLOBAL_NAMESPACE)
            # Generate a function
            params = None
            if signature:
                etype, params = self._gen_ret_and_paramas_from_sig(etype)
            func = self.gen_func_decl(etype, params=params, not_void=not_void)
            self.namespace = initial_namespace
            func_type_var_map = {}
            if func.is_parameterized():
                func_type_var_map = tu.instantiate_parameterized_function(
                    func.type_parameters,
                    self.get_types(),
                    only_regular=True,
                    type_var_map={})
            msg = "Generating a method {} of type {}; TypeVarMap {}".format(
                func.name, etype, func_type_var_map)
            log(self.logger, msg)
            return gu.AttrAccessInfo(None, {}, func, func_type_var_map)
        # Generate a class containing the requested function
        return self._gen_matching_class(etype,
                                        'functions',
                                        signature=signature)

    # noinspection PyProtectedMember
    def _get_matching_class(self,
                            etype: tp.Type,
                            subtype: bool,
                            attr_name: str,
                            signature=False) -> gu.AttrAccessInfo:
        """Get a class that has an attribute of attr_name that is/return etype.

        This function essentially searches for a class that has either a field
        of a specific value or a function that return a particular value.

        Args:
            etype: the targeted type that we are searching. Functions should
                return that type.
            subtype: The type of matching attribute could be a subtype of
                `etype`.
            attr_name: 'fields' or 'functions'
            signature: etype is a signature.

        Returns:
            An AttrAccessInfo with a matched class type and attribute
            declaration (field or function).
        """
        msg = "Searching for class that contains {} of type {}"
        log(self.logger, msg.format(attr_name, etype))
        class_decls = self._get_matching_class_decls(etype,
                                                     subtype=subtype,
                                                     attr_name=attr_name,
                                                     signature=signature)
        if not class_decls:
            return None
        cls, type_var_map, attr = ut.randomUtil.choice(class_decls)
        func_type_var_map = {}
        is_parameterized_func = isinstance(
            attr, ast.FunctionDeclaration) and attr.is_parameterized()
        if cls.is_parameterized():
            cls_type_var_map = type_var_map

            variance_choices = (None if cls_type_var_map is None else
                                gu.init_variance_choices(cls_type_var_map))
            cls_type, params_map = tu.instantiate_type_constructor(
                cls.get_type(),
                self.get_types(),
                only_regular=True,
                type_var_map=type_var_map,
                enable_pecs=self.enable_pecs,
                disable_variance_functions=self.disable_variance_functions,
                variance_choices=variance_choices,
                disable_variance=variance_choices is None)
            msg = ("Found parameterized class {} with TypeVarMap {} and "
                   "incomplete TypeVarMap {}")
            log(self.logger, msg.format(cls.name, params_map, type_var_map))
            if is_parameterized_func:
                # Here we have found a parameterized function in a
                # parameterized class. So wee need to both instantiate
                # the type constructor and the parameterized function.
                types = tu._get_available_types(cls.get_type(),
                                                self.get_types(), True, False)
                _, type_var_map = tu._compute_type_variable_assignments(
                    cls.type_parameters + attr.type_parameters,
                    types,
                    type_var_map=type_var_map,
                    variance_choices=variance_choices)
                params_map, func_type_var_map = tu.split_type_var_map(
                    type_var_map, cls.type_parameters, attr.type_parameters)
                targs = [
                    params_map[t_param] for t_param in cls.type_parameters
                ]
                cls_type = cls.get_type().new(targs)
            else:
                # Here, we have a non-parameterized function in a parameterized
                # class. So we only need to instantiate the type constructor.
                cls_type, params_map = tu.instantiate_type_constructor(
                    cls.get_type(),
                    self.get_types(),
                    only_regular=True,
                    type_var_map=cls_type_var_map,
                    enable_pecs=self.enable_pecs,
                    variance_choices=variance_choices,
                    disable_variance=variance_choices is None)
        else:
            if is_parameterized_func:
                # We are in a parameterized class defined in a class that
                # is not a type constructor.
                func_type_var_map = tu.instantiate_parameterized_function(
                    attr.type_parameters,
                    self.get_types(),
                    only_regular=True,
                    type_var_map=type_var_map)
            cls_type, params_map = cls.get_type(), {}

        attr_msg = "Attribute {}; type: {}, TypeVarMap{}".format(
            attr_name, etype, func_type_var_map)
        msg = "Selected class {} with TypeVarMap {};" " matches {}".format(
            cls.name, params_map, attr_msg)
        log(self.logger, msg)
        return gu.AttrAccessInfo(cls_type, params_map, attr, func_type_var_map)

    def _is_sigtype_compatible(
        self,
        attr,
        etype,
        type_var_map,
        check_signature,
        subtype,
        get_attr_type=lambda x, y: tp.substitute_type(x.get_type(), y)):
        attr_type = get_attr_type(attr, type_var_map)
        if not check_signature:
            if subtype:
                return attr_type.is_assignable(etype)
            return attr_type == etype
        param_types = [
            tp.substitute_type(p.get_type(), type_var_map) for p in attr.params
        ]
        sig = tp.ParameterizedType(
            self.bt_factory.get_function_type(len(attr.params)),
            param_types + [attr_type])
        return etype == sig

    def _is_signature_compatible(self, attr, etype, check_signature, subtype):
        """
        Checks if the signature of attr is compatible with etype.
        """
        type_var_map = {}
        attr_type = attr.get_type()
        if check_signature:
            signature_types = [p.get_type() for p in attr.params]
            signature_types.append(attr_type)
            # The signature of the function `attr` does not match with `etype`.
            # Namely, attr does not contain the same number of parameters
            # as `etype`.
            if len(signature_types) != len(etype.type_args):
                return False, None

            for i, st in enumerate(signature_types):
                if not st.has_type_variables():
                    continue
                # Unify its component of attr with the corresponding type
                # argument of etype.
                new_tvm = tu.unify_types(etype.type_args[i], st,
                                         self.bt_factory)
                if not new_tvm:
                    return False, None
                for k, v in new_tvm.items():
                    assigned_t = type_var_map.get(k, v)
                    # The instantiation of type variable k clashes with
                    # a previous instantiation of this type variable.
                    if assigned_t != v:
                        return False, None
                type_var_map.update(new_tvm)
        else:
            # if the type of the attribute has type variables,
            # then we have to unify it with the expected type so that
            # we can instantiate the corresponding type constructor
            # accordingly
            if attr_type.has_type_variables():
                type_var_map = tu.unify_types(etype, attr_type,
                                              self.bt_factory)
        is_comb = self._is_sigtype_compatible(attr, etype, type_var_map,
                                              check_signature, subtype)
        return is_comb, type_var_map

    def _get_matching_class_decls(
        self,
        etype: tp.Type,
        subtype: bool,
        attr_name: str,
        signature=False
    ) -> List[Tuple[ast.ClassDeclaration, tu.TypeVarMap, ast.Declaration]]:
        """Get classes that have attributes of attr_name that are/return etype.

        Args:
            etype: the targeted type that we are searching. Functions should
                return that type.
            subtype: The type of matching attribute could be a subtype of
                `etype`.
            attr_name: 'fields' or 'functions'
            signature: etype is a signature.

        Returns:
            A list of tuples that include class declarations, TypeVarMaps for
            the attributes and the declarations of the attributes (fields or
            functions).
        """

        class_decls = []
        for c in self.context.get_classes(self.namespace).values():
            for attr in self._get_class_attributes(c, attr_name):
                attr_type = attr.get_type()
                if not attr_type:
                    continue
                if attr_type == self.bt_factory.get_void_type():
                    continue
                # Avoid recursive decls because of incomplete information.
                if attr.name == self.namespace[-1] and signature:
                    continue

                is_comb, type_var_map = self._is_signature_compatible(
                    attr, etype, signature, subtype)
                if not is_comb:
                    continue
                # Now here we keep the class and the function that match
                # the given type.
                class_decls.append((c, type_var_map, attr))
        return class_decls

    def _gen_matching_class(self,
                            etype: tp.Type,
                            attr_name: str,
                            not_void=False,
                            signature=False) -> gu.AttrAccessInfo:
        """Generate a class that has an attribute of attr_name that is/return etype.

        Args:
            etype: the targeted type that we want to get. Functions should
                return that type.
            attr_name: 'fields' or 'functions'
            not_void: Functions of the class should not return void.
            signature: etype is a signature.

        Returns:
            An AttrAccessInfo for the generated class type and attribute
            declaration (field or function).
        """
        initial_namespace = self.namespace
        class_name = gu.gen_identifier('capitalize')
        type_params = None

        # Get return type, type_var_map, and flag for wildcards
        if etype.has_type_variables():
            # We have to create a class that has an attribute whose type
            # is a type parameter. The only way to achieve this is to create
            # a parameterized class, and pass the type parameter 'etype'
            # as a type argument to the corresponding type constructor.
            self.namespace = ast.GLOBAL_NAMESPACE + (class_name, )
            type_params, type_var_map, can_wildcard = \
                self._create_type_params_from_etype(etype)
            etype2 = tp.substitute_type(etype, type_var_map)
        else:
            type_var_map, etype2, can_wildcard = {}, etype, False

        self.namespace = ast.GLOBAL_NAMESPACE

        # Create class
        if attr_name == 'functions':
            kwargs = {'fret_type': etype2} if not signature \
                else {'signature': etype2}
        else:
            kwargs = {'field_type': etype2}
        cls = self.gen_class_decl(**kwargs,
                                  not_void=not_void,
                                  type_params=type_params,
                                  class_name=class_name)
        self.namespace = initial_namespace

        # Get receiver
        if cls.is_parameterized():
            type_map = {v: k for k, v in type_var_map.items()}
            if etype2.is_primitive() and (etype2.box_type()
                                          == self.bt_factory.get_void_type()):
                type_map = None

            if can_wildcard:
                variance_choices = gu.init_variance_choices(type_map)
            else:
                variance_choices = None
            cls_type, params_map = tu.instantiate_type_constructor(
                cls.get_type(),
                self.get_types(),
                type_var_map=type_map,
                enable_pecs=self.enable_pecs,
                disable_variance_functions=self.disable_variance_functions,
                variance_choices=variance_choices,
                disable_variance=variance_choices is None)
        else:
            cls_type, params_map = cls.get_type(), {}

        # Generate func_type_var_map
        for attr in getattr(cls, attr_name):
            if not self._is_sigtype_compatible(attr, etype, params_map,
                                               signature, False):
                continue

            func_type_var_map = {}
            if isinstance(attr,
                          ast.FunctionDeclaration) and attr.is_parameterized():
                func_type_var_map = tu.instantiate_parameterized_function(
                    attr.type_parameters,
                    self.get_types(),
                    only_regular=True,
                    type_var_map=params_map)

            msg = ("Generated a class {} with an attribute {} of type {}; "
                   "ClassTypeVarMap {}, FuncTypeVarMap {}")
            log(
                self.logger,
                msg.format(cls.name, attr_name, etype, params_map,
                           func_type_var_map))
            return gu.AttrAccessInfo(cls_type, params_map, attr,
                                     func_type_var_map)
        return None

    # Where

    def _create_type_params_from_etype(self, etype: tp.Type):
        """Generate type parameters for a type.

        Returns:
            * A list of type parameters.
            * A TypeVarMap for the type parameters.
            * A boolean to declare if we can use wildcards.
        """
        if not etype.has_type_variables():
            return []

        if isinstance(etype, tp.TypeParameter):
            type_params = self.gen_type_params(count=1)
            type_params[0].bound = etype.get_bound_rec(self.bt_factory)
            type_params[0].variance = tp.Invariant
            return type_params, {etype: type_params[0]}, True

        # the given type is parameterized
        assert isinstance(etype, (tp.ParameterizedType, tp.WildCardType))
        type_vars = etype.get_type_variables(self.bt_factory)
        type_params = self.gen_type_params(len(type_vars))
        type_var_map = {}
        available_type_params = list(type_params)
        can_wildcard = True
        for type_var, bounds in type_vars.items():
            # The given type 'etype' has type variables.
            # So, it's not safe to instantiate these type variables with
            # wildcard types. In this way we prevent errors like the following.
            #
            # class A<T> {
            #   B<T> foo();
            # }
            # A<? extends Number> x = new A<>();
            # B<Number> = x.foo(); // error: incompatible types
            # TODO: We may support this case in the future.
            can_wildcard = False
            bounds = list(bounds)
            type_param = ut.randomUtil.choice(available_type_params)
            available_type_params.remove(type_param)
            if bounds != [None]:
                type_param.bound = functools.reduce(
                    lambda acc, t: t if t.is_subtype(acc) else acc,
                    filter(lambda t: t is not None, bounds), bounds[0])
            else:
                type_param.bound = None
            type_param.variance = tp.Invariant
            type_var_map[type_var] = type_param
        return type_params, type_var_map, can_wildcard
