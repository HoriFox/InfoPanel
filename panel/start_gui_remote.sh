#!/bin/bash

USER=root
REMOTE_IP=192.168.31.33


echo "> Stop panel service..."
ssh $USER@$REMOTE_IP "systemctl stop panel"
echo "> Remove panel files..."
ssh $USER@$REMOTE_IP "rm -rf /home/user/panel_tmp; mkdir /home/user/panel_tmp"
echo "> Copy panel files..."
scp -r * $USER@$REMOTE_IP:/home/user/panel_tmp > /dev/null
echo "> Start panel service..."
ssh $USER@$REMOTE_IP "systemctl start panel"
