# Flock

Flock is a Python library for dealing with complex Twitter streams.

Twitter does not allow developers to stream from multiple tracks. 
This tool allows developers to monitor a stream of many keywords, and group the tweets with labels. 

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install flock.

```bash
pip install flock
```

## Usage

```python
from flock import Flock

stream = Flock('output.txt') # saves tweets to output.txt
stream.start() # begin reading tweets
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
[MIT](https://choosealicense.com/licenses/mit/)


