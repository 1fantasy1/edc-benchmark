@echo off
cd /d E:\edc\Samples
start "" cmd /c java "-Dedc.fs.config=transfer/transfer-00-prerequisites/resources/configuration/provider-configuration.properties" -jar transfer/transfer-00-prerequisites/connector/build/libs/connector.jar >> E:\edc-benchmark\edc-benchmark-2\results\provider_restart.log 2>&1
