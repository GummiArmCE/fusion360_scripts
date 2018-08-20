# fusion360_scripts

Scripts that utilise the Fusion 360 API: URDF generation, and open-source CAD-file version control.


## URDF Generator:

You need to load it as an Add-in and set it to run. It runs in Fusion as a new command, so it needs to be done this way.

The sequence to create the urdf is still a bit lenghty, first you create a new element, then define it as either link or joint, press create to instantiate the object and select to work on it. Then select either one or more occurrences to create an urdf link or a joint to create an urdf joint. Finally, to set the joint properly, you need to select its father and child links, which should be done after both of those links are instantiated. 

Finally, before clicking OK, you need to run "Create Tree". This will parse all elements (joints and links), to check whether you have actually build a linkage tree (at this moment it only checks for disconnected elements, but that's the idea anyway)

### Caveats:

You may need to change documents dimensions to cm to run it properly. I haven't checked it yet, just making sure, if you are using this code right now, that you can get something you can still view in rviz



### TODO list:


- generated model is rotated to the side since the axis from fusion and rviz are different. have to fix this to make these models usable
- add masses and moments of inertia to model (currently i only read them and write them down to debug)
- generate also srdf

### Planned features list

- add more controls to interface allow for checking the generated urdf
- add button to load generate urdf with fusion and the ability to run it from a single click
- streamline the whole create link thing (it is maybe a bit too much clinking right now)
- try to go over all joints and make them visible and clickable

- add a control to change the colour of the link and maybe add a texture (rviz supports this, so no reason why I shouldn't either)
- add mimic joints (it is rather useful for making pretty urdfs, although, this is probably a bit too much to ask of my code, since its interface is not great and currently I don't know how to save progress half-way through, putting too many things that can go wrong is perhaps not the best idea)
- add the ability to save progress halfway: currently I don't know how to do this. Pickle does not save swig objects, and I do have the .groups property in links (and maybe something in joints as well), so I can't really save it completely. Perhaps I should clear this property and have a method to set it by name. For links this is doable, but for joints it is a bit trickier. 


- ???
