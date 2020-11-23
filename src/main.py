import requests
import time
import glob
from elasticsearch import Elasticsearch
from src.html_parser import CustomHtmlParser


# TODO: proper API call to return wiki templates
def wiki_api(lang: str):
    """
    this function sends API request to wikipedia in order to get names of all template pages (for different language
    wikis, change prefix in url)

    :return:
    """

    with open(f"{lang}_templates.txt", "w", encoding="utf-8") as f:

        session = requests.Session()
        url = f"https://{lang}.wikipedia.org/w/api.php"

        params = {
            "action": "query",
            "format": "json",
            "prop": "info",
            "list": "allpages",
            # namespace 10 = template pages
            "apnamespace": 10,
            "aplimit": "max",
        }

        # get response with names of template pages, although aplimit is set to max, wiki will send only first 500 pages
        # and offset (apcontinue parameter) to create the next request
        response = session.get(url=url, params=params)
        data = response.json()
        print(data)
        f.writelines("\n".join([page['title'] for page in data['query']['allpages']]))
        counter = 1

        # keep sending requests while there are template pages, or until counter ends (each request returns 500
        # results, so 100 requests = 500,000 Template pages)
        while 'continue' in data and counter < 100:

            params['apcontinue'] = data['continue']['apcontinue']
            response = session.get(url=url, params=params)
            data = response.json()
            print(data)
            f.writelines("\n".join([page['title'] for page in data['query']['allpages']]))
            counter += 1


def parse_xml_file(file_lang: str, num_pages: int):
    es = Elasticsearch()

    myparser = CustomHtmlParser()
    template_translation = {
        "sk": "Šablóna",
        "cs": "Šablona",
        "en": "Template"
    }

    with open(f"../{file_lang}wiki-latest-pages-articles.xml", "r", encoding="utf8") as file:
        pages = 0
        namespaces = {}

        for line in file:
            # print(line.strip())

            # first, get namespace number of Template pages
            if "<namespaces>" in line:
                # print(f"namespace line: {line.strip()}")

                for namespace_line in file:
                    # print(namespace_line.strip())
                    myparser.reset()
                    myparser.parse(namespace_line)
                    if myparser.start_tag == 'namespace':
                        # get all namespace numbers from namespace html lines
                        namespaces[myparser.content] = myparser.params.get('key')

                    if "</namespaces>" in namespace_line:
                        template_namespace = namespaces[template_translation[file_lang]]
                        break

            if "<page>" in line:
                page_xml = ""
                # concatenate all lines of page into single html/xml string
                for page_line in file:

                    if "<page>" in page_line:
                        continue
                    if "</page>" in page_line:
                        myparser.reset()
                        myparser.parse_page(xml_string=page_xml)
                        pages += 1
                        # if parsed page is a template, then upload this template to elasticsearch
                        page_dict = myparser.params
                        if int(page_dict['ns']) == int(template_namespace):
                            pass
                            es.index(index="vi_index", id=1, body=page_dict)
                            print(f"Insert {page_dict['title']} namespace {page_dict['ns']}.")
                        break

                    page_xml += page_line.strip()

            if pages >= num_pages:
                print(f"Parsed {pages} pages from {file_lang}wiki.")
                break


if __name__ == "__main__":

    # get template names for all language versions of Wikipedia
    # for language in ['sk', 'cs']:
    #     wiki_api(language)

    for language in ['sk', 'cs']:
        parse_xml_file(language, 15000)
