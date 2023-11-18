import logging
import os
import shutil

# functions to manage that disk space remains below a threshold
def get_free_space(path_dir, logger=logging):
    """

    Parameters
    ----------
    path_dir : str, path-like
        root dir from which to check for space.
    logger : Logger
        logging object

    Returns
    -------

    """
    # --- Get size of HDD ---
    f = os.statvfs(path_dir)
    free_space = f.f_frsize * f.f_bavail
    free_space = free_space / 10e8
    logger.info("Free space on machine is " + str(free_space) + " GB")

    return free_space


def delete_folder(path_to_folder, logger=logging):
    """
    Deletes a complete folder with all contents
    :param path_to_folder: [str]
    :return:
    """
    try:
        shutil.rmtree(path_to_folder)
        logger.info(
            "Removed folder: " + str(path_to_folder)
        )
        return True
    except:
        logger.error(
            "Could not remove directory" + str(path_to_folder),
            exc_info=True
        )
        return False

def delete_file(path_to_file):
    """
    Deletes a file
    :param path_to_file: [str]
    :return:
    """
    try:
        os.remove(path_to_file)
        return True
    except:
        logging.error(
            "Could not remove file" + str(path_to_file),
            exc_info=True
        )
        return False

