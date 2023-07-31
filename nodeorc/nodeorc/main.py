import pika
import traceback
import os
import json
from . import log, models, tasks
from pydantic import ValidationError
logger = log.start_logger(True, False)

# Callback function for each process task that is queued.
def process(ch, method, properties, body):
    task_dict = json.loads(body.decode("utf-8"))
    # validate callback url
    if "callback_url" in task_dict:
        # test if url is functioning
        try:
            # validate url
            callback_url = models.CallbackUrl(**body["callback_url"])
        except ValidationError as exc:
            logger.error(f"{exc.errors()[0]['type']}: {exc.errors()[0]['msg']}")
    else:
        msg = "AMQP message body does not contain callback_url"
        logger.error(msg)
        raise ValueError(msg)
    # validate message body entirely
    try:
        task = models.task(**task_dict)
    except ValidationError as exc:
        logger.error(f"{exc.errors()[0]['type']}: {exc.errors()[0]['msg']}")
    # execute the task
    execute_task(task, logger)

        # try:
    #     perform_task(**kwargs, logger=logger)
    #     logger.info(f"Task {task_name} was successful")
    #     # Acknowledge queue item at end of task.
    ch.basic_ack(delivery_tag=method.delivery_tag)

    #     r = 200
    # except BaseException as e:
    #     logger.error(f"{task_name} failed with error {e}")
    #     # Acknowledge queue item at end of task.
    #     ch.basic_ack(delivery_tag=method.delivery_tag)
    #     # requests.post(
    #     #     "{}/processing/error/{}".format(os.getenv("ORC_API_URL"), taskInput["kwargs"]["movie"]["id"]),
    #     #     json={"error_message": str(e)},
    #     # )
    #     r = 500
    #
    # except Exception as e:
    #     print("Processing failed with error: %s" % str(e))
    #     traceback.print_tb(e.__traceback__)

def main():
    connection = pika.BlockingConnection(
        pika.URLParameters('{}?heartbeat=1800&blocked_connection_timeout=900'.format(os.getenv("AMQP_CONNECTION_STRING")))
    )
    channel = connection.channel()
    channel.queue_declare(queue="processing")
    # Process a single task at a time.
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="processing", on_message_callback=process)

    try:
        logger.info("Start listening for processing tasks in queue.")
        channel.start_consuming()
    except Exception as e:
        logger.error("Reboot service due to error: %s" % str(e))
        channel.stop_consuming()
        connection.close()
        traceback.print_tb(e.__traceback__)

if __name__ == "__main__":
    main()