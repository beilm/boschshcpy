import json
import logging
import os.path
import base64
import pkg_resources

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager

from .generate_cert import generate_selfsigned_cert

logger = logging.getLogger("boschshcpy")

class HostNameIgnoringAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                                    maxsize=maxsize,
                                    block=block,
                                    assert_hostname=False)

class SHCRegisterClient:
    """ Press and hold the button at the front of the SHC until the lights are blinking before you POST the command. When the SHC is not in pairing mode, there will be a connection error."""

    def __init__(self, controller_ip: str, password: str):
        """Initializes with IP address and access credentials."""
        self._controller_ip = controller_ip
        self._url = f"https://{self._controller_ip}:8443/smarthome/clients"

        # Settings for API call
        password_base64 = base64.b64encode(password.encode('utf-8'))
        self._requests_session = requests.Session()
        self._requests_session.mount('https://', HostNameIgnoringAdapter())
        self._requests_session.headers.update(
            {"Content-Type": "application/json", "Systempassword": password_base64.decode('utf-8')}
        )
        self._requests_session.verify = pkg_resources.resource_filename('boschshcpy', 'tls_ca_chain.pem')

        import urllib3

        urllib3.disable_warnings()

    def _post_api_or_fail(self, body, timeout=30):
        try:
            result = self._requests_session.post(
                self._url, data=json.dumps(body), timeout=timeout
            )
            if not result.ok:
                self._process_nok_result(result)
            if len(result.content) > 0:
                return json.loads(result.content)
            else:
                return {}
        except requests.exceptions.SSLError as e:
            logger.error(
                "An error occured during requests.post(%s): %s. SHC not in pairing mode?"
                % (self._url, e)
            )
            return {}

    def _process_nok_result(self, result):
        logging.error(f"Body: {result.request.body}")
        logging.error(f"Headers: {result.request.headers}")
        logging.error(f"URL: {result.request.url}")
        raise ValueError(
            f"API call returned non-OK result (code {result.status_code})!: {result.content}"
        )

    def register(self, oss_id, name, certificate=None):
        cert = key = None
        if not certificate:
            cert, key = generate_selfsigned_cert(self._controller_ip, [self._controller_ip])
            certstr = (
                cert.decode('utf-8')
                .replace("\n", "")
                .replace("-----BEGIN CERTIFICATE-----", "-----BEGIN CERTIFICATE-----\r")
                .replace("-----END CERTIFICATE-----", "\r-----END CERTIFICATE-----")
            )
            print(certstr)

        else:
            if not os.path.exists(certificate):
                logger.error("No valid cert file, aborting!")
                # only continue if path to certificate is valid
                return None

            with open(certificate, "r") as file:
                certstr = (
                    file.read()
                    .replace("\n", "")
                    .replace("-----BEGIN CERTIFICATE-----", "-----BEGIN CERTIFICATE-----\r")
                    .replace("-----END CERTIFICATE-----", "\r-----END CERTIFICATE-----")
                )

        data = {
            "@type": "client",
            "id": oss_id,
            "name": "oss_{}".format(name),
            "primaryRole": "ROLE_RESTRICTED_CLIENT",
            "certificate": certstr,
        }

        result = self._post_api_or_fail(data)
        return {"token": result["token"], "cert": cert, "key": key} if "token" in result else None
