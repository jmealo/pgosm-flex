"""Import Mode provides class to ease logic related to various import modes.
"""
import logging
import json
from packaging.version import parse as parse_version

import helpers


class ImportMode():
    """Determines logical variables used to control program flow.

    WARNING:  The values for `append_first_run` and `replication_update`
    are used to determine when to drop the local DB.  Be careful with any
    changes to these values.
    """
    def __init__(self, replication: bool, replication_update: bool,
                 update: str, force: bool):
        """Computes two variables, slim_no_drop and append_first_run
        based on inputs.

        Parameters
        --------------------------
        replication : bool
        replication_update : bool
        update : str or None
            Valid options are 'create' or 'append', lining up with osm2pgsql's
            `--create` and `--append` modes.
        force : bool
        """
        self.logger = logging.getLogger('pgosm-flex')
        self.replication = replication
        self.replication_update = replication_update

        # The input via click should enforce this, still worth checking here
        valid_update_options = ['append', 'create', None]

        if update not in valid_update_options:
            raise ValueError(f'Invalid option for --update. Valid options: {valid_update_options}')

        self.update = update
        self.force = force

        self.set_slim_no_drop()
        self.set_append_first_run()
        self.set_run_post_sql()


    def okay_to_run(self, prior_import: dict) -> bool:
        """Determines if it is okay to run PgOSM Flex without fear of data loss.

        This logic was along with the `--force` option to make it
        less likely to accidentally lose data with improper PgOSM Flex
        options.

        Remember, this is free and open source software and there is
        no warranty!
        This does not imply a guarantee that you **cannot** lose data,
        only that we want to make it **less likely** something bad will happen.
        If you find a way bad things can happen that could be detected here,
        please open an issue:

            https://github.com/rustprooflabs/pgosm-flex/issues/new?assignees=&labels=&projects=&template=bug_report.md&title=Data%20Safety%20Idea

        Parameters
        -------------------
        prior_import : dict
            Details about the latest import from osm.pgosm_flex table.

            An empty dictionary (len==0) indicates no prior import.
            Only the replication key is specifically used

        Returns
        -------------------
        okay_to_run : bool
        """
        self.logger.debug(f'Checking if it is okay to run...')
        if self.force:
            self.logger.warn(f'Using --force, kiss existing data goodbye')
            return True

        # If no prior imports, do not require force
        if len(prior_import) == 0:
            self.logger.debug(f'No prior import found, okay to proceed.')
            return True

        prior_replication = prior_import['replication']

        # Check git version against latest.
        # If current version is lower than prior version from latest import, stop.
        prior_import_version = prior_import['pgosm_flex_version_no_hash']
        git_tag = helpers.get_git_info(tag_only=True)

        if git_tag == '-- (version unknown) --':
            msg = 'Unable to detect PgOSM Flex version from Git.'
            msg += ' Not enforcing version check against prior version.'
            self.logger.warning(msg)
        elif parse_version(git_tag) < parse_version(prior_import_version):
            msg = f'PgOSM Flex version ({git_tag}) is lower than latest import'
            msg += f' tracked in the pgosm_flex table ({prior_import_version}).'
            msg += f' Use PgOSM Flex version {prior_import_version} or newer'
            self.logger.error(msg)
            return False
        else:
            self.logger.info(f'Prior import used PgOSM Flex: {prior_import_version}')

        if self.replication:
            if not prior_replication:
                self.logger.error('Running w/ replication but prior import did not.  Requires --force to proceed.')
                return False
            self.logger.debug('Okay to proceed with replication')
            return True

        msg = 'Prior data exists in the osm schema and --force was not used.'
        self.logger.error(msg)
        return False

    def set_append_first_run(self):
        """Uses `replication_update` and `update` to determine value for
        `self.append_first_run`
        """
        if self.replication_update:
            self.append_first_run = False
        else:
            self.append_first_run = True

        if self.update is not None:
            if self.update == 'create':
                self.append_first_run = True
            else:
                self.append_first_run = False

    def set_slim_no_drop(self):
        """Uses `replication` and `update` to determine value for
        `self.slim_no_drop`
        """
        self.slim_no_drop = False

        if self.replication:
            self.slim_no_drop = True

        if self.update is not None:
            self.slim_no_drop = True

    def set_run_post_sql(self):
        """Uses `update` value to determine value for
        `self.run_post_sql`.  This value determines if the post-processing SQL
        should be executed.

        Note:  Not checking replication/replication_update because subsequent
        imports use osm2pgsql-replication, which does not attempt to run
        the post-processing SQL scripts.
        """
        self.run_post_sql = True

        if self.update is not None:
            if self.update == 'append':
                self.run_post_sql = False

    def as_json(self) -> str:
        """Packs key details as a dictionary passed through `json.dumps()`

        Returns
        ------------------------
        json_text : str
            Text representation of JSON object built using class attributes.
        """
        self_as_dict = {'update': self.update,
                'replication': self.replication,
                'replication_update': self.replication_update,
                'append_first_run': self.append_first_run,
                'slim_no_drop': self.slim_no_drop,
                'run_post_sql': self.run_post_sql}
        return json.dumps(self_as_dict)

