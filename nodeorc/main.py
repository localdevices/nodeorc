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
from nodeorc import settings_path, db
# load env variables. These are not overridden if they are already defined
load_dotenv()

temp_path = os.getenv("TEMP_PATH", "./tmp")
# settings_path = os.path.join(os.path.split(__file__)[0], "..", "settings")

def load_settings(settings_fn):
    # define local settings below
    if os.path.isfile(settings_fn):
        try:
            with open(settings_fn, "r") as f:
                settings = models.LocalConfig(**json.load(f))
            return settings
        except ValidationError as e:
            raise ValueError(
                f"Settings file in {os.path.abspath(settings_fn)} is not a valid local configuration file. Error: {e}")

def validate_env(env_var):
    if os.getenv(env_var) is None:
        raise EnvironmentError(f"{env_var} is not an environment variable. Set it in an .env file or set it in your "
                               f"environment profile")


def validate_listen(ctx, param, value):
    if value == "AMQP":
        validate_env("AMQP_CONNECTION_STRING")

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

def print_info(ctx, param, value):
    if not value:
        return {}
    click.echo(f"NodeOpenRiverCam, Copyright Localdevices, Rainbow Sensing")
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
settings_opt = click.option(
    "--settings",
    type=click.Path(exists=True),
    help="location of the settings .json file",
    default=os.path.join(settings_path, "settings.json")
)
task_form_opt = click.option(
    "--task_form",
    type=click.Path(exists=True),
    help="location of the task form .json file",
    default=os.path.join(settings_path, "task_form.json")
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
# @click.command()
@click.group()
@click.version_option(__version__, message="NodeOpenRiverCam version: %(version)s")
@click.option(
    "--license",
    default=False,
    is_flag=True,
    is_eager=True,
    help="Print license information for NodeOpenRiverCam",
    callback=print_license,
)
@click.option(
    "--info",
    default=False,
    is_flag=True,
    is_eager=True,
    help="Print information and version of NodeOpenRiverCam",
    callback=print_info,
)
@click.option(
    '--debug/--no-debug',
    default=False,
    envvar='REPO_DEBUG'
)
@click.pass_context
def cli(ctx, info, license, debug):  # , quiet, verbose):
    """Command line interface for pyOpenRiverCam."""
    if ctx.obj is None:
        ctx.obj = {}

@cli.command(short_help="Start main daemon")
@storage_opt
@listen_opt
@settings_opt
@task_form_opt
def start(storage, listen, settings, task_form):
    print(storage)
    logger = log.start_logger(True, False)
    # remote storage parameters with local processing is not possible
    if listen == "local" and storage == "remote":
        raise ValidationError('Locally defined tasks ("--listen local")  cannot have remotely defined storage ("--storage remote").')
    if listen == "local":
        settings = load_settings(settings)
        if settings is None:
            raise IOError("For local processing, a settings file must be present in /settings/settings.json. Please create or modify your settings accordingly")
        # validate the settings into a task model
        with open(task_form, "r") as f:
            task_form = json.load(f)
        # verify that task_template can be converted to a valid Task
        try:
            task_test = models.Task(**task_form)
        except Exception as e:
            logger.error(f"Task file in {os.path.abspath(task_form)} cannot be formed into a valid Task instance. Reason: {str(e)}")
        try:
            processor = tasks.LocalTaskProcessor(task_form=task_form, temp_path=temp_path, logger=logger, **settings.model_dump())
            processor.await_task()
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
