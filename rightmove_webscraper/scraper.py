import json
import re
from lxml import html
import numpy as np
import requests


class RightmoveData:
    """The `RightmoveData` webscraper collects structured data on properties
    returned by a search performed on www.rightmove.co.uk

    An instance of the class provides attributes to access data from the search
    results, the most useful being `get_results`, which returns all results as a
    Pandas DataFrame object.

    The query to rightmove can be renewed by calling the `refresh_data` method.
    """

    def __init__(self, url: str, results_fpath: str):
        """Initialize the scraper with a URL from the results of a property
        search performed on www.rightmove.co.uk.

        Args:
            url (str): full HTML link to a page of rightmove search results.
        """
        self._status_code, self._first_page = self._request(url)
        self._url = url
        self._results_fpath = results_fpath
        self._validate_url()
        self._results = self._get_results()

    @staticmethod
    def _request(url: str):
        r = requests.get(url)
        return r.status_code, r.content

    def refresh_data(self, url: str = None):
        """Make a fresh GET request for the rightmove data.

        Args:
            url (str): optionally pass a new HTML link to a page of rightmove
                search results (else defaults to the current `url` attribute).
        """
        url = self.url if not url else url
        self._status_code, self._first_page = self._request(url)
        self._url = url
        self._validate_url()
        self._results = self._get_results()

    def _validate_url(self):
        """Basic validation that the URL at least starts in the right format and
        returns status code 200."""
        real_url = "{}://www.rightmove.co.uk/{}/find.html?"
        protocols = ["http", "https"]
        types = ["property-to-rent", "property-for-sale", "new-homes-for-sale"]
        urls = [real_url.format(p, t) for p in protocols for t in types]
        conditions = [self.url.startswith(u) for u in urls]
        conditions.append(self._status_code == 200)
        if not any(conditions):
            raise ValueError(f"Invalid rightmove search URL:\n\n\t{self.url}")

    @property
    def url(self):
        return self._url

    @property
    def get_results(self):
        """list of all results returned by the search."""
        return self._results

    @property
    def results_count(self):
        """Total number of results returned by `get_results`. Note that the
        rightmove website may state a much higher number of results; this is
        because they artificially restrict the number of results pages that can
        be accessed to 42."""
        return len(self.get_results)

    @property
    def average_price(self):
        """Average price of all results returned by `get_results` (ignoring
        results which don't list a price)."""
        # total = self.get_results["price"].dropna().sum()
        prices = [float(x['price']['amount']) for x in self.get_results]
        total = np.sum(prices)
        return total / self.results_count



    @property
    def rent_or_sale(self):
        """String specifying if the search is for properties for rent or sale.
        Required because Xpaths are different for the target elements."""
        if "/property-for-sale/" in self.url or "/new-homes-for-sale/" in self.url:
            return "sale"
        elif "/property-to-rent/" in self.url:
            return "rent"
        elif "/commercial-property-for-sale/" in self.url:
            return "sale-commercial"
        elif "/commercial-property-to-let/" in self.url:
            return "rent-commercial"
        else:
            raise ValueError(f"Invalid rightmove URL:\n\n\t{self.url}")

    @property
    def results_count_display(self):
        """Returns an integer of the total number of listings as displayed on
        the first page of results. Note that not all listings are available to
        scrape because rightmove limits the number of accessible pages."""
        tree = html.fromstring(self._first_page)
        xpath = """//span[@class="searchHeader-resultCount"]/text()"""
        return int(tree.xpath(xpath)[0].replace(",", ""))

    @property
    def page_count(self):
        """Returns the number of result pages returned by the search URL. There
        are 24 results per page. Note that the website limits results to a
        maximum of 42 accessible pages."""
        page_count = self.results_count_display // 24
        if self.results_count_display % 24 > 0:
            page_count += 1
        # Rightmove will return a maximum of 42 results pages, hence:
        if page_count > 42:
            page_count = 42
        return page_count

    def _get_page(self, request_content: str) -> list:
        """Method to scrape data from a single page of search results. Used
        iteratively by the `get_results` method to scrape data from every page
        returned by the search."""
        # Process the html:
        tree = html.fromstring(request_content)

        data_sel = '/html/body/script[5]/text()'
        script = tree.xpath(data_sel)[0]
        data = json.loads(re.search(r"window.jsonModel = (.*?)$", script).group(1))
        return data['properties']
        # properties = [flatten(x) for x in j['properties']]

        # db = sqlite_utils.Database("properties.db")
        # db["properties"].insert_all(
        #     properties,
        #     pk="id",
        #     replace=True
        # )

        # print(db)

        # # Store the data in a Pandas DataFrame:
        # data = [price_pcm, titles, addresses, weblinks, agent_urls]
        # data = data + [floorplan_urls] if get_floorplans else data
        # temp_df = pd.DataFrame(data)
        # temp_df = temp_df.transpose()
        # columns = ["price", "type", "address", "url", "agent_url"]
        # columns = columns + ["floorplan_url"] if get_floorplans else columns
        # temp_df.columns = columns

        # # Drop empty rows which come from placeholders in the html:
        # temp_df = temp_df[temp_df["address"].notnull()]

        # return temp_df

    def _get_results(self) -> list:
        """Build a Pandas DataFrame with all results returned by the search."""
        results = self._get_page(
            self._first_page)

        # Iterate through all pages scraping results:
        for p in range(1, self.page_count + 1, 1):

            # Create the URL of the specific results page:
            p_url = f"{str(self.url)}&index={p * 24}"

            # Make the request:
            status_code, content = self._request(p_url)

            # Requests to scrape lots of pages eventually get status 400, so:
            if status_code != 200:
                break

            results += self._get_page(content)

        with open(self._results_fpath, 'w') as f:
            json.dump(results, f)

        return results

    # @staticmethod
    # def _clean_results(results: pd.DataFrame):
    #     # Reset the index:
    #     results.reset_index(inplace=True, drop=True)

    #     # Convert price column to numeric type:
    #     results["price"] = results["price"].replace(regex=True, to_replace=r"\D", value=r"")
    #     results["price"] = pd.to_numeric(results["price"])

    #     # Extract short postcode area to a separate column:
    #     pat = r"\b([A-Za-z][A-Za-z]?[0-9][0-9]?[A-Za-z]?)\b"
    #     results["postcode"] = results["address"].astype(str).str.extract(pat, expand=True)[0]

    #     # Extract full postcode to a separate column:
    #     pat = r"([A-Za-z][A-Za-z]?[0-9][0-9]?[A-Za-z]?[0-9]?\s[0-9]?[A-Za-z][A-Za-z])"
    #     results["full_postcode"] = results["address"].astype(str).str.extract(pat, expand=True)[0]

    #     # Extract number of bedrooms from `type` to a separate column:
    #     pat = r"\b([\d][\d]?)\b"
    #     results["number_bedrooms"] = results["type"].astype(str).str.extract(pat, expand=True)[0]
    #     results.loc[results["type"].str.contains("studio", case=False), "number_bedrooms"] = 0
    #     results["number_bedrooms"] = pd.to_numeric(results["number_bedrooms"])

    #     # Clean up annoying white spaces and newlines in `type` column:
    #     results["type"] = results["type"].str.strip("\n").str.strip()

    #     # Add column with datetime when the search was run (i.e. now):
    #     now = datetime.datetime.now()
    #     results["search_date"] = now

    #     return results
