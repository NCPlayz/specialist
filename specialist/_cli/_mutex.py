import functools
from typing import Any, List, Mapping, Tuple
from click import Option, option, UsageError, Context


class MutuallyExclusiveOption(Option):
    def __init__(self, *args: Any, disallow: List[str], **kwargs: Any) -> None:
        self.disallow = disallow
        super().__init__(*args, **kwargs)

    def handle_parse_result(
        self, ctx: Context, opts: Mapping[str, Any], args: List[str]
    ) -> Tuple[Any, List[str]]:
        present = self.name in opts

        disallowed = next((d for d in self.disallow if d in opts), "")

        if present and disallowed:
            raise UsageError(
                f"Option -{self.name} cannot be used with -{disallowed}. They are mutually exclusive."
            )

        return super().handle_parse_result(ctx, opts, args)


mutex = functools.partial(option, cls=MutuallyExclusiveOption)
