import requests
import argparse
import csv
import yaml
import json
import toml
import xml.etree.ElementTree as ET
import tldextract
import pprint
import re
import sys
from bs4 import BeautifulSoup

def struct_data(url, params):
    data = {
        "name": '',
        "title": '',
        "url": '',
        "categories": 'エンタメ',
        "tags": [],
        "locale": "ja-jp",
        "limit": 1,
        }

    data.update(generate_name_from_url(url))
    data.update({"feed_url": find_rss_feeds(url, *params)})

    return data

def generate_name_from_url(url):
    # response = requests.get(url)
    top_domain = tldextract.extract(url).domain
    name = top_domain

    return {
        "name": name,
        "url": url,
    }

def get_metadata(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        metadata = {
            'title': '',
            'published_time': soup.find('meta', property='article:published_time')['content'] if soup.find('meta', property='article:published_time') else None,
            'categories': [],
            'tags': [],
            'keywords': [],
        }

        title_meta = soup.find('meta', attrs={'name': 'title'})
        categories_meta = soup.find_all('meta', property='article:section')
        tags_meta = soup.find_all('meta', property='article:tag')
        keywords_meta = soup.find('meta', attrs={'name': 'keywords'})

        if title_meta:
            metadata['title'] = [t.strip() for t in re.split(r'[/,]', title_meta['content'])]

        for meta in categories_meta:
            metadata['categories'].extend([cat.strip() for cat in re.split(r'[/,]', meta['content'])])

        for meta in tags_meta:
            metadata['tags'].extend([tag.strip() for tag in re.split(r'[/,]', meta['content'])])

        if keywords_meta:
            metadata['keywords'] = [kw.strip() for kw in re.split(r'[/,]', keywords_meta['content'])]

        metadata['title'] = metadata['title'][:3]
        metadata['categories'] = metadata['categories'][:3]
        metadata['tags'] = metadata['tags'][:3]
        metadata['keywords'] = metadata['keywords'][:3]

        return metadata
    except Exception as e:
        print(f"Error retrieving metadata for {url}: {e}")
        return {}

def find_rss_feeds(site_url, info=True, favicon=False, skip_crawl=False, opml=False):
    base_url = "https://feedsearch.dev/api/v1/search"
    params = {
        "url": site_url,
        "info": str(info).lower(),
        "favicon": str(favicon).lower(),
        "skip_crawl": str(skip_crawl).lower(),
        "opml": str(opml).lower(),
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()

        if response.text:
            feeds = [feed['url'] for feed in response.json()]
            print(f'🟢 processing completed {site_url}')
            print(feeds)
            print()
            return feeds
        else:
            print(f"🔴 No JSON data received for {site_url}")
            return []

    except requests.exceptions.HTTPError as http_err:
        print(f"🔴 HTTP error occurred: {http_err}")
        return []
    except Exception as e:
        print(f"🔴 Error searching for feeds: {e}")
        return []

class Interface:

    def read_csv(csv_file):
        feeds = []
        with open(csv_file, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                feeds.append(row)
        data = {"items": feeds}
        return data

    def read_json(json_file):
        with open(json_file, 'r') as f:
            data = json.load(f)
        return data

    def read_yaml(yaml_file):
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
        return data

    def read_toml(toml_file):
        with open(toml_file, 'r') as f:
            data = toml.load(f)
        return data

    def read_xml(xml_file):
        data = {}
        tree = ET.parse(xml_file)
        root = tree.getroot()

        for child in root:
            data[child.tag] = child.text

        return data

    def read_opml(opml_file):
        feeds = []
        tree = ET.parse(opml_file)
        root = tree.getroot()
        body = root.find('body')

        for outer_outline in body.findall('outline'):
            # Process the inner outlines
            for inner_outline in outer_outline.findall('outline'):
                feed = dict(inner_outline.attrib)  # Extract all attributes of the inner outline
                feeds.append(feed)

                # console.print(f'+++ {feed["url"]}')

        data = {"items": feeds}
        return data

    def transform_opml_data(data):
        def walk(data):
            if isinstance(data, dict):
                filtered_data = {key: value for key, value in data.items() if value is not None}
                return {key: walk(value) for key, value in filtered_data.items()}
            elif isinstance(data, list):
                return [walk(item) for item in data]
            else:
                return data

        items = []
        _data = walk(data)
        for obj in _data["items"]:
            item = {
                "text": obj.get("text"),
                "type": obj.get("type"),
                "title": obj.get("title"),
                "url": obj.get("xmlUrl"),   # This is target_url
                "htmlUrl": obj.get("htmlUrl")
            }
            items.append(item)

        data = {"items": items}
        return data

    def read_raw(raw_file):
        with open(raw_file, 'r') as f:
            data = f.read()
        return {"items": [{'data': data}]}

    def read_file(fpath):
        if fpath.endswith('.csv'):
            data = Interface.read_csv(fpath)
        elif fpath.endswith('.json'):
            data = Interface.read_json(fpath)
        elif fpath.endswith('.yaml') or fpath.endswith('.yml'):
            data = Interface.read_yaml(fpath)
        elif fpath.endswith('.toml'):
            data = Interface.read_toml(fpath)
        elif fpath.endswith('.xml'):
            data = Interface.read_xml(fpath)
        elif fpath.endswith('.opml'):
            data = Interface.read_opml(fpath)
            data = Interface.transform_opml_data(data)
        elif fpath.endswith(''):
            data = Interface.read_raw(fpath)
        else:
            raise ValueError(f"Invalid file format: {fpath}")
        return data

    def write_csv(data, path):
        with open(path, 'w', encoding='utf-8-sig', newline='') as csvfile:

            fieldnames = data[0].keys()

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for feed_obj in data:
                writer.writerow(feed_obj)

    def write_json(data, path):
        data = {"items": data}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def write_yaml(data, path):
        with open(path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def write_toml(data, path):
        with open(path, 'w', encoding='utf-8') as f:
            toml.dump(data, f)

    def write_xml(data, path, root_element="root"):
        def to_xml(data):
            xml_string = '<?xml version="1.0" encoding="UTF-8"?>\n'
            xml_string += f'<{root_element}>\n'
            for key, value in data.items():
                xml_string += f'  <{key}>{value}</{key}>\n'
            xml_string += f'</{root_element}>'
            return xml_string

        try:
            xml_data = to_xml(data)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(xml_data)
        except Exception as e:
            print("Error while writing to file:", str(e))

    def write_opml(data, path):
        def to_opml(data):
            opml_string = '<?xml version="1.0" encoding="UTF-8"?>\n<opml version="1.0">\n<head>\n<title>My OPML</title>\n</head>\n<body>\n'
            for feed in data:
                opml_string += f'<outline type="rss" text="{feed}" />\n'
            opml_string += '</body>\n</opml>'
            return data
        try:
            data = to_opml(data)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(data)
        except Exception as e:
            print("Error while writing to file:", str(e))

    def write_raw(data, path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(data, f)

    def write_file(fpath, result):
        if fpath.endswith('.csv'):
            Interface.write_csv(result, fpath)
        elif fpath.endswith('.json'):
            Interface.write_json(result, fpath)
        elif fpath.endswith('.yaml') or fpath.endswith('.yml'):
            Interface.write_yaml(result, fpath)
        elif fpath.endswith('.toml'):
            Interface.write_toml(result, fpath)
        elif fpath.endswith('.xml'):
            Interface.write_xml(result, fpath)
        elif fpath.endswith('.opml'):
            Interface.write_opml(result, fpath)
        elif fpath.endswith(''):
            Interface.write_raw(result, fpath)
        else:
            raise ValueError(f"Invalid file format: {fpath}")


def main():
    logotext = f"""
    _____             _   ____                      _
    |  ___|__  ___  __| | / ___|  ___  __ _ _ __ ___| |__   ___ _ __
    | |_ / _ \/ _ \/ _` | \___ \ / _ \/ _` | '__/ __| '_ \ / _ \ '__|
    |  _|  __/  __/ (_| |  ___) |  __/ (_| | | | (__| | | |  __/ |
    |_|  \___|\___|\__,_| |____/ \___|\__,_|_|  \___|_| |_|\___|_|
    """
    print(logotext)

    parser = argparse.ArgumentParser(description="Fetch valid RSS feed URLs using the Feedsearch API.")
    parser.add_argument('input_file', type=str, nargs='?', default=None, help='Input file with a list of URLs')
    parser.add_argument('output_file', type=str, nargs='?', default=None, help='Output path')
    # parser.add_argument("df", help="Path to the Dataframe file (json,yaml,toml,etc) containing a list of URLs")
    parser.add_argument("--info", type=bool, default=True, help="Return feed metadata (default: True)")
    parser.add_argument("--favicon", type=bool, default=False, help="Return favicon as Data URI (default: False)")
    parser.add_argument("--skip_crawl", type=bool, default=False, help="Skip crawl and return saved feeds (default: False)")
    parser.add_argument("--opml", type=bool, default=False, help="Return feeds as OPML XML string (default: False)")

    parser.usage =f"""
    1. Input URL as list ( separated with newline )
    python feedsearcher.py input.txt

    2. Input URL as dataframe ( [ csv/json/yaml/toml ])
    python feedsearcher.py input.yaml output.yaml
    """
    args = parser.parse_args()

    result = {}

    if args.input_file:
        file_extension = args.input_file.lower().split('.')[-1]

        if file_extension in ['csv', 'json', 'yaml', 'yml', 'toml', 'xml', 'opml']:
            data = Interface.read_file(args.input_file)
            urls = [item["url"] for item in data.get("items", [])]
        else:
            with open(args.input_file, 'r') as file:
                urls = [line.strip() for line in file.readlines()]
    else:
        urls = []
        print("Enter URLs separated by newline (Ctrl+D to finish):")
        try:
            while True:
                url = input()
                urls.append(url)
        except EOFError:
            pass


    common_params = {
        'info': args.info,
        'favicon': args.favicon,
        'skip_crawl': args.skip_crawl,
        'opml': args.opml
    }

    items = list(map(lambda url: struct_data(url, common_params), urls))
    result = {'items': items}

    pprint.pprint(result)
    if args.output_file:
        Interface.write_file(args.output_file, result)
        print()
        print(f'🔵 Done output to {args.output_file}')


if __name__ == "__main__":
    main()
