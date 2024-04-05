from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from pydantic import field_validator, BaseModel

# nodeodm specific imports
from .. import callbacks
from . import File, Storage


class Callback(BaseModel):
    timestamp: datetime = datetime.now()
    func_name: str = "discharge"  # name of function that establishes the callback json
    storage: Storage = Storage()  # storage where the file(s) must be located
    file: Optional[Union[File, str]] = None  # filename specific to the used callback, if callback does not require any input file, then leave empty
    files_to_send: Optional[Union[List[str], Dict[str, File]]] = None
    request_type: str = "POST"
    kwargs: Optional[Dict[str, Any]] = {}  # set of kwargs to add to the callback msg body
    endpoint: Optional[str] = "/api/timeseries/"  # used to extend the default callback url

    @field_validator("func_name")
    @classmethod
    def name_in_callbacks(cls, v):
        if not(hasattr(callbacks, v)):
            raise ValueError(f"callback {v} not available in callbacks")
        return v

    def get_body(self):
        # get the name of callback
        func = getattr(callbacks, self.func_name)
        data, files = func(self)
        # data, files = func(task, subtask, tmp=tmp, **self.kwargs)
        return data, files

    def to_db(self):
        from .. import db  # import lazily to prevent circular imports
        session_data = db.init_basedata.get_data_session()
        rec = db.models.Callback(
            body=self.model_dump_json()
        )
        session_data.add(rec)
        session_data.commit()