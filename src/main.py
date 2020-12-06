import requests
import re
from elasticsearch import Elasticsearch
from src.html_parser import CustomHtmlParser


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

        # keep sending requests while there are template pages (each request returns 500 template pages)
        while 'continue' in data:
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
                            es.index(index="vi_index", id=pages, body=page_dict)
                            print(f"Insert {page_dict['title']} namespace {page_dict['ns']}.")
                        break

                    page_xml += page_line.strip()

            if pages >= num_pages:
                print(f"Parsed {pages} pages from {file_lang}wiki.")
                break


# global variables to count templates for stats
known_templates = []
template_count = 0


def check_template(name: str) -> bool:
    """
    function checks if given template name is really a template and not a false positive

    :param name: name of potential template parsed from text
    :return: bool value if function found given template
    """

    is_valid = False

    # if I found a new template, check if this template is in my file containing all EN templates, it may be
    # false positive, if the template is in the file, add it to global list, so that I don't have to
    # look for it again (while the program runs)
    if name in known_templates:
        is_valid = True
    else:
        # capitalize only first letter of name, because wikipedia has that naming convention
        name_match = name[0].upper() + name[1:]
        with open("en_templates.txt", "r", encoding="utf-8") as f:
            for line in f:
                if line == f"Template:{name_match}\n":
                    known_templates.append(name)
                    is_valid = True
                    break

    return is_valid


# number of caught false templates
false = 0


def remove_wikilinks(template: str) -> str:
    """
    function that finds all Wikilinks and replaces dangerous pipes with safe Wikilink(LINK)

    :param template: whole template
    :return: same template with replaced Wikilinks
    """

    wikilink_regex = "\[\[.*?\]\]"
    links = re.findall(wikilink_regex, template)
    for link in links:
        edited_link = link.split('|')[0].replace('[', '').replace(']', '')
        template = template.replace(link, f"Wikilink({edited_link})")
    return template


def get_template_info(template: str) -> str:
    """
    function gets template text and extracts template name and params

    :param template: raw template text, for example {{ date | 2020-12-24 | MDY}}
    :return: parsed template name and params as a string that won't match the regular expression
    """

    global template_count, false

    # remove parentheses from the beginning and end of template text
    template = template.replace("{", "").replace("}", "")

    # lambda function to transform integer to ordinal string, copied from
    # https://stackoverflow.com/questions/9647202/ordinal-numbers-replacement
    ordinal = lambda n: "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])

    name = ''
    params = []

    # remove dangerous wikilinks, they sometimes contain pipes that will mess up template parsing, for example
    # [[Android (operating system)|Android]]
    template = remove_wikilinks(template)

    for index, item in enumerate(template.split('|')):
        # name of the template is always first item
        if index == 0:
            name = item.strip()
            template_check = check_template(name)
            # if checked template is not valid, return with message
            if not template_check:
                print(f"False positive Template found: {name}")
                false += 1
                return f"False positive Template"
        # then we can parse template parameters
        else:
            param = item.split('=')
            if len(param) > 1:
                params.append(f"{param[0].strip()}: {param[1].strip()}")
            else:
                params.append(f"{ordinal(index)} (unnamed): {param[0].strip() if param[0] else None}")

    tmplt = f"ParsedTemplate(name is {name}, params are {params if params else None})"
    print(f"Found template {name} with parameters: {'' if len(params) > 1 else None}")
    for param in params:
        print(f"\t\t{param}")
    template_count += 1
    return tmplt


def parse_templates(input_text: str):
    # regular expression that matches template that doesn't contain other templates (doesn't contain { or }), because
    # we want to parse the innermost templates first
    regex_innermost_template = "{{[^{}]*}}"
    matched_templates = re.findall(regex_innermost_template, input_text)

    while matched_templates:
        # iterate over found templates and replace them inside mediawiki text, so that they can't be found again
        for template in matched_templates:
            input_text = input_text.replace(template, get_template_info(template=template))

        # input_text = re.sub(regex_innermost_template, "test", input_text)
        matched_templates = re.findall(regex_innermost_template, input_text)
    # print(input_text)
    print("", f"Stats:\tTemplates found: {template_count}", f"\t\tUnique templates identified: {len(known_templates)}",
          f"\t\tFalse positives: {false}", sep='\n')


def get_wiki_text():
    """
    function waits for mediaWiki text input and constructs a single line string that is then sent into parse function
    """

    # read text until User inputs "exit!"
    print("Insert mediawiki text and press Enter:")
    lines = []
    while True:
        line = input()
        if line == 'exit!':
            break
        else:
            lines.append(line)
    # reconstruct mediawiki text from multiple lines and replace multiple whitespaces for one, so we have only one
    # line string
    text = '\n'.join(lines)
    text = ' '.join((text.replace("\n", " ")).split())
    # print(text)
    parse_templates(input_text=text)


if __name__ == "__main__":
    # get template names for all language versions of Wikipedia
    # for language in ['en']:
    #     wiki_api(language)

    # for language in ['en']:
    #     parse_xml_file(language, 150000)

    get_wiki_text()
