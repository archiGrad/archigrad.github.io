import os
import json
import shutil
from natsort import natsorted
import re
import subprocess
from pdf2image import convert_from_path
import math
from PIL import Image
import string
import random
import platform

# OS Detection - Add system info detection
def get_os_info():
    system = platform.system()
    if system == "Windows":
        return {
            "os": "Windows",
            "is_windows": True,
            "is_linux": False,
            "imagemagick_cmd": "magick",
            "path_separator": "\\"
        }
    else:
        return {
            "os": system,
            "is_windows": False,
            "is_linux": True,
            "imagemagick_cmd": "convert",
            "path_separator": "/"
        }

# Get OS information
OS_INFO = get_os_info()
print(f"Running on {OS_INFO['os']} operating system")

# Helper function to run imagemagick commands on any OS
def run_imagemagick(command_args):
    """Run ImageMagick commands with proper syntax for the current OS"""
    if OS_INFO["is_windows"]:
        if command_args.startswith('convert '):
            command_args = command_args[8:]
            command = f'magick {command_args}'
        else:
            command = command_args
    else:
        command = command_args
    
    print(f"Running command: {command}")
    return subprocess.run(command, shell=True)

# preprocessing functions
def resize_file_if_large(filePath, maxBytes):
    file_size = os.path.getsize(filePath)
    if file_size > maxBytes:
        print(f"{filePath} is too big with {file_size}bytes. It will be modified. Max bytes is {maxBytes}")
        
        if os.path.splitext(filePath)[1].lower() == ".gif":
            command = f'convert "{filePath}" -resize 512x -colors 64 "{filePath}"'
        else:
            command = f'convert "{filePath}" -resize 512x -quality 80 "{filePath}"'
        
        run_imagemagick(command)
        
def remove_unsupported_file(file_path):
    if os.path.isfile(file_path):
        supported_extensions = (".jpg", ".png", ".jpeg", ".txt", ".gif", ".pdf")
        if not file_path.lower().endswith(supported_extensions):
            os.remove(file_path)
            print(f'{file_path} is not supported and is removed, please use one of the supported extensions {supported_extensions}')

def randomizeFilenames():   
    content_path = os.path.join("src", "content")
    
    for group in sorted(os.listdir(content_path)):
        group_path = os.path.join(content_path, group)
        if not os.path.isdir(group_path):
            continue
            
        for student in natsorted(os.listdir(group_path)):
            student_path = os.path.join(group_path, student)
            if not os.path.isdir(student_path):
                continue
                
            for week_folder in sorted(os.listdir(student_path)):
                week_folder_path = os.path.join(student_path, week_folder)
                if not os.path.isdir(week_folder_path):
                    continue
                    
                for item in sorted(os.listdir(week_folder_path)):
                    item_path = os.path.join(week_folder_path, item)
                    
                    # Process files
                    if os.path.isfile(item_path):
                        item = item.replace(' ','_')
                        base_name, extension = os.path.splitext(item)
                        random_string = ''.join(random.choices(string.ascii_letters, k=10))
                        modified_base_name = base_name[:4] + "_" + random_string
                        random_name_item = modified_base_name + extension
                        new_item_path = os.path.join(week_folder_path, random_name_item)
                        
                        if item_path != new_item_path:  # Only rename if different
                            os.rename(item_path, new_item_path)
                    
                    # Process directories (but skip "processed" folder)
                    elif os.path.isdir(item_path) and item != "processed":
                        for sub_item in os.listdir(item_path):
                            sub_item_path = os.path.join(item_path, sub_item)
                            
                            if os.path.isfile(sub_item_path):
                                base_name, extension = os.path.splitext(sub_item)
                                random_string = ''.join(random.choices(string.ascii_letters, k=10))
                                modified_base_name = base_name[:4] + "_" + random_string
                                random_name_item = modified_base_name + extension
                                new_sub_item_path = os.path.join(item_path, random_name_item)
                                
                                if sub_item_path != new_sub_item_path:  # Only rename if different
                                    os.rename(sub_item_path, new_sub_item_path)

def remove_too_big(file_path, maxWidth, maxHeight):
    if os.path.isfile(file_path):
        imageToProcess = Image.open(file_path)
        width, height = imageToProcess.size

        if width > maxWidth or height > maxHeight:
            print("Too big to process.")
            os.remove(file_path)

def preProcessImages(item, week_folder_path, nestedDir=None):
    item_path = os.path.join(week_folder_path, item)   
    
    if os.path.isfile(item_path):
        if item_path.lower().endswith((".jpg", ".png", ".jpeg")):
            processed_dir = os.path.join(week_folder_path, "processed")
            optionalArgs = "-fuzz 20% -transparent black"
            resizeArg = "-resize 512x512 "
            print(f"processing {item}")    

            if nestedDir != None:
                print("nested directory -images- is activated")
                processed_dir = os.path.join(nestedDir, "processed")
                optionalArgs = "-fuzz 20% -transparent black  "
                
            if "long" in os.path.splitext(item)[0]:
                resizeArg = "-resize x512 "
                print("contains long")
            
            os.makedirs(processed_dir, exist_ok=True)
            saveImg = os.path.splitext(item)[0] + "_pr.png"
            processed_path = os.path.join(processed_dir, saveImg)

            remove_too_big(item_path, 10000, 10000)
            
            cmd = f'convert "{item_path}" {resizeArg} -interpolate nearest-neighbor -sharpen 0x2 -quality 50 {optionalArgs} "{processed_path}"'
            run_imagemagick(cmd)
            
            resize_file_if_large(item_path, 1000000)

            images.append("../" + processed_path)
            week.append(processed_path)

def preProcessText(item, week_folder_path, nestedDir=None):
    item_path = os.path.join(week_folder_path, item)   
    if os.path.isfile(item_path):
        if item_path.lower().endswith((".txt")):
            processed_dir = os.path.join(week_folder_path, "processed")

            textColor = "white"
            textId = "textInfo"

            if nestedDir != None:
                print("nested directory -text- is activated")
                processed_dir = os.path.join(nestedDir, "processed")
                textColor = "grey"
                textId = "nestedTextInfo"

            os.makedirs(processed_dir, exist_ok=True)
            
            saveImg = os.path.splitext(item)[0] + "_pr.png"
            processed_path = os.path.join(processed_dir, saveImg)

            saveTextTemp = os.path.splitext(item)[0] + "_temp.txt"
            processedTextForImg = os.path.join(processed_dir, saveTextTemp)

            saveText = os.path.splitext(item)[0] + "_pr.txt"
            processedTextForHTML = os.path.join(processed_dir, saveText)

            with open(item_path, "r") as file:
                content = file.read()

            modified_content = re.sub(r'<iframe\b[^>]*>.*?</iframe>', '', content, flags=re.DOTALL)
            modified_content = f'<span foreground="{textColor}">' + modified_content + "</span>\n"
            modified_content = modified_content.replace("&", "and")

            with open(processedTextForImg, "w") as new_file:
                new_file.write(modified_content)
                print(f'{item} -> temp text for panco image file written')

            with open(processedTextForHTML, "w") as new_file:
                new_file.write(f'<span class="{textId}">' + content + '</span>')
                print(f'{item} -> text file written')
            
            cmd = f'convert -background none -size 512x512 -pointsize 20 -define pango:justify=true pango:@"{processedTextForImg}" "{processed_path}"'
            run_imagemagick(cmd)
            
            os.remove(processedTextForImg)
            text.append(processedTextForHTML)
            week.append(processed_path)

def preProcessPdfs(item, week_folder_path, nestedDir=None):
    item_path = os.path.join(week_folder_path, item)   
    if os.path.isfile(item_path) and item_path.lower().endswith((".pdf")):
        print(f"Skipping PDF processing for {item} - Poppler not installed")
        return  # Skip PDF processing
    
def preProcessGifs(item, week_folder_path, nestedDir=None):
    item_path = os.path.join(week_folder_path, item)   
    print(item_path)
    if os.path.isfile(item_path):
        if item.lower().endswith((".gif")):
            processed_dir = os.path.join(week_folder_path, "processed")

            resize_file_if_large(item_path, 1000000)

            optionalArgs = ''
            if nestedDir != None:
                print("nested directory -gif- is activated")
                processed_dir = os.path.join(nestedDir, "processed")
                optionalArgs = " "

            os.makedirs(processed_dir, exist_ok=True)

            if not re.search(r"preProcessed", item_path):
                gifTempFolder = os.path.join(week_folder_path, "gifTemp")                
                os.makedirs(gifTempFolder, exist_ok=True)
                tempImgPath = os.path.join(gifTempFolder, os.path.splitext(item)[0] + "_preProcessed")
                
                cmd = f'convert "{item_path}" -coalesce -sharpen 0x1 -resize 512x512!  "{tempImgPath}.png"'
                run_imagemagick(cmd)
                
                divider = math.ceil(len(os.listdir(gifTempFolder))*0.1)
                for i, image in enumerate(natsorted(os.listdir(gifTempFolder))):
                    tempImg = os.path.join(gifTempFolder, image)
                    if i%divider!=0:
                        os.remove(tempImg)

                print(tempImgPath)
                nFrames = 10
                additionalImg = (nFrames-len(natsorted(os.listdir(gifTempFolder))))
                if additionalImg !=0:
                    for i in range(0,additionalImg):
                        i = nFrames - i
                        cmd = f'convert -size 512x512 xc:none  "{os.path.join(gifTempFolder, f"zzz_{i}.png")}"'
                        run_imagemagick(cmd)
                
                for i, img in enumerate(natsorted(os.listdir(gifTempFolder))):
                    originalPath = os.path.join(gifTempFolder, img)
                    newPath = os.path.join(gifTempFolder, f'{i}_{img}')
                    os.rename(originalPath, newPath)

                processed_path = os.path.join(processed_dir, f'{item}_preProcessed_long_.png')
                
                if OS_INFO["is_windows"]:
                    gif_temp_pattern = os.path.join(gifTempFolder, "*.png")
                    cmd = f'magick "{gif_temp_pattern}" -resize 512x512 -append {optionalArgs} "{processed_path}"'
                else:
                    cmd = f'convert "{os.path.join(gifTempFolder, "*.png")}" -resize 512x512 -append {optionalArgs} "{processed_path}"'
                
                run_imagemagick(cmd)

                processed_path_gif = os.path.join(processed_dir, f'{item}_preProcessed.gif')
                cmd = f'convert "{item_path}" -coalesce -resize 512x -colors 32 -deconstruct -loop 0 {optionalArgs} "{processed_path_gif}"'
                run_imagemagick(cmd)

                images.append("../" + processed_path_gif)
                week.append(processed_path)

                shutil.rmtree(gifTempFolder)

def generate_html_file(filename, title, groupContent, weeks, content, images, group):
    with open(filename, 'w') as file:
        file.write("<!DOCTYPE html>\n")
        file.write("<html>\n")
        file.write("<head>\n")
        file.write(f"<title>{title}</title>\n")
        file.write("<link rel='stylesheet' href='../style.css'>\n")
        file.write("</head>\n")
        file.write("<body id='groupDescription'>\n")
        file.write(f"<h1>{title}</h1>\n")

        text_content = group

        if groupContent != False:
            for content in os.listdir(groupContent):
                file_path = os.path.join(groupContent, content)
                if os.path.isfile(file_path):
                    file_name, file_extension = os.path.splitext(content)
                    if file_extension.strip().lower() == ".txt":
                        with open(file_path, 'r') as groupFile:
                            text_content = groupFile.read()
        
        file.write(f"<p>{text_content}</p>\n")

        for week, week_content, week_images in zip(weeks, content, images):
            file.write(f"<h2>{week}</h2>\n")
            
            file.write("<div>\n")
            for text_item in week_content:
                with open(text_item, 'r') as text_file:
                    content = text_file.read().replace('\n', '<br>')     
                    file.write(f"<p>{content}</p>\n")
            file.write("</div>\n")
            
            for image_item in week_images:
                file.write(f"<img onclick='enlargeImage(this)' src='{image_item}' alt='Image'>\n")

        file.write("<script>function enlargeImage(img) {  if (img.style.width === '100%') { img.style.width = '100px'; } else { img.style.width = '100%'; }}</script>\n")
        file.write("</body>\n")
        file.write("</html>")

# Make sure output directories exist
info = "info"
if os.path.exists(info):
    file_list = os.listdir(info)
    for file_name in file_list:
        file_path = os.path.join(info, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)
else:
    os.makedirs(info)

additional_folder_path = "extra"
if os.path.exists(additional_folder_path):
    file_list = os.listdir(additional_folder_path)
    for file_name in file_list:
        file_path = os.path.join(additional_folder_path, file_name)
        os.remove(file_path)
else:
    os.makedirs(additional_folder_path)

groups = {}
groups["archiGrad"] = {}
weeksHTML = {}

def check_folder_for_txt_file(folder_path):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            file_name, file_extension = os.path.splitext(filename)
            if file_extension.strip().lower() == ".txt":
                with open(file_path, 'r') as file:
                    content = file.read()
                return content
    return None

def create_text_image(text, output_path, color="white"):
    # Escape special characters for Pango
    text = text.replace("&", "and").replace("<", "&lt;").replace(">", "&gt;")
    cmd = f'convert -background none -size 256x256 -pointsize 20 -define pango:justify=true pango:"<span foreground=\\"{color}\\">{text}</span>" "{output_path}"'
    run_imagemagick(cmd)
    return output_path

# Start the processing
randomizeFilenames()

# Main processing loop
content_path = os.path.join("src", "content")

for group in sorted(os.listdir(content_path)):
    group_path = os.path.join(content_path, group)

    if os.path.isdir(group_path):
        groups[group] = {}

        for student in natsorted(os.listdir(group_path)):
            student_path = os.path.join(group_path, student)

            content = check_folder_for_txt_file(group_path)
            if content:
                generate_html_file(f"info/{group.replace(' ', '_')}.html", group.replace(' ', '_'), 
                                  group_path, [], [], [], f"no data available. please add a text file: {group_path}")
                print(f"successfully generated {group} description file")
            else:
                generate_html_file(f"info/{group.replace(' ', '_')}.html", group.replace(' ', '_'), 
                                  group_path, [], [], [], f"no data available. please add a text file: {group_path}")
                print(f"successfully generated {group} from non exist description file")

            if os.path.isdir(student_path):
                weeks = []
                textArray = []
                imgArray = []
                weekArray = []

                for week_folder in sorted(os.listdir(student_path)):
                    weekArray.append(week_folder)
                    week_folder_path = os.path.join(student_path, week_folder)
                    if os.path.isdir(week_folder_path) and week_folder != "processed":
                        week = []
                        text = []
                        images = []
                      
                        processed_dir = os.path.join(week_folder_path, "processed")
                        if os.path.exists(processed_dir):
                            shutil.rmtree(processed_dir)

                        for item in sorted(os.listdir(week_folder_path)):
                            item_path = os.path.join(week_folder_path, item)
                            
                            if os.path.isdir(item_path) and item != "processed":
                                output_path = f'./{additional_folder_path}/{week_folder}.png'
                                create_text_image(week_folder, output_path)
                                week.append(output_path)

                                for sub_item in natsorted(os.listdir(item_path)):
                                    sub_item_path = os.path.join(item_path, sub_item)
                                    preProcessPdfs(sub_item, item_path, week_folder_path)
                                    preProcessGifs(sub_item, item_path, week_folder_path)
                                    preProcessImages(sub_item, item_path, week_folder_path)
                                    preProcessText(sub_item, item_path, week_folder_path)
                                    remove_unsupported_file(os.path.join(item_path, sub_item))

                        output_path = f'./{additional_folder_path}/foo_{week_folder}.png'
                        create_text_image(f"{item}: {week_folder}", output_path)
                        week.append(output_path)
                        
                        for item in natsorted(os.listdir(week_folder_path)):
                            print(item)
                            preProcessPdfs(item, week_folder_path)
                            preProcessGifs(item, week_folder_path)
                            preProcessImages(item, week_folder_path)
                            preProcessText(item, week_folder_path)
                            remove_unsupported_file(os.path.join(week_folder_path, item))
                            
                        textArray.append(text)
                        imgArray.append(images)
    
                        output_path = f'./{additional_folder_path}/ref_{week_folder}.png'
                        create_text_image(f"content: {week_folder}", output_path)
                        week.append(output_path)
                        weeks.append(week)

                processed_images = []
                for root, dirs, files in os.walk(student_path):
                    if 'processed' in root:
                        for file in files:
                            if file.endswith(('_pr.png', '_pr.jpg', '_alpha.png', '.gif')):
                                full_path = os.path.join(root, file).replace('\\', '/')
                                # Remove the extra "src/" if it exists
                                if full_path.startswith('src/'):
                                    full_path = full_path[4:]  # Remove first "src/"
                                processed_images.append(full_path)

                                groups[group][student] = sorted(processed_images)
                                groups["archiGrad"][student] = sorted(processed_images)

                generate_html_file(f"info/{student.replace(' ', '_')}.html", student.replace(' ', '_'), 
                                 False, weekArray, textArray, imgArray, group)

# Generate data.js with correct paths
def generate_data_js():
    with open("data.js", "w") as file:
        file.write("var groups = ")
        file.write(json.dumps(groups, indent=2))
        file.write(";\n")
        file.write("var conversations = {};\n")

generate_data_js()

print("Data written to data.js successfully.")
print(f"Script completed successfully on {OS_INFO['os']}!")