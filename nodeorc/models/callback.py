import json
from typing import Optional, Dict, Any
from pydantic import field_validator, BaseModel

# nodeodm specific imports
from nodeorc import callbacks

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


    def get_body(self, task, subtask, tmp="."):
        # get the name of callback
        func = getattr(callbacks, self.func_name)
        data, files = func(task, subtask, tmp=tmp, **self.kwargs)
        return data, files