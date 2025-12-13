"""
Request wrapper for fetching URLs with retry logic.
"""
import logging
import time
import requests


logger = logging.getLogger(__name__)


class RequestError(Exception):
    """Custom exception used for errors in the Request class."""


class Request:
    """
    Simple HTTP client for fetching URLs from newspapers and other
    data sources.
    """

    def __init__(
        self,
        timeout=10,
        max_retries=3,
        retry_delay=2.0,
        user_agent="ProxectoNOSApp/1.0",
    ):
        """
        :param timeout: maximum number of seconds to wait for a response.
        :param max_retries: maximum number of attempts before giving up.
        :param retry_delay: delay (in seconds) between retries.
        :param user_agent: default User-Agent header for all requests.
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.user_agent = user_agent

        self._retry_status_codes = {500, 502, 503, 504, 429}

    def _request_with_retries(self, url, headers=None):
        """
        Perform a GET request and return the raw Response object.

        :param url: URL to fetch.
        :param headers: optional extra headers to send with the request.
        :raises RequestError: when all attempts fail.
        :return: a requests.Response object.
        """
        merged_headers = {"User-Agent": self.user_agent}
        if headers:
            merged_headers.update(headers)

        last_exc = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(
                    "Fetching URL: %s (attempt %d)",
                    url,
                    attempt,
                )
                response = requests.get(
                    url,
                    timeout=self.timeout,
                    headers=merged_headers,
                )

                status = response.status_code

                if (
                    status in self._retry_status_codes
                    and attempt < self.max_retries
                ):
                    logger.warning(
                        "Got status code %d for %s, retrying (attempt #%d)...",
                        status,
                        url,
                        attempt + 1,
                    )
                    time.sleep(self.retry_delay)
                    continue

                return response

            except (
                requests.Timeout,
                requests.ConnectionError,
                requests.RequestException,
            ) as e:
                last_exc = e
                logger.error(
                    "Error fetching the URL %s (attempt %d): %s",
                    url,
                    attempt,
                    e,
                )
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    break

        if isinstance(last_exc, requests.Timeout):
            raise RequestError("Timeout occurred")
        if isinstance(last_exc, requests.ConnectionError):
            raise RequestError("Connection error occurred")
        if last_exc is not None:
            raise RequestError(f"Error fetching URL: {last_exc}")

        raise RequestError("Unknown error fetching URL")

    def fetch_response(self, url, headers=None):
        """
        Fetch a URL and return the raw Response object.

        :param url: URL to fetch.
        :param headers: optional extra headers.
        :return: a requests.Response object.
        :raises RequestError: if the request fails after all retries.
        """
        response = self._request_with_retries(url, headers=headers)
        logger.info(
            "Fetched URL %s with status %d",
            url,
            response.status_code,
        )
        return response

    def fetch(self, url, headers=None):
        """
        Fetch a URL and return the response body as text.

        :param url: URL to fetch.
        :param headers: optional extra headers.
        :return: response body as a string.
        :raises RequestError: if the request fails or HTTP status is not OK.
        """
        response = self._request_with_retries(url, headers=headers)

        try:
            response.raise_for_status()
            logger.info("Successfully fetched URL: %s", url)
            return response.text
        except requests.HTTPError as e:
            status = response.status_code
            logger.error(
                "HTTP error occurred while fetching %s: %s (status %d)",
                url,
                e,
                status,
            )
            raise RequestError(f"HTTP {status} error in {url}") from e
