"""
Script para descarregar artigos de jornais galegos.
"""
import argparse
import configparser
import logging
import sys
from pathlib import Path
from news_scraper.prazapublica import Praza, CATEGORIES
from news_scraper.nosdiario import NosDiario

logger = logging.getLogger(__name__)


def load_config(path="config.ini"):
    """
    Carrega a configuração do ficheiro INI.

    :param path: ficheiro de configuração
    :returns: objeto ConfigParser com a configuração
    """
    cfg = configparser.ConfigParser()
    cfg.read(path, encoding="utf-8")
    return cfg


def parse_args():
    """
    Processa os argumentos da linha de comandos.

    :returns: argumentos processados
    """
    parser = argparse.ArgumentParser(description="News scraper")
    parser.add_argument(
        "--loglevel",
        "-l",
        type=str,
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Define o nivel de registo.",
    )

    subparsers = parser.add_subparsers(
        title="source",
        dest="source",
        required=True,
    )

    praza_parser = subparsers.add_parser(
        "praza",
        help="Scraper de Praza Pública"
    )
    group_p = praza_parser.add_mutually_exclusive_group(required=True)
    praza_parser.add_argument(
        "--category",
        "-c",
        nargs="+",
        choices=sorted(CATEGORIES.keys()),
        default=sorted(CATEGORIES.keys()),
        help="Categorias para descarregar.",
    )
    group_p.add_argument(
        "--download",
        "-d",
        nargs="?",
        const="category",
        choices=["category", "rss"],
        metavar="FROM",
        help=(
            "Descarregar os ficheiros HTML "
            "(FROM: [%(choices)s]; por defecto: '%(const)s')."
        ),
    )
    group_p.add_argument(
        "--parse",
        "-p",
        nargs="?",
        const="ALL",
        metavar="FILE",
        help=(
            "Parsea todos os ficheiros HTML descarregados "
            "(FILE para processar só um ficheiro)."
        )
    )

    nos_parser = subparsers.add_parser(
        "nosdiario",
        help="Scraper de Nós Diario"
    )
    group_n = nos_parser.add_mutually_exclusive_group(required=True)
    group_n.add_argument(
        "--parse",
        "-p",
        nargs="?",
        const="ALL",
        metavar="FILE",
        help=(
            "Parsea todos os ficheiros XML descarregados "
            "(FILE para processar só um ficheiro)."
        )
    )
    group_n.add_argument(
        "--download",
        "-d",
        nargs="?",
        const="category",
        choices=["category", "rss"],
        metavar="FROM",
        help=(
            "Descarregar os ficheiros XML "
            "(FROM: [%(choices)s]; por defecto: '%(const)s')."
        ),
    )

    return parser.parse_args()


def main(args):
    """
    Função principal do programa.

    :params: args: argumentos da linha de comandos
    """
    def parse_paths(args, config, pattern):
        """
        Retorna os paths a parsear segundo os argumentos.

        :params: args: argumentos da linha de comandos
        :params: config: configuração do scraper
        :params: pattern: extensão dos ficheiros a parsear
        :returns: lista de paths a parsear
        """
        if args.parse == "ALL":
            return Path(config["source"]).rglob(pattern)
        return [Path(args.parse)]

    try:
        config = load_config()[args.source]
    except KeyError:
        logger.error("No configuration found for source: %s", args.source)
        sys.exit(1)

    if args.source == "praza":
        p = Praza(config=config)
        pattern = "*.html"
    elif args.source == "nosdiario":
        p = NosDiario(config=config)
        pattern = "*.xml"
    else:
        raise ValueError(f"Unknown source: {args.source}")

    if args.parse:
        p.parse(parse_paths(args, config, pattern))
        print(
            f"Parsed {p.articles_ok + p.articles_error} articles, "
            f"{p.articles_error} with errors"
        )

    elif args.source == "praza" and args.download:
        if args.download == "rss":
            raise RuntimeError("rss not implemented yet")
        for category in args.category:
            logger.info("Fetching category: %s", category)
            p.download_from_category(category)


if __name__ == "__main__":
    p_args = parse_args()

    logging.basicConfig(
        level=getattr(logging, p_args.loglevel),
        format="[%(levelname)s] %(name)s: %(message)s"
    )

    logger = logging.getLogger(__name__)
    main(p_args)
