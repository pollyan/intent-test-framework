#!/bin/bash
# 远程命令执行辅助脚本

SERVER="120.53.220.231"
USER="ubuntu"
PASSWORD="Shunlian04"

# 执行远程命令
remote_exec() {
    expect << EOF
set timeout 300
spawn ssh -o StrictHostKeyChecking=no ${USER}@${SERVER} "$1"
expect {
    "password:" {
        send "${PASSWORD}\r"
        exp_continue
    }
    eof
}
EOF
}

# 执行传入的命令
remote_exec "$@"

