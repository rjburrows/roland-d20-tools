# All-file converter (`d20-tools all`) — work in progress

All files use the `.111` extension. This command is a documented placeholder
in version 0.1 and intentionally performs no conversion.

`d20-tools inspect INPUT` already identifies a native All container from its
validated header structure, but does not yet decode or convert its contents.

An All file combines several D-20 memory domains. Support will be added only
after its container layout and every embedded native mirror/consistency rule
are independently validated.
