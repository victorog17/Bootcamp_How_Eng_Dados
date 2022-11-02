from abc import ABC, abstractmethod
from datetime import datetime, date, timedelta
import time
from schedule import repeat, every, run_pending
import json
import os
from typing import List
import requests
import logging
from backoff import on_exception, expo
import ratelimit

from traitlets import default

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class MercadoBitcoinApi(ABC):
    def __init__(self, coin: str) -> None:
        self.coin = coin
        self.base_endpoint = "https://www.mercadobitcoin.net/api"

    @abstractmethod
    def _get_endpoint(self, **kwargs) -> str:
        pass
        
    @on_exception(expo, ratelimit.exception.RateLimitException, max_tries=10)
    @ratelimit.limits(calls=29, period=30)
    @on_exception(expo, requests.exceptions.HTTPError, max_tries=10)
    def get_data(self, **kwargs) -> dict:
        endpoint = self._get_endpoint(**kwargs)
        logger.info(f"Getting data from endpoint: {endpoint}")
        response = requests.get(endpoint)
        response.raise_for_status()
        return response.json()

class DaySummaryApi(MercadoBitcoinApi):
    type = "day-summary"
    def _get_endpoint(self, date: date) -> str:
        return f"{self.base_endpoint}/{self.coin}/{self.type}/{date.year}/{date.month}/{date.day}"

class TradesApi(MercadoBitcoinApi):
    type = "trades"

    def _get_unix_epoch(self, date: datetime) -> int:
        return int(date.timestamp())

    def _get_endpoint(self, date_from: datetime = None, date_to: datetime = None) -> str:
        if date_from and not date_to:
            unix_date_from = self._get_unix_epoch(date_from)
            endpoint = f"{self.base_endpoint}/{self.coin}/{self.type}/{unix_date_from}"
        elif date_from and date_to:
            unix_date_from = self._get_unix_epoch(date_from)
            unix_date_to = self._get_unix_epoch(date_to)
            endpoint = f"{self.base_endpoint}/{self.coin}/{self.type}/{unix_date_from}/{unix_date_to}"
        else:
            endpoint = f"{self.base_endpoint}/{self.coin}/{self.type}"

        return endpoint


class DataTypeNotSupportedForIngestionException(Exception):
    def __init__(self, data):
        self.data = data
        self.message = f"Data type {type(data)} is not supported for ingestion"
        super().__init__(self.message)

class DataWritter:

    def __init__(self, coin: str, api: str) -> None:
        self.coin = coin
        self.api = api
        self.filename = f"{self.api}/{self.coin}/{datetime.now().strftime('%Y-%m-%d')}.json"

    def _write_row(self, row: str) -> None:
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        with open(self.filename, "a") as f:
            f.write(row)

    def write(self, data: [List, dict]):
        if isinstance(data, dict):
            self._write_row(json.dumps(data) + "\n")
        elif isinstance(data, List):
            for element in data:
                self.write(element)
        else:
            raise DataTypeNotSupportedForIngestionException(data)

class DataIngestor(ABC):

    def __init__(self, writer, coins: List[str], default_start_date: date) -> None:
        self.coins = coins
        self.default_start_date = default_start_date
        self.writer = writer
        self._checkpoint = self._load_checkpoint()

    @property
    def _checkpoint_filename(self) -> str:
        return f"{self.__class__.__name__}.checkpoint"

    def _write_checkpoint(self):
        with open(self._checkpoint_filename, "w") as f:
            f.write(f"{self._checkpoint}")

    def _load_checkpoint(self) -> date:
        try:
            with open(self._checkpoint_filename, "r") as f:
                return datetime.strptime(f.read(), "%Y-%m-%d").date()
        except FileExistsError:
            return self.default_start_date

    def _get_checkpoint(self):
        if not self._checkpoint:
            print(f"Foi aqui que rolou: default_start_date - {self.default_start_date}")
            return self.default_start_date
        else:
            print(f"Foi aqui que rolou: _checkpoint - {self._checkpoint}")
            return self._checkpoint

    def _update_checkpoint(self, value):
        self._checkpoint = value
        self._write_checkpoint()

    @abstractmethod
    def ingest(self) -> None:
        pass

class DaySummaryIngestor(DataIngestor):

    def ingest(self) -> None:
        date2 = self._get_checkpoint()
        #date2 = date.today()
        print(f"LINHA 01 {date}")
        print(f"LINHA 02 {datetime.now().strftime('%Y-%m-%d')}")
        #print(f"LINHA 03 {date2}")
        if date2 < date.today():
            for coin in self.coins:
                api = DaySummaryApi(coin=coin)
                data = api.get_data(date=date2)
                self.writer(coin=coin, api=api.type).write(data)
                # atualizar a data
            self._update_checkpoint(date2 + timedelta(days=1))


ingestor = DaySummaryIngestor(writer=DataWritter, coins=["BTC", "ETH", "LTC", "BCH"], default_start_date=date(2021, 6, 1))

@repeat(every(1).seconds)
def job():
    ingestor.ingest()

while True:
    run_pending()
    time.sleep(0.5)