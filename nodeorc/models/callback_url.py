import copy
import json
import logging
import os
import requests
import shutil
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, AnyStr, Union
from pydantic import field_validator, BaseModel, AnyHttpUrl, ConfigDict, model_validator, DirectoryPath, StrictBool
from pyorc import service
from io import BytesIO
# nodeodm specific imports
from nodeorc import callbacks, utils
from urllib.parse import urljoin
from urllib.error import HTTPError

from nodeorc import settings_path
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
    token_expiration: Optional[datetime] = datetime(2000, 1, 1, 0, 0, 0)

    # @field_validator("url")
    # @classmethod
    # def validate_url(cls, v):
    #     try:
    #         r = requests.get(
    #             v,
    #             timeout=5,
    #         )
    #     except requests.exceptions.ConnectionError as e:
    #         raise ValueError(f"Timeout of 5 seconds reached on connection {v} reached")
    #     return v

    @model_validator(mode="after")
    def check_replace_token(self) -> 'CallbackUrl':
        """
        Upon creating an instance, immediately replace the access tokens by fresh ones, to ensure no security risks
        are occurring. This is only necessary when there is an access token. If not it is assumed the server is local
        and no authentication is required.

        Returns
        -------

        """
        if self.token_refresh and self.token_refresh_end_point:
            # if the token is stored in a file, then it is assumed that this file contains the most actual CallbackUrl
            # for this server, and the entire instance will be replaced
            if os.path.isfile(self.token_file):
                # read contents into a new instance and return that instead of self
                with open(self.token_file, "r") as f:
                    return CallbackUrl(**json.loads(f.read()))
        return self

    @property
    def token_file(self):
        return os.path.join(settings_path, self.server_name + ".json")

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
        url = self.url + self.token_refresh_endpoint
        body = {"refresh": self.token_refresh}
        r = requests.post(url, json=body)
        if r.status_code != 200:
            raise HTTPError(f"Error code: {r.status_code}, message: {r.json()}")
        self.token_access = r.json()["access"]
        self.token_refresh = r.json()["refresh"]
        # store the tokens in file

    def store_tokens(self):
        """
        Store the tokens in the default file path with server_name in it.

        Returns
        -------

        """
        self.to_file(fn=self.token_file, indent=4)

    def request(self):
        raise NotImplementedError
