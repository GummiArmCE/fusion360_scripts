#Author-frederico
#Description-

import adsk.core, adsk.fusion, traceback
import os #, sys
import re
import xml.etree.cElementTree as etree 
import xml.dom.minidom # for prettying it....

def save_to_stl(design, rootComp, meshes_dir):
    
    # create a single exportManager instance
    exportMgr = design.exportManager
    
    #stlname = rootComp.name.translate(None, ':!@#$')  
    #line = re.sub('[!@#$]', '', line)
    stlname = clearupst(rootComp.name)        
    
    # export the root component to printer utility
    stlRootOptions = exportMgr.createSTLExportOptions(rootComp,  meshes_dir+'/' + stlname)

    # get all available print utilities
    #printUtils = stlRootOptions.availablePrintUtilities
    
    # export the root component to the print utility, instead of a specified file            
    #for printUtil in printUtils:
    #    stlRootOptions.sendToPrintUtility = True
    #   stlRootOptions.printUtility = printUtil
    stlRootOptions.sendToPrintUtility = False
    
    exportMgr.execute(stlRootOptions)
        
        
    return 

class Link:
    def __init__(self,occ):
        self.name = ''
        self.inertial = Inertial()
        self.visual = Visual()
        self.collision = Collision();
        
        self.name = clearupst(occ.name);
        self.visual.geometryfilename = "package://somepackage/meshes/" + self.name +".stl"
        self.collision.geometryfilename = self.visual.geometryfilename # the legend has it that this file should be a slimmer version of the visuals, so that collisions can be calculated more easily.... 
        
    def makelinkxml(self, urdfroot):
    
        link = etree.SubElement(urdfroot, "link", name= self.name)

        inertial = etree.SubElement(link, "inertial")
        etree.SubElement(inertial, "origin", xyz = self.inertial.origin.xyz, rpy = self.inertial.origin.rpy  )
        etree.SubElement(inertial, "mass", value = self.inertial.mass)      
        etree.SubElement(inertial, "inertia", ixx= self.inertial.inertia.ixx, ixy= self.inertial.inertia.ixy, ixz= self.inertial.inertia.ixz, iyy= self.inertial.inertia.iyy, iyz= self.inertial.inertia.iyz, izz= self.inertial.inertia.izz )
        
        visual = etree.SubElement(link, "visual")        
        etree.SubElement(visual, "origin", xyz = self.visual.origin.xyz, rpy = self.visual.origin.rpy  )  
        geometry = etree.SubElement(visual, "geometry")
        etree.SubElement(geometry, "mesh", filename = self.visual.geometryfilename)
        material = etree.SubElement(visual, "material", name = self.visual.materialname)
        etree.SubElement(material, "color", rgba = self.visual.color)
        
        collision = etree.SubElement(link, "collision")        
        etree.SubElement(collision, "origin", xyz = self.collision.origin.xyz, rpy = self.collision.origin.rpy  )  
        geometry = etree.SubElement(collision, "geometry")
        etree.SubElement(geometry, "mesh", filename = self.visual.geometryfilename)
        #origin = etree.SubElement(inertial, "origin")
        #etree.SubElement(origin, "xyz").text = self.inertial.origin.xyz
        #etree.SubElement(origin, "rpy").text = self.inertial.origin.rpy
        
        return urdfroot

class Inertial:
    def __init__(self):
        self.origin = OrVec()
        self.mass = '0'
        self.inertia = Inertia()
        
class Inertia:
    def __init__(self):
        self.ixx = '0'
        self.ixy = '0'
        self.ixz = '0'
        self.iyy = '0'
        self.iyz = '0'
        self.izz = '0'
        
class OrVec:
    def __init__(self):
        self.xyz = '0 0 0'
        self.rpy = '0 0 0'
   
class Visual:
    def __init__(self):
        self.origin = OrVec()
        self.geometryfilename = ""
        self.materialname = ""
        self.color = '0 0 0 1'
        
class Collision:
    def __init__(self):
        self.origin = OrVec()
        self.geometryfilename = ""
        
class Joint:
    def __init__(self,joint):
        self.origin = OrVec()       
        self.parentlink = ''
        self.childlink = ''
        self.axis = '0 0 0'
        self.limit = Limit()
        
        self.name = joint.name
        #python doesnt have a switch statement, i repeat python does not have a switch statement...
        #from the docs, we should implement this:
        #Name 	Value 	Description
        #BallJointType 	6 	Specifies a ball type of joint.
        #CylindricalJointType 	3 	Specifies a cylindrical type of joint.
        #PinSlotJointType 	4 	Specifies a pin-slot type of joint.
        #PlanarJointType 	5 	Specifies a planar type of joint.
        #RevoluteJointType 	1 	Specifies a revolute type of joint.
        #RigidJointType 	0 	Specifies a rigid type of joint.
        #SliderJointType 	2 	Specifies a slider type of joint.
        if joint.jointMotion.jointType is 1:
            self.type = "revolute"
            self.axis = str(joint.jointMotion.rotationAxisVector.x)+ ' ' + str(joint.jointMotion.rotationAxisVector.y)+ ' ' + str(joint.jointMotion.rotationAxisVector.z)
        if joint.jointMotion.jointType is 0:
            self.type = "fixed"
        
        if joint.jointMotion.rotationLimits.isMinimumValueEnabled:
            self.limit.lower = joint.jointMotion.rotationLimits.minimumValue
            
        if joint.jointMotion.rotationLimits.isMaximumValueEnabled:
            self.limit.upper = joint.jointMotion.rotationLimits.maximumValue
        
        
    
    def makejointxml(self, urdfroot):
    
        joint = etree.SubElement(urdfroot, "joint", name= self.name, type = self.type)
        etree.SubElement(joint, "origin", xyz = self.origin.xyz, rpy = self.origin.rpy)
        etree.SubElement(joint, "parent", link = self.parentlink)        
        etree.SubElement(joint, "child", link = self.childlink)        
        etree.SubElement(joint, "axis", xyz = self.axis)
        etree.SubElement(joint, "limit", lower = self.limit.lower, upper = self.limit.upper, effort=self.limit.effort, velocity = self.limit.velocity)
        #origin = etree.SubElement(inertial, "origin")
        #etree.SubElement(origin, "xyz").text = self.inertial.origin.xyz
        #etree.SubElement(origin, "rpy").text = self.inertial.origin.rpy
        
        return urdfroot
        
class Limit:
    def __init__(self):
        self.lower = '-1'
        self.upper = '1'
        self.effort = '0'
        self.velocity = '0'
        
# Performs a recursive traversal of an entire assembly structure.
def traverseAssembly(design, urdfroot, occurrences, currentLevel, inputString, meshes_dir):
    occurancelist = []; # to make sure i will only place joints when i can.
    for i in range(0, occurrences.count):
        occ = occurrences.item(i)
        curritemname = clearupst(occ.name)
        if occ.name not in occurancelist:
            occurancelist.append( curritemname)
        
        linkdefs = Link(occ)
        #set the rest of the link properties
        #....
        
        urdfroot = linkdefs.makelinkxml(urdfroot)
        
        for j in range(0, occ.joints.count):
            if occ.joints.item(j).occurrenceOne is None or occ.joints.item(j).occurrenceTwo is None:
                #joint to nothingness????                
                
                jointdefs = Joint(occ.joints.item(j));
                jointdefs.parentlink = curritemname
                jointdefs.childlink = 'nothingness?????'
                urdfroot = jointdefs.makejointxml(urdfroot)
            else: 
                if clearupst(occ.joints.item(j).occurrenceOne.name) in occurancelist and clearupst(occ.joints.item(j).occurrenceTwo.name) in occurancelist :
                    
                    jointdefs = Joint(occ.joints.item(j));
                    jointdefs.name = clearupst(occ.joints.item(j).name)
                    jointdefs.parentlink = clearupst(occ.joints.item(j).occurrenceOne.name)
                    jointdefs.childlink =  clearupst(occ.joints.item(j).occurrenceTwo.name)
                    #update the values from jointdefs from a360 variable and stuff
                    urdfroot = jointdefs.makejointxml(urdfroot)
            
                
                    
            # I am assuming you can only have a joint between 2 objects. also reinventing the wheel here, joint might have a property telling who it links to...    
            #etree.SubElement(urdfroot, "joint" + str(j), name="joint"+ str(j)).text = occ.joints.item(j).name

                      
        save_to_stl(design, occ, meshes_dir)
        
        if occ.childOccurrences:
            urdfroot = traverseAssembly(occ.childOccurrences, urdfroot, currentLevel + 1, inputString, meshes_dir)
  


    return urdfroot
    
 
def clearupst(stringo):
    strstr = re.sub('[:!@#$]', '',stringo)
    strstr = re.sub(' ', '_',strstr)
    return strstr

# Returns a string containing the especified number of spaces.
def spaces(spaceCount):
    result = ''
    for i in range(0, spaceCount):
        result += ' '

    return result

def run(context):
    ui = None
    try:
        base_directory = "c:/test_gummi_urdf"
        if not os.path.exists(base_directory):
            os.makedirs(base_directory)
        meshes_directory = "c:/test_gummi_urdf/meshes"
        if not os.path.exists(meshes_directory):
            os.makedirs(meshes_directory)           
                    
            
        app = adsk.core.Application.get()
        ui  = app.userInterface
        
        product = app.activeProduct
        design = adsk.fusion.Design.cast(product)
        if not design:
            ui.messageBox('No active Fusion design', 'No Design')
            return

        # Get the root component of the active design.
        rootComp = design.rootComponent
        
        # Create the title for the output.
        resultString = 'Assembly structure of ' + design.parentDocument.name + '\n'
        
        urdfroot = etree.Element("robot", name = "gummi")        
     
        
        # Call the recursive function to traverse the assembly and build the output string.
        urdfroot = traverseAssembly(design,urdfroot, rootComp.occurrences.asList, 1, resultString, meshes_directory)
              
        tree = etree.ElementTree(urdfroot)     
        root = tree.getroot()
        treestring = etree.tostring(root)
        #treestring = str(root)
        
        #ui.messageBox(treestring)
        xmldomtype = xml.dom.minidom.parseString(treestring)
        pretty_xml_as_string = xmldomtype.toprettyxml()
        #prettytree = etree();
        #prettytree = etree.fromstring(pretty_xml_as_string)
        #prettytree.write("c:/test/robot.urdf")
        
        with open(base_directory +"/robot.urdf", "w") as text_file:
            print(pretty_xml_as_string, file=text_file)        
        
        
        ui.messageBox(resultString)
       
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))