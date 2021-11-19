import warnings, inspect, functools
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union
from django.db import models
from dataclasses import dataclass, field


class OrmManager(models.Manager):
    # TODO: find the way to override the default manager or assign this manager as default
    def exclude(self, *args: Any, **kwargs: Any):
        hybrid_expression_results: List[OrmExpressionResult] = []
        qq_results: List[QQ] = []
        common_filter_args = []
        for arg in args:
            if isinstance(arg, OrmExpressionResult):
                arg.method = 'exclude'
                hybrid_expression_results.append(arg)
                continue
            if isinstance(arg, QQ):
                qq_results.append(arg)
                continue
            if isinstance(arg, OrmExpression):
                raise ValueError(f'{arg=} is not an OrmExpressionResult')

            common_filter_args.append(arg)

        self = super().exclude(*common_filter_args, **kwargs)

        for qq_result in qq_results:
            for orm_expression in qq_result.orm_expression_results:
                self = self.annotate(**orm_expression._annotate())
        self = self.exclude(*qq_results)

        for orm_expression_result in hybrid_expression_results:
            self = orm_expression_result.apply(queryset=self)

        return self

    def filter(self, *args: Any, **kwargs: Any) -> models.QuerySet:
        qq_results: List[QQ] = []
        hybrid_expression_results: List[OrmExpressionResult] = []
        common_filter_args = []
        for arg in args:
            if isinstance(arg, OrmExpressionResult):
                arg.method = 'filter'
                hybrid_expression_results.append(arg)
                continue
            if isinstance(arg, QQ):
                qq_results.append(arg)
                continue
            if isinstance(arg, OrmExpression):
                raise ValueError(f'{arg=} is not an OrmExpressionResult')
            common_filter_args.append(arg)

        self = super().filter(*common_filter_args, **kwargs)

        for qq_result in qq_results:
            for orm_expression in qq_result.orm_expression_results:
                self = self.annotate(**orm_expression._annotate())
        self = self.filter(*qq_results)

        for orm_expression_result in hybrid_expression_results:
            self = orm_expression_result.apply(queryset=self)

        return self


    def annotate(self, *args, **kwargs):
        orm_expression_results: Dict[str, Any] = {}
        common_annotate_args = []
        for arg in args:
            if isinstance(arg, OrmExpression):
                annotate = arg.annotate()
                orm_expression_results.update(annotate)
                continue
            if isinstance(arg, OrmExpressionResult):
                raise ValueError(f'{arg=} is not an OrmExpression')
            common_annotate_args.append(arg)

        self = super().annotate(**orm_expression_results).annotate(*common_annotate_args, **kwargs)
        return self


@dataclass
class OrmExpressionResult:
    expr: Callable
    lookup: Literal['exact'] = 'exact'
    value: Optional[Any] = None
    expr_args: Tuple = field(default_factory=tuple)
    expr_kwargs: Dict[str, Any] = field(default_factory=dict)
    method: Literal['filter', 'exclude'] = 'filter'
    alias: Optional[str] = 'asdaslkdj'
    ignore_case: Optional[bool] = False
    
    @property
    def expression(self):
        return self._filter_exclude

    def apply(self, queryset: models.QuerySet) -> models.QuerySet:
        queryset = queryset.annotate(**self._annotate())
        return getattr(queryset, self.method)(**self._filter_exclude())

    def _annotate(self) -> Dict[str, Any]:
        return {self.alias: self.expr(self.expr, *self.expr_args, **self.expr_kwargs)}

    def _filter_exclude(self) -> Dict[str, Any]:
        return {f'{self.alias}__{"i" if self.ignore_case else ""}{self.lookup}': self.value}

class QQ(models.Q):
    orm_expression_results: List[OrmExpressionResult] = []

    def __init__(self, *args, _connector=None, _negated=False, **kwargs):
        common_args = []
        for arg in args:
            if isinstance(arg, OrmExpressionResult):
                self.orm_expression_results.append(arg)
                kwargs.update(arg._filter_exclude())
                continue
            common_args.append(arg)
        super().__init__(*common_args, _connector=_connector, _negated=_negated, **kwargs)


@dataclass
class OrmExpression:
    expr: Callable
    expr_args: Tuple = field(default_factory=tuple)
    expr_kwargs: Dict = field(default_factory=dict)
    alias: Optional[str] = field(init=False)
    ignore_case: Optional[bool] = False
    method: Literal['filter', 'exclude'] = 'filter'

    def __post_init__(self):
        self.alias = self.expr_kwargs.pop('alias', self.expr.__name__)
        self.ignore_case = self.expr_kwargs.pop('ignore_case', False)
        if 'through' in self.expr_kwargs:
            self._validate_through()

    def _validate_through(self) -> None:
            through: str = self.expr_kwargs['through']
            assert not through.endswith('__'), f'{through=} can\'t end with "__"'
            assert not through.startswith('__'), f'{through=} can\'t start with "__"'
            self.expr_kwargs['through'] = f'{through}__'

    def __call__(self):
        return self.expr(self.expr, *self.expr_args, **self.expr_kwargs)

    def annotate(self):
        return self._generate()._annotate()

    def __generate(lookup: str) -> OrmExpressionResult:
        def inner(self, value):
            return self._generate(value, lookup)
        return inner

    def _generate(self, value: Any = None, lookup: Optional[str] = None) -> OrmExpressionResult:
        return OrmExpressionResult(
            expr=self.expr,
            value=value,
            expr_args=self.expr_args,
            expr_kwargs=self.expr_kwargs,
            lookup=lookup,
            alias=self.alias,
            ignore_case=self.ignore_case,
            method=self.method,
        )

    def __invert__(self):
        self.method = 'exclude' if self.method == 'filter' else 'filter'
        return self

    __eq__ = __generate('exact')
    __contains__ = __generate('contains') # FIXME: not working
    __lt__ = __generate('lt')
    __gt__ = __generate('gt')
    __ge__ = __generate('gte')
    __le__ = __generate('lte')
    exact = __generate('exact')
    gt = __generate('gt')
    gte = __generate('gte')
    lt = __generate('lt')
    lte = __generate('lte')
    iexact = __generate('iexact')
    contains = __generate('contains')
    icontains = __generate('icontains')
    in_ = __generate('in')
    startswith = __generate('startswith')
    istartswith = __generate('istartswith')
    endswith = __generate('endswith')
    iendswith = __generate('iendswith')
    range = __generate('range')
    isnull = __generate('isnull')
    regex = __generate('regex')
    iregex = __generate('iregex')
    date = __generate('date')
    year = __generate('year')
    month = __generate('month')
    day = __generate('day')
    search = __generate('search') # FIXME: check datbaase usage


@dataclass
class orm_property:
    func: Callable
    expr: Optional[Callable] = field(init=False, default=None)

    def __get__(self, instance, owner) -> Union[Callable, OrmExpression]:
        if instance is None:
            assert self.expr is not None, f'Must define a @{self.func.__name__}.expression first'
            return self._wrapper(self.expr)
        return self.func.__get__(instance, owner)
    
    def _wrapper(self, expr):
        @functools.wraps(expr)
        def inner(*args, **kwargs):
            return OrmExpression(expr, expr_args=args, expr_kwargs=kwargs)
        return inner
    
    def expression(self, expr):
        if 'through' not in inspect.getfullargspec(expr).args:
            warnings.warn(f'{expr} should have a "through" argument')
        if expr.__doc__ is None:
            expr.__doc__ = self.func.__doc__ if self.func.__doc__ else ''
        expr.__doc__ += '''

        **kwargs:
            * alias (str): alias to be annotated.
            * through (str): through from where be accesss.
        '''

        self.expr = expr
        return self
