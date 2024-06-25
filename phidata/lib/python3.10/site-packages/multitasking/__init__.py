#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# multitasking: Non-blocking Python methods using decorators
# https://github.com/ranaroussi/multitasking
#
# Copyright 2016-2021 Ran Aroussi
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

__version__ = "0.0.11"

import time as _time

from sys import exit as sysexit
from os import _exit as osexit

from threading import Thread, Semaphore
from multiprocessing import Process, cpu_count

config = {
    "CPU_CORES": cpu_count(),
    "ENGINE": "thread",
    "MAX_THREADS": cpu_count(),
    "KILL_RECEIVED": False,
    "TASKS": [],
    "POOLS": {},
    "POOL_NAME": "Main"
}


def set_max_threads(threads=None):
    if threads is not None:
        config["MAX_THREADS"] = threads
    else:
        config["MAX_THREADS"] = cpu_count()


def set_engine(kind=""):
    if "process" in kind.lower():
        config["ENGINE"] = "process"
    else:
        config["ENGINE"] = "thread"


def getPool(name=None):
    if name is None:
        name = config["POOL_NAME"]

    engine = "thread"
    if config["POOLS"][config["POOL_NAME"]]["engine"] == Thread:
        engine = "process"

    return {
        "engine": engine,
        "name": name,
        "threads": config["POOLS"][config["POOL_NAME"]]["threads"]
    }


def createPool(name="main", threads=None, engine=None):

    config["POOL_NAME"] = name

    try:
        threads = int(threads)
    except Exception:
        threads = config["MAX_THREADS"]
    if threads < 2:
        threads = 0

    engine = engine if engine is not None else config["ENGINE"]

    config["MAX_THREADS"] = threads
    config["ENGINE"] = engine

    config["POOLS"][config["POOL_NAME"]] = {
        "pool": Semaphore(threads) if threads > 0 else None,
        "engine": Process if "process" in engine.lower() else Thread,
        "name": name,
        "threads": threads
    }


def task(callee):

    # create default pool if nont exists
    if not config["POOLS"]:
        createPool()

    def _run_via_pool(*args, **kwargs):
        with config["POOLS"][config["POOL_NAME"]]['pool']:
            return callee(*args, **kwargs)

    def async_method(*args, **kwargs):
        # no threads
        if config["POOLS"][config["POOL_NAME"]]['threads'] == 0:
            return callee(*args, **kwargs)

        # has threads
        if not config["KILL_RECEIVED"]:
            try:
                single = config["POOLS"][config["POOL_NAME"]]['engine'](
                    target=_run_via_pool, args=args,
                    kwargs=kwargs, daemon=False)
            except Exception:
                single = config["POOLS"][config["POOL_NAME"]]['engine'](
                    target=_run_via_pool, args=args, kwargs=kwargs)
            config["TASKS"].append(single)
            single.start()
            return single

    return async_method

def get_list_of_tasks():
    return config["TASKS"]

def get_active_tasks():
    return [x for x in config["TASKS"] if x.is_alive()]

def wait_for_tasks(sleep=0):
    config["KILL_RECEIVED"] = True

    if config["POOLS"][config["POOL_NAME"]]['threads'] == 0:
        return True

    try:
        while True:
            running = len([t.join(1) for t in config["TASKS"]
                           if t is not None and t.is_alive()])
            if running == 0:
                break
            _time.sleep(sleep)
    except Exception:
        pass

    config["KILL_RECEIVED"] = False

    return True


def killall(self, cls):
    config["KILL_RECEIVED"] = True
    try:
        sysexit(0)
    except SystemExit:
        osexit(0)

    config["KILL_RECEIVED"] = False
