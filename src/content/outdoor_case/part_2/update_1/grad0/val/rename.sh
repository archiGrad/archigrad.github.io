#!/bin/bash

# Counter variable
counter=1

# Loop through each .jpg file and rename it
for file in *.jpg; do
    # Check if the item is a file
    if [ -f "$file" ]; then
        # Construct the new file name
        new_name="${counter}.jpg"

        # Rename the file using mv
        mv "$file" "${new_name}"

        # Increment the counter for the next file
        ((counter++))
    fi
done
