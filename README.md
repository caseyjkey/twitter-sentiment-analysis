# Flock

Flock is a Python library for collecting sets of data from Twitter.

Twitter does not allow streaming from multiple tracks. 
This tool allows you to monitor a stream of many keywords, and group those tweets with labels. 

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install flock.

```bash
pip install flock
```

## Usage
As a script from the command line.
```bash
git clone https://github.com/caseykey/flock
cd flock
python3 flock.py api-creds.json output.txt
```
After exiting the process, the search can continue.
```bash
python3 flock.py api-creds.json output.txt go
```
# Usage as a Python module.
```python
from flock import Flock

# save tweets to output.txt using previous search terms
stream = Flock('api_creds.json', 'output.txt', 'continue')
stream.start() # begin reading tweets
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
[MIT](https://choosealicense.com/licenses/mit/)


