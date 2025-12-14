"""
Class to download and parse data from Praza Pública.
"""
import hashlib
import json
import logging
from pathlib import Path
from lxml import html as h
from news_scraper.html_content import clean_html_body
from news_scraper.request import Request, RequestError


CATEGORIES = {
    "Política": "https://praza.gal/politica/todo?p={}",
    "Deportes": "https://praza.gal/deportes/todo?p={}",
    "Ciencia e tecnoloxía": "https://praza.gal/ciencia-e-tecnoloxia/todo?p={}",
    "Acontece": "https://praza.gal/acontece/todo?p={}",
    "Cultura": "https://praza.gal/cultura/todo?p={}",
    "Lecer": "https://praza.gal/lecer/todo?p={}",
    "Mundo": "https://praza.gal/mundo/todo?p={}",
    "Economía": "https://praza.gal/economia/todo?p={}",
    "Movementos sociais": "https://praza.gal/movementos-sociais/todo?p={}"
}

logger = logging.getLogger(__name__)


class Praza():
    """
    Class to download and parse articles from Praza Pública.
    """
    def __init__(self, config):
        self.config = config
        self.categories = CATEGORIES.keys()
        self.url = None
        self.r = Request()
        self.articles_ok = 0
        self.articles_error = 0
        self.articles_exists = 0

    def download_from_category(self, category):
        """
        Download all articles in a given category.
        :params: category: category to download
        :returns: None
        """
        if category not in self.categories:
            raise ValueError(f"Invalid category: {category}")

        page = 1
        try:
            response = self.r.fetch(CATEGORIES[category].format(page))
        except RequestError as e:
            logger.error("Error downloading category: %s", e)

        tree = h.fromstring(response)
        last_page = self._get_category_end(tree)
        logger.info("Category %s with %d pages", category, last_page)

        self._get_articles_in_page(tree)
        logger.info("Finished page %d", page)
        for page in range(2, last_page + 1):
            try:
                response = self.r.fetch(CATEGORIES[category].format(page))
            except RequestError as e:
                logger.error("Error downloading category page: %s", e)

            tree = h.fromstring(response)
            self._get_articles_in_page(tree)
            logger.info("Finished page %d", page)
        logger.info(
            "Category %s: downloaded %d articles (%d skipped) with %d errors",
            category,
            self.articles_ok + self.articles_exists,
            self.articles_exists,
            self.articles_error
        )

    def parse(self, html_files):
        """
        Parsea o HTML duma nova e extrae os dados relevantes.

        :params: html_file: ficheiro HTML da nova
        :returns: none:
        """
        for html_file in html_files:
            logger.info("Parsing file: %s", html_file)
            doc = {}

            try:
                html_content = self._get_content(html_file)
            except Exception as e:
                logger.error("%s", e)
                self.articles_error += 1
                continue

            try:
                tree = h.fromstring(html_content)
            except Exception as e:
                logger.error("Error parsing HTML content: %s", e)
                self.articles_error += 1
                continue

            doc.update({"metadata": self._get_metadata(tree)})

            news = self._parse_article(tree)
            if not news:
                logger.error("Error parsing article in file %s", html_file)
                self.articles_error += 1
                continue

            doc.update({"news": news})
            doc.update({"source": str(html_file)})

            self._write_json(doc, html_file)
            self.articles_ok += 1

    def _write_json(self, doc, html_file):
        """
        Escreve o documento JSON na saída estándar.

        :params: doc: documento a escrever
        """
        dst = Path(
            self.config["corpus"]) / html_file.relative_to(
                Path(self.config["source"])
            ).with_suffix(".json")
        dst.parent.mkdir(parents=True, exist_ok=True)

        dst.write_text(
            json.dumps(doc, ensure_ascii=False, indent=4), encoding="utf-8")

    def _get_related(self, tree):
        """
        Extrae as novas relacionadas.

        :params: tree: árvore do artigo
        :returns: list: URLs das novas relacionadas
        """
        related = []
        if not tree:
            return related

        for link in tree[0].xpath(".//h1[contains(@class, 'ref-title')]/a"):
            href = link.get("href").strip()
            text = link.xpath(".//text()")[0].strip()
            related.append(
                {
                    "link": self.config["base_url"] + href,
                    "title": text,
                    "news_item_id": self._get_id(
                        self.config["base_url"] + href)
                }
            )

        return related

    def _parse_article(self, tree):
        """
        Parsea o contido HTML dunha nova.

        :params: tree: árvore do artigo
        :returns: dict: datos extraídos
        """
        data = {}

        title = self._get_title(tree)
        abstract = self._get_abstract(tree)
        category, topics, loc = self._get_categories(
            tree.xpath("//article[@id='article']//ul")
        )
        related = self._get_related(tree.xpath(
            ".//ul[contains(@class, 'at-archive-refs-list')]")
        )
        body_html = self._get_htmlbody(tree)
        if body_html is None:
            return None

        body = self._get_bodytext(tree)
        if body is None:
            return None
        images = self._get_images(tree)

        data.update(
            {
                "headline": title,
                "abstract": abstract,
                "taxonomy": {
                    "categories": [category],
                    "topics": topics,
                    "local-edition": loc
                },
                "body_html": body_html,
                "body": body,
                "related": related,
                "images": images
            }
        )

        return data

    def _get_htmlbody(self, tree):
        """
        Extrae o contido HTML da nova.

        :params: tree: árvore do artigo
        :returns: str: contido HTML extraído
        """
        article_body = tree.xpath("//div[contains(@class, 'article-body')]")
        if article_body:
            return h.tostring(article_body[0], encoding="unicode")
        logger.warning("No article body found in article %s", self.url)

        return None

    def _get_bodytext(self, tree):
        """
        Extrae o contido en texto da nova.

        :params: tree: árvore do artigo
        :returns: str: conteúdo do texto extraído
        """
        try:
            body = clean_html_body(h.tostring(tree, encoding="unicode"))
        except RuntimeError as e:
            logger.error("Error cleaning HTML body: %s", e)
            return None

        return body

    def _get_images(self, tree):
        """
        Extrae as imagens da nova.

        :params: tree: árvore do artigo
        :returns: list: URLs das imagens extraídas
        """
        images = []
        for fig in tree.xpath("//figure[contains(@class, 'at-image')]"):
            caption = fig.xpath(".//figcaption//text()")
            if caption:
                caption = caption[0].strip()
            link = fig.xpath(".//a[@href]")
            if link:
                images.append({
                    "url": link[0].get("href"),
                    "caption": caption or None
                })

        return images

    def _get_categories(self, article):
        """
        Extrae as categorías da nova.

        :params: article: árvore do artigo
        :returns: list: categorias extraídas
        """
        topics = []
        loc = None
        category = None
        if article:
            article = article[0]

        for link in article.xpath(".//a"):
            cls = link.get("class", "")
            if cls == "topic":
                topics.append(link.text_content().strip())
            elif cls == "area":
                category = link.text_content().strip()
            elif cls == "local-edition":
                loc = link.text_content().strip()
        return category or "", topics or "", loc or ""

    def _get_content(self, html_file):
        """
        Lê o conteúdo HTML dende o ficheiro.

        :params: html_file: ficheiro HTML
        :returns: str: conteúdo HTML
        """
        try:
            with html_file.open("r", encoding="utf-8") as f:
                return f.read()
        except OSError as e:
            raise OSError(f"Error reading HTML file {html_file}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error reading {html_file}") from e

    def _get_property(self, tree, prop):
        """
        Extrae o valor duma propiedade meta do HTML.

        :params: tree: árvore do HTML
        :params: prop: propiedade a extraer
        :returns: str: valor da propiedade
        """
        result = tree.xpath(f"//meta[@property='{prop}']/@content")
        if result:
            return result[0].strip()
        return None

    def _get_name(self, tree, name):
        """
        Extrae o valor dum nome meta do HTML.

        :params: tree: árvore do HTML
        :params: name: nome a extraer
        :returns: str: valor do nome
        """
        result = tree.xpath(f"//meta[@name='{name}']/@content")
        if result:
            return result[0].strip()
        return None

    def _get_metadata(self, tree):
        """
        Extrae os metadados do HTML.

        :params: tree: árvore do HTML
        :returns: dict: metadatos extraídos
        """
        metadata = {}

        url = self._get_property(tree, "og:url")
        if url:
            metadata = {
                "news_item_id": self._get_id(url),
                "url": url
            }

        self.url = url
        published_time = self._get_property(tree, "article:published_time")
        if published_time:
            metadata["this_revision_created"] = published_time

        return metadata

    def _get_id(self, url):
        """
        Gera un ID único para a nova a partir da súa URL.

        :params: url: URL da nova
        :returns: str: ID único
        """
        return hashlib.md5(url.encode("utf-8")).hexdigest()

    def _get_title(self, tree):
        """
        Extrae o título da nova.

        :params: tree: árvore do artigo
        :returns: str: título extraído
        """
        title = (
            self._get_property(tree, "og:title") or
            self._get_name(tree, "title") or
            logger.warning(
                "No title found in article %s", self.url)
        )
        if title:
            return title.replace(" - Praza Pública", "").strip()
        return ""

    def _get_abstract(self, tree):
        """
        Extrae o abstract da nova.

        :params: tree: árvore do artigo
        :returns: str: abstract extraído
        """
        abstract = (
            self._get_property(tree, "og:description") or
            self._get_name(tree, "description") or
            logger.warning(
                "No description found in article %s", self.url)
        )
        if abstract:
            return abstract.strip()
        return None

    def _download_article(self, url, isodate):
        """
        Descarrega a nova da URI e almacena o HTML, organizando os dados por
        ano e mes.

        :params: url: URI para descarregar
        :params: isodate: data en formato ISO 8601
        :returns: boolean: resultado da descarga
        """
        (year, month, day) = isodate.split('.')[0].split("T")[0].split("-")

        try:
            out_dir = Path(self.config["source"]) / str(year) / str(month)
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return False, str(e)

        filename = f"praza_{year + month + day}_{url.split("/")[-1]}.html"
        out_path = out_dir / Path(filename).name
        if out_path.exists():
            logger.debug("File %s already exists, skipping download", out_path)
            return True, "exists"

        try:
            content = self.r.fetch(str(url))
        except RequestError as e:
            logger.error("Error downloading article: %s", e)
            return False, str(e)

        if not content or len(content) == 0:
            logger.warning("Empty content for URI %s", url)
            return False, "empty_content"

        try:
            with out_path.open("w") as f:
                f.write(content)
        except Exception as e:
            return False, str(e)

        return True, "ok"

    def _get_articles_in_page(self, tree):
        """
        Get links from the category index and download each article.

        :params: tree: árbore lida da páxina de categoría
        :returns: None
        """
        articles = tree.xpath(
            '//ul[contains(@class, "articles-list")]//article'
        )

        for a in articles:
            href = a.xpath('.//h2[contains(@class, "headline")]/a/@href')
            if href:
                href = href[0]
            date = a.xpath('.//time[contains(@class, "date")]/@datetime')
            if date:
                date = date[0]

            result, msg = self._download_article(
                f"{self.config['base_url']}{href}", date)
            if result:
                if msg == "exists":
                    self.articles_exists += 1
                    logger.info("Article already exists: %s", href)
                else:
                    self.articles_ok += 1
                    logger.info("Successfully downloaded article: %s", href)
            else:
                self.articles_error += 1
                logger.error(
                    "Error downloading article %s: %s", href, msg)

    def _get_category_end(self, tree):
        """
        Get the last page number from the category pagination.
        :params: tree: árvore da página de categoria
        :returns: int: last page number
        """
        links = tree.xpath(
            '//nav[contains(@class, "at-pagination")]'
            '//a[contains(@class, "pagination-link")]'
        )

        nav = [
            int(p.text_content()) for p in links if p.text_content().isdigit()
        ]

        return max(nav) if nav else 1
