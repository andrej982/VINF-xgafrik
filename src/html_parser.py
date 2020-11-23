import re


class CustomHtmlParser:

    def __init__(self):
        self.content = ""
        self.start_tag = ""
        self.end_tag = ""
        self.params = {}

    def parse(self, data: str):
        """
        parse html string from input, get start tag, content and end tag (and all params within tags)

        :param data: html string to be parsed
        """

        start_tag_regex = "<.+?>"
        end_tag_regex = "</.+?>"
        content_regex = ">.*<"

        result_start = re.search(start_tag_regex, data)
        result_content = re.search(content_regex, data)
        result_end_tag = re.search(end_tag_regex, data)

        if result_start:
            # delete <,> from html line and split string into tags
            start_tag = result_start.group().replace("<", "").replace(">", "").split(" ")

            for index, param in enumerate(start_tag):
                # index 0 is start tag itself, all other elements are params within tag
                if index == 0:
                    self.start_tag = param
                elif param == '/':
                    continue
                else:
                    params = param.split("=")
                    self.params[params[0]] = params[1].replace('"', "")

        if result_end_tag:
            self.end_tag = result_end_tag.group().replace("</", "").replace(">", "")

        if result_content:
            self.content = result_content.group().replace("<", "").replace(">", "")

    def reset(self):
        """
        reset all params in parser
        """
        self.content = ""
        self.start_tag = ""
        self.end_tag = ""
        self.params = {}

    def parse_page(self, xml_string: str):
        """
        Function that parses page xml and returns a dictionary with all extracted parameters

        :param xml_string: whole xml wiki page string
        :return: dictionary with all extracted parameters
        """

        for parameter in ['title', 'ns', 'id', 'revision', 'timestamp', 'username', 'text', 'sha1']:

            regex = f"<{parameter}.*?>(.*?)</{parameter}>"
            result = re.search(regex, xml_string)
            self.params[parameter] = result.group(1) if result else ""

        pass
