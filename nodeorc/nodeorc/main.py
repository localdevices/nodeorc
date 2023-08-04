import pika
import traceback
import os
import json
from nodeorc import log, models, tasks
from pydantic import ValidationError
logger = log.start_logger(True, False)

temp_path = os.getenv("TEMP_PATH", "./tmp")
# Callback function for each process task that is queued.
def process(ch, method, properties, body):
    task_dict = json.loads(body.decode("utf-8"))
    try:
        task = models.Task(**task_dict)
        task.logger = logger
    except ValidationError as exc:
        logger.error(f"{exc.errors()[0]['type']}: {exc.errors()[0]['msg']}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        raise ValidationError("Task not valid, restarting node...")
    # execute the task
    task.execute(temp_path)
    ch.basic_ack(delivery_tag=method.delivery_tag)

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
        logger.error("Reboot service: %s" % str(e))
        channel.stop_consuming()
        connection.close()
        traceback.print_tb(e.__traceback__)

if __name__ == "__main__":
    main()