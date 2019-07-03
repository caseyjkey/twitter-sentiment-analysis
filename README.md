# Flock

Flock is a Python library for collecting sets of data from Twitter.

Twitter does not allow streaming from multiple tracks. 
This tool allows you to monitor a stream of many keywords, and group those tweets with labels. 

## Usage
First create a twitter-creds.json file with your keys and tokens from a [Twitter Developer] app.
```json
{
    "CONSUMER_KEY": "apikeyhere123456abcdefgh",
    "CONSUMER_SECRET": "consumersecrethere123456789abcdefghijklmnopqrstuv",
    "ACCESS_KEY": "accesskeyhereaccesskeyhereaccesskeyhereaccesskey1",
    "ACCESS_SECRET": "accesssecrethereaccesssecrethereaccesssecret12"
}  
``` 

### Command-line Script
```bash
git clone https://github.com/caseykey/flock
cd flock
python3 flock.py api-creds.json output.txt
```
After exiting the process, the search can continue.
```bash
python3 flock.py api-creds.json output.txt go
```
### As a Python Module
```python
from flock import Flock

# save tweets to output.txt using previous search terms
stream = Flock(json_creds='api_creds.json', output='output.txt', cont='go')
stream.start() # begin reading tweets
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
[MIT](https://choosealicense.com/licenses/mit/)


