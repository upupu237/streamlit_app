#!/usr/bin/env python
# -*- coding:utf-8 -*-

import json
import os
from datetime import datetime
import base64

# 用户数据管理
class UserManager:
    def __init__(self, data_file="data/users.json"):
        self.data_file = data_file
        self.users = self.load_users()

    def load_users(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_users(self):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.users, f, ensure_ascii=False, indent=4)

    def register_user(self, username, password):
        if username in self.users:
            return False, "用户名已存在"
        self.users[username] = {
            "password": password,
            "register_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "interview_history": [],
            "resume": None,
            "parsed_resume": None,  # 存储解析后的简历信息
            "resume_evaluations": {}  # 存储简历评估结果
        }
        self.save_users()
        return True, "注册成功"

    def login_user(self, username, password):
        if username not in self.users:
            return False, "用户名不存在"
        if self.users[username]["password"] != password:
            return False, "密码错误"
        return True, "登录成功"

    def upload_resume(self, username, resume_file):
        # 将简历保存为base64编码
        resume_bytes = resume_file.getvalue()
        encoded_resume = base64.b64encode(resume_bytes).decode("utf-8")
        self.users[username]["resume"] = {
            "filename": resume_file.name,
            "data": encoded_resume,
            "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        # 上传新简历时清除旧的解析结果和评估
        self.users[username]["parsed_resume"] = None
        self.users[username]["resume_evaluations"] = {}
        self.save_users()
        return True, "简历上传成功"

    def get_resume(self, username):
        if username in self.users and "resume" in self.users[username] and self.users[username]["resume"]:
            return self.users[username]["resume"]
        return None

    def update_parsed_resume(self, username, parsed_data):
        """更新解析后的简历信息"""
        if username in self.users:
            self.users[username]["parsed_resume"] = parsed_data
            self.save_users()
            return True
        return False

    def save_resume_evaluation(self, username, job, evaluation):
        """保存简历评估结果"""
        if username in self.users:
            if "resume_evaluations" not in self.users[username]:
                self.users[username]["resume_evaluations"] = {}
            self.users[username]["resume_evaluations"][job] = evaluation
            self.save_users()
            return True
        return False

    def add_interview_history(self, username, job, score, level, match):
        history_entry = {
            "job": job,
            "score": score,
            "level": level,
            "match": match,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.users[username]["interview_history"].append(history_entry)
        self.save_users()