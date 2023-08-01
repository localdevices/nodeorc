from nodeorc import tasks

def test_velocity_flow(task, temp_path):

    # try:
    # callback = models.Callback(
    #     func_name="get_discharge",
    #     url_subpath="http://localhost:8000/api"
    # )
    # print(task)
    #     = nodeorc.models.Task(
    #     storage={"endpoint_url": s3_url},
    #     callback_url={"url": callback_url}
    #     # callbacks = [callback]
    # )
    task.execute(temp_path)
    # forward the task to the processor
    # except ValidationError as exc:
    #     # TODO: perform callback
    #     print(repr(exc.errors()[0]))


