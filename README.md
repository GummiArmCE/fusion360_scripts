# fusion360_scripts

Scripts that utilise the Fusion 360 API: URDF generation, and open-source CAD-file version control.


## URDF Generator:

You need to load it as an Add-in and set it to run. It runs in Fusion as a new command, so it needs to be done this way.

### TODO list:

- generated model is rotated to the side since the axis from fusion and rviz are different. have to fix this to make these models usable
- add masses and moments of inertia to model (currently i only read them and write them down to debug)
- generate also srdf

### Planned features list

- add more controls to interface allow for checking the generated urdf
- add button to load generate urdf with fusion and the ability to run it from a single click
- streamline the whole create link thing (it is maybe a bit too much clinking right now)
- try to go over all joints and make them visible and clickable
- ???
