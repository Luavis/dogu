
import logging
import sys

logger = logging.getLogger('dogu')

hdlr = logging.StreamHandler(sys.stdout)  # logging.FileHandler('/var/tmp/myapp.log')

formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

hdlr.setFormatter(formatter)

logger.addHandler(hdlr)

logger.setLevel(logging.DEBUG)
