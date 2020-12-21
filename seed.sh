#!/usr/bin/env bash

mkdir images
touch images/image{0001..0003}.png
aws s3 mv images/ s3://cd-old-bucket/legacy-url/ --recursive --exclude "*" --include "*.png"

mysql -h $DB_HOST -u $DB_USER -p $DB_PASSWORD \
      -e 'CREATE DATABASE IF NOT EXISTS frontend; \
          use frontend; \
          CREATE OR REPLACE TABLE images (id SERIAL, base_url VARCHAR(100) NOT NULL, url VARCHAR(100) NOT NULL, name VARCHAR(100) NOT NULL, PRIMARY KEY (id)); \
          INSERT INTO images (base_url, url, name) VALUES ("cd-new-bucket", "legacy-url/image01.png", "image01.png"), ("cd-new-bucket", "legacy-url/image02.png", "image02.png"), ("cd-new-bucket", "legacy-url/image03.png", "image03.png");'
