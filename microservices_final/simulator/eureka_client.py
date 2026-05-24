import py_eureka_client.eureka_client as eureka_client
import logging

logger = logging.getLogger(__name__)

def register(app_name, port):
    try:
        eureka_client.init(
            eureka_server="http://discovery-service:8761/eureka/",
            app_name=app_name,
            instance_port=port,
            instance_host="simulator",
            health_check_url=f"http://simulator:{port}/health",
            renewal_interval_in_secs=10,
            duration_in_secs=30
        )
        logger.info(f"Registered {app_name} with Eureka")
    except Exception as e:
        logger.error(f"Eureka registration failed: {e}")
