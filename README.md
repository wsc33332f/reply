# reply

## Command calls

`autoreply.call("whoami")` runs the host's `whoami` command and returns its
output as a string. For safety, `whoami` is the only supported command;
unsupported commands raise `ValueError`.
