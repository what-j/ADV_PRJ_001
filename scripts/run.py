import os
import time
import argparse
from datetime import datetime
from dateutil import parser
from newspaper import Article
from newspaper import Config
from newspaper import Source

import feedparser
import tempfile,zipfile
import csv,json,yaml,toml
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import requests
import re
import random
from pathlib import Path
from urllib.parse import urlparse
from shutil import copyfile
import html
import base64
import tldextract

from janome.tokenizer import Tokenizer
from sklearn.feature_extraction.text import TfidfVectorizer

def download_article_content(article_url, news_date):
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:78.0) Gecko/20100101 Firefox/78.0'
    config = Config()
    # src_url = Source(article_url)

    config.browser_user_agent = user_agent
    config.language = 'ja'
    config.request_timeout = 10
    config.number_threads = 10

    article = Article(article_url, config=config, keep_article_html=True)
    print(article)
    # article.set_html(article.html.encode('utf-8', 'ignore').decode('utf-8'))
    article.download()
    article.parse()

    # soup = BeautifulSoup(article.html, 'html.parser')
    # decoded_html = html.unescape(str(soup))
    # article.set_html(decoded_html)
    # article.parse()
    # if article.publish_date.strftime('%Y-%m-%dT%H:%M:%S%z') == str(news_date):

    return article


def extract_article_id(url):
    parsed_url = urlparse(url)
    path_segments = parsed_url.path.strip('/').split('/')
    article_id = path_segments[-1] if path_segments else None

    return article_id

def generate_filename(site_name, url):
    article_id = extract_article_id(url)
    timestamp = datetime.now().timestamp()
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    # file_name = f"{site_name.split('.')[0]}_{article_id}.md"
    file_name = f"{timestamp}.md"
    return file_name

def get_metadata(article_url):
    try:
        response = requests.get(article_url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # document_id_meta =  soup.find('meta', attrs={'name': 'id'})
        published_time_meta = soup.find('meta', property='article:published_time')['content'] if soup.find('meta', property='article:published_time') else None
        categories_meta = soup.find_all('meta', property='article:section')
        tags_meta = soup.find_all('meta', property='article:tag')
        keywords_meta = soup.find('meta', attrs={'name': 'keywords'})

        metadata = {
            # 'document_id': document_id_meta,
            'published_time': published_time_meta,
            'categories': [],
            'tags': [],
            'keywords': [],
        }

        for meta in categories_meta:
            metadata['categories'].extend([cat.strip() for cat in re.split(r'[/,]', meta['content'])])

        for meta in tags_meta:
            metadata['tags'].extend([tag.strip() for tag in re.split(r'[/,]', meta['content'])])

        if keywords_meta:
            metadata['keywords'] = [kw.strip() for kw in re.split(r'[/,]', keywords_meta['content'])]


        metadata['categories'] = metadata['categories'][:3]
        metadata['tags'] = metadata['tags'][:3]
        metadata['keywords'] = metadata['keywords'][:3]

        return metadata
    except Exception as e:
        print(f"Error retrieving metadata for {article_url}: {e}")
        return {}

def generate_hugo_posts(rss_urls, site_no, site_name, article_urls, output_dir, news_date, wordlist):
    articles_list = []
    now = datetime.now()

    output_image_dir = os.path.join(output_dir, '../images')
    os.makedirs(output_image_dir, exist_ok=True)

    # alt_image_path = Path('assets/images/alt.png')
    # alt_image_copy_path = os.path.join(output_image_dir, 'alt.png')
    # copyfile(alt_image_path, alt_image_copy_path)
    print(article_urls)

    for index, article_url in enumerate(article_urls):
        entry = {}
        article = {}
        ts = now.timestamp()
        file_name = generate_filename(site_name, article_url)
        file_path = os.path.join(output_dir, file_name)
        try:
            entry = download_article_content(article_url, news_date)

            metadata = get_metadata(article_url)
            print(metadata)
            # article['document_id'] = metadata['document_id']
            article['categories'] = metadata['categories']
            article['tags'] = metadata['tags']
            article['keywords'] = metadata['keywords']

            if metadata['published_time'] is not None:
                article['publish_date'] = metadata['published_time']
            elif entry.publish_date is not None:
                article['publish_date'] = entry.publish_date.strftime('%Y-%m-%dT%H:%M:%S%z')
            else:
                article['publish_date'] = ''

            article['short_url'] = site_name
            article['full_url'] = article_url
            article['author'] = entry.authors
            article['title'] = entry.title
            article['body'] = entry.article_html
            article['summary'] = entry.summary
            article['keywords'] = entry.keywords
            article['image_url'] = entry.top_image
            article['images'] = entry.images
            article['movies'] = entry.movies

            article['popular'] = random.randint(1, 2000)
            article['latest'] = random.randint(1, 2000)
            article['trend'] = random.randint(1, 2000)
            article['featured'] = random.randint(1, 2000)
            article['views'] = random.randint(1, 2000)
            article['comments'] = random.randint(1, 200)
            article['weight'] = random.randint(1, 20)


            # Download image
            # ext = os.path.splitext(urlparse(article['image_url']).path)[-1]
            # image_file_name = f"{ts}_{site_no :04d}_{index + 1 :03d}{ext}"
            # image_file_path = os.path.join(output_image_dir, image_file_name)

            # response = requests.get(article['image_url'])
            # if response.status_code == 200:
            #     with open(image_file_path, 'wb') as file:
            #         file.write(response.content)
            #     article['image_url'] = image_file_path
            # else:
            #     print(f"Failed to download image from {article['image_url']}")
            #     article['image_url'] = alt_image_copy_path

            # relative_path = os.path.relpath(article['image_url'], start=output_dir)
            # article['image_url'] = relative_path

            # print(article['image_url'])


            articles_list.append(article)

            title = safe_yaml(article['title'], wordlist)
            # images = safe_yaml(article['images'])
            # videos = safe_yaml(article['movies'])
            body = safe_yaml(html.unescape(article['body']), wordlist)
            full_url = safe_yaml(html.unescape(article['full_url']), wordlist)

            encoded_url = base64.urlsafe_b64encode(full_url.encode()).decode()

            if not article["tags"]:
                print(article["tags"])
                filter_dict = {
                    r'(.)\1+':'',
                    r'\d+': '',
                    r'([ぁ-んー])\1+': '',
                    r'([ァ-ンー])\1+': '',
                    r'[ぁ-んー]{2,}': '',
                    r'[ァ-ンー]{2,}': '',
                    r'[一-鿄]{1,2}': '',
                    r'\b[a-zA-Z]{1,2}\b': '',
                    # 'いる': '',
                    # 'ある': '',
                    # 'です': '',
                }

                tags = nlp_process(article["title"], filter_dict)
                encoded_tags = []
                for tag in tags:
                    encoded_tags.append(base64.urlsafe_b64encode(tag.encode()).decode())



            with open(file_path, 'w', encoding='utf-8') as f:
            # with open(file_path, 'w', encoding='cp932') as f:

                f.write(f'---\n')
                # f.write(f'published_time: "{article["published_time"]}"\n')  # FIX
                f.write(f'title: "{title}"\n')
                f.write(f'full_url: "{article["full_url"]}"\n')
                f.write(f'short_url: "{article["short_url"]}"\n')
                f.write(f'language: "ja"\n')
                f.write(f'date: {article["publish_date"]}\n')
                f.write(f'lastmod: \n')
                f.write(f'draft: false\n')
                f.write(f'author: {article["author"]}\n')
                # f.write(f'categories: {article["category_urls"]}\n')
                f.write(f'categories: {article["categories"]}\n')
                f.write(f'tags: {tags}\n')
                f.write(f'encoded_tags: {encoded_tags}\n')
                f.write(f'keywords: {article["keywords"]}\n')
                f.write(f'thumbnail: "{article["image_url"]}"\n')
                # f.write(f'images: "{images}"\n')
                # f.write(f'videos: "{videos}"\n')
                f.write(f'popular: {article["popular"]}\n')
                f.write(f'latest: {article["latest"]}\n')
                f.write(f'trend: {article["trend"]}\n')
                f.write(f'featured: {article["featured"]}\n')
                f.write(f'views: {article["views"]}\n')
                f.write(f'comments: {article["comments"]}\n')
                f.write(f'weight: {article["weight"]}\n')
                f.write(f'slug: {encoded_url}\n')
                f.write(f'---\n\n')
                f.write(f'![]({article["image_url"]})\n\n')
                # f.write(f'![]({article["movies"]})\n\n')
                f.write(f'{body}\n\n')
                f.write(f'({full_url})\n')

            print(f"🟢 New {site_name} in {file_path}.", end='\n\n')
        except Exception as e:
            print(f"🔴 Failed {site_name}.", end='\n\n')
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f'Delete {file_path}')
                except OSError as e:
                    print(f'Delete failed {e}')
            else:
                print(f'Not Exist {file_path}')
            print(e)

def safe_yaml(text, wordlist):
    char_mapping = {
        # ':': '\:',
        # '-': '\-',
        # '&': '\&',
        # "'": "\'",
        # '"': '\"',
        # '!': '\!',
        # '|': '\|',
        # '<br>':'',
        '"':'\'',
        ':':'',
        '\n': ' ',
        '\u3000': ' ',
    }

    exception_words = Interface.read_file(wordlist)
    items = exception_words.get('items')

    if items:
        exception_words = {}
        for item in items:
            if isinstance(item, dict):
                char_mapping.update(item)
        # char_mapping.update(exception_words)

    print(f'char_mapping: \n\n{char_mapping}')

    for char, replacement in char_mapping.items():
        text = text.replace(char, replacement)

    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'(<br>)+', '<br>', text)
    text = re.sub(r'\s+', ' ', text)

    exclusion_words = {
    }
    exw_file = None # TODO
    try:
        if exw_file:
            df = Interface.read_file(exw_file)
            df = df['items']
            for k, v in df:
                exclusion_words[k] = v
    except Exception as e:
        print(e)


    for word, _ in exclusion_words.items():
        print(word)
        text = text.replace(word, '')


    return text

def nlp_process(title, filter_dict, num_keywords=3):
    # 形態素解析
    tokenizer = Tokenizer()
    tokens = [token.surface for token in tokenizer.tokenize(title)]

    # 除外語フィルターを適用
    for pattern, replacement in filter_dict.items():
        tokens = [token if not re.search(pattern, token) else replacement for token in tokens]

    # 形態素をスペースで連結
    filtered_title = ' '.join(tokens)

    # TF-IDFベクトル化
    tfidf_vectorizer = TfidfVectorizer()
    tfidf_matrix = tfidf_vectorizer.fit_transform([filtered_title])

    # TF-IDF値が高いトークンを取得
    feature_names = tfidf_vectorizer.get_feature_names_out()
    sorted_indices = (-tfidf_matrix.toarray()[0]).argsort()[:num_keywords]  # 密な行列に変換してargsortを適用
    keywords = [feature_names[idx] for idx in sorted_indices]

    return keywords

def remove_old_hugo_posts(output_dir, max_posts=1000):
    files = os.listdir(output_dir)
    files.sort(key=lambda x: os.path.getctime(os.path.join(output_dir, x)))

    while len(files) > max_posts:
        file_to_delete = os.path.join(output_dir, files.pop(0))
        os.remove(file_to_delete)
        print(f"Removed old Hugo post: {file_to_delete}")

def random_sort_dict(input_dict):
    random_keys = list(input_dict.keys())
    random.shuffle(random_keys)

    shuffled_dict = {}
    for key in random_keys:
        shuffled_dict[key] = input_dict[key]

    return shuffled_dict

class Interface:

    def get_tempdir():
        timestamp = int(time.time())
        temp_dir = tempfile.mkdtemp()
        return timestamp, temp_dir

    def create_zip(filelist):
        if not filelist:
            return
        else:
            tmp_dir = os.path.dirname(filelist[0])
            tmp_fname = "tmp.zip"
            zip_name = os.path.join(tmp_dir, tmp_fname)
            with zipfile.ZipFile(zip_name, "w") as zipf:
                for file in filelist:
                    zipf.write(file, os.path.basename(file))
            return zip_name

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

    def read_raw(raw_file):
        with open(raw_file, 'r') as f:
            data = f.read()
        return {"items": [{'data': data}]}

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

    def read_file(fpath):
        if fpath.endswith('.csv'):
            data = Interface.read_csv(fpath)
        elif fpath.endswith('.json'):
            data = Interface.read_json(fpath)
        elif fpath.endswith('.opml'):
            data = Interface.read_opml(fpath)
            data = Interface.transform_opml_data(data)
        elif fpath.endswith('.toml'):
            data = Interface.read_toml(fpath)
        elif fpath.endswith('.yaml') or fpath.endswith('.yml'):
            data = Interface.read_yaml(fpath)
        elif fpath.endswith(''):
            data = Interface.read_raw(fpath)
        else:
            raise ValueError(f"Invalid file format: {fpath}")
        return data

def main():
    parser = argparse.ArgumentParser(description="Generate Hugo posts from article URLs.")
    parser.add_argument("-i", "--input_file", nargs="?", const=None, help="Path to the input JSON file")
    parser.add_argument("-o", "--output_dir", nargs="?", default="content/post", help="Output directory for Hugo posts")
    parser.add_argument("--news_date", default=datetime.now().strftime('%Y-%m-%dT%H:%M:%S%z'), help="News date")
    parser.add_argument("-l", "--limit", type=int, default=1, help="Limit the number of articles to process")
    parser.add_argument("-sl", "--site_limit", type=int, default=None, help="Limit of the number of websites to process")
    parser.add_argument("-r", "--random", action="store_true", help="Get random site order")
    parser.add_argument("-s", "--shuffle", action="store_true", help="[WIP] Shuffle output articles order")
    parser.add_argument("-w", "--wordlist", help="[WIP] Pass a wordlist of various purpose")
    parser.usage = f"""
    1. Execute the process without input file (use dict in script)

        python scripts/run.py -o content/post

    2. Specify both input and output files

        python scripts/run.py -i data/feeds.json -o content/post -l 3
    """

    args = parser.parse_args()

    rss_urls = {
    }

    if args.input_file:
        rss_df = Interface.read_file(args.input_file)
        df = rss_df['items']

        for item in df:
            site_name = item["name"]
            rss_url = item["feed_url"][0]  # TODO: multi feed for 1 name
            rss_urls[site_name] = rss_url

    if args.random:
        rss_urls = random_sort_dict(rss_urls)

    if args.shuffle:
        pass

    if args.site_limit:
        rss_urls = {k: v for k, v in list(rss_urls.items())[:args.site_limit]}

    print(rss_urls)

    for key, value in rss_urls.items():
        print(f"{key}: {value}")

    limit = 1
    if args.limit:
        limit = args.limit

    os.makedirs(args.output_dir, exist_ok=True)

    for site_no, (site_name, rss_url) in enumerate(rss_urls.items()):
        feed = feedparser.parse(rss_url)
        article_urls = [entry.link for entry in feed.entries[:limit]]
        generate_hugo_posts(rss_urls, site_no, site_name, article_urls, args.output_dir, args.news_date, args.wordlist)

    remove_old_hugo_posts(args.output_dir, max_posts=1000)


if __name__ == "__main__":
    main()