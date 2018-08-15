#Author-Autodesk Inc.
#Description-Demo command input examples
import adsk.core, adsk.fusion, traceback
import xml.etree.cElementTree as etree
import xml.dom.minidom # for prettying it....
import inspect
import logging
import re
import os , sys


_app = None
_ui  = None
_design = None
_rowNumber = 0
_linknum = 0
_linkname = 'link' + str(_linknum)

# Global set of event handlers to keep them referenced for the duration of the command
_handlers = []

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

class Link:
    def __init__(self,occname):
        parent = '' ### incorrect, we need to parse the fullPathName, which should be the way to instantiate this as well!
        #### actually, since i've changed this structure so much, now is not the time to try to set this things correctly...
        level = 0
        self.inertial = Inertial()
        self.visual = Visual()
        self.collision = Collision();
        self.level = level
        self.name = parent+ occname;
        self.visual.geometryfilename = ""
        self.collision.geometryfilename = ""
        self.group = []
    def __groupmembers(self,rigidgrouplist):
        self.group = rigidgrouplist.getgroupmemberships(self.name)
        return rigidgrouplist.getwholegroup(self.name)
        
    def makelinkxml(self, urdfroot):
        self.visual.geometryfilename = "package://somepackage/meshes/" + clearupst(self.name) +".stl"

        link = etree.SubElement(urdfroot, "link", name= clearupst(self.name))
        
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
        

    def save_to_stl3(self, meshes_directory):
        didifail = 0        
        
        try:            
            # Get the root component of the active design
            rootComp = _design.rootComponent
    
            # Create two new components under root component
            allOccs = rootComp.allOccurrences                    
            
            # create a single exportManager instance
            exportMgr = _design.exportManager
            
            #### add occurrances from other stuff to this new stuff
            for i in range(0,len(self.group)):
                #express = 'it'+str(i)+ '=self.group[i].transform.copy()'
                pathsplit = self.group[i].fullPathName.split('+')                

                newrotl = []
                for j in range(1,len(pathsplit)):                 
                    thisoccnamelist = pathsplit[0:j]
                    thisoccname = thisoccnamelist[0]
                    for k in range(1,len(thisoccnamelist)):
                        thisoccname = thisoccname + '+' + thisoccnamelist[k]
                    logging.info('getting the tm for:'+thisoccname)
                    for l in range(0,allOccs.count):
                        if allOccs.item(l).fullPathName == thisoccname:
                            #then i want to multiply their matrices!
                            lasttm = allOccs.item(l).transform.copy()
                            newrotl.append(lasttm)
                            logging.debug(allOccs.item(l).fullPathName)
                            logging.debug('with tm:' + str(lasttm.asArray()))
                            #newrot.transformBy(allOccs.item(l).transform)
                    ### now that i have all the occurrences names i need to get them from allOccs(?!)
                newrotl.append(self.group[i].transform.copy())
                newrot = adsk.core.Matrix3D.create()
                newrot.setToIdentity()
                for j in reversed(range(0,len(newrotl))):
                    newrot.transformBy(newrotl[j])
                express = 'it'+str(i)+ '=newrot'
                exec(express)
            
            
            #stlname = rootComp.name.translate(None, ':!@#$')
            #line = re.sub('[!@#$]', '', line)
            stlname = clearupst(self.name)
            
            fileName = meshes_directory+'/' + stlname
            for i in range(0,len(self.group)):
                # export the root component to printer utility
                fileName = meshes_directory+'/' + stlname+str(i)
                logging.info('saving file '+fileName )
                logging.info('from occurrence' + self.group[i].fullPathName)
                
                logging.debug('with tm:' + str(eval('it'+str(i)+'.asArray()')))
                stpOptions = exportMgr.createSTEPExportOptions(fileName, self.group[i].component)           
                exportMgr.execute(stpOptions)
                
            # Create a document.
            doc = _app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
            
            product = _app.activeProduct
            design = adsk.fusion.Design.cast(product)
            
            # Get the root component of the active design
            rootComp = design.rootComponent
    
            # Create two new components under root component
            allOccs = rootComp.occurrences   
            
            # Get import manager
            importManager = _app.importManager            
            
            #### add occurrances from other stuff to this new stuff
            for i in range(0,len(self.group)):
                fileName = meshes_directory+'/' + stlname+str(i)+'.stp'
                logging.info('loading file: '+fileName)
                stpOptions = importManager.createSTEPImportOptions(fileName)
                importManager.importToTarget(stpOptions, rootComp)
            for i in range(0,len(rootComp.occurrences)):
                rootComp.occurrences.item(i).transform = eval('it'+str(i))
                pass
            
            self.visual.geometryfilename = "package://somepackage/meshes/" + stlname +".stl"
            self.collision.geometryfilename = self.visual.geometryfilename # the legend has it that this file should be a slimmer version of the visuals, so that collisions can be calculated more easily....       
    
        except:
            logging.debug('could not save stl. {}'.format(traceback.format_exc()))
            didifail = 1
        return didifail
        
class Joint:
    # jointdefs = Joint(actualjoint, actualjointname,parentl,childl, currentLevel,parent);
    def __init__(self,joint,jointname,parentl,childl,level,parent):
        self.origin = OrVec()
        self.parentlinkrealname = parentl
        self.childlinkrealname = childl
        self.parentlink = clearupst(self.parentlinkrealname)
        self.childlink = clearupst(self.childlinkrealname)
        self.axis = '0 0 0'
        self.limit = Limit()
        self.level = level
        self.name = jointname
        superprint(self.level, 'joint: my name is:' + self.name)
        superprint(self.level, 'my parent link is' + self.parentlink)
        superprint(self.level, 'my child link is' + self.childlink)
        logging.debug( inspect.stack())
        #python doesnt have a switch statement, i repeat python does not have a switch statement...
        #from the docs, we should implement this:
        #Name     Value     Description
        #BallJointType     6     Specifies a ball type of joint.
        #CylindricalJointType     3     Specifies a cylindrical type of joint.
        #PinSlotJointType     4     Specifies a pin-slot type of joint.
        #PlanarJointType     5     Specifies a planar type of joint.
        #RevoluteJointType     1     Specifies a revolute type of joint.
        #RigidJointType     0     Specifies a rigid type of joint.
        #SliderJointType     2     Specifies a slider type of joint.
        if joint.jointMotion.jointType is 1:
            self.type = "revolute"
            self.axis = str(joint.jointMotion.rotationAxisVector.x)+ ' ' + str(joint.jointMotion.rotationAxisVector.y)+ ' ' + str(joint.jointMotion.rotationAxisVector.z)
        if joint.jointMotion.jointType is 0:
            self.type = "fixed"

        if 'rotationLimits' in dir(joint.jointMotion):
            if joint.jointMotion.rotationLimits.isMinimumValueEnabled:
                self.limit.lower = joint.jointMotion.rotationLimits.minimumValue
            if joint.jointMotion.rotationLimits.isMaximumValueEnabled:
                self.limit.upper = joint.jointMotion.rotationLimits.maximumValue

    def updatename(self):
        self.parentlink = clearupst(self.parentlinkrealname)
        self.childlink = clearupst(self.childlinkrealname)

    def makejointxml(self, urdfroot):

        joint = etree.SubElement(urdfroot, "joint", name= clearupst(self.name), type = self.type)
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
        
def superprint(level,stringo):
    #logger = logging.getLogger(__name__)
    #logger.debug(spaces(level*5)+stringo)
    logging.debug(spaces(level*5)+stringo)


def clearupst(stringo):
    strstr1 = re.sub('[:!@#$.()/-]', '',stringo)
    strstr2 = re.sub(' ', '_',strstr1)
    return strstr2

# Returns a string containing the especified number of spaces.
def spaces(spaceCount):
    result = ''
    for i in range(0, spaceCount):
        result += ' '

    return result


# Event handler that reacts to any changes the user makes to any of the command inputs.
class AddLinkCommandInputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            eventArgs = adsk.core.InputChangedEventArgs.cast(args)
            inputs = eventArgs.inputs
            cmdInput = eventArgs.input
            
            linkInput = inputs.itemById('linkname')
            linkselInput = inputs.itemById('linkselection') 
            if cmdInput.id == 'linkname':
                currentlink.name = linkInput.value
            elif cmdInput.id == 'linkselection':
                #### wait, i think i can export a selection! so...
                currentlink.group = []
                for i in range(0, linkselInput.selectionCount):
                    if linkselInput.selection(i).entity not in currentlink.group:
                        currentlink.group.append( linkselInput.selection(i).entity)
                        #logging.debug(dir(linkselInput.selection(i).entity))
            ## if i ever get to use inputs
#            tableInput = inputs.itemById('table')
#            if cmdInput.id == 'tableAdd':
#                addRowToTable(tableInput)
#            elif cmdInput.id == 'tableDelete':
#                if tableInput.selectedRow == -1:
#                    _ui.messageBox('Select one row to delete.')
#                else:
#                    tableInput.deleteRow(tableInput.selectedRow)
          
        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Event handler that reacts to when the command is destroyed. This terminates the script.            
class AddLinkCommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            # When the command is done, terminate the script
            # This will release all globals which will remove all event handlers
            for handler in logging.root.handlers[:]:
                handler.close()
                logging.root.removeHandler(handler)
            
            adsk.terminate()
        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class AddLinkCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            #eventArgs = adsk.core.CommandEventArgs.cast(args)    
            #inputs = eventArgs.inputs
            #cmdInput = eventArgs.input
    
            
            urdfroot = etree.Element("robot", name = "gummi")
            
            currentlink.save_to_stl3(meshes_directory)
            #currentlink.name = linkInput.value
            currentlink.makelinkxml(urdfroot)            
            
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
    
            # Code to react to the event.
            #_ui.messageBox('In MyExecuteHandler event handler.')
        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
        
# Event handler that reacts when the command definitio is executed which
# results in the command being created and this event being fired.
class AddLinkCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            # Get the command that was created.
            cmd = adsk.core.Command.cast(args.command)

            # Connect to the command destroyed event.
            onDestroy = AddLinkCommandDestroyHandler()
            cmd.destroy.add(onDestroy)
            _handlers.append(onDestroy)

            # Connect to the input changed event.           
            onInputChanged = AddLinkCommandInputChangedHandler()
            cmd.inputChanged.add(onInputChanged)
            _handlers.append(onInputChanged)    

            onExecute = AddLinkCommandExecuteHandler()
            cmd.execute.add(onExecute)
            _handlers.append(onExecute)

            # Get the CommandInputs collection associated with the command.
            inputs = cmd.commandInputs

            # Create a tab input.
            tabCmdInput3 = inputs.addTabCommandInput('tab_1', 'Add Link')
            tab3ChildInputs = tabCmdInput3.children
            
            # Create a read only textbox input.
            #tab1ChildInputs.addTextBoxCommandInput('readonly_textBox', 'URDF TREE', 'this would be the tree', 10, True)

          
            # Create a message that spans the entire width of the dialog by leaving out the "name" argument.
            message = '<div align="center">A "full width" message using <a href="http:fusion360.autodesk.com">html.</a></div>'
            tab3ChildInputs.addTextBoxCommandInput('fullWidth_textBox', '', message, 1, True)            

            
            # Create a selection input.
            selectionInput1 = tab3ChildInputs.addSelectionInput('linkselection', 'Select Link Components', 'Basic select command input')
            selectionInput1.addSelectionFilter('Occurrences')
            selectionInput1.setSelectionLimits(0)

            # Create a string value input.
            strInput = tab3ChildInputs.addStringValueInput('linkname', 'Name of link', _linkname)


        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


currentlink = Link(_linkname)
base_directory = "c:/test_gummi_urdf2"
if not os.path.exists(base_directory):
    os.makedirs(base_directory)
meshes_directory = base_directory + "/meshes"
if not os.path.exists(meshes_directory):
    os.makedirs(meshes_directory)    


def run(context):
    try:
        global _app, _ui, _design
        _app = adsk.core.Application.get()
        _ui = _app.userInterface
        product = _app.activeProduct
        _design = adsk.fusion.Design.cast(product)
        
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        logging.basicConfig(filename=os.path.join(base_directory,'urdfgen.log'),level=logging.DEBUG)

        # Get the existing command definition or create it if it doesn't already exist.
        addlinkcmdDef = _ui.commandDefinitions.itemById('cmdInputsAddLink')
        if not addlinkcmdDef:
            addlinkcmdDef = _ui.commandDefinitions.addButtonDefinition('cmdInputsAddLink', 'Add Link', 'My attempt to add a link.')

        # Connect to the command created event.
        onCommandCreated = AddLinkCommandCreatedHandler()
        addlinkcmdDef.commandCreated.add(onCommandCreated)
        _handlers.append(onCommandCreated)
               
        # Execute the command definition.
        addlinkcmdDef.execute()
        
        # Prevent this module from being terminated when the script returns, because we are waiting for event handlers to fire.
        adsk.autoTerminate(False)
        
    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))