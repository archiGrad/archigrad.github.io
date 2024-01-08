import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.121.1/build/three.module.js'
import {    OrbitControls} from 'https://cdn.jsdelivr.net/npm/three@0.121.1/examples/jsm/controls/OrbitControls.js'



var scene = new THREE.Scene();



// function onWindowResize() {
//     const aspectRatio = threeDiv.offsetWidth / threeDiv.offsetHeight;
//     // const aspectRatio = 1;
//     // const aspectRatio = 1;
//     const frustumSize = 30 / zoomFactor;
//     camera.left = frustumSize * aspectRatio / -2;
//     camera.right = frustumSize * aspectRatio / 2;
//     camera.top = frustumSize / 2;
//     camera.bottom = frustumSize / -2;
//     camera.updateProjectionMatrix();
//     renderer.setSize(threeDiv.offsetWidth, threeDiv.offsetHeight);

//     // Update the positions of the tags when the window is resized
//     for (var i = 0; i < scene.children.length; i++) {
//         var object = scene.children[i];
//         if (object instanceof THREE.Mesh) {
//             var plane = object;
//             var tag = plane.userData.tag;
//             if (tag) {
//                 var planeWorldPosition = new THREE.Vector3();
//                 plane.getWorldPosition(planeWorldPosition);

//                 var planeScreenPosition = planeWorldPosition.clone();
//                 planeScreenPosition.project(camera);

//                 tag.style.left = ((planeScreenPosition.x + 1) / 2) * window.innerWidth + 'px';
//                 tag.style.top = ((-planeScreenPosition.y + 1) / 2) * window.innerHeight + 'px';
//             }
//         }
//     }

// }


var threeDiv = document.getElementById('three');
var screenDiv = document.getElementById('screen');

var headerDiv = document.getElementById("header");

// Create an orthographic camera with adjusted frustum size
// const zoomFactor = 60; // Adjust this value to control the zoom level
const aspectRatio = threeDiv.offsetWidth / threeDiv.offsetHeight;

const zoomFactor = Math.ceil(Math.random() * 10) + 2; // Generates a random value between 10 and 60
const frustumSize = 50 / zoomFactor;
// const newFrustumSize = 30 / zoomFactor;
const camera = new THREE.OrthographicCamera(
    frustumSize * aspectRatio / -2,
    frustumSize * aspectRatio / 2,
    frustumSize / 2,
    frustumSize / -2,
    0.1,
    1000
);



var PLANEHEIGHT = 0.032;







// Create a renderer
const renderer = new THREE.WebGLRenderer({
    alpha: true
});
renderer.setSize(threeDiv.offsetWidth, threeDiv.offsetHeight);
threeDiv.appendChild(renderer.domElement);

// Set camera position
camera.position.set(10, 10, 10);



const controls = new OrbitControls(camera, renderer.domElement);


const projectName = "archiGrad" 
var planesByStack = []

function createStacksOfPlanes(students) {

    function loadImagesAsync(imageUrls) {
        return new Promise((resolve) => {
            const loader = new THREE.TextureLoader();
            const loadedTextures = [];

            let loadedCount = 0;
            let screenDivContent = '.'
            const allImageUrls = Math.floor(imageUrls.length)
            const rootAllImageUrls = Math.ceil(Math.sqrt(allImageUrls)+1)

            for (const url of imageUrls) {
                loader.load(url, (texture) => {
                    loadedTextures.push(texture);
                    
                    loadedCount++;
                    screenDivContent += '.'
                    if(screenDivContent.length%(rootAllImageUrls)==0){
                        screenDivContent +='<br>'
                    }
                    
                    // let loadingAnimationContent =  '<img id="loading" src="loading.gif"></img>' 
                    screenDiv.innerHTML ='compiling archive <br>' + (loadedCount-1) + '/' + (allImageUrls-1)  + '<br>' +screenDivContent + '<br>' +Math.ceil((loadedCount-1)/(allImageUrls-1)*100) + '%'

                    if (loadedCount === allImageUrls) {
                        resolve(loadedTextures);
                    }   
                });
            }
        });
    }



    // Get an array of all image URLs used in the stacks
    const imageUrls = [];
    
    for (const student of Object.values(students)) {
        for (const content of student) {
            imageUrls.push(content);
        }
    }

    // Call the loader to load all the images
    loadImagesAsync(imageUrls).then();

    while (scene.children.length > 0) {
        scene.remove(scene.children[0]);
    }

    var activeStack = -1;
    var activePlanes = [];

  
    
    // Clear existing span elements
    var existingSpans = document.getElementsByTagName("span");
    for (var i = existingSpans.length - 1; i >= 0; i--) {
        existingSpans[i].remove();
    }

    var stackCount = Object.keys(students).length;
    var stackDistance = 1.0;
    var gridWidth = Math.floor(Math.sqrt(stackCount)); // Number of stacks per row

    var offsetX = (gridWidth - 1) * stackDistance * 0.5;
    var offsetZ = (Math.ceil(stackCount / gridWidth) - 1) * stackDistance * 0.5;




    
    let totalItems = 0;
    
    

    for (var i = 0; i < stackCount; i++) {
        var x = i % gridWidth;
        var z = Math.floor(i / gridWidth);

        var student = Object.keys(students)[i];
        var content = students[student];
        var itemCount = content.length;


        for (var j = 0; j < itemCount; j++) {
            totalItems +=1
            // console.log(totalItems);
            var isGif = content[j].includes("gif");
            var textureLoader = new THREE.TextureLoader();
            var texture;

            if (isGif) {
                    // Load the image as a vertical animation
                    texture = textureLoader.load(content[j], function(texture) {
                        var totalFrames = 10;
                        texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
                        texture.repeat.set(1, 1 / totalFrames);
    
                        var frameDuration = 200; // speed
                        var currentFrame = 0;
                        var frameTimer = setInterval(function() {
                            currentFrame = (currentFrame + 1) % totalFrames;
                            texture.offset.y = 1 - (currentFrame / totalFrames);
                        }, frameDuration);
                    });
            } else {
                // Load normal image
                texture = textureLoader.load(content[j]);
            }

            texture.minFilter = THREE.NearestFilter;
            texture.magFilter = THREE.NearestFilter;

            var geometry = new THREE.PlaneGeometry(1, 1);
            var material = new THREE.MeshBasicMaterial({
                map: texture,
                side: THREE.DoubleSide,
                transparent: true,
                opacity:1,
            });

            var plane = new THREE.Mesh(geometry, material);
            var posX = (x * stackDistance) - offsetX;
            var posZ = (z * stackDistance) - offsetZ;

            plane.position.set(posX, j * PLANEHEIGHT, posZ);
            plane.rotation.x = Math.PI / 2;
            plane.rotation.y = Math.PI; // Turn 180 so facing top
            plane.rotation.z = Math.PI ;
            scene.add(plane);

            if (!planesByStack[i]) {
                planesByStack[i] = [];
            }
            planesByStack[i].push(plane);
            

            if (j === itemCount-1) {
                var planeWorldPosition = new THREE.Vector3();
                plane.getWorldPosition(planeWorldPosition);
                var planeScreenPosition = planeWorldPosition.clone();
                planeScreenPosition.project(camera);

                
                    

                var span = document.createElement('span');

                span.classList.add('tag');
                span.style.position = 'absolute';
                span.style.display = "block"
                
                span.style.left = ((planeScreenPosition.x + 1) / 2) * window.innerWidth + 'px';
                span.style.top = ((-planeScreenPosition.y + 1) / 2) * window.innerHeight + 'px';
                
                const countSpan = document.createElement("code");
                span.textContent = student;

                countSpan.textContent = " ";
                countSpan.textContent += itemCount - 1 ;

                countSpan.style.fontSize = "9px";
                span.appendChild(countSpan);
                span.style.cursor = 'pointer';

                span.addEventListener('click', (function (stackIndex) {
                    return function () {
                    //  Check if the clicked stack is already active
                    if (stackIndex === activeStack) {
                        // Reset opacity for the clicked stack
                        var planes = planesByStack[stackIndex];
                        for (var p = 0; p < planes.length; p++) {
                            planes[p].material.opacity = 1;
                        }
                        // Reset opacity for all other stacks
                        for (var s = 0; s < planesByStack.length; s++) {
                            if (s !== stackIndex) {
                                var otherPlanes = planesByStack[s];
                                for (var p = 0; p < otherPlanes.length; p++) {
                                    otherPlanes[p].material.opacity = 1;
                                }
                            }
                        }
                        // Reset the active stack and its planes
                        activeStack = -1;
                        activePlanes = [];
                    } else {
                        // Reset opacity of previously altered planes
                        for (var p = 0; p < activePlanes.length; p++) {
                            activePlanes[p].material.opacity = 1;
                        }
                        // Set opacity for the clicked stack
                        var planes = planesByStack[stackIndex];
                        for (var p = 0; p < planes.length; p++) {
                            planes[p].material.opacity = 1;
                            // planes[p].rotation.x = 00;
                            // planes[p].rotation.z = 0;
                        }
                        // Set opacity to 0.5 for all other stacks
                        for (var s = 0; s < planesByStack.length; s++) {
                            if (s !== stackIndex) {
                                var otherPlanes = planesByStack[s];
                                for (var p = 0; p < otherPlanes.length; p++) {
                                    otherPlanes[p].material.opacity = 0.15;
                                }
                            }
                        }
                        // Update the active stack and its planes
                        activeStack = stackIndex;
                        activePlanes = planes;
                    }
                };
            })(i));


            span.addEventListener('click', (function(student) {
                return function() {
                    const infoDiv = document.getElementById('info');
                    const tags = document.getElementsByClassName('tag');
            
                    // Check if the clicked span is already active
                    if (this.classList.contains('active')) {

               

                        // Revert back to the original content
                        infoDiv.innerHTML = infoDiv.originalContent;

                        // console.log(infoDiv.originalContent);
            
                        // Remove the active class and set text decoration to none for all tags
                        for (let k = 0; k < tags.length; k++) {
                            tags[k].classList.remove('active');
                            tags[k].style.textDecoration = 'none';
                            tags[k].style.color = 'white';
                        }
                    } else {
                        // Store the original content if it hasn't been stored yet
                        if (!infoDiv.originalContent) {
                            infoDiv.originalContent = infoDiv.innerHTML;
                        }
            
                        // Set the new content and add the active class to the clicked span
                        const iframe = document.createElement('iframe');
                        iframe.src = `info/${student.replace(/ /g, "_")}.html`; //replace space by underscore so it matches the html files
            
                        infoDiv.innerHTML = '';
                        infoDiv.appendChild(iframe);
            
                        // Remove the active class and set text decoration to none for all tags
                        for (let i = 0; i < tags.length; i++) {
                            tags[i].classList.remove('active');
                            tags[i].style.textDecoration = 'none';
                            // tags[i].style.color = spanColor;
                        }

                        // Add the active class and set text decoration to underline for the clicked span
                        this.classList.add('active');
                        this.style.textDecoration = 'underline';
                        this.style.color = 'white';
                    }
                };
            })(student));
        
                        document.getElementById("span").appendChild(span);
                        plane.userData.tag = span;
            }



                       
                            // // The student matches with one of the keys
                            // const studentConversations = conversations[student];
                            // console.log(Object.keys(studentConversations).includes(j.toString()));
                            
                            // if (Object.keys(studentConversations).includes(j.toString())) {
                            //   // Conversation number j exists for the student
                            //   const conversation = studentConversations[j.toString()];
                          
                            //   // Create a bubble tag element
                            //   var bubbleTag = document.createElement('div');
                            //   bubbleTag.classList.add('bubbleTag');
                            //   bubbleTag.style.position = 'absolute';
                            //   bubbleTag.style.display = "block";
                          
                            //   // Iterate over each message in the conversation
                            //   for (let message of conversation) {
                            //     let messageDiv = document.createElement('div');
                            //     messageDiv.classList.add(message.type);
                            //     messageDiv.innerHTML = message.content;
                            //     bubbleTag.appendChild(messageDiv);
                            //   }
                          
                            //   // Append the bubble tag to the span element
                            //   document.getElementById("span").appendChild(bubbleTag);
                            //   // Assign the bubble tag to the plane's user data
                            //   plane.userData.tag = bubbleTag;
                            // } 
                            
                            const studentConversations = conversations[student];


                            if (studentConversations && Object.prototype.hasOwnProperty.call(studentConversations, j.toString())) {
                                // Conversation number j exists for the student
                                const conversation = studentConversations[j.toString()];
                              
                                // Create a bubble tag element
                                const bubbleTag = document.createElement('div');
                                bubbleTag.classList.add('bubbleTag');
                                bubbleTag.style.position = 'absolute';
                                bubbleTag.style.display = "block";
                              
                                // Create message elements using Array.map
                                const messageDivs = conversation.map(message => {
                                  const div = document.createElement('div');
                                  div.classList.add(message.type);
                                  div.innerHTML = message.content;
                                  return div;
                                });
                              
                                // Append all message elements to the bubble tag
                                bubbleTag.append(...messageDivs);
                              
                                // Append the bubble tag to the span element
                                document.getElementById("span").appendChild(bubbleTag);
                              
                                // Assign the bubble tag to the plane's user data
                                plane.userData.tag = bubbleTag;
                              } 
        }
    }
}







function animate() {
    requestAnimationFrame(animate);
    controls.update();
    scene.rotation.y += 0.001;
   

    
    // Update the positions of the tags
    for (var i = 0; i < scene.children.length; i++) {
        var object = scene.children[i];
        if (object instanceof THREE.Mesh) {
            var plane = object;
            var tag = plane.userData.tag;


            function setTagPosition(tag, screenPosition) {
                tag.style.left = (screenPosition.x * 0.5 + 0.5) * renderer.domElement.clientWidth + "px";
                tag.style.top = (-screenPosition.y * 0.5 + 0.5) * renderer.domElement.clientHeight + "px";
            }
            
            if (object instanceof THREE.Mesh) {
                var plane = object;
                var tag = plane.userData.tag;
            
                if (tag) {
                    var planeWorldPosition = new THREE.Vector3();
                    plane.getWorldPosition(planeWorldPosition);
            
                    var planeWorldPositionClone = planeWorldPosition.clone();
            
                    var planeScreenPosition = planeWorldPositionClone.project(camera);

            
                    if (tag.classList.contains('tag')) {
                        setTagPosition(tag, planeScreenPosition);
            
                        // Adjust visibility based on tag position
                        tag.style.display = (
                            planeScreenPosition.x >= -1 && planeScreenPosition.x <= 0.9 &&
                            planeScreenPosition.y >= -0.9 && planeScreenPosition.y <= 1
                        ) ? "block" : "none";
                    } else if (tag.classList.contains('bubbleTag')) {
                        tag.style.display = (
                            camera.zoom > 0.05 &&
                            planeScreenPosition.x >= -1 && planeScreenPosition.x <= 0.8 &&
                            planeScreenPosition.y >= -0.8 && planeScreenPosition.y <= 1
                        ) ? "block" : "none";

            
                        setTagPosition(tag, planeScreenPosition);
                    }
                }
            }
        }


        // else {
        //     var line = object;
        
        //     // Get the world position of the line
        //     var lineWorldPosition = new THREE.Vector3().setFromMatrixPosition(line.matrixWorld);
        
        //     // Project the world space coordinate to screen space
        //     var lineScreenPosition = lineWorldPosition.clone().project(camera);
        
        //     // Calculate the screen space coordinates
        //     var posX = (lineScreenPosition.x * 0.5 + 0.5) * renderer.domElement.clientHeight;
        //     var posY = 0;
        
        //     // Assuming the line has at least one point
        //     var positionAttribute = line.geometry.attributes.position;
        //     if (positionAttribute.count > 0) {
        //         var index = 0; // Index of the first point
        
        //         // Get the world position of the first point
        //         var firstPointWorldPosition = new THREE.Vector3().fromBufferAttribute(positionAttribute, index);
        
        //         // Project the world space coordinate to screen space
        //         var firstPointScreenPosition = firstPointWorldPosition.clone().project(camera);
        
        //         // Check if the x coordinate in screen space is negative
        //         if (firstPointScreenPosition.x > 0) {
        //             posX *= -1;
        //         }
        //     }
        
        //     var lineMaterial = line.material;
        
        //     // Calculate target screen space vector
        //     const targetScreenSpaceVector = new THREE.Vector3(posX, posY, -2);
        
        //     // Unproject the screen space coordinate to get the corresponding world space position
        //     const targetWorldSpaceVector = targetScreenSpaceVector.clone().unproject(camera);
        
        //     // Update the first point of the line
        //     line.geometry.attributes.position.setXYZ(1, targetWorldSpaceVector.x, targetWorldSpaceVector.y, targetWorldSpaceVector.z);
        //     line.geometry.attributes.position.needsUpdate = true;
        // }
    }
    
    
    renderer.render(scene, camera);
}







const info = document.getElementById("info");

for (var group in groups) {
    // add groups as buttons top left
    var groupButton = document.createElement("button");
    groupButton.innerHTML = group ;
    groupButton.classList.add("group-button");
    groupButton.style.backgroundColor = "rgba(0,0,0,0)"
    groupButton.style.fontSize = '12px';
   
    var newLine = document.createElement("br");

    groupButton.addEventListener("click", function() {
        var buttons = document.getElementsByClassName("group-button");
        for (var i = 0; i < buttons.length; i++) {
            buttons[i].style.textDecoration = "none";
        }

        // Add underline to the clicked button
        this.style.textDecoration = "underline";
        
        // this.style.fontWeight = 'bold';

        var selectedGroup = this.innerHTML;
        var students = groups[selectedGroup];

        if(selectedGroup === projectName){ info.innerHTML = "<iframe src='" + selectedGroup + ".html'></iframe>";}
        else{info.innerHTML = "<iframe src='./info/" + selectedGroup + ".html'></iframe>";}
        info.originalContent = info.innerHTML; // Update original content
        
        // console.log(info.innerHTML);
        
        const bubbleTags = document.getElementsByClassName('bubbleTag');

        // Loop through the elements and remove them
        while (bubbleTags.length > 0) {
            const bubbleTag = bubbleTags[0];
            bubbleTag.parentNode.removeChild(bubbleTag);
            // console.log("del");
        }

        
        createStacksOfPlanes(students);
    });

    // Check if the current button is "archiGrad" and underline it on startup
    if (group === projectName) {
        groupButton.style.textDecoration = "underline";

        // camera.position.set(10, 10, 0);
        // scene.position.y -= centerHeight +2;
        // scene.position.x -= centerHeight +10;
        // camera.zoom =100;
    }
    
    headerDiv.appendChild(groupButton);
    headerDiv.appendChild(newLine);
}


function onWindowResize() {
    const aspectRatio = threeDiv.offsetWidth / threeDiv.offsetHeight;
    // const aspectRatio = 1;
    // const aspectRatio = 1;
    const frustumSize = 30 / zoomFactor;
    camera.left = frustumSize * aspectRatio / -2;
    camera.right = frustumSize * aspectRatio / 2;
    camera.top = frustumSize / 2;
    camera.bottom = frustumSize / -2;
    camera.updateProjectionMatrix();
    renderer.setSize(threeDiv.offsetWidth, threeDiv.offsetHeight);

    // Update the positions of the tags when the window is resized
    for (var i = 0; i < scene.children.length; i++) {
        var object = scene.children[i];
        if (object instanceof THREE.Mesh) {
            var plane = object;
            var tag = plane.userData.tag;
            if (tag) {
                var planeWorldPosition = new THREE.Vector3();
                plane.getWorldPosition(planeWorldPosition);

                var planeScreenPosition = planeWorldPosition.clone();
                planeScreenPosition.project(camera);

                tag.style.left = ((planeScreenPosition.x + 1) / 2) * window.innerWidth + 'px';
                tag.style.top = ((-planeScreenPosition.y + 1) / 2) * window.innerHeight + 'px';
            }
        }
    }

}


var randomGroup = groups[projectName]
createStacksOfPlanes(randomGroup);

/// Calculate the maximum and minimum heights so that the mopdel is always centered on the screen
var boundingBox = new THREE.Box3();
boundingBox.setFromObject(scene);
var minHeight = boundingBox.min.y;
var maxHeight = boundingBox.max.y;


// Calculate the center height
var centerHeight = (minHeight + maxHeight) / 2;
// console.log(boundingBox.setFromObject(scene));

// Adjust the position of the object to center it vertically
scene.position.y -= centerHeight + 0.2;

animate();
window.addEventListener('resize', onWindowResize);



