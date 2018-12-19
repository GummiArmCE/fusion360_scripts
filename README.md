# fusion360_scripts

Scripts that utilise the Fusion 360 API: URDF generation, and open-source CAD-file version control.


## URDF Generator:

You need to load it as an Add-in and set it to run. It runs in Fusion as a new command, so it needs to be done this way.

The sequence to create the urdf is: 

1 - add links or joints from button

2 - press the select button to start working with that element. This will update the selection tool to either the joint or occurrences. 

3 - press the selection button to select either one or more occurrences (when building a link) or one joint (when building a joint)

4 - for joints you also need to set up parent and child, which should already be on the table (or they won't show up in the droplist)

5 - review what you did by clicking on the "Select" button again on the element you've just created. The information about it should change to:

In case it is a link:

    current element: XXXX <- your linkname 
    List of assembly elements that this link contains <- this is the group 
    .... 
 
    List of links/joints already present in urdftree. 
    ....
 
 
In case it is a joint:

    current element: YYYY <- your jointname 
    genjn: WWWW <- the name of the joint from the assembly that lends its properties to the URDF joint we will create 
    parent: XXXX   child: ZZZZ <- the names of the links who are parent and child references for that joint, respectively 

    List of links/joints already present in urdftree. 
    ....
 
 
6 - Finally, before clicking OK, you need to run "Create Tree". This will parse all elements (joints and links), to check whether you have actually build a linkage tree (at this moment it only checks for disconnected elements and links with empty groups, but that's the idea anyway).

When all of this is done and you are satisfied with your results, click OK. This will create new documents for each link you created (they should be centred and all put together nicely), create a new directory where you set it to be created, with the name that you defined (the default is mypackage) on the interface and set-up a pretty basic ros package definition. 

If you have rviz installed, you can use the display.launch file provided and see what you have done with:

    roslaunch mypackage display.launch
    
This will start rviz and robot and joint state publisher so you can move it around. 

A sample of a created urdf using this add-in is available in the mypackage folder. 

### Caveats:

You may need to change documents dimensions to cm to run it properly. I believe this was fixed, but until I have confirmation the warning will stay here.


### TODO list:

- addin functionality is not being used properly. It currently cannot be loaded at startup and is working like a script (needs to be fixed before we make a release version)
- add button to launch command from toolbar
- add masses and moments of inertia to model (currently i only read them and write them down to debug)
- add prismatic joints
- add control to change joint types
- add control to change link origins (solidworks plugin allows this, but is it even necessary?)

### Planned features list

- generate also srdf
- update joint visibility when command starts
- add a control to change the colour of the link and maybe add a texture (rviz supports this, so no reason why I shouldn't either)
- add mimic joints 
- add the ability to save progress halfway: currently I don't know how to do this. Pickle does not save swig objects, and I do have the .groups property in links (and maybe something in joints as well), so I can't really save it completely. Perhaps I should clear this property and have a method to set it by name. 
