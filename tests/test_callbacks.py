import json
import requests
from urllib.parse import urljoin

import models


def test_discharge(callback_url, callback):
    url = urljoin(str(callback_url.url), callback.endpoint)
    request = getattr(requests, callback.request_type.lower())
    r = request(
        url,
        json={
            "timestamp": "2000-01-01T00:00:00Z",
            "h": 1.,
            "q_05": 5,
            "q_25": 6,
            "q_50": 7,
            "q_75": 8,
            "q_95": 9,
            "fraction_velocimetry": 0.8
        }
    )
    assert(r.status_code == 200)


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

def test_discharge(callback_url, callback):
    url = urljoin(str(callback_url.url), callback.endpoint)
    request = getattr(requests, callback.request_type.lower())
    r = request(
        url,
        json={
            "timestamp": "2000-01-01T00:00:00Z",
            "h": 1.,
            "q_05": 5,
            "q_25": 6,
            "q_50": 7,
            "q_75": 8,
            "q_95": 9,
            "fraction_velocimetry": 0.8
        }
    )
    assert(r.status_code == 200)


def test_discharge_cranky():
    json_dict = {
        'timestamp': '2023-09-22T08:01:00Z',
        'h': 92.428,
        'q_05': 1.0591092628182952,
        'q_25': 1.2217395277472864,
        'q_50': 1.3466954527061719,
        'q_75': 1.4587283752842657,
        'q_95': 1.5817134735060967,
        'fraction_velocimetry': 54.63708952856439
    }
    files = None

    callback_url = models.CallbackUrl(**{
        # "server_name": "local_server",
        "url": "http://127.0.0.1:8001",
        "token_refresh_end_point": "/api/token/refresh/",
        "token_refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MjAxMDczMjc4MCwiaWF0IjoxNjk1MzcyNzgwLCJqdGkiOiI5OWFlZmMwMzI5ODA0NDBmOWUwMDM0ZmMyZGYzM2Y3YSIsInVzZXJfaWQiOjF9.GufHPgiaI_IxfigZI6xG7qFgtB4DDTPkDyBihLfJQXE",
        "token_access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNjk1Mzk0MzgwLCJpYXQiOjE2OTUzNzI3ODAsImp0aSI6IjQ2YTgwMWUzZjY4MjRhNzY5NmIxMzA3ODZhZjE5MGIyIiwidXNlcl9pZCI6MX0.i8DwIBYwiFIJ-OiiFwevJ8uNyV57JbXgv_-W2oY2jYM",
        # "token_refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MjAxMDczODU4OSwiaWF0IjoxNjk1Mzc4NTg5LCJqdGkiOiI0Nzg1NWI3YTczNjA0ZjdhYWY4YTdjNzA5OWFkYjNhMCIsInVzZXJfaWQiOjF9.9lKmEvfk9NWQv6MgAIYPS3fg4Kp2o3IMLz4OYTf2Beg",
        # "token_access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNjk1NDAwMTg5LCJpYXQiOjE2OTUzNzg1ODksImp0aSI6IjU1NzFmNTk1MTQwZDQwYTc5MTQyMjUyNGI2NTY0N2VjIiwidXNlcl9pZCI6MX0.c1vzkQvObboYEeKYdshNuC4w-gQpuRbTdQjVynFxnrc",
    })
    callback_dict = {
        "func_name": "discharge",
        "request_type": "POST",
        "endpoint": "/api/site/1/timeseries/"
    }
    callback = models.Callback(**callback_dict)
    # func = getattr(callbacks, self.callback.func_name)
    # msg = func(self.output_files, timestamp=task.timestamp, tmp=tmp)

    # get the type of request. Typically this is POST for an entirely new time series record created from an edge
    # device, and PATCH for an existing record that must be provided with analyzed flows
    callback_url.send_request(callback, json_dict, files)