#!/bin/bash
# SSH密码登录脚本

SERVER="120.53.220.231"
USER="ubuntu"
PASSWORD="Shunlian04"

# 使用expect进行密码登录
expect << EOF
set timeout 30
spawn ssh -o StrictHostKeyChecking=no ${USER}@${SERVER} "$@"
expect {
    "password:" {
        send "${PASSWORD}\r"
        exp_continue
    }
    eof
}
EOF


