#!/usr/bin/env python3
# -*- coding: utf8 -*-
'''
Author       : Pooneyy
Date         : 2023-03-14 20:08:52
LastEditors  : Pooneyy 85266337+pooneyy@users.noreply.github.com
LastEditTime : 2023-03-31 21:48:32
FilePath     : /suanleme/index.py
Description  : “算了么”平台 监听任务列表

Copyright (c) 2023-2024 by Pooneyy, All Rights Reserved. 
'''

import json
import os
import datetime, pytz, time
import sys
import requests

VERSION = '1.3' # 2024.01.25
CONFIG_VERSION = 2
HOST = "https://api.suanleme.cn/api/v1"

def timeStamp_To_dateTime(timeStamp):return datetime.datetime.fromtimestamp(int(timeStamp), pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')

def isoDateTime_To_dateTime(iso_date_time):return datetime.datetime.strptime(iso_date_time, "%Y-%m-%dT%H:%M:%S.%f%z").strftime('%Y-%m-%d<br />%H:%M:%S')

def saveConfig(config):
    config['tasks_record'] = dict(sorted(config['tasks_record'].items(), reverse=True))
    with open("config.json", "w", encoding='utf8') as file:
        json.dump(config, file, ensure_ascii=False, indent = 4)

def loadConfig():
    with open("config.json", "r+", encoding='utf8') as file:
        config = json.load(file)
    config['tasks_record'] = {int(key):config['tasks_record'][key] for key in config['tasks_record']}
    return config

def checkUpdate():
    url = "https://api.github.com/repos/pooneyy/suanleme/releases/latest"
    try:
        response = requests.get(url)
        latest = json.loads(response.text)["tag_name"]
        return VERSION != latest
    except:return False

def init():
    print('首次运行初始化')
    config = {}
    config['config_version'] = CONFIG_VERSION
    config['latest_id'] = 0
    config['suanleme_username'] = input('请输入算了么账号：')
    config['suanleme_password'] = input('请输入算了么密码：')
    config['truecaptcha_userid'] = ''
    config['truecaptcha_apikey'] = ''
    config['pushplus_token'] = input('请输入pushplus推送加的token：')
    config['pushplus_topic'] = input('(选填)输入pushplus推送加的群组编码：')
    config['tasks_record'] = {}
    saveConfig(config)
    print('初始化完成，请重新运行')

def sendMsg(config, msg):
    data = {}
    url = "http://www.pushplus.plus/send"
    data['token'] = config['pushplus_token']
    data['title'] = '算了么来新单啦！'
    data['template'] = 'html'
    data['topic'] = config['pushplus_topic'] # 群组编码，发送群组消息。
    data['content'] = msg
    response = requests.post(url,data=data)
    return response.text

def login(config):
    url = f"{HOST}/user/token"
    payload={
        'username': config['suanleme_username'],
        'password': config['suanleme_password'],
    }
    response = requests.post(url, data=payload)
    print(f"{timeStamp_To_dateTime(time.time())}\t登录成功")
    refresh_token = response.json()['refresh']
    return refresh_token

def refresh(refresh_token):
    url = f"{HOST}/user/token/refresh"
    payload={'refresh': refresh_token}
    response = requests.post(url, data=payload)
    return response.json()["access"]

def getTasks(refresh_token):
    '''获取全部订单'''
    url = f"{HOST}/tasks/?page=1&data_type=all"
    headers = {'Authorization': f'Bearer {refresh(refresh_token)}'}
    response = requests.get(url, headers=headers)
    response.close()
    return response.json()

def analyzing_tasks_info(tasks):
    '''分析订单页面
    这是一个订单信息的数据结构
    ```json
{
    "id": 107,              //订单id
    "author": 23,           //发布者id?
    "status": "Running",    //状态 Running / Finished / Canceled / Received
    "finished_points": 28,  //已完成任务点
    "running_points": 2,    //进行中任务点
    "name": "cytx",         //任务名
    "desc": "cytx",         //任务描述
    "peer_income": 1,       //单位收益
    "expect_time": "1",     //预期单位时长
    "type": "Deployment",   //类型 Deployment / Job
    "points": 30,           //总任务点
    "cpu_required": 0,      //硬件要求 CPU核心数
    "memory_required": 0,   //硬件要求 内存 单位GB
    "disk_required": 0,     //硬件要求 磁盘空间要求 单位GB
    "time_required": "00:00:00",    //连续时长要求
    "created_time": "2024-01-10T11:19:36.165607+08:00", //创建时间()
    "modify_time": "2024-01-19T17:48:05.918623+08:00",  //修改时间
    "finished_time": "2024-01-18T07:31:00+08:00",       //完成时间
    "runtime": 4,
    "package": "eca6bf8b-d71d-4143-b259-f7ca9294d9ff",
    "joined_user": [ //参加计算成员id?
        1,
        22,
        36,
        46,
        47,
        50
    ],
    "affinity": [
        1,
        2
    ],
    "aversion": []
}
    ```
    '''
    taskList = []
    for task in tasks['results']:
        taskData = {}
        taskData['id'] = task['id']
        taskData['name'] = task['name']
        taskData['detail'] = task['desc']
        taskData['created_time'] = task['created_time']
        taskData['peer_income'] = task['peer_income']
        taskData['points'] = task['points']
        taskList.append(taskData)
    return taskList

def taskList_To_Msg(taskList):
    msg = r'''<div class="table-container"><table class="new-tasks"><tr><th class="other-column">任务ID</th><th class="detail-time">任务细节</th><th class="detail-time">创建时间</th><th class="other-column">单位收益</th><th class="other-column">总量</th></tr>'''
    for i in taskList:
        msg += f'''<tr><td class="other-column">{i['id']}</td><td class="detail-time">{i['detail']}</td><td class="detail-time">{isoDateTime_To_dateTime(i['created_time'])}</td><td class="other-column">{i['peer_income']}</td><td class="other-column">{i['points']}</td></tr>'''
    msg += "</table></div>"
    return msg

def updated_Tasks_To_Msg(tasksList,config):
    msg = r'''<div class="table-container"><table class="new-points"><tr><th class="other-column">任务ID</th><th class="other-column">任务点更新前</th><th class="other-column">任务点更新后</th></tr>'''
    for task in tasksList:
        msg += f'''<tr><td class="other-column">{task['id']}</td><td class="other-column">{config.get('tasks_record').get(task['id'],{}).get('points',0)}</td><td class="other-column">{task['points']}</td></tr>'''
    msg += "</table></div>"
    return msg

def loop(config):
    try:
        refresh_token = login(config)
        while True:
            tasksList = analyzing_tasks_info(getTasks(refresh_token))
            if tasksList:
                i = [i['id'] for i in tasksList] # 列表，临时存储订单ID用于寻找最大的ID
                latest_id = int(max(i))
                msg = '<style>.table-container {overflow-x: auto;}table {width: 100%;border-collapse: collapse;}.new-tasks {min-width: 700px;}.new-points {min-width: 100px;}th, td {border: 1px solid black;padding: 8px;text-align: left;}.detail-time {width: 50px;word-wrap: break-word;}.other-column {width: 10px;word-wrap: break-word;}</style>'
                if latest_id > config['latest_id']:
                    config['latest_id'] = latest_id
                    msg += f"<h4>有新订单。当前最新是 {latest_id}</h4>"
                    msg += taskList_To_Msg(tasksList)
                    print(f"{taskList_To_Msg(tasksList)}")
                updated_tasks = []
                for task in tasksList:
                    if task['points'] > config.get('tasks_record').get(task['id'],{}).get('points',0):updated_tasks.append(task)
                if updated_tasks:
                    msg += f"<h4>有新任务点</h4>"
                    msg += updated_Tasks_To_Msg(updated_tasks,config)
                    print(f"{updated_Tasks_To_Msg(updated_tasks,config)}")
                    for task in tasksList:config['tasks_record'][task['id']] = task
                if latest_id > config['latest_id'] or updated_tasks:sendMsg(config, msg)
                saveConfig(config)
                print(f"{timeStamp_To_dateTime(time.time())}\t当前最新{latest_id}...\r",end='')
            else:
                print(f"{timeStamp_To_dateTime(time.time())}\t当前没有订单...\r",end='')
            time.sleep(30)
    except KeyboardInterrupt:print("\n结束")
    except requests.exceptions.ConnectionError:
        try:
            print(f"{timeStamp_To_dateTime(time.time())}\t网络连接中断")
            time.sleep(30)
            loop(config)
        except KeyboardInterrupt:print("结束")
    except requests.exceptions.ChunkedEncodingError:
        print(f"{timeStamp_To_dateTime(time.time())}\t远程主机关闭连接")
        time.sleep(3)
        loop(config)

def main():
    if 'linux' in sys.platform: sys.stdout.write(f"\x1b]2;算了么 - 监听任务列表 - 版本 {VERSION}\x07")
    elif 'win' in sys.platform: os.system(f"title 算了么 - 监听任务列表 - 版本 {VERSION}")
    if checkUpdate():print("请更新到最新版本：https://github.com/pooneyy/suanleme/releases/latest \n")
    try:loop(loadConfig())
    except FileNotFoundError:
        try:init()
        except KeyboardInterrupt:print("\n退出，取消初始化")

if __name__ == '__main__':
    main()
