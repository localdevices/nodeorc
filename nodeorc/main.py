import click
import json
import os
import pika
import sys
import traceback

from nodeorc import log, models, tasks, __version__
from pydantic import ValidationError
from dotenv import load_dotenv
# import tasks

# load env variables. These are not overridden if they are already defined
load_dotenv()

def validate_env(env_var):
    if os.getenv(env_var) is None:
        raise EnvironmentError(f"{env_var} is not an environment variable. Set it in an .env file or set it in your "
                               f"environment profile")


def validate_listen(ctx, param, value):
    if value == "AMQP":
        validate_env("AMQP_CONNECTION_STRING")
    elif value == "local":
        # check if settings file is set as environment variable
        validate_env("NODEORC_SETTINGS")
        validate_env("WATER_LEVEL_WILDCARD")
        validate_env("VIDEO_DATETIMEFMT")

    return value

def validate_storage(ctx, param, value):
    if value == "local":
        # local processing and storage
        validate_env("INCOMING_VIDEO_PATH")
    elif value == "S3":
        # local processing but remote storage
        validate_env("S3_ENDPOINT_URL")
        validate_env("S3_ACCESS_KEY")
        validate_env("S3_ACCESS_SECRET")
    elif "remote":
        # storage is defined by remote task so not relevant now
        pass
    return value

def print_license(ctx, param, value):
    if not value:
        return {}
    click.echo(f"GNU Affero General Public License v3 (AGPLv3). See https://www.gnu.org/licenses/agpl-3.0.en.html")
    ctx.exit()


verbose_opt = click.option("--verbose", "-v", count=True, help="Increase verbosity.")

storage_opt = click.option(
    "-s",
    "--storage",
    type=click.Choice(["S3", "local", "remote"]),
    help='Storage solution to use (either "local" for a locally mounted folder, "S3" for a S3-compatible bucket, or "remote" for storage defined entirely by a remote server. In the last case, "--listen" must be set to "AMQP")',
    required=True,
)
listen_opt = click.option(
    "-l",
    "--listen",
    type=click.Choice(["local", "AMQP"]),
    help='Method for listening for new tasks (either "local" or "AMQP" Storage solution to use (either "local" for '
         'listening to a locally mounted folder for new videos, or "AMQP" for tasks sent from a remote platform)',
    callback=validate_listen
)

# Callback function for each process task that is queued.
# def process(ch, method, properties, body):
#     task_dict = json.loads(body.decode("utf-8"))
#     try:
#         task = models.Task(**task_dict)
#         task.logger = logger
#     except ValidationError as exc:
#         logger.error(f"{exc.errors()[0]['type']}: {exc.errors()[0]['msg']}")
#         ch.basic_ack(delivery_tag=method.delivery_tag)
#         raise ValidationError("Task not valid, restarting node...")
#     # execute the task
#     task.execute(temp_path)
#     ch.basic_ack(delivery_tag=method.delivery_tag)
#
# @click.group()
@click.command()
@click.version_option(__version__, message="NodeOpenRiverCam version: %(version)s")
@storage_opt
@listen_opt
def cli(storage, listen):
    print(storage)
    logger = log.start_logger(True, False)
    temp_path = os.getenv("TEMP_PATH", "./tmp")
    # remote storage parameters with local processing is not possible
    if listen == "local" and storage == "remote":
        raise ValidationError('Locally defined tasks ("--listen local")  cannot have remotely defined storage ("--storage remote").')
    if listen == "local":
        # validate the settings into a task model
        settings_fn = os.getenv("NODEORC_SETTINGS")
        incoming_video_path = os.getenv("INCOMING_VIDEO_PATH")
        with open(settings_fn, "r") as f:
            task_template = json.load(f)
        # verify that task_template can be converted to a valid Task
        try:
            task_test = models.Task(**task_template)
        except Exception as e:
            logger.error(f"Settings in {os.path.abspath(settings_fn)} cannot be formed into a valid Task instance")
        try:
            logger.info(f"Start listening to new videos in folder {os.getenv('LOCAL_URL')}")
            tasks.local_tasks(task_template, incoming_video_path, temp_path, logger=logger)
        except Exception as e:
            logger.error("Reboot service: %s" % str(e))
    else:
        raise NotImplementedError


# def main():
#     connection = pika.BlockingConnection(
#         pika.URLParameters(
#             '{}?heartbeat=1800&blocked_connection_timeout=900'.format(
#                 os.getenv("AMQP_CONNECTION_STRING")
#             )
#         )
#     )
#     channel = connection.channel()
#     channel.queue_declare(queue="processing")
#     # Process a single task at a time.
#     channel.basic_qos(prefetch_count=1)
#     channel.basic_consume(queue="processing", on_message_callback=process)
#
#     try:
#         logger.info("Start listening for processing tasks in queue.")
#         channel.start_consuming()
#     except Exception as e:
#         logger.error("Reboot service: %s" % str(e))
#         channel.stop_consuming()
#         connection.close()
#         traceback.print_tb(e.__traceback__)

if __name__ == "__main__":
    cli()
