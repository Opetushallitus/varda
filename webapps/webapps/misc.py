import logging
import os

from socket import gaierror, gethostbyname_ex


logger = logging.getLogger(__name__)


def get_memcached_servers():
    """
    Example taken from: https://cloud.google.com/solutions/deploying-memcached-on-kubernetes-engine
    Also good info: https://patrickeasters.com/deploying-memcached-in-a-statefulset/
    """
    try:
        """
        In OpenShift the below command returns only the service-IP. Based on the example above
        the command should return the Pod-IPs (i.e. multiple IPs if more than 1 replica).
        """
        project_hostname = os.getenv('VARDA_HOSTNAME', None)
        if project_hostname is None:
            logger.error('Memcached: Did not get a hostname.')
            return []
        else:
            project_namespace = project_hostname.split(".")[0]

        _, _, ips = gethostbyname_ex('varda-memcached.' + project_namespace + '.svc.cluster.local')
        servers = [ip + ":11211" for ip in ips]
    except gaierror:
        logger.error('Could not get memcached-servers.')
        servers = []
    return servers
