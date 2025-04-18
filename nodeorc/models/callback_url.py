import os
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pydantic import field_validator, BaseModel, AnyHttpUrl
# nodeodm specific imports
from .. import callbacks
from urllib.parse import urljoin

from .. import settings_path


class Callback(BaseModel):
    func_name: Optional[str] = "discharge"  # name of function that establishes the callback json
    request_type: str = "POST"
    kwargs: Optional[Dict[str, Any]] = {}
    endpoint: Optional[str] = "/api/timeseries/"  # used to extend the default callback url

    @field_validator("func_name")
    @classmethod
    def name_in_callbacks(cls, v):
        if not(hasattr(callbacks, v)):
            raise ValueError(f"callback {v} not available in callbacks")
        return v



class CallbackUrl(BaseModel):
    """
    Definition of accessibility to storage and callback locations
    """
    server_name: str = "some_server"  # required only for storing access tokens
    url: AnyHttpUrl = "https://127.0.0.1:8000/api"
    token_refresh_end_point: Optional[str] = None
    token_refresh: Optional[str] = None
    token_access: Optional[str] = None
    token_expiration: Optional[datetime] = datetime.now()

    @property
    def token_file(self):
        return os.path.join(settings_path, self.server_name + ".json")

    @property
    def has_token(self):
        return self.token_refresh is not None and len(self.token_refresh_end_point) > 0

    def to_json(self, **kwargs):
        """
        Write task to fully serializable json format

        Parameters
        ----------
        indent : int
            indentation of json string (typically only used for

        Returns
        -------

        """
        callback_url_json = self.model_dump_json(**kwargs)
        # load back and then store with indents
        return callback_url_json

    def to_file(self, fn, **kwargs):
        with open(fn, "w") as f:
            f.write(self.to_json(**kwargs))

    def refresh_tokens(self):
        url = urljoin(str(self.url), self.token_refresh_end_point)
        body = {"refresh": self.token_refresh}
        r = requests.post(url, json=body)
        if r.status_code != 200:
            raise ValueError(f"Refresh token not accepted with error code {r.status_code}, message: {r.json()}")
        self.token_access = r.json()["access"]
        self.token_refresh = r.json()["refresh"]
        self.token_expiration = datetime.now() + timedelta(hours=5)  # TODO: make configurable. LiveORC works with 6 hours.
        # store the tokens in file
        self.store_tokens()

    def store_tokens(self):
        """Store the tokens in the active database config record."""
        # get the active configuration record
        from .. import db_ops  # import lazily to avoid circular referencing
        from ..db import session  # import lazily to avoid circular referencing

        callback_url = db_ops.get_callback_url(session)
        # update the tokens
        callback_url.token_access = self.token_access
        callback_url.token_refresh = self.token_refresh
        callback_url.token_expiration = self.token_expiration
        session.commit()

    def send_callback(self, callback):
        data, files = callback.get_body()
        # get the type of request. Typically this is POST for an entirely new time series record created from an edge
        # device, and PATCH for an existing record that must be provided with analyzed flows
        try:
            r = self.send_request(callback, data, files)
        except Exception as e:
            # store callback in database instead
            r = None
        return r

    def send_request(self, callback, data, files):
        if self.has_token:
            # first check if tokens must be refreshed
            if datetime.now() > self.token_expiration:
                # first refresh tokens
                self.refresh_tokens()
            headers = {"Authorization": f"Bearer {self.token_access}"}
        else:
            headers = {}
        url = urljoin(str(self.url), callback.endpoint)
        request = getattr(
            requests,
            callback.request_type.lower()
        )
        # perform callback (arrange the adding of token)
        r = request(
            url,
            data=data,
            headers=headers,
            files=files
        )
        return r
        # if r.status_code != 200 and r.status_code != 201:
        #     try:
        #         raise ValueError(f'callback to {url} failed with error code {r.status_code} and body "{r.json()}"')
        #     except:
        #         raise ValueError(f'callback to {url} failed with error code {r.status_code}, and text body "{r.text}"')

