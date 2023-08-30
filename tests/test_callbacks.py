import requests
from urllib.parse import urljoin

def test_discharge(callback_url, callback):
    url = urljoin(str(callback_url.url), callback.endpoint)
    # url = str(callback_url.url) + callback.endpoint
    requests.post(
        url,
        json={
            "h": 1.,
            "q_05": 5,
            "q_25": 6,
            "q_50": 7,
            "q_75": 8,
            "q_95": 9,
            "fraction_velocimetry": 0.8
        }
    )
