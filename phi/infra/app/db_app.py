from typing import Optional

from phi.infra.app.base import InfraApp, ContainerContext, InfraResource  # noqa: F401


class DbApp(InfraApp):
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_schema: Optional[str] = None
    db_driver: Optional[str] = None

    def get_db_user(self) -> Optional[str]:
        return self.db_user or self.get_secret_from_file("DB_USER")

    def get_db_password(self) -> Optional[str]:
        return self.db_password or self.get_secret_from_file("DB_PASSWORD")

    def get_db_schema(self) -> Optional[str]:
        return self.db_schema or self.get_secret_from_file("DB_SCHEMA")

    def get_db_driver(self) -> Optional[str]:
        return self.db_driver or self.get_secret_from_file("DB_DRIVER")

    def get_db_host(self) -> Optional[str]:
        raise NotImplementedError

    def get_db_port(self) -> Optional[int]:
        raise NotImplementedError

    def get_db_connection(self) -> Optional[str]:
        user = self.get_db_user()
        password = self.get_db_password()
        schema = self.get_db_schema()
        driver = self.get_db_driver()
        host = self.get_db_host()
        port = self.get_db_port()
        return f"{driver}://{user}:{password}@{host}:{port}/{schema}"

    def get_db_host_local(self) -> Optional[str]:
        return "localhost"

    def get_db_port_local(self) -> Optional[int]:
        return self.host_port

    def get_db_connection_local(self) -> Optional[str]:
        user = self.get_db_user()
        password = self.get_db_password()
        schema = self.get_db_schema()
        driver = self.get_db_driver()
        host = self.get_db_host_local()
        port = self.get_db_port_local()
        return f"{driver}://{user}:{password}@{host}:{port}/{schema}"
