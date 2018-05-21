#!/usr/bin/env python3
# coding:utf-8

"""抓取斗鱼弹幕."""

__author__ = 'zzzzer'

import re
import socket
import struct
import time
from threading import Thread

import requests


# 服务器有效 2018.5.21
SERVER_ADDR = ('223.111.12.101', 12601)


def get_room_info(uid):
    """根据主播的uid(房间url上的), 获取纯数字的room_id和主播中文名.
    
    :param uid: str.

    :return room_id: str, 房间id.
            name: str, 主播中文名.
    """

    url = 'http://www.douyu.com/{}'.format(uid)
    r = requests.get(url)
    pattern = re.compile(r'"room_id":(\d+)')
    room_id = pattern.findall(r.text)[0]
    pattern = re.compile(r'<a class="zb-name">(.*?)</a>')
    name = pattern.findall(r.text)[0]
    return room_id, name


def send_msg(cfd, msg):
    """发给斗鱼服务器所有的包都得加上消息头, 格式见斗鱼弹幕手册.
    
    :param msg: str.
    """

    content = msg.encode()
    # 消息长度, 这里加8而不是加12.所以实际tcp数据部分长度会比斗鱼协议头长度大4
    length = len(content) + 8
    # 689代表客户端向服务器发送的数据, 690代表服务器向客户端发送的数据
    code = 689
    head = struct.pack('i', length) + struct.pack('i', length) + struct.pack('i', code)
    cfd.sendall(head + content)


def init(uid):
    """向服务器发送相应数据包, 准备接收弹幕.
    
    :param uid: str, 主播的uid(房间url上的).
    
    :return cfd: 套接字描述符.
    """

    room_id, name = get_room_info(uid)
    cfd = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    cfd.connect(SERVER_ADDR)
    # loginreq中的req指requests, 还需要紧接着发下面一个包, 服务器会返回loginres
    msg_login = 'type@=loginreq/username@=/password@=/roomid@={}/\x00'.format(room_id)
    send_msg(cfd, msg_login)
    print('你进入了{}的直播间，房间id是{}'.format(name, room_id))
    # 直觉认为这里暂停一秒比较好
    time.sleep(1)
    # gid=-9999代表接收海量弹幕, 发完下面这个包, 服务器才会向客户端发送弹幕
    msg_join = 'type@=joingroup/rid@={}/gid@=-9999/\x00'.format(room_id)
    send_msg(cfd, msg_join)
    return cfd
    

def get_dm(cfd):
    """接受服务器消息, 并提取弹幕信息."""

    pattern = re.compile(b'type@=chatmsg/.+?/nn@=(.+?)/txt@=(.+?)/.+?/level@=(.+?)/')
    while True:
        # 接收的包有可能被分割, 需要把它们重新合并起来, 不然信息可能会缺失
        buffer = b''
        while True:
            recv_data = cfd.recv(4096)
            buffer += recv_data
            if recv_data.endswith(b'\x00'):
                break
        for nn, txt, level in pattern.findall(buffer):
            # 斗鱼有些表情会引发unicode编码错误
            # `error='replace'`, 把其替换成'?'
            print('[lv.{:0<2}][{}]: {}'.
                    format(level.decode(), nn.decode(), txt.decode(errors='replace').strip()))


def keep_live(cfd):
    """每隔40s发送心跳包."""

    while True:
        time.sleep(40)
        msg_keep = 'type@=mrkl/\x00'
        send_msg(cfd, msg_keep)


def main():
    uid = input('请输入主播uid：')
    cfd = init(uid)
    t1 = Thread(target=get_dm, args=(cfd,))
    t2 = Thread(target=keep_live, args=(cfd,))
    t1.start()
    t2.start()


if __name__ == '__main__':
    main()
