#!/bin/bash

rm -f *.py
rm -f manifest.json
rm -f services.yaml

wget https://raw.githubusercontent.com/kevinvincent/ha-wyzesense/master/custom_components/wyzesense/__init__.py
wget https://raw.githubusercontent.com/kevinvincent/ha-wyzesense/master/custom_components/wyzesense/binary_sensor.py
wget https://raw.githubusercontent.com/kevinvincent/ha-wyzesense/master/custom_components/wyzesense/manifest.json
wget https://raw.githubusercontent.com/kevinvincent/ha-wyzesense/master/custom_components/wyzesense/services.yaml
wget https://raw.githubusercontent.com/kevinvincent/ha-wyzesense/master/custom_components/wyzesense/wyzesense_custom.py
