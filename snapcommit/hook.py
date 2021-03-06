import os
import json
import logging
from logging.handlers import RotatingFileHandler
from os import path

import requests

import snapconfig
import gitops
import grab


log_levels = {
    'info': logging.INFO,
    'debug': logging.DEBUG,
    'error': logging.ERROR,
    'warn': logging.WARNING,
    'critical': logging.CRITICAL,
}

def logger(config):
    log_dir = config['log_dir']
    if log_dir.startswith('~'):
        log_dir = log_dir.replace('~', os.path.expanduser('~'))
    log_file = path.join(log_dir, 'snap-commit-hook.log')
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    handler = RotatingFileHandler(log_file, maxBytes=5242880, backupCount=2)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    logger = logging.getLogger('snap-commit-hook')
    logger.setLevel(log_levels[config['log_level']])
    logger.addHandler(handler)
    return logger

def new_path(prefix=None):
    commit = gitops.get_commit()
    remote = gitops.get_remote_url()
    if remote:
        host = remote.split('.')[0].split('@')[1]
        user, repo = remote.split(':')[1].replace('.git', '').split('/')
    else:
        host, user, repo = ['', '', '']
    filename = '{}_{}_{}_{}_{}.jpg'.format(
        commit.commit_time*1000,
        commit.hex[:7],
        user,
        repo,
        host
    )
    if prefix:
        paths = [prefix, filename]
    else:
        paths = [filename]
    return path.join(*paths)

def upload(config):
    log = config['logger']
    base = config['image_dir']
    for item in os.listdir(base):
        try:
            filepath = path.join(base, item)
            r = requests.post(
                config['snap_server'] + '/v1',
                files={'file': (item, open(filepath, 'rb'))}
            )
            if r.ok:
                if not config.get('keep_snaps', False):
                    os.remove(filepath)
                    log.debug('Removed {}'.format(filepath))
            else:
                log.error('error occurred {} {} while uploading {}'.format(
                        r.status_code,
                        r.text,
                        item
                    )
                )
        except requests.exceptions.RequestException, e:
            log.error('error occurred {} while uploading {}'.format(e, item))
            log.info('saving image for next upload')

def run_hook(config):
    file_path = new_path(config['image_dir'])
    try:
        os.makedirs(path.dirname(file_path))
    except OSError, e:
        if e.errno is not 17:
            raise
    grab.grab_image(
        file_path,
        width=config['width'],
        height=config['height'],
        device=config['video_device']
    )

def main():
    import sys
    if len(sys.argv) > 1:
        config = snapconfig.load_config(sys.argv[1])
    else:
        config = snapconfig.load_config()
    config['logger'] = logger(config)
    run_hook(config)
    if config.get('snap_server') and config['snap_server']:
        upload(config)
    sys.exit(0)


if __name__ == '__main__':
    main()
