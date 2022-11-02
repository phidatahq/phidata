from typing import Optional

from phidata.app.phidata_app import PhidataApp, PhidataAppArgs
from phidata.utils.log import logger


class DbAppArgs(PhidataAppArgs):
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_schema: Optional[str] = None
    db_driver: Optional[str] = None


class DbApp(PhidataApp):
    def __init__(self):
        super().__init__()
        self.args: DbAppArgs

    def get_db_user(self) -> Optional[str]:
        logger.debug(f"@get_db_user not defined for {self.__class__.__name__}")
        return self.args.db_user if self.args else None

    def get_db_password(self) -> Optional[str]:
        logger.debug(f"@get_db_password not defined for {self.__class__.__name__}")
        return self.args.db_password if self.args else None

    def get_db_schema(self) -> Optional[str]:
        logger.debug(f"@get_db_schema not defined for {self.__class__.__name__}")
        return self.args.db_schema if self.args else None

    def get_db_driver(self) -> Optional[str]:
        logger.debug(f"@get_db_driver not defined for {self.__class__.__name__}")
        return self.args.db_driver if self.args else None

    def get_db_host_local(self) -> Optional[str]:
        logger.debug(f"@get_db_host_local not defined for {self.__class__.__name__}")
        return None

    def get_db_port_local(self) -> Optional[int]:
        logger.debug(f"@get_db_port_local not defined for {self.__class__.__name__}")
        return None

    def get_db_host_docker(self) -> Optional[str]:
        logger.debug(f"@get_db_host_docker not defined for {self.__class__.__name__}")
        return None

    def get_db_port_docker(self) -> Optional[int]:
        logger.debug(f"@get_db_port_docker not defined for {self.__class__.__name__}")
        return None

    def get_db_host_k8s(self) -> Optional[str]:
        logger.debug(f"@get_db_host_k8s not defined for {self.__class__.__name__}")
        return None

    def get_db_port_k8s(self) -> Optional[int]:
        logger.debug(f"@get_db_port_k8s not defined for {self.__class__.__name__}")
        return None

    def get_db_connection_url_local(self) -> Optional[str]:
        user = self.get_db_user()
        password = self.get_db_password()
        schema = self.get_db_schema()
        driver = self.get_db_driver()
        host = self.get_db_host_local()
        port = self.get_db_port_local()
        return f"{driver}://{user}:{password}@{host}:{port}/{schema}"

    def get_db_connection_url_docker(self) -> Optional[str]:
        user = self.get_db_user()
        password = self.get_db_password()
        schema = self.get_db_schema()
        driver = self.get_db_driver()
        host = self.get_db_host_docker()
        port = self.get_db_port_docker()
        return f"{driver}://{user}:{password}@{host}:{port}/{schema}"

    def get_db_connection_url_k8s(self) -> Optional[str]:
        user = self.get_db_user()
        password = self.get_db_password()
        schema = self.get_db_schema()
        driver = self.get_db_driver()
        host = self.get_db_host_k8s()
        port = self.get_db_port_k8s()
        return f"{driver}://{user}:{password}@{host}:{port}/{schema}"
