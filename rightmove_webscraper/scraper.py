import json
import re
from lxml import html
import requests
from concurrent.futures import ThreadPoolExecutor
import time

DETAIL_PAGE_PART = "https://www.rightmove.co.uk%s"
PROPERTY_URL_JSON_KEY = 'propertyUrl'
UA_HEADER = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

class RightmoveData:
    """The `RightmoveData` webscraper collects structured data on properties
    returned by a search performed on www.rightmove.co.uk

    An instance of the class provides attributes to access data from the search
    results, the most useful being `get_results`, which returns all results as a
    Pandas DataFrame object.

    The query to rightmove can be renewed by calling the `refresh_data` method.
    """

    def __init__(self, url: str, results_fpath: str, detail_results_fpath: str = '', detail_threaded: bool = False):
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
        self._detail_results = self._get_detail_results(detail_results_fpath, threaded=detail_threaded)

    @staticmethod
    def _request(url: str):
        r = requests.get(url, headers=UA_HEADER)
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
    def get_detail_results(self):
        return self._detail_results

    @property
    def results_count(self):
        """Total number of results returned by `get_results`. Note that the
        rightmove website may state a much higher number of results; this is
        because they artificially restrict the number of results pages that can
        be accessed to 42."""
        return len(self.get_results)

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
        data = json.loads(
            re.search(r"window.jsonModel = (.*?)$", script).group(1))
        return data['properties']

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

    def _get_detail_page(self, url: str):
        status_code, request_content = self._request(url)

        if status_code != 200:
            return None

        tree = html.fromstring(request_content)
        data_sel = '/html/body/script[2]/text()'
        s = tree.xpath(data_sel)[0]
        s = s.split('window.PAGE_MODEL = ')[1]
        s = s.split('.propertyData')[0]
        s = s.split('window.adInfo')[0].strip()
        data = json.loads(s)
        return data

    def _get_detail_results(self, fpath: str, threaded: bool = False) -> list:
        if not fpath:
            return []

        urls = [DETAIL_PAGE_PART % x[PROPERTY_URL_JSON_KEY]
                for x in self.get_results]

        t1 = time.perf_counter()
        if threaded:
            with ThreadPoolExecutor(max_workers=12) as executor:
                results = list(executor.map(self._get_detail_page, urls))
        else:
            results = [self._get_detail_page(x) for x in urls]
        t2 = time.perf_counter()
        print("Time taken to scrape detail: ", t2-t1)

        with open(fpath, 'w') as f:
            json.dump(results, f)

        return results
