"""Generic functions used in multiple modules.
"""
import datetime
import logging
import subprocess
import os
import sys
from time import sleep

import db


DEFAULT_SRID = '3857'


def get_today():
    """Returns yyyy-mm-dd formatted string for today.

    Retunrs
    -------------------------
    today : str
    """
    today = datetime.datetime.today().strftime('%Y-%m-%d')
    return today


def run_command_via_subprocess(cmd, cwd):
    """Wraps around subprocess.Popen to run commands outside of Python. Prints
    output as it goes, returns the status code from the command.

    Parameters
    -----------------------
    cmd : list
        Parts of the command to run.
    cwd : str or None
        Set the working directory, or to None.

    Returns
    -----------------------
    status : int
        Return code from command
    """
    logger = logging.getLogger('pgosm-flex')
    with subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT
                          ) as process:
        while True:
            output = process.stdout.readline()
            if process.poll() is not None and output == b'':
                break

            if output:
                logger.info(output.strip().decode('utf-8'))
            else:
                # Only sleep when there wasn't output
                sleep(1)
        status = process.poll()
    return status


def verify_checksum(md5_file, path):
    """If verfication fails calls `sys.exit()`

    Parameters
    ---------------------
    md5_file : str
    path : str
        Path to directory with `md5_file` to validate
    """
    logger = logging.getLogger('pgosm-flex')
    logger.debug(f'Validating {md5_file} in {path}')

    returncode = run_command_via_subprocess(cmd=['md5sum', '-c', md5_file],
                                            cwd=path)

    if returncode != 0:
        err_msg = f'Failed to validate md5sum. Return code: {output.returncode}'
        logger.error(err_msg)
        sys.exit(err_msg)

    logger.debug('md5sum validated')


def set_env_vars(region, subregion, srid, language, pgosm_date, layerset,
                 layerset_path):
    """Sets environment variables needed by PgOSM Flex.

    See /docs/MANUAL-STEPS-RUN.md for usage examples of environment variables.

    Parameters
    ------------------------
    region : str
    subregion : str
    srid : str
    language : str
    pgosm_date : str
    layerset : str
    layerset_path : str
        str when set, or None
    """
    logger = logging.getLogger('pgosm-flex')
    logger.debug('Ensuring env vars are not set from prior run')
    unset_env_vars()
    logger.debug('Setting environment variables')

    os.environ['PGOSM_REGION'] = region

    if subregion is None:
        pgosm_region = f'{region}'
    else:
        os.environ['PGOSM_SUBREGION'] = subregion
        pgosm_region = f'{region}-{subregion}'

    # Used by helpers.lua
    logger.debug(f'PGOSM_REGION_COMBINED: {pgosm_region}')
    os.environ['PGOSM_REGION_COMBINED'] = pgosm_region

    if srid != DEFAULT_SRID:
        logger.info(f'SRID set: {srid}')
        os.environ['PGOSM_SRID'] = str(srid)
    if language is not None:
        logger.info(f'Language set: {language}')
        os.environ['PGOSM_LANGUAGE'] = str(language)

    if layerset_path is not None:
        logger.info(f'Custom layerset path set: {layerset_path}')
        os.environ['PGOSM_LAYERSET_PATH'] = str(layerset_path)

    os.environ['PGOSM_DATE'] = pgosm_date
    os.environ['PGOSM_LAYERSET'] = layerset

    # PGOSM_CONN is required to be set by the Lua styles used by osm2pgsql
    os.environ['PGOSM_CONN'] = db.connection_string()
    # Connection to DB for admin purposes, e.g. drop/create main database
    os.environ['PGOSM_CONN_PG'] = db.connection_string(admin=True)


def unset_env_vars():
    """Unsets environment variables used by PgOSM Flex.

    Does not pop POSTGRES_DB on purpose to allow non-Docker operation.
    """
    os.environ.pop('PGOSM_REGION', None)
    os.environ.pop('PGOSM_SUBREGION', None)
    os.environ.pop('PGOSM_COMBINED', None)
    os.environ.pop('PGOSM_SRID', None)
    os.environ.pop('PGOSM_LANGUAGE', None)
    os.environ.pop('PGOSM_LAYERSET_PATH', None)
    os.environ.pop('PGOSM_DATE', None)
    os.environ.pop('PGOSM_LAYERSET', None)
    os.environ.pop('PGOSM_CONN', None)
    os.environ.pop('PGOSM_CONN_PG', None)
