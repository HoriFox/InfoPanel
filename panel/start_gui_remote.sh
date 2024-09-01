#!/bin/bash

echo "> Stop panel service..."
ssh root@192.168.31.33 "systemctl stop panel"
echo "> Remove panel files..."
ssh root@192.168.31.33 "rm -rf /home/user/panel_tmp; mkdir /home/user/panel_tmp"
echo "> Copy panel files..."
scp -r * root@192.168.31.33:/home/user/panel_tmp > /dev/null
echo "> Start panel service..."
ssh root@192.168.31.33 "systemctl start panel"
