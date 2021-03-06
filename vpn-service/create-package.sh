#!/bin/sh

# creating the pacakge folder if non existing
mkdir -p package
# copy over the build files
cp -r dist package
cd package
mv dist bin

# creating the package info file
echo '{
    "name": "APP_openmotics_vpn",
    "version": [0, 0, 1],
    "description": "openmotics vpn service",
    "date": "'$(date +%d-%m-%Y)'",
    "fingerprint": "NA"
}'>> package_info.txt

# creating the start-application script
echo '#!/bin/sh
APP_PATH=$1
APP_DATA_PATH=$2
APP_TMP_PATH=$3
MAIN_CONFIG_FILE=$4

echo "$0"
echo "$APP_PATH"
echo "$APP_DATA_PATH"
echo "$APP_TMP_PATH"
echo "$MAIN_CONFIG_FILE"

logger "Starting the openmotics vpn package"
logger "\$0: $0"
logger "app path: $APP_PATH"
logger "app data path: $APP_DATA_PATH"
logger "app tmp path: $APP_TMP_PATH"
logger "config file: $MAIN_CONFIG_FILE"

# -- start gateway service --
killall -9 "vpn_service"
sleep 5

logger "Killed the current version"

# -- Setting the data path correct and start the app --
if [ ! -d "${APP_DATA_PATH}/etc" ]; then
    logger "etc/ folder does not exist -> creating it and setting up the basic files"
    mkdir -p ${APP_DATA_PATH}/etc # this is needed since the application searches in the etc folder
    cp -r ${APP_PATH}/etc ${APP_DATA_PATH}
fi
logger "starting the openmotics vpn service"
export OPENMOTICS_PREFIX=${APP_DATA_PATH}
exec ${APP_PATH}/vpn_service/vpn_service
'>> bin/start-application.sh
chmod u+x bin/start-application.sh

# creating the stop-application script
echo '#!/bin/sh

echo "$0"
killall vpn_service

# allow process to stop quietly
for i in $(seq 1 10); do
    ps | grep "/vpn"
    if [ $? -ne 0 ]; then
        exit 0 # done
    fi
    sleep 0.5
done

# force kill if necessary
ps | grep "/vpn"
if [ $? -eq 0 ]; then
  echo "openmotics vpn service did not shutdown gracefully, forcing stop"
  killall -9 vpn_service
fi
' >> bin/stop-application.sh
chmod u+x bin/stop-application.sh

