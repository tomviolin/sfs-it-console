#!/bin/bash

# This script is used to test the SMTP relay server

ssh sfs-fatm 'curl -s --url smtp://smtprelay.uwm.edu:25 --mail-from "tomh@uwm.edu" --mail-rcpt "tomh@uwm.edu" -H "From: tomh@uwm.edu" -H "To: tomh@uwm.edu" -H "Subject: test" --upload-file -' <<_EOF_
From: tomh@uwm.edu
To: tomh@uwm.edu
Subject: testing

This is a test message
_EOF_

