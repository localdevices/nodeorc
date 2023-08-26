# test the AMQP task handling
def test_task(channel, task):
    # get rid of logger and deserialize
    del task.logger
    body = task.json()
    # change a few http addresses
    body = body.replace(
        "http://127.0.0.1:1080",
        "http://mockserver:1080",
    )
    body = body.replace(
        "http://127.0.0.1:9000",
        "http://storage:9000",
    )
    # execute task
    channel.basic_publish(
        exchange="",
        routing_key="processing",
        body=body,
    )
