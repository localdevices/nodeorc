import click
import json
import os

from pydantic import ValidationError
from dotenv import load_dotenv
# import tasks

# import nodeorc specifics
from nodeorc import db, log, models, db_ops, tasks, settings_path, utils, __version__

session = db_ops.get_session()  # db.session
# see if there is an active config, if not logger goes to $HOME/.nodeorc
active_config = db_ops.get_active_config(parse=True)
if active_config:
    log_path = active_config.disk_management.log_path
else:
    log_path = None
logger = log.start_logger(
    True,
    False,
    log_path=log_path
)

# load env variables. These are not overridden if they are already defined
load_dotenv()

# temp_path = os.getenv("TEMP_PATH", "./tmp")
# settings_path = os.path.join(os.path.split(__file__)[0], "..", "settings")

device = session.query(db.models.Device).first()

def get_docs_settings():
    fixed_fields = ["id", "created_at", "metadata", "registry", "callback_url", "storage", "settings", "disk_management"]
    # list all attributes except internal and fixed fields
    fields = [f for f in dir(db.models.ActiveConfig) if not(f in fixed_fields) if not f.startswith("_")]
    docs = """JSON-file should contain the following settings: \n"""
    docs += """================================================\n\n"""
    for f in fields:
        attr_doc = getattr(db.models.ActiveConfig, f).comment
        docs += " {} : {}\n\n".format(f[:-3], attr_doc)
    return docs


def load_config(config_fn):
    # define local settings below
    if os.path.isfile(config_fn):
        try:
            with open(config_fn, "r") as f:
                settings = models.LocalConfig(**json.load(f))
            return settings
        except ValidationError as e:
            raise ValueError(
                f"Settings file in {os.path.abspath(config_fn)} contains errors. Error: {e}")


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

def load_script(ctx, param, value):
    with open(value, "r") as f:
        script = f.read()
    return script

def validate_frequency(ctx, param, value):
    if value < 60:
        raise click.BadParameter("Frequency must be at least 60 seconds (i.e. 1 minute)")
    if value > 86400:
        raise click.BadParameter("Frequency must be at most 86400 seconds (i.e. 1 day)")
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
def start():
    # get the device id
    session = db_ops.get_session()
    logger.info(f"Device {str(device)} is online to run video analyses")
    # remote storage parameters with local processing is not possible
    # if listen == "local" and storage == "remote":
    #     raise click.UsageError('Locally defined tasks ("--listen local")  cannot have remotely defined storage ('
    #                           '"--storage remote").')
    # if listen == "local":
    # get the stored configuration
    active_config = db_ops.get_active_config(session=session, parse=True)
    if not(active_config):
        raise click.UsageError(
            'You do not yet have an active configuration. Upload an activate configuration '
            'through the CLI. Type "nodeorc upload-config --help" for more information'
        )
    water_level_config = db_ops.get_water_level_config(session=session)
    if not(water_level_config):
        raise click.UsageError(
            'You do not yet have a water level configuration. Upload a water level retrieval '
            'script through the CLI. Type "nodeorc upload-water-level-script --help" for more information'
        )
    else:
        water_level_config = utils.model_to_dict(water_level_config)
    # initialize the database for storing data
    # session_data = db.init_basedata.get_data_session()
    # read the task form from the configuration
    task_form_template = db_ops.get_active_task_form(session, parse=True)
    callback_url = active_config.callback_url
    if task_form_template is None:
        # go into the task form get daemon and try to acquire a task form from server every 5 minutes
        logger.info("Awaiting task by requesting a new task every 5 seconds")
        tasks.wait_for_task_form(
            session=session,
            callback_url=callback_url,
            device=device,
            logger=logger,
            reboot_after=active_config.settings.reboot_after
        )
        # this return never happens, unless isolated unit tests are run
        return 0
    else:
        # check for a new form with one single request
        logger.info("Checking if a new task form is available for me...")
        new_task_form_row = tasks.request_task_form(
            session=session,
            callback_url=callback_url,
            device=device,
            logger=logger
        )
        if new_task_form_row:
            task_form_template = new_task_form_row.task_body
    # verify that task_template can be converted to a valid Task
    try:
        task_test = models.Task(**task_form_template)
    except Exception as e:
        logger.error(
            f"Task body set as active configuration cannot be formed into a valid Task instance. Reason: {str(e)}"
        )
        # This only happens with version upgrades. Update the status to BROKEN and report back to platform
        task_form_template = db_ops.get_active_task_form(session, parse=False)
        task_form_template.status = db.models.TaskFormStatus.BROKEN
        device.form_status = db.models.DeviceFormStatus.BROKEN_FORM
        session.commit()
    try:
        processor = tasks.LocalTaskProcessor(
            task_form_template=task_form_template,
            logger=logger,
            water_level_config=water_level_config,
            **active_config.model_dump()
        )
        processor.await_task()
    except Exception as e:
        logger.error("Reboot service: %s" % str(e))
    # else:
    #     raise NotImplementedError

@cli.command(
    short_help="Upload a new configuration for this device from a JSON formatted file",
    epilog=get_docs_settings()
)
@click.argument(
    "JSON-file",
    type=click.Path(resolve_path=True, dir_okay=False, file_okay=True),
    required=True,
)
@click.option(
    "-a",
    "--set-as-active",
    is_flag=True,
    default=True,
    help="Flag to define if uploaded configuration should be set as active (default: True)"
)
def upload_config(json_file, set_as_active):
    """Upload a new configuration for this device from a JSON formatted file"""
    logger.info(f"Device {str(device)} receiving new configuration from {json_file}")
    config_ = load_config(json_file)
    rec = db_ops.add_config(session, config=config_, set_as_active=set_as_active)
    logger.info(f"Settings updated successfully to {rec}")

@cli.command(
    short_help="Upload a new water level script to NodeORC database",
)
@click.option(
    "-s",
    "--script",
    type=click.Path(exists=True, dir_okay=False, file_okay=True),
    callback=load_script,
    help="location of the script file",
    required=True
)
@click.option(
    "-t",
    "--script-type",
    type=click.Choice(["python", "bash"]),
    default="bash",
    show_default=True,
    help="Script type (either 'python' or 'bash')",
)
@click.option(
    "-f",
    "--file-template",
    type=str,
    default="wl_{%Y%m%d}.txt",
    help="file template with optional datetime format between curly braces {}.",
    show_default=True,
    required=True,
)
@click.option(
    "-fr",
    "--frequency",
    type=float,
    help="frequency of the script execution in seconds.",
    default=600,
    show_default=True,
    required=True,
    callback=validate_frequency
)
@click.option(
    "-dt",
    "--datetime-fmt",
    type=str,
    default="%Y-%m-%dT%H:%M:%SZ",
    help="datetime format of datetime indexes in the water level files.",
    show_default=True,
)
def upload_water_level_script(script, script_type, file_template, frequency, datetime_fmt):
    logger.info(f"Device {str(device)} receiving new water level script configuration. Script must provide ")
    logger.info(
        "valid outputs. If API is called, ensure a valid response is returned and you are connected to internet."
    )

    rec = db_ops.add_replace_water_level_script(
        session,
        script,
        script_type,
        file_template,
        frequency,
        datetime_fmt
    )
    logger.info(f"Settings updated successfully to {rec}")


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


upload_config.__doc__ = get_docs_settings()

if __name__ == "__main__":
    cli()
