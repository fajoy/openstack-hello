#!/bin/bash
export OS_AUTH_URL=http://127.0.0.1:5000/v2.0
export OS_TENANT_NAME=demo
export OS_USERNAME=cyfang
export OS_HELLO_URL=http://127.0.0.1:10001/v1
echo "Please enter your OpenStack Password: "
read -s OS_PASSWORD_INPUT
export OS_PASSWORD=$OS_PASSWORD_INPUT
