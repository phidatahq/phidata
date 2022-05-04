from typing import Optional

from phidata.utils.log import logger
from phidata.task import PythonTask, PythonTaskArgs
from phidata.infra.aws.resource.glue.crawler import GlueCrawler


class StartGlueCrawlerArgs(PythonTaskArgs):
    crawler: GlueCrawler
    create_crawler: bool = True


class StartGlueCrawler(PythonTask):
    def __init__(
        self,
        crawler: GlueCrawler,
        create_crawler: bool = True,
        name: str = "start_glue_crawler",
        task_id: Optional[str] = None,
        dag_id: Optional[str] = None,
        version: Optional[str] = None,
        enabled: bool = True,
    ):
        super().__init__()
        try:
            self.args: StartGlueCrawlerArgs = StartGlueCrawlerArgs(
                crawler=crawler,
                create_crawler=create_crawler,
                name=name,
                task_id=task_id,
                dag_id=dag_id,
                version=version,
                enabled=enabled,
                entrypoint=start_glue_crawler,
            )
        except Exception as e:
            logger.error(f"Args for {self.__class__.__name__} are not valid")
            raise

    @property
    def crawler(self) -> GlueCrawler:
        return self.args.crawler

    @crawler.setter
    def crawler(self, crawler: GlueCrawler) -> None:
        if crawler is not None:
            self.args.crawler = crawler

    @property
    def create_crawler(self) -> bool:
        return self.args.create_crawler

    @create_crawler.setter
    def create_crawler(self, create_crawler: bool) -> None:
        if create_crawler is not None:
            self.args.create_crawler = create_crawler


def start_glue_crawler(**kwargs) -> bool:

    args: StartGlueCrawlerArgs = StartGlueCrawlerArgs(**kwargs)
    # logger.debug("StartGlueCrawlerArgs: {}".format(args))

    if args.create_crawler:
        create_success = args.crawler.create()
        if not create_success:
            logger.warning("Crawler could not be created.")

    return args.crawler.start_crawler()
