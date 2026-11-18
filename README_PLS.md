# autoreply


`autoreply` is a small Python package for studying basic library design and
common Python tasks:

- arithmetic helpers

## Requirements

- Python 3.9 or newer


Install the package from the repository root:

```bash
python -m pip install .
```


## Public API

The package exports these helpers:

```python
import autoreply

autoreply.add(2, 3)
autoreply.subtract(7, 4)

```


```python
import autoreply

print(autoreply.add(2, 3))       # 5
print(autoreply.subtract(7, 4))  # 3
```


Run the unit tests:

```bash
python -m unittest discover -s tests -v
```
