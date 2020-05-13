"""
使用py脚本启动程序
"""
import platform
from multiprocessing import Process

from Api.ProxyApi import runFlask, runFlaskWithGunicorn
from Schedule.ProxyScheduler import runScheduler


def schedule():
    """ 启动调度程序 """
    runScheduler()


def webserver():
    """ 启动web服务 """
    if platform.system() == "Windows":
        runFlask()
    else:
        runFlaskWithGunicorn()


if __name__ == '__main__':
    Process(target=schedule).start()
    Process(target=webserver).start()
