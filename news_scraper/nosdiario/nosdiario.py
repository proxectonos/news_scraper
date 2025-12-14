"""
Parse data from NÓS Diário using XML files
"""
import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from lxml import html as h
from news_scraper.html_content import (
    clean_html_body, clean_html_abstract, prepare_html
)
from news_scraper.request import Request

logger = logging.getLogger(__name__)


class NosDiario():
    """
    Class to download and parse articles from NÓS Diario.
    """
    def __init__(self, config):
        self.config = config
        self.url = None
        self.r = Request()
        self.articles_ok = 0
        self.articles_error = 0
        self.articles_exists = 0

    def download(self, url):
        """
        Descarrega o XML duma nova.

        :params: url: URL da nova
        :returns: ficheiro XML da nova
        """
        raise NotImplementedError("Download method is not implemented yet.")

    def parse(self, xml_files):
        """
        Parsea o HTML duma nova e extrae os dados relevantes.

        :params: html_file: ficheiro HTML da nova
        :returns: none:
        """
        for xml_path in xml_files:
            logger.info("Parsing file: %s", xml_path)
            doc = {}

            if xml_path.stat().st_size == 0:
                logger.warning("Skipping empty file: %s", xml_path)
                continue

            try:
                root = ET.parse(xml_path)
                tree = root.getroot()
            except ET.ParseError as e:
                logger.error("Error parsing XML file %s: %s", xml_path, e)
                continue

            doc.update({"metadata": self._get_metadata(tree)})
            news = self._parse_article(tree)
            if not news:
                logger.error("Error parsing article in file %s", xml_path)
                self.articles_error += 1
                continue

            url = self._get_url(tree, news["categories"][0])
            if url:
                doc["metadata"]["url"] = url

            doc.update({"news": news})
            doc.update({"source_xml": str(xml_path.name)})
            self._write_json(doc, xml_path)
            self.articles_ok += 1

    def _parse_article(self, tree):
        """
        Parse article data from the XML tree.

        :param tree: XML document
        :returns: Dictionary with extracted article data
        """
        data = {}

        headline = self._get_headlines(tree)
        subheadline = self._get_subheadlines(tree)

        if headline:
            data["headline"] = headline
        if subheadline:
            data["subheadline"] = subheadline

        categories = self._get_categories(tree)
        if len(categories) < 1:
            logging.warning("No categories found in XML file")
            return {}
        data["categories"] = categories

        abstract = self._get_abstract(tree)
        if abstract:
            data["abstract"] = abstract

        body_html = self._get_html_body(tree)
        if not body_html.strip():
            return None
        related, body_html = self._get_related(body_html)
        data["body_html"] = body_html
        body = self._get_body(body_html)
        data["body"] = body
        if related:
            data["related"] = related

        if not abstract and not body:
            return None

        keywords = self._get_keywords(tree)
        if keywords:
            data["keywords"] = sorted(list(keywords), key=str.lower)

        # Images
        images = self._get_images(tree)
        if images:
            data["images"] = images

        return data

    def _get_metadata(self, tree):
        """
        Extract metadata from the XML root element.
        :param tree: XML document
        :returns: Dictionary with metadata
        """
        return {
            "news_item_id": tree.findtext(".//NewsIdentifier/NewsItemId"),
            "first_created": tree.findtext(".//NewsManagement/FirstCreated"),
            "first_published": tree.findtext(
                ".//NewsManagement/FirstPublished"),
            "this_revision_created": tree.findtext(
                ".//NewsManagement/ThisRevisionCreated"),
        }

    def _get_headlines(self, tree):
        """
        Extract headline from the XML root element.

        :param tree: XML root element
        :returns: str: headline
        """
        return tree.findtext(".//NewsLines/HeadLine")

    def _get_subheadlines(self, tree):
        """
        Extract subheadline from the XML root element.

        :param tree: XML root element
        :returns: str: subheadline
        """
        return tree.findtext(".//NewsLines/SubHeadLine")

    def _get_categories(self, tree):
        """
        Extract categories from the XML root element.
        :param tree: XML root element
        :returns: Set of categories
        """
        categories = set()
        for category in tree.findall(".//Property"):
            if category.attrib.get("FormalName") == "Tesauro":
                categories.add(category.attrib.get("Value"))
        return list(categories)

    def _get_url(self, tree, category):
        """
        Construct the URL for the news article.
        :param tree: XML root element
        :param category: Category of the news article
        :returns: Constructed URL as a string
        """
        uid = tree.findtext(".//NewsIdentifier/NewsItemId")
        date_id = tree.findtext(
            ".//NewsIdentifier/DateId").split("+")[0].replace("T", "")

        return (
            f"{self.config["base_url"]}/articulo/"
            f"{category}/-/{date_id}{uid}.html"
        )

    def _get_abstract(self, tree):
        """
        Extract the abstract from the XML root element.
        :param tree: XML root element
        :param xml_path: Path to the XML file
        :returns: abstract as a string
        """
        abstract = ""
        abstract_html = tree.findtext(
            ".//ContentItem[@type='article']/DataContent/nitf/body/body.head/abstract/p"  # noqa
        ) or tree.findtext(
            ".//abstract/p"
        )

        if abstract_html:
            raw_abstract = prepare_html(abstract_html)
            try:
                abstract = clean_html_abstract(raw_abstract.strip())
                if not abstract:
                    raise RuntimeError("abstract is empty after cleaning.")
            except RuntimeError as e:
                logger.warning("Error cleaning abstract in %s: %s", e, e)

        return abstract

    def _get_html_body(self, tree):
        """
        Extract the raw HTML body from the XML root element.
        :param tree: XML root element
        :returns: Raw HTML body as a string
        """
        body_html = tree.findtext(
            ".//ContentItem[@type='article']/DataContent/nitf/body/body.content"  # noqa
        ) or tree.findtext(
            ".//body.content"
        )
        return body_html

    def _get_body(self, body_html):
        """
        Extract the body from the XML root element.
        :param body_html: XML root element
        :param xml_path: Path to the XML file
        :returns: Tuple with cleaned body and raw HTML body
        """
        body = ""
        raw_body = prepare_html(body_html)
        try:
            body = clean_html_body(raw_body)
        except RuntimeError as e:
            logger.error("Error cleaning body in XML file %s: %s", e, e)

        return body

    def _get_related(self, body):
        """
        Extract related articles from the HTML body
        :param body: HTML body content (str)
        :returns: List of related articles and cleaned body
        """
        related_uris = []
        doc = h.fromstring(f"<html><body>{body}</body></html>")

        for div in doc.xpath("//div[contains(@class, 'related-content')]"):
            for a in div.xpath(".//ul//a"):
                href = a.get("href")
                text = "".join(a.itertext()).strip()
                if href:
                    related_uris.append(
                        {
                            "link": f"{self.config['base_url']}{href}",
                            "title": text,
                            "newsid": self._get_newsid(href)
                        }
                    )

            parent = div.getparent()
            if parent is not None:
                parent.remove(div)

        body = h.tostring(doc, encoding="unicode").replace(
            "<html><body>", "").replace("</body></html>", "")

        return related_uris, body

    def _get_newsid(self, url):
        """
        Extract the news ID from the URL.
        :param url: URL string
        :returns: News ID as a string
        """
        return url.split("/")[-1].replace(".html", "")[14:]

    def _get_keywords(self, tree):
        """
        Extract keywords from the XML root element.
        :param tree: XML root element
        :returns: Set of keywords
        """
        keywords = set()
        for kw in tree.findall(".//keyword"):
            keywords.update(
                [k.strip() for k in kw.attrib.get("key").split(",")])
        return keywords

    def _get_images(self, tree):
        """
        Extract images from the XML root element.
        :param tree: XML root element
        :returns: List of image dictionaries
        """
        images = []
        for newscomponent in tree.findall(".//NewsComponent"):
            if newscomponent.get("Duid", "").endswith(".photos"):
                images = self._get_photo_urls(newscomponent)

        return images

    def _get_photo_urls(self, component):
        """
        Extract photo URLs and captions from the given NewsComponent.
        :param component: XML element representing the NewsComponent
        :returns: List of dictionaries with 'href' and 'caption' keys
        """
        images = []
        img_url = set()
        img_caption = set()

        for subc in component.findall(".//NewsComponent"):
            if subc.get("Duid", "").endswith(".file"):
                img_url.add(subc.find(
                    ".//ContentItem[@Href]").get("Href").strip())
            elif subc.get("Duid", "").endswith(".text"):
                img_caption.add(subc.findtext(
                    ".//DataContent/nitf/body/body.content/p").strip())
            elif subc.get("Duid", "").endswith(".text"):
                img_caption.add(subc.findtext(
                    ".//DataContent/nitf/body/body.head/abstract/p").strip())
        if len(img_url) == len(img_caption) and len(img_url) > 0:
            for href, caption in zip(img_url, img_caption):
                images.append({
                    "url": href,
                    "caption": caption
                })

        return images

    def _write_json(self, doc, xml_file):
        """
        Escreve o documento JSON na saída estándar.

        :params: doc: documento a escrever
        """
        dst = Path(
            self.config["corpus"]) / xml_file.relative_to(
                Path(self.config["source"])
            ).with_suffix(".json")
        dst.parent.mkdir(parents=True, exist_ok=True)

        dst.write_text(
            json.dumps(doc, ensure_ascii=False, indent=4), encoding="utf-8")
