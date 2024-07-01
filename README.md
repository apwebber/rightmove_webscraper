# rightmove-webscraper

<code>rightmove_webscraper</code> is based on the package found [here](https://github.com/toby-p/rightmove_webscraper.py), with some modifications. It now only has one goal which is to scrape the data and store it in a json. All data interpretation or aggregation is now assumed to happen elsewhere.

It also does scraping by harvesting the json contained in the javascript at the bottom of the results page. This way there are a LOT more things available for use.

## Installation

git clone

## Scraping property listings

1) Go to <a href="http://www.rightmove.co.uk/">rightmove.co.uk</a> and search for whatever region, postcode, city, etc. you are interested in. You can also add any additional filters, e.g. property type, price, number of bedrooms, etc.

<img src = "./docs/images/rightmove_search_screen.PNG">

2) Run the search on the rightmove website and copy the URL of the first results page.

3) Create an instance of the class with the URL as the init argument.

```python
from rightmove_webscraper import RightmoveData


url = "https://www.rightmove.co.uk/property-for-sale/find.html?searchType=SALE&locationIdentifier=REGION%5E94346"
rm = RightmoveData(url, results_fpath)

# Access data
data = rm.get_data()

# Or read the json file that was written
import json

with open(results_fpath, 'r') as f:
    data = json.load(f)
```


## Legal

<a href="https://github.com/toddy86">@toddy86</a> has pointed out per the terms and conditions <a href="https://www.rightmove.co.uk/this-site/terms-of-use.html"> here</a> the use of webscrapers is unauthorised by rightmove. So please don't use this package!
