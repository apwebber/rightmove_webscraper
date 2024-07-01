
DELETE_KEYS = [
    "numberOfImages",
    "numberOfFloorplans",
    "numberOfVirtualTours",
    "countryCode",
    "premiumListing",
    "featuredProperty",
    "customer",
    "transactionType",
    "productLabel",
    "feesApplyText"
]
def format_properties_json(data: list) -> dict:
    """
    Format the properties json so that it contains only the useful data
    """

    def format_propert(x: dict) -> dict:


    return [format_propery(x) for x in data]
