import json
import requests
from urllib.parse import urljoin


def test_discharge(callback_url, callback):
    r = callback_url.send_callback(callback)
    if r is None:
        # store callback in database instead
        print("Storing not possible, store in database instead")
        callback.to_db()


def test_discharge_patch(callback_url, callback_patch):
    url = urljoin(str(callback_url.url), callback_patch.endpoint)
    request = getattr(requests, callback_patch.request_type.lower())
    # url = str(callback_url.url) + callback.endpoint
    r = request(
        url,
        json={
            "q_05": 5,
            "q_25": 6,
            "q_50": 7,
            "q_75": 8,
            "q_95": 9,
            "fraction_velocimetry": 0.8
        }
    )
    assert(r.status_code == 200)

