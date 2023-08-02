from koil.helpers import unkoil
from koil.koil import Koil
import inspect
from typing import Callable, Type, TypeVar
from koil.vars import current_loop
import logging

T = TypeVar("T")


logger = logging.getLogger(__name__)


def koilable(
    fieldname: str = "__koil",
    add_connectors: bool = False,
    koil_class: Type[Koil] = Koil,
    **koilparams,
) -> Callable[[Type[T]], Type[T]]:
    """
    Decorator to make an async generator koilable.

    Args:
        fieldname (str, optional): The name of the field to store the koil instance. Defaults to "__koil".
        add_connectors (bool, optional): If True, it will add the connectors to the class. Defaults to False.
        koil_class (Type[Koil], optional): The class of the koil to use. Defaults to Koil.

    """

    def real_cls_decorator(cls: Type[T]) -> Type[T]:
        cls.__koilable__ = True
        assert hasattr(cls, "__aenter__"), "Class must implement __aenter__"
        assert hasattr(cls, "__aenter__"), "Class must implement __aexit__"
        assert inspect.iscoroutinefunction(
            cls.__aenter__
        ), "__aenter__ must be a coroutine"
        assert inspect.iscoroutinefunction(
            cls.__aexit__
        ), "__aexit__ must be a coroutine (awaitable)"

        def koiled_enter(self, *args, **kwargs):
            potential_koiled_loop = current_loop.get()
            if potential_koiled_loop is not None:
                return unkoil(self.__aenter__, *args, **kwargs)
            else:
                setattr(
                    self,
                    fieldname,
                    koil_class(name=f"{repr(self)}", **koilparams),
                )
                getattr(self, fieldname).__enter__()
                return unkoil(self.__aenter__, *args, **kwargs)

        def koiled_exit(self, *args, **kwargs):
            unkoil(self.__aexit__, *args, **kwargs)
            koil = getattr(self, fieldname, None)
            if koil is not None:
                koil.__exit__(None, None, None)

        async def aexit(self):
            return await self.__aexit__(None, None, None)

        async def aenter(self):
            return await self.__aenter__()

        cls.__enter__ = koiled_enter
        cls.__exit__ = koiled_exit
        if add_connectors:
            cls.aexit = aexit
            cls.aenter = aenter
            cls.exit = koiled_exit
            cls.enter = koiled_enter

        return cls

    return real_cls_decorator


def unkoilable(func):
    def wrapper(*args, **kwargs):
        return unkoil(func, *args, **kwargs)

    return wrapper
