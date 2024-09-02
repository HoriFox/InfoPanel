#!/bin/bash

USER=root
REMOTE_IP=192.168.31.33


echo "> Stop panel service..."
ssh $USER@$REMOTE_IP "systemctl stop panel"
