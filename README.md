# TwinCAT Structured Text C

### WORK IN PROGRESS

Current functionality:

```sh
# TwinCAT to Structured Text
# extract structured text from the specified project
# optional: --fmt to reformat the extracted code
# NOTE: clobbers anything already existing in the destination folder
tc2st --src /path/to/project.plcproj --dest /path/to/destination/folder

# Structured Text Format
# format structured text in the specified folder
stfmt --dir /path/to/structured/text/folder
```
