[![Build Status](https://travis-ci.com/hukkinj1/loga.svg?branch=master)](https://travis-ci.com/hukkinj1/loga)
[![codecov.io](https://codecov.io/gh/hukkinj1/loga/branch/master/graph/badge.svg)](https://codecov.io/gh/hukkinj1/loga)
[![PyPI version](https://badge.fury.io/py/loga.svg)](https://badge.fury.io/py/loga)

# `@loga`: automated logging for Python

<!--- Don't edit the version line below manually. Let bump2version do it for you. -->
> Version 1.0.0

> You find Python's builtin `logging` module repetitive, tedious and ugly, and the logs you do write with it clash with your otherwise awesome style. `loga` is here to help: it automates the boring stuff, simplifies the tricky stuff, hooks up effortlessly to [graylog](https://www.graylog.org/), and keeps an eye out for privacy and security if you need it to.

## Install

```bash
pip install loga
```

To install with Graylog support, do:
```bash
pip install loga[graylog]
```

## Setup

To get started, import and instantiate the main class, ideally somewhere at the core of your project. If you have a module with multiple files, do the initial configuration in the main `__init__.py`, or in a file called `log.py`. so you can import the same, ready-set-up logger easily.

For example, if your app was called `tester`, you could add the following to `tester/__init__.py`:

```python
from loga import Loga

# all setup values are optional
loga = Loga(
    facility="tester",  # name of program logging the message
    graylog_address=("0.0.0.0", 9999),  # address for graylog (ip, port)
    do_print=True,  # print each log to console
    do_write=True,  # write each log to file
    logfile="mylog.txt",  # custom path to logfile
    truncation=1000,  # longest possible value in extra data
    private_data={"password"},  # set of sensitive args/kwargs
)
```

## Usage

In other parts of the project, you can then access the configured logger instance with:

```python
from tester import loga
```

### Loga as decorator

You can use `@loga` as a decorator on any callable: a class, on its method, or on function. On classes, it will log every method; on methods and functions it will log the call signature, return and errors. The central idea behind `loga` is that you can simply decorate every class in your project, as well as any important standalone functions, and have comprehensive, standardised information about your project's internals without any extra labour.

If a method within a decorated class is called too often, or if you don't need to keep an eye on it, you can use `@loga.ignore` to ignore it. Also available is `@loga.errors`, which will only log exceptions, not calls and returns.

For an example use-case, let's make a simple class that multiplies two numbers, but only if a password is supplied. We will ignore logging of the boring authentication system.

```python
@loga
class Multiplier:
    def __init__(self, base):
        self.base = base

    def multiply(self, n, password):
        """
        Multiply by the number given during initialisation--requires password
        """
        self.authenticated = self._do_authentication(password)
        if not self.authenticated:
            raise ValueError("Not authenticated!")
        return self.base * n

    @loga.ignore
    def _do_authentication(self, password):
        """Not exactly Fort Knox"""
        return password == "tOpSeCrEt"
```

First, let's use it properly, with our secret password passed in:

```python
mult = Multiplier(50)
result = mult.multiply(50, "tOpSeCrEt")
assert result == 2500  # True
```

We'll get some nice text in the console:

```
11.05 2018 17:14:54 *Called Multiplier.multiply(n=50, password='******')
11.05 2018 17:14:54 *Returned from Multiplier.multiply(n=50, password='******') with int (2500)
```

Notice that our private argument `password` was successfully obscured, even without us naming the argument when we called the method. If you used `do_write=True`, this log will also be in your specified log file, also with password obscured.

```python
result = mult.multiply(7, "password123")
```

Here an error will raise, a log will be generated, and we'll get extra info in the console, including traceback:

```
11.05 2018 17:19:43 *Called Multiplier.multiply(n=7, password='******')
11.05 2018 17:19:43 *Errored during Multiplier.multiply(n=7, password='******') with ValueError "Not authenticated!"    20 -- see below:
Traceback (most recent call last):
  File "/Users/danny/work/loga/loga/loga.py", line 137, in full_decoration
    response = function(*args, **kwargs)
  File "tester.py", line 13, in multiply
    raise ValueError('Not authenticated!')
ValueError: Not authenticated!
```

If you're using [graypy](https://github.com/severb/graypy/), you'll get a lot of extra goodness, such as key-value pairs for call signatures, timestamps, arguments, return values, exception information, and so on.

### Custom messages

When configuring `loga`, you can use your own message format for the auto-generated logs. There are four keys, one for each autolog type:

```python
loga = Loga(
    called="Log before callable is run",
    returned="Log for return from {call_signature} at {timestamp}",
    returned_none="Log when the return value of the callable is None",
    errored="Log string on exception: {exception_type}",
)


@loga
def test():
    pass
```

If you pass `None` for any of these keyword arguments, logs of that time will be completely suppressed. If you do not provide a value for `returned_none`, `loga` will use the value you provided for `returned`, or fall back to its own default.

Notice, in the example above, you can include particular format strings in the log message. Currently supported are:
* `call_signature`: the callable name and its arguments and keyword arguments
* `callable`: the `__qualname__` of the decorated object
* `params`: comma separated key value pairs for arguments passed
* `log_level`: the log level associated with this log
* `timestamp`: time at time of logging
* `couplet`: `uuid.uuid1()` for the called and returned/errored pair
* `number_of_params`: total `args + kwargs` as int
* `decorated`: always `True`

The `errored` log additionally supports:
* `exception_type`: `ValueError`, `AttributeError`, etc.
* `exception_msg`: details about the thrown exception
* `traceback`: exception traceback

And the `returned` and `returned_none` logs support:
* `return_value`: the object returned by the callable
* `return_type`: type of returned object

Adding more such strings is trivial; submit an issue if there is something else you need.

### Logging without decorators

For logging manually, `loga` provides methods similar to the logging functions of the `logging` standard library: `loga.log`, `loga.debug`, `loga.info`, `loga.warning`, `loga.error`, and `loga.critical`. The methods use the configuration that has already been defined. The main method `loga.log` takes three parameters:

```python
level = 50
msg = "Message to log"
extra = dict(some="data", that="will", be="logged")
loga.log(level, msg, extra)
# console: 11.05 2018 17:36:24 Message to log  50
# extra_data in log file if `do_print` setting is True
```

Methods `loga.debug`, `loga.info`, `loga.warning`, `loga.error` and `loga.critical` are convenience methods for setting the log level. For instance,

```python
loga.warning("A message", dict(some="data"))
```

is equivalent to

```python
loga.log(logging.WARNING, "A message", dict(some="data"))
```

where `logging.WARNING` is an integer constant imported from the standard library.

The advantage of using `loga` for these kinds of logs is that `loga` will make the extra data more readable and truncate very large strings. More importantly, you also still get whatever extras you've configured, like obfuscation of private data, or writing to console/file.

### Methods

You can also start and stop logging with `loga.start()` and `loga.stop()`, at any point in your code, though by default, error logs will still get through. If you want to suppress errors too, you can pass in `allow_errors=False`.

### Context managers

You can suppress logs using a context manager. Errors are allowed here by default too:

```python
with loga.pause(allow_errors=False):
    do_something()
```

## Limitations

`loga` uses Python's standard library (`logging`) to generate logs. There are some gotchas when using it: for instance, in terms of the extra data that can be passed in, key names for this extra data cannot clash with some internal names used within the `logging` module (`message`, `args`, etc.). To get around this, you'll get a warning that your data contains a bad key name, and it will be changed (i.e. from `message` to `protected_message`).
