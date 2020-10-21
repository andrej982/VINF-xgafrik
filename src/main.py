import requests
import xml.etree.ElementTree as ET
import time
import re


def wiki_api():
    session = requests.Session()

    url = "https://en.wikipedia.org/w/api.php"

    params = {
        "action": "query",
        "titles": "Albert Einstein",
        # "titles": 'Wikipedia',
        "prop": "templates",
        "format": "json",
        # "tlnamespace": 10
    }

    response = session.get(url=url, params=params)
    data = response.json()

    print(data)


def parse_xml_file(file_name: str, num_pages: int):

    with open(file_name, "r", encoding="utf8") as file:
        for line in file:
            print(line.lstrip())
            time.sleep(0.2)
            # first, get namespace number of Template pages
            if "<namespaces>" in line:
                regex = ">.*<"


if __name__ == "__main__":
    # for now, only parse english wikipedia

    # wiki_api()
    parse_xml_file("..\enwiki-latest-pages-articles.xml", 200)
