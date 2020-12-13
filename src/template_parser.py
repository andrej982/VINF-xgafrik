import requests
import re
from os import path


def wiki_api(lang: str):
    """
    this function sends API request to wikipedia in order to get names of all template pages (for different language
    wikis, change prefix in url)

    :return:
    """

    if path.exists(f"{lang}_templates.txt"):
        print("Templates already collected.")
        return

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
                if line == f"Template:{name_match}\n" or line == f"Template:{name_match}/doc\n":
                    known_templates.append(name)
                    is_valid = True
                    break

    return is_valid


# number of caught false templates
false = 0

#
# def remove_wikilinks(template: str) -> str:
#     """
#     function that finds all Wikilinks and replaces dangerous pipes with safe Wikilink(LINK)
#
#     :param template: whole template
#     :return: same template with replaced Wikilinks
#     """
#
#     wikilink_regex = "\[\[.*?\]\]"
#     links = re.findall(wikilink_regex, template)
#     for link in links:
#         edited_link = link.replace('|', 'WikiLinkPipe()')
#         template = template.replace(link, edited_link)
#     return template


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

    # template is split along "|" characters to get all its parameters, but these "pipes" cant be inside [], because
    # then they would be a part of a wikilink that's inside current template
    parameters = re.split(r"\|(?![^\[\]]*])", template)

    for index, item in enumerate(parameters):
        # name of the template is always first item
        if index == 0:
            name = item.strip()
            template_check = check_template(name)
            # if checked template is not valid, return with message
            if not template_check:
                print(f"False positive Template found: {name}")
                false += 1
                return template
        # then we can parse template parameters
        else:
            # regex split for parameters that contain XML elements inside them (< and > parentheses)
            param = re.split(r'=(?![^<>]*>)', item)
            if len(param) > 1:
                params.append(f"{param[0].strip()}: {param[1].strip()}")
            else:
                params.append(f"{ordinal(index)} (unnamed): {param[0].strip() if param[0] else None}")

    tmplt = f"ParsedTemplate(name is {name}, params are {params if params else None})"
    print(f"Found template {name} with parameters: {'' if len(params) > 0 else None}")
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

    if not path.exists(f"en_templates.txt"):
        print("You need to collect templates from API first.")
        return

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


def print_menu():
    print("[1] Get Wikipedia Templates from API (lasts 8-10 minutes)")
    print("[2] Parse Templates from MediaWiki text")
    print("[0] Exit application")


if __name__ == "__main__":

    print_menu()
    option = input("Select an Option: ")

    while option != '0':
        if option == '1':
            wiki_api('en')
        elif option == '2':
            get_wiki_text()
        else:
            print("Invalid Input.")

        print()
        print_menu()
        option = input("Select an Option: ")
