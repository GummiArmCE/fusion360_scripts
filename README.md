# fusion360_scripts

Scripts that utilise the Fusion 360 API: URDF generation, and open-source CAD-file version control.


##URDF Generator:

You need to load it as an Add-in and set it to run. It runs in Fusion as a new command, so it needs to be done this way.

### TODO list:

- fix selections when people are putting joints after doing a link
- making more timely updates to the debug panel (which also shouldn't be called a debug panel anymore i believe..)
- check if generated model is correct in rviz
- add masses and moments of inertia to model (currently i only read them and write them down to debug)
- add other package files to make it functional
- generate also srdf

### Planned features list

- add more controls to interface allow for checking the generated urdf
- add button to load generate urdf with fusion and the ability to run it from a single click
- streamline the whole create link thing (it is maybe a bit too much clinking right now)
- try to go over all joints and make them visible and clickable
- ???