import numpy as np
import os
import shutil

# functions to manage that disk space remains below a threshold
def get_free_space(path_dir):
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

    return free_space

def scan_folder(incoming, clean_empty_dirs=True, suffix=None):
    """
    File scanner for designated incoming path.
    Remove empty directories automatically

    Parameters
    ----------
    incoming : list or str, path-like
        folder or multiple folder containing relevant files
    clean_empty_dirs : bool, optional
        setting to cleanup found empty dirs, defaults to True
    suffix : str, optional
        suffix to use for finding relevant files

    Returns
    -------
    """
    incoming = list(np.atleast_1d(incoming))
    file_paths = []
    for folder in incoming:
        if not folder:
            return file_paths
        for root, paths, files in os.walk(folder):
            if clean_empty_dirs:
                if len(paths) == 0 and len(files) == 0:
                    # remove the empty folder if it is not the top folder
                    if os.path.abspath(root) != os.path.abspath(folder):
                        os.rmdir(root)
            for f in files:
                if type(f) is bytes:
                    f = f.decode()
                full_path = os.path.join(root, f)
                if suffix is not None:
                    if full_path[-len(suffix):] == suffix:
                        file_paths.append(full_path)
                else:
                    file_paths.append(full_path)
    return file_paths

def delete_folder(path_to_folder, logger):
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

def delete_file(path_to_file, logger):
    """
    Deletes a file
    :param path_to_file: [str]
    :return:
    """
    try:
        os.remove(path_to_file)
        logger.info(f"Purged {path_to_file}")
        return True
    except:
        logger.error(
            "Could not remove file" + str(path_to_file),
            exc_info=True
        )
        return False

def purge(paths, free_space, min_free_space, logger, home="/home"):
    # check for files
    fns = scan_folder(paths)
    # get timestamp of files
    timestamps = [os.path.getmtime(fn) for fn in fns]
    # sort all on time stamps
    idx = np.argsort(timestamps)
    fns = list(np.array(fns)[idx])
    timestamps = list(np.array(timestamps)[idx])
    cur_idx = 0
    while free_space < min_free_space:
        if cur_idx > len(fns) - 1:
            # apparently there is no way to free up more space than needed, return a serious error
            logger.warning(f"No files can be deleted, but free space {free_space} GB is lower than threshold {min_free_space} GB")
            return False
        # keep on removing files until the free space is sufficient again
        if not(delete_file(fns[cur_idx], logger=logger)):
            logger.warning(
                f"File {fns[cur_idx]} could not be deleted, skipping..."
            )
        free_space = get_free_space(home)
        # continue with the next file in the list
        cur_idx += 1
    return True
